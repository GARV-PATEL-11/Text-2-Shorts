#!/usr/bin/env python3
"""layout_probe.py — deterministic layout QA for a Manim scene (no LLM, no video encode).

Runs the scene with Manim's dry_run (no frames written), and after every play()/wait()
snapshots the bounding box of each top-level visible mobject. Reports:
  OUT_OF_FRAME   a mobject extends past the safe frame (current camera frame minus margin);
                 while the camera is zoomed only text leaves are checked (shape cropping is intended)
  OVERLAP        two text/math-bearing mobjects overlap by more than a threshold
  TINY_TEXT      a Text/MathTex rendered below a minimum on-screen height
  EVENT_TIMELINE cumulative time of each event
  CLIP_TIMING    measured duration of every clip_NN() method vs its narration budget
                 (--budget clip_01=6.2,clip_02=8.0 --tolerance 0.5)

This replaces most of the "look at PNG frames" work the current render agent does with an
LLM; frame inspection is kept only for what geometry cannot judge (aesthetics, meaning).

Usage: python tools/layout_probe.py scene.py Scene003 [--margin 0.3] [--json]
Status: IMPLEMENTED in this package (tested against manim==0.20.1, Cairo renderer).
"""
from __future__ import annotations
import argparse, importlib.util, json, sys
from pathlib import Path

TEXTY = ("Text", "MathTex", "Tex", "MarkupText", "Paragraph", "DecimalNumber", "Integer")

def bbox(m):
    import numpy as np
    pts = m.get_all_points() if hasattr(m, "get_all_points") else None
    if pts is None or len(pts) == 0:
        return None
    return float(np.min(pts[:, 0])), float(np.min(pts[:, 1])), float(np.max(pts[:, 0])), float(np.max(pts[:, 1]))

def is_texty(m):
    if type(m).__name__ in TEXTY:
        return True
    return any(type(s).__name__ in TEXTY for s in m.submobjects[:50]) if hasattr(m, "submobjects") else False

def text_leaves(m):
    """Text-like leaves of a mobject tree. Comparing group bounding boxes gives false overlaps
    (axis labels at opposite ends of the axes form one huge box), so overlap is judged per leaf."""
    if type(m).__name__ in TEXTY:
        return [m]
    out = []
    for sub in getattr(m, "submobjects", []):
        out.extend(text_leaves(sub))
    return out

def visible(m):
    """Max fill/stroke opacity over the mobject family. Container mobjects (MathTex, VGroup)
    report 0 opacity themselves even when their glyphs are fully visible."""
    fam = m.family_members_with_points() if hasattr(m, "family_members_with_points") else [m]
    return max([max(s.get_fill_opacity(), s.get_stroke_opacity()) for s in fam] or [0.0])

