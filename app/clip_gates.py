"""./check — deterministic gates for ONE clip, run by the clip-builder agent and re-run by the orchestrator.

cwd = runs/<id>/scenes/sNN/work/clip_MM/ holding TASK.json, clip_MM.py and scene/clips/ (earlier approved clips).
    ./check static | probe | render | frames | all | doc Name1,Name2
Each gate writes checks/<gate>.json and exits 0 (pass) or 1 (fail).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "tools"
PY = sys.executable


def save(gate: str, ok: bool, **data) -> bool:
    Path("checks").mkdir(exist_ok=True)
    Path(f"checks/{gate}.json").write_text(json.dumps({"ok": ok, **data}, indent=1))
    print(json.dumps({"gate": gate, "ok": ok, **data}, indent=1)[:6000])
    return ok


def run(*args, **kw) -> subprocess.CompletedProcess:
    return subprocess.run([PY, *map(str, args)], capture_output=True, text=True, **kw)


def compose(t: dict) -> None:
    clips = Path("scene/clips")
    clips.mkdir(parents=True, exist_ok=True)
    shutil.copy(f"{t['clip']}.py", clips / f"{t['clip']}.py")
    p = run(TOOLS / "scene_harness.py", "compose", "scene", "--scene-id", t["scene_id"])
    if p.returncode:
        save("compose", False, error=(p.stderr or p.stdout)[-2000:])
        raise SystemExit(1)


def static(t: dict) -> bool:
    p = run(TOOLS / "validate_manim_code.py", f"{t['clip']}.py", "--clip-file", "--index", t["api_index"],
            "--entry", ",".join(t["entry"]), "--exit", ",".join(t["exit"]), "--json")
    try:
        found = json.loads(p.stdout)
    except json.JSONDecodeError:
        return save("static", False, error=(p.stderr or p.stdout)[-3000:])
    return save("static", not any(f["severity"] == "ERROR" for f in found), findings=found)


def probe(t: dict) -> bool:
    compose(t)
    p = run(TOOLS / "layout_probe.py", "scene.py", t["class"], "--budget", f"{t['clip']}={t['seconds']}", "--json",
            cwd="scene", env={**os.environ, "T2S_STOP_AFTER": t["clip"]})
    try:
        out = json.loads(p.stdout)
    except json.JSONDecodeError:
        return save("probe", False, error=p.stderr[-3000:])
    span = next((c for c in out["clips"] if c["clip"] == t["clip"]), None)
    mine = [f for f in out["findings"]  # earlier clips are already approved: judge only this clip's time window
            if f.get("event") == t["clip"] or (span and span["start"] <= f["t"] <= span["end"])]
    return save("probe", not any(f["severity"] == "ERROR" for f in mine), clip=span, findings=mine)


def render(t: dict) -> bool:
    compose(t)
    p = run(TOOLS / "scene_harness.py", "render", "scene", "--scene-id", t["scene_id"], "--target", t["clip"],
            "--quality", "l", env={**os.environ, "T2S_BACKGROUND": t.get("background", "")})
    try:
        r = json.loads(p.stdout)
    except json.JSONDecodeError:
        r = {"ok": False, "stderr_tail": (p.stderr or p.stdout)[-3000:]}
    sec = next((s for s in r.get("sections", []) if s.get("name") == t["clip"]), None)
    return save("render", bool(r.get("ok") and sec), video=sec and str(Path("scene") / sec["path"]),
                duration=sec and sec["duration"], error=r.get("stderr_tail"))


def frames(t: dict) -> bool:
    r = json.loads(Path("checks/render.json").read_text()) if Path("checks/render.json").exists() else {}
    if not r.get("ok") and not render(t):
        return save("frames", False, error="render failed")
    video = json.loads(Path("checks/render.json").read_text())["video"]
    shutil.rmtree("frames", ignore_errors=True)
    Path("frames").mkdir()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-vf", "fps=1/2", "frames/f_%02d.png"])
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-sseof", "-0.1", "-i", video, "-frames:v", "1",
                    "-update", "1", "frames/f_last.png"])
    return save("frames", True, frames=sorted(str(f) for f in Path("frames").glob("*.png")))


def main() -> None:
    gate = sys.argv[1] if len(sys.argv) > 1 else "all"
    if gate == "doc":
        t = json.loads(Path("TASK.json").read_text())
        p = run(TOOLS / "doc_cards.py", "--index", t["api_index"], "--names", sys.argv[2] if len(sys.argv) > 2 else "")
        print(p.stdout or p.stderr)
        return
    t = json.loads(Path("TASK.json").read_text())
    gates = {"static": static, "probe": probe, "render": render, "frames": frames}
    if gate == "all":
        ok = static(t) and probe(t) and render(t)  # stop at the first failing gate
    elif gate in gates:
        ok = gates[gate](t)
    else:
        raise SystemExit(f"unknown gate {gate!r}: static | probe | render | frames | all | doc Names")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
