"""./check — deterministic gates for ONE clip, run by the clip-builder agent and re-run by the orchestrator.

cwd = artifacts/runs/<id>/scenes/sNN/work/clip_MM/ holding TASK.json, clip_MM.py and scene/clips/
(the accepted earlier clips).
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

from pydantic import ValidationError
from schemas.media import ClipTask, GateResult, SceneRender

TOOLS_DIRECTORY = Path(__file__).resolve().parent  # this script lives in backend/tools/
PYTHON_EXECUTABLE = sys.executable


def save_gate_result(gate: str, passed: bool, **data) -> bool:
    """checks/<gate>.json, validated against GateResult (what `accept` and the sync report read)."""
    result = GateResult.model_validate({"ok": passed, **data})
    Path("checks").mkdir(exist_ok=True)
    Path(f"checks/{gate}.json").write_text(result.model_dump_json(indent=1))
    print(json.dumps({"gate": gate, **result.model_dump(exclude_defaults=True)}, indent=1)[:6000])
    return passed


def run_tool(*args, **options) -> subprocess.CompletedProcess:
    return subprocess.run([PYTHON_EXECUTABLE, *map(str, args)], capture_output=True, text=True, **options)


def compose_scene(task: ClipTask) -> None:
    clips_directory = Path("scene/clips")
    clips_directory.mkdir(parents=True, exist_ok=True)
    shutil.copy(f"{task.clip_name}.py", clips_directory / f"{task.clip_name}.py")
    process = run_tool(TOOLS_DIRECTORY / "scene_harness.py", "compose", "scene", "--scene-id", task.scene_id)
    if process.returncode:
        save_gate_result("compose", False, error=(process.stderr or process.stdout)[-2000:])
        raise SystemExit(1)


def static(task: ClipTask) -> bool:
    process = run_tool(
        TOOLS_DIRECTORY / "validate_manim_code.py",
        f"{task.clip_name}.py",
        "--clip-file",
        "--index",
        task.api_index,
        "--entry",
        ",".join(task.entry),
        "--exit",
        ",".join(task.exit),
        "--json",
    )
    try:
        findings = json.loads(process.stdout)
    except json.JSONDecodeError:
        return save_gate_result("static", False, error=(process.stderr or process.stdout)[-3000:])
    return save_gate_result(
        "static", not any(finding["severity"] == "ERROR" for finding in findings), findings=findings
    )


def probe(task: ClipTask) -> bool:
    compose_scene(task)
    process = run_tool(
        TOOLS_DIRECTORY / "layout_probe.py",
        "scene.py",
        task.scene_class_name,
        "--budget",
        f"{task.clip_name}={task.clip_seconds}",
        "--json",
        cwd="scene",
        env={**os.environ, "TEXT_2_SHORTS_STOP_AFTER": task.clip_name},
    )
    try:
        probe_report = json.loads(process.stdout)
    except json.JSONDecodeError:
        return save_gate_result("probe", False, error=process.stderr[-3000:])
    clip_span = next((clip for clip in probe_report["clips"] if clip["clip"] == task.clip_name), None)
    clip_findings = [
        finding
        for finding in probe_report[
            "findings"
        ]  # earlier clips are already approved: judge only this clip's time window
        if finding.get("event") == task.clip_name
        or (clip_span and clip_span["start"] <= finding["t"] <= clip_span["end"])
    ]
    beats = probe_report.get("beats", {}).get(task.clip_name, {})
    if missing := [number for number in range(1, task.beats + 1) if str(number) not in beats]:
        clip_findings.append(
            {
                "severity": "ERROR",
                "code": "BEAT_MARKS_MISSING",
                "t": 0,
                "event": task.clip_name,
                "mobject": f"call self.beat(n) where beat n starts; missing beats {missing}",
            }
        )
    return save_gate_result(
        "probe",
        not any(finding["severity"] == "ERROR" for finding in clip_findings),
        clip=clip_span,
        beats=beats,
        findings=clip_findings,
    )


def render(task: ClipTask) -> bool:
    compose_scene(task)
    process = run_tool(
        TOOLS_DIRECTORY / "scene_harness.py",
        "render",
        "scene",
        "--scene-id",
        task.scene_id,
        "--target",
        task.clip_name,
        "--quality",
        "m",  # drafts: 1280×720 at 30 fps (only the final delivery renders 1440p)
        env={**os.environ, "TEXT_2_SHORTS_BACKGROUND": task.background},
    )
    try:
        render_report = SceneRender.model_validate_json(process.stdout)
    except ValidationError:
        render_report = SceneRender(ok=False, stderr_tail=(process.stderr or process.stdout)[-3000:])
    section = next((candidate for candidate in render_report.sections if candidate.name == task.clip_name), None)
    return save_gate_result(
        "render",
        bool(render_report.ok and section),
        video=str(Path("scene") / section.path) if section else None,
        duration=section.duration if section else None,
        error=render_report.stderr_tail,
    )


def frames(task: ClipTask) -> bool:
    render_path = Path("checks/render.json")
    rendered = GateResult.model_validate_json(render_path.read_text()) if render_path.exists() else None
    if not (rendered and rendered.ok) and not render(task):
        return save_gate_result("frames", False, error="render failed")
    video = GateResult.model_validate_json(render_path.read_text()).video
    if video is None:
        return save_gate_result("frames", False, error="render produced no video for this clip")
    shutil.rmtree("frames", ignore_errors=True)
    Path("frames").mkdir()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-vf", "fps=1/2", "frames/f_%02d.png"])
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-sseof",
            "-0.1",
            "-i",
            video,
            "-frames:v",
            "1",
            "-update",
            "1",
            "frames/f_last.png",
        ]
    )
    return save_gate_result(
        "frames", True, frames=sorted(str(frame_path) for frame_path in Path("frames").glob("*.png"))
    )


def main() -> None:
    gate = sys.argv[1] if len(sys.argv) > 1 else "all"
    if gate == "doc":
        task = ClipTask.model_validate_json(Path("TASK.json").read_text())
        process = run_tool(
            TOOLS_DIRECTORY / "doc_cards.py",
            "--index",
            task.api_index,
            "--names",
            sys.argv[2] if len(sys.argv) > 2 else "",
        )
        print(process.stdout or process.stderr)
        return
    task = ClipTask.model_validate_json(Path("TASK.json").read_text())
    gates = {"static": static, "probe": probe, "render": render, "frames": frames}
    if gate == "all":
        passed = static(task) and probe(task) and render(task)  # stop at the first failing gate
    elif gate in gates:
        passed = gates[gate](task)
    else:
        raise SystemExit(f"unknown gate {gate!r}: static | probe | render | frames | all | doc Names")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
