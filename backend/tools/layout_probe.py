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

Usage: python backend/tools/layout_probe.py scene.py Scene003 [--margin 0.3] [--json]
Status: IMPLEMENTED in this package (tested against manim==0.20.1, Cairo renderer).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

TEXT_CLASS_NAMES = ("Text", "MathTex", "Tex", "MarkupText", "Paragraph", "DecimalNumber", "Integer")


def bounding_box(mobject):
    import numpy as np

    points = mobject.get_all_points() if hasattr(mobject, "get_all_points") else None
    if points is None or len(points) == 0:
        return None
    return (
        float(np.min(points[:, 0])),
        float(np.min(points[:, 1])),
        float(np.max(points[:, 0])),
        float(np.max(points[:, 1])),
    )


def is_text_like(mobject):
    if type(mobject).__name__ in TEXT_CLASS_NAMES:
        return True
    return (
        any(type(submobject).__name__ in TEXT_CLASS_NAMES for submobject in mobject.submobjects[:50])
        if hasattr(mobject, "submobjects")
        else False
    )


def text_leaves(mobject):
    """Text-like leaves of a mobject tree. Comparing group bounding boxes gives false overlaps
    (axis labels at opposite ends of the axes form one huge box), so overlap is judged per leaf."""
    if type(mobject).__name__ in TEXT_CLASS_NAMES:
        return [mobject]
    leaves = []
    for submobject in getattr(mobject, "submobjects", []):
        leaves.extend(text_leaves(submobject))
    return leaves


def max_opacity(mobject):
    """Max fill/stroke opacity over the mobject family. Container mobjects (MathTex, VGroup)
    report 0 opacity themselves even when their glyphs are fully visible."""
    family = mobject.family_members_with_points() if hasattr(mobject, "family_members_with_points") else [mobject]
    return max([max(member.get_fill_opacity(), member.get_stroke_opacity()) for member in family] or [0.0])