def inter(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0]); h = min(a[3], b[3]) - max(a[1], b[1])
    return max(0.0, w) * max(0.0, h)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file"); ap.add_argument("cls")
    ap.add_argument("--margin", type=float, default=0.3)
    ap.add_argument("--overlap-ratio", type=float, default=0.15, help="fraction of the smaller box")
    ap.add_argument("--min-text-height", type=float, default=0.18)
    ap.add_argument("--budget", help="clip_01=6.2,clip_02=8.0 (seconds of narration per clip)")
    ap.add_argument("--tolerance", type=float, default=0.5, help="allowed |video-audio| seconds per clip")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    from manim import config, Scene
    config.dry_run = True
    config.disable_caching = True
    config.verbosity = "ERROR"
    fw, fh = config.frame_width / 2 - a.margin, config.frame_height / 2 - a.margin

    findings, timeline, t = [], [], 0.0
    orig_play = Scene.play

    def snapshot(scene, label):
        frame = getattr(scene.camera, "frame", None)  # MovingCameraScene: bounds follow the camera frame
        if frame is not None:
            cx, cy = frame.get_center()[:2]
            hx, hy = frame.width / 2 - a.margin * frame.width / config.frame_width, frame.height / 2 - a.margin * frame.height / config.frame_height
        else:
            cx, cy, hx, hy = 0.0, 0.0, fw, fh
        mobs = [m for m in scene.mobjects if m is not frame and bbox(m)]
        zoomed = frame is not None and abs(frame.width - config.frame_width) > 1e-3
        # Zoomed-in camera: cropping shapes is intentional, cropped TEXT is still a defect.
        check = [leaf for m in mobs for leaf in text_leaves(m)] if zoomed else mobs
        for m in check:
            b = bbox(m); name = type(m).__name__
            if b[0] < cx - hx or b[2] > cx + hx or b[1] < cy - hy or b[3] > cy + hy:
                findings.append({"severity": "ERROR", "code": "OUT_OF_FRAME", "t": round(t, 2), "event": label,
                                 "mobject": name, "bbox": [round(x, 2) for x in b]})
            if type(m).__name__ in TEXTY and (b[3] - b[1]) < a.min_text_height and visible(m) > 0.05:
                findings.append({"severity": "WARN", "code": "TINY_TEXT", "t": round(t, 2), "event": label, "mobject": name})
        texty = [leaf for m in mobs for leaf in text_leaves(m) if visible(leaf) > 0.05]
        for i in range(len(texty)):
            for j in range(i + 1, len(texty)):
                b1, b2 = bbox(texty[i]), bbox(texty[j])
                smaller = min((b1[2]-b1[0])*(b1[3]-b1[1]), (b2[2]-b2[0])*(b2[3]-b2[1])) or 1e-9
                if inter(b1, b2) / smaller > a.overlap_ratio:
                    findings.append({"severity": "ERROR", "code": "OVERLAP", "t": round(t, 2), "event": label,
                                     "mobjects": [type(texty[i]).__name__, type(texty[j]).__name__]})

    def play(self, *args, **kw):
        nonlocal t
        r = orig_play(self, *args, **kw)
        t = float(getattr(self.renderer, "time", t))
        label = "play(" + ",".join(type(x).__name__ for x in args)[:80] + ")"
        timeline.append({"t_end": round(self.renderer.time, 3), "event": label})
        snapshot(self, label)
        return r

    # Scene.wait() is implemented as play(Wait(...)) in Manim CE, so patching play() covers both.
    Scene.play = play
    spec = importlib.util.spec_from_file_location("clip_under_test", a.file)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    cls = getattr(mod, a.cls)
    clip_spans: dict[str, list[float]] = {}
    import re as _re
    for name in [n for n in dir(cls) if _re.fullmatch(r"clip_\d+", n)]:
        fn = getattr(cls, name)
        def wrapped(self, *args, _fn=fn, _name=name, **kw):
            start = float(getattr(self.renderer, "time", 0.0))
            r = _fn(self, *args, **kw)
            clip_spans[_name] = [round(start, 3), round(float(getattr(self.renderer, "time", 0.0)), 3)]
            return r
        setattr(cls, name, wrapped)
    cls().render()

    budget = dict((k, float(v)) for k, v in (x.split("=") for x in a.budget.split(","))) if a.budget else {}
    clips = []
    for name, (s0, s1) in sorted(clip_spans.items()):
        d = round(s1 - s0, 3); entry = {"clip": name, "start": s0, "end": s1, "duration": d}
        if name in budget:
            entry["budget"] = budget[name]; entry["delta"] = round(d - budget[name], 3)
            if d + a.tolerance < budget[name]:
                findings.append({"severity": "ERROR", "code": "CLIP_TOO_SHORT", "t": s1, "event": name,
                                 "mobject": f"{d}s < narration {budget[name]}s"})
            elif d - budget[name] > max(a.tolerance, 1.5):
                findings.append({"severity": "WARN", "code": "CLIP_TOO_LONG", "t": s1, "event": name,
                                 "mobject": f"{d}s > narration {budget[name]}s"})
        clips.append(entry)
    for missing in sorted(set(budget) - set(clip_spans)):
        findings.append({"severity": "ERROR", "code": "CLIP_NOT_RUN", "t": 0, "event": missing, "mobject": "method never executed"})

    out = {"duration_s": timeline[-1]["t_end"] if timeline else 0.0, "clips": clips, "events": timeline, "findings": findings}
    if a.json:
        print(json.dumps(out, indent=1))
    else:
        print(f"duration {out['duration_s']}s · {len(timeline)} events")
        for c in clips:
            print(f"  {c['clip']}: {c['start']}→{c['end']} ({c['duration']}s){'  budget ' + str(c['budget']) if 'budget' in c else ''}")
        for f in findings:
            print(f"{f['severity']:5} {f['code']:13} t={f['t']:<6} {f.get('mobject') or f.get('mobjects')} @ {f['event']}")
    sys.exit(1 if any(f["severity"] == "ERROR" for f in findings) else 0)

if __name__ == "__main__":
    main()
