"""./check — deterministic gates for ONE scene's code, run by the scene-builder and re-run by `text-2-shorts accept`.

cwd = artifacts/runs/<id>/scenes/sNN/work/ holding TASK.json (SceneTask) and scene_code.py (class SceneNN with
_build_objects, _clip_1 … _clip_N, construct).
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
from schemas.media import GateResult, SceneRender, SceneTask

TOOLS_DIRECTORY = Path(__file__).resolve().parent  # this script lives in backend/tools/
PYTHON_EXECUTABLE = sys.executable
CODE = "scene_code.py"


def save_gate_result(gate: str, passed: bool, **data) -> bool:
    """checks/<gate>.json, validated against GateResult (what `accept` and the sync report read)."""
    result = GateResult.model_validate({"ok": passed, **data})
    Path("checks").mkdir(exist_ok=True)
    Path(f"checks/{gate}.json").write_text(result.model_dump_json(indent=1))
    print(json.dumps({"gate": gate, **result.model_dump(exclude_defaults=True)}, indent=1)[:6000])
    return passed


def run_tool(*args, **options) -> subprocess.CompletedProcess:
    return subprocess.run([PYTHON_EXECUTABLE, *map(str, args)], capture_output=True, text=True, **options)


def compose(task: SceneTask) -> None:
    """scene.py: the generated class wrapped by the harness (template backdrop, one section per clip)."""
    process = run_tool(TOOLS_DIRECTORY / "scene_harness.py", "compose", ".", "--scene-id", task.scene_id)
    if process.returncode:
        save_gate_result("compose", False, error=(process.stderr or process.stdout)[-2000:])
        raise SystemExit(1)


def static(task: SceneTask) -> bool:
    process = run_tool(
        TOOLS_DIRECTORY / "validate_manim_code.py",
        CODE,
        "--class-name",
        task.scene_class_name,
        "--clips",
        ",".join(str(int(clip.name[5:])) for clip in task.clips),
        "--index",
        task.api_index,
        "--json",
    )
    try:
        findings = json.loads(process.stdout)
    except json.JSONDecodeError:
        return save_gate_result("static", False, error=(process.stderr or process.stdout)[-3000:])
    return save_gate_result(
        "static", not any(finding["severity"] == "ERROR" for finding in findings), findings=findings
    )


def probe(task: SceneTask) -> bool:
    """Layout (frame, overlap, text size) over the whole scene, and every clip's length against its voice."""
    compose(task)
    process = run_tool(
        TOOLS_DIRECTORY / "layout_probe.py",
        "scene.py",
        task.scene_class_name,
        "--budget",
        ",".join(f"{clip.name}={clip.seconds}" for clip in task.clips),
        "--json",
    )
    try:
        report = json.loads(process.stdout)
    except json.JSONDecodeError:
        return save_gate_result("probe", False, error=process.stderr[-3000:])
    findings = list(report["findings"])
    spans = {clip["clip"] for clip in report["clips"]}
    findings += [
        {
            "severity": "ERROR",
            "code": "CLIP_METHOD_MISSING",
            "t": 0,
            "event": clip.name,
            "mobject": f"no _clip_{int(clip.name[5:])} method ran: one method per planned clip",
        }
        for clip in task.clips
        if clip.name not in spans
    ]
    return save_gate_result(
        "probe",
        not any(finding["severity"] == "ERROR" for finding in findings),
        clips=report["clips"],
        beats=report.get("beats", {}),
        findings=findings,
    )


def render(task: SceneTask) -> bool:
    """A draft of the whole scene (1280×720 at 30 fps), every clip its own section video."""
    compose(task)
    shutil.rmtree("media", ignore_errors=True)
    process = run_tool(
        TOOLS_DIRECTORY / "scene_harness.py",
        "render",
        ".",
        "--scene-id",
        task.scene_id,
        "--quality",
        "m",
        env={**os.environ, "TEXT_2_SHORTS_LOOK": json.dumps(task.look)},
    )
    try:
        report = SceneRender.model_validate_json(process.stdout)
    except ValidationError:
        report = SceneRender(ok=False, stderr_tail=(process.stderr or process.stdout)[-3000:])
    sections = {section.name: section for section in report.sections}
    missing = [clip.name for clip in task.clips if clip.name not in sections]
    return save_gate_result(
        "render",
        bool(report.ok and not missing),
        videos={name: section.path for name, section in sections.items() if name.startswith("clip_")},
        durations={name: section.duration for name, section in sections.items() if name.startswith("clip_")},
        error=report.stderr_tail or (f"no section video for {', '.join(missing)}" if missing else None),
    )


def frames(task: SceneTask) -> bool:
    """Frames for the critic: every 2 s and the last frame of each clip's section."""
    render_path = Path("checks/render.json")
    rendered = GateResult.model_validate_json(render_path.read_text()) if render_path.exists() else None
    if not (rendered and rendered.ok) and not render(task):
        return save_gate_result("frames", False, error="render failed")
    videos = GateResult.model_validate_json(render_path.read_text()).videos
    shutil.rmtree("frames", ignore_errors=True)
    Path("frames").mkdir()
    for name, video in sorted(videos.items()):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-vf", "fps=1/2", f"frames/{name}_%02d.png"])
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
                f"frames/{name}_last.png",
            ]
        )
    return save_gate_result("frames", True, frames=sorted(str(frame) for frame in Path("frames").glob("*.png")))


def main() -> None:
    gate = sys.argv[1] if len(sys.argv) > 1 else "all"
    task = SceneTask.model_validate_json(Path("TASK.json").read_text())
    if gate == "doc":
        process = run_tool(
            TOOLS_DIRECTORY / "doc_cards.py",
            "--index",
            task.api_index,
            "--names",
            sys.argv[2] if len(sys.argv) > 2 else "",
        )
        print(process.stdout or process.stderr)
        return
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