def intersection_area(first_box, second_box):
    overlap_width = min(first_box[2], second_box[2]) - max(first_box[0], second_box[0])
    overlap_height = min(first_box[3], second_box[3]) - max(first_box[1], second_box[1])
    return max(0.0, overlap_width) * max(0.0, overlap_height)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("cls")
    parser.add_argument("--margin", type=float, default=0.3)
    parser.add_argument("--overlap-ratio", type=float, default=0.15, help="fraction of the smaller box")
    parser.add_argument("--min-text-height", type=float, default=0.18)
    parser.add_argument("--budget", help="clip_01=6.2,clip_02=8.0 (seconds of narration per clip)")
    parser.add_argument("--tolerance", type=float, default=0.5, help="allowed |video-audio| seconds per clip")
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args()

    from manim import Scene, config

    config.dry_run = True
    config.disable_caching = True
    config.verbosity = "ERROR"
    half_safe_width, half_safe_height = (
        config.frame_width / 2 - arguments.margin,
        config.frame_height / 2 - arguments.margin,
    )

    findings, timeline, elapsed_seconds = [], [], 0.0
    original_play = Scene.play

    def snapshot(scene, label):
        frame = getattr(scene.camera, "frame", None)  # MovingCameraScene: bounds follow the camera frame
        if frame is not None:
            center_x, center_y = frame.get_center()[:2]
            half_width, half_height = (
                frame.width / 2 - arguments.margin * frame.width / config.frame_width,
                frame.height / 2 - arguments.margin * frame.height / config.frame_height,
            )
        else:
            center_x, center_y, half_width, half_height = 0.0, 0.0, half_safe_width, half_safe_height
        backdrop = getattr(scene, "_backdrop", [])  # the template's backdrop and border are not content
        visible_mobjects = [
            mobject
            for mobject in scene.mobjects
            if mobject is not frame and mobject not in backdrop and bounding_box(mobject)
        ]
        zoomed = frame is not None and abs(frame.width - config.frame_width) > 1e-3
        # Zoomed-in camera: cropping shapes is intentional, cropped TEXT is still a defect.
        check = [leaf for mobject in visible_mobjects for leaf in text_leaves(mobject)] if zoomed else visible_mobjects
        for mobject in check:
            box = bounding_box(mobject)
            name = type(mobject).__name__
            if (
                box[0] < center_x - half_width
                or box[2] > center_x + half_width
                or box[1] < center_y - half_height
                or box[3] > center_y + half_height
            ):
                findings.append(
                    {
                        "severity": "ERROR",
                        "code": "OUT_OF_FRAME",
                        "t": round(elapsed_seconds, 2),
                        "event": label,
                        "mobject": name,
                        "bbox": [round(x, 2) for x in box],
                    }
                )
            if (
                type(mobject).__name__ in TEXT_CLASS_NAMES
                and (box[3] - box[1]) < arguments.min_text_height
                and max_opacity(mobject) > 0.05
            ):
                findings.append(
                    {
                        "severity": "WARN",
                        "code": "TINY_TEXT",
                        "t": round(elapsed_seconds, 2),
                        "event": label,
                        "mobject": name,
                    }
                )
        text_leaves_shown = [
            leaf for mobject in visible_mobjects for leaf in text_leaves(mobject) if max_opacity(leaf) > 0.05
        ]
        for i in range(len(text_leaves_shown)):
            for j in range(i + 1, len(text_leaves_shown)):
                first_box, second_box = bounding_box(text_leaves_shown[i]), bounding_box(text_leaves_shown[j])
                smaller = (
                    min(
                        (first_box[2] - first_box[0]) * (first_box[3] - first_box[1]),
                        (second_box[2] - second_box[0]) * (second_box[3] - second_box[1]),
                    )
                    or 1e-9
                )
                if intersection_area(first_box, second_box) / smaller > arguments.overlap_ratio:
                    findings.append(
                        {
                            "severity": "ERROR",
                            "code": "OVERLAP",
                            "t": round(elapsed_seconds, 2),
                            "event": label,
                            "mobjects": [type(text_leaves_shown[i]).__name__, type(text_leaves_shown[j]).__name__],
                        }
                    )

    def play(self, *args, **keyword_arguments):
        nonlocal elapsed_seconds
        result = original_play(self, *args, **keyword_arguments)
        elapsed_seconds = float(getattr(self.renderer, "time", elapsed_seconds))
        label = "play(" + ",".join(type(x).__name__ for x in args)[:80] + ")"
        timeline.append({"t_end": round(self.renderer.time, 3), "event": label})
        snapshot(self, label)
        return result

    # Scene.wait() is implemented as play(Wait(...)) in Manim CE, so patching play() covers both.
    Scene.play = play
    sys.path.insert(
        0, str(Path(arguments.file).resolve().parent)
    )  # like `manim render`: the scene's folder is importable
    spec = importlib.util.spec_from_file_location("clip_under_test", arguments.file)
    scene_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scene_module)
    scene_class = getattr(scene_module, arguments.cls)
    clip_spans: dict[str, list[float]] = {}
    import re

    for name in [attribute_name for attribute_name in dir(scene_class) if re.fullmatch(r"clip_\d+", attribute_name)]:
        clip_method = getattr(scene_class, name)

        def wrapped(self, *args, _clip_method=clip_method, _clip_name=name, **keyword_arguments):
            start = float(getattr(self.renderer, "time", 0.0))
            result = _clip_method(self, *args, **keyword_arguments)
            clip_spans[_clip_name] = [round(start, 3), round(float(getattr(self.renderer, "time", 0.0)), 3)]
            return result

        setattr(scene_class, name, wrapped)
    scene = scene_class()
    scene.render()
    beats: dict[str, dict[str, float]] = {}
    for clip_name, number, time in getattr(scene, "beat_log", []):  # scenes composed by scene_harness.py
        clip_start = clip_spans.get(clip_name, [0.0])[0]
        beats.setdefault(clip_name, {})[str(number)] = round(time - clip_start, 3)

    budget = (
        {clip_name: float(seconds) for clip_name, seconds in (x.split("=") for x in arguments.budget.split(","))}
        if arguments.budget
        else {}
    )
    clips = []
    for name, (start_seconds, end_seconds) in sorted(clip_spans.items()):
        duration = round(end_seconds - start_seconds, 3)
        entry = {"clip": name, "start": start_seconds, "end": end_seconds, "duration": duration}
        if name in budget:
            entry["budget"] = budget[name]
            entry["delta"] = round(duration - budget[name], 3)
            if duration + arguments.tolerance < budget[name]:
                findings.append(
                    {
                        "severity": "ERROR",
                        "code": "CLIP_TOO_SHORT",
                        "t": end_seconds,
                        "event": name,
                        "mobject": f"{duration}s < narration {budget[name]}s",
                    }
                )
            elif duration - budget[name] > max(arguments.tolerance, 1.5):
                findings.append(
                    {
                        "severity": "WARN",
                        "code": "CLIP_TOO_LONG",
                        "t": end_seconds,
                        "event": name,
                        "mobject": f"{duration}s > narration {budget[name]}s",
                    }
                )
        clips.append(entry)
    for missing in sorted(set(budget) - set(clip_spans)):
        findings.append(
            {"severity": "ERROR", "code": "CLIP_NOT_RUN", "t": 0, "event": missing, "mobject": "method never executed"}
        )

    report = {
        "duration_s": timeline[-1]["t_end"] if timeline else 0.0,
        "beats": beats,
        "clips": clips,
        "events": timeline,
        "findings": findings,
    }
    if arguments.json:
        print(json.dumps(report, indent=1))
    else:
        print(f"duration {report['duration_s']}s · {len(timeline)} events")
        for clip in clips:
            print(
                f"  {clip['clip']}: {clip['start']}→{clip['end']} ({clip['duration']}s)"
                f"{'  budget ' + str(clip['budget']) if 'budget' in clip else ''}"
            )
        for finding in findings:
            print(
                f"{finding['severity']:5} {finding['code']:13} t={finding['t']:<6} "
                f"{finding.get('mobject') or finding.get('mobjects')} @ {finding['event']}"
            )
    sys.exit(1 if any(finding["severity"] == "ERROR" for finding in findings) else 0)


if __name__ == "__main__":
    main()
