"""Manim code generation (v3: consumes v7 Scene Execution Plans), wired into the run: one Python file per scene.

Prompt text lives in Markdown files; this module only loads and fills them (tokens with str.replace, never .format:
plans and references contain literal braces).

    references/codegen-system.md            role, tables, rules CG1-CG13, checks X1-X12 (the scene-builder reads it)
    manim-vocabulary.md, manim-construction-patterns.md, manim-common-mistakes.md   (the Manim reference skill)
    references/codegen-task.md              the task + inputs, printed by `text-2-shorts task . sNN`

`text-2-shorts task . sNN` prepares scenes/sNN/work/ (TASK.json for ./check, the previous attempt) and prints the
filled task; the scene-builder subagent writes scene_code.py there; `text-2-shorts accept . sNN` re-runs every check
in a jail and installs the file as scenes/sNN/scene_code.py. No Claude call happens here.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from schemas.media import GateResult, SceneTask, SceneTaskClip
from schemas.plans import ScenePlan
from schemas.reviews import MistakeIssue
from schemas.run_state import ClipBuild

from app.config import (
    ALWAYS_LOADED_TOPICS,
    API_INDEX_PATH,
    END_HOLD_SECONDS,
    PYTHON_EXECUTABLE,
    REFERENCES_DIRECTORY,
    SCENE_GATES_PATH,
    TOOLS_DIRECTORY,
    TOPICS_DIRECTORY,
    VOICE_LEAD_IN_SECONDS,
)
from app.sandbox import render_jail_prefix
from app.workflow import mistakes
from app.workflow.artifacts import load_audio_index, load_scene_plans
from app.workflow.change_requests import requests_for, requests_text, resolve_clip_requests
from app.workflow.checkpoints import require_approval
from app.workflow.critiques import review_notes
from app.workflow.fingerprints import clip_key
from app.workflow.ledger import count_attempt, update_state
from app.workflow.templates import drawing, install_template, look_brief

SYSTEM_FILE = REFERENCES_DIRECTORY / "codegen-system.md"
TASK_FILE = REFERENCES_DIRECTORY / "codegen-task.md"
SYSTEM_FILES = (SYSTEM_FILE, *(TOPICS_DIRECTORY / f"{topic}.md" for topic in ALWAYS_LOADED_TOPICS))
CODE_FILE = "scene_code.py"
_REQUIRED_SECTIONS = ("SCENE_OVERVIEW", "OBJECT_REGISTRY", "COLOR_MAP", "CLIP_SEQUENCE", "TIMING_SUMMARY")


@dataclass(frozen=True)
class CodegenInput:
    scene_plan: str  # Visual Director output, <SCENE_OVERVIEW> ... </IMPLEMENTATION_NOTES> (plan.json execution_plan)
    template_reference: str  # the TEMPLATE block: colour roles with values, font, text sizes, safe area
    scene_class_name: str  # e.g. "Scene03"; the renderer looks this up
    clip_timings: str = ""  # each clip's real length from the voice, and when its phrases are spoken
    notes: str = ""  # change requests and accuracy notes for this scene
    work_folder: str = "."


def _validate(inp: CodegenInput) -> None:
    if not inp.scene_plan.strip():
        raise ValueError("scene_plan is empty")
    missing = [s for s in _REQUIRED_SECTIONS if f"<{s}>" not in inp.scene_plan]
    if missing:
        raise ValueError(f"scene_plan is missing sections: {', '.join(missing)}")
    if not inp.template_reference.strip():
        raise ValueError("template_reference is required (rule CG3: colors come only from the template)")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", inp.scene_class_name):
        raise ValueError(f"scene_class_name is not a valid Python class name: {inp.scene_class_name!r}")


def build_user_prompt(inp: CodegenInput) -> str:
    _validate(inp)
    return (
        TASK_FILE.read_text(encoding="utf-8")
        .strip()
        .replace("__READ_FIRST__", "READ FIRST, in this order: " + ", ".join(str(path) for path in SYSTEM_FILES))
        .replace("__WORK_FOLDER__", inp.work_folder)
        .replace("__SCENE_CLASS_NAME__", inp.scene_class_name)
        .replace("__TEMPLATE_REFERENCE__", inp.template_reference.strip())
        .replace("__CLIP_TIMINGS__", inp.clip_timings.strip() or "(none)")
        .replace("__NOTES__", inp.notes.strip() or "none")
        .replace("__SCENE_PLAN__", inp.scene_plan.strip())
    )


def class_name(scene_id: str) -> str:
    """The scene class the harness renders (Scene01, Scene02, …); the same name as scene_harness.class_name."""
    return "Scene" + scene_id[1:].zfill(2)


def clip_seconds(audio_seconds: float) -> float:
    """A clip's length: the visual lead-in, its narration, the hold after it."""
    return round(VOICE_LEAD_IN_SECONDS + audio_seconds + END_HOLD_SECONDS, 2)


def load_plan(run: Path, scene_id: str) -> ScenePlan:
    plan = next((p for p in load_scene_plans(run) if p.scene_id == scene_id), None)
    if plan is None:
        raise SystemExit(f"no valid plan for {scene_id}")
    return plan


def ensure_api_index() -> None:
    if not API_INDEX_PATH.exists():
        API_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [PYTHON_EXECUTABLE, str(TOOLS_DIRECTORY / "build_manim_api_index.py"), "--out", str(API_INDEX_PATH)],
            check=True,
            capture_output=True,
        )


def prepare_scene(run: Path, scene_id: str) -> str:
    """Set up scenes/sNN/work/ for the scene-builder (TASK.json, ./check, the last accepted file to start from) and
    return the filled task."""
    require_approval(run, "plan")
    plan = load_plan(run, scene_id)
    install_template(run)  # the renderer the harness draws the backdrop with, in the run environment
    audio = load_audio_index(run, scene_id)
    if missing := [clip.clip_id for clip in plan.clips if clip.clip_id not in audio]:
        raise SystemExit(f"No audio for {', '.join(missing)}: run voice first (`text-2-shorts voice .`)")
    ensure_api_index()
    scene_directory = run / "scenes" / scene_id
    work = scene_directory / "work"
    work.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(work / "checks", ignore_errors=True)
    accepted = scene_directory / CODE_FILE
    if accepted.exists() and not (work / CODE_FILE).exists():
        shutil.copy(accepted, work / CODE_FILE)  # a rebuild starts from the accepted version
    task = SceneTask(
        scene_id=scene_id,
        scene_class_name=class_name(scene_id),
        clips=[
            SceneTaskClip(name=f"clip_{clip.index:02d}", seconds=clip_seconds(audio[clip.clip_id].seconds))
            for clip in plan.clips
        ],
        api_index=str(API_INDEX_PATH),
        look=drawing(run),
    )
    (work / "TASK.json").write_text(task.model_dump_json(indent=2))
    (work / "check").write_text(f'#!/bin/sh\nexec "{PYTHON_EXECUTABLE}" "{SCENE_GATES_PATH}" "$@"\n')
    (work / "check").chmod(0o755)
    timings = []
    for clip, clip_task in zip(plan.clips, task.clips):
        spoken = audio[clip.clip_id].beat_times or [None] * len(clip.beats)
        phrases = "".join(
            f"\n    {'' if at is None else f'at {VOICE_LEAD_IN_SECONDS + at:.1f}s '}{beat}"
            for beat, at in zip(clip.beats, spoken)
        )
        timings.append(
            f"CLIP {clip.index} ({clip.clip_id}, method _clip_{clip.index}, section {clip_task.name}): exactly "
            f"{clip_task.seconds}s = {VOICE_LEAD_IN_SECONDS}s lead-in + {audio[clip.clip_id].seconds}s narration + "
            f"{END_HOLD_SECONDS}s hold or more. Phrases:{phrases or ' -'}"
        )
    notes = [
        f"Change requests:\n{requests_text(requests_for(run, scene_id, *(clip.clip_id for clip in plan.clips)))}",
        "Accuracy notes (verified): "
        + ("; ".join(note for clip in plan.clips for note in review_notes(run, scene_id, clip.clip_id)) or "none"),
        f"Previous attempt: {'scene_code.py exists in the work folder: start from it' if (work / CODE_FILE).exists() else 'none'}",
    ]
    return build_user_prompt(
        CodegenInput(
            scene_plan=plan.execution_plan,
            template_reference=look_brief(run),
            scene_class_name=task.scene_class_name,
            clip_timings="\n".join(timings),
            notes="\n".join(notes),
            work_folder=str(work),
        )
    )


def accept_scene(run: Path, scene_id: str) -> ClipBuild:
    """Re-run every check on the scene's code in a jail (it is LLM-written); install it only if all pass. Every clip of
    the scene shares the result: one file per scene."""
    plan = load_plan(run, scene_id)
    scene_directory = run / "scenes" / scene_id
    work = scene_directory / "work"
    passed = (work / CODE_FILE).exists() and subprocess.run(
        render_jail_prefix() + ["--bind", str(work), str(work), PYTHON_EXECUTABLE, str(SCENE_GATES_PATH), "all"],
        cwd=work,
        capture_output=True,
    ).returncode == 0
    findings = [
        f"{gate.stem}: {finding.code}"
        for gate in sorted((work / "checks").glob("*.json"))
        for finding in GateResult.model_validate_json(gate.read_text()).findings
        if finding.severity == "ERROR"
    ]
    if passed:
        shutil.copy(work / CODE_FILE, scene_directory / CODE_FILE)
    at = datetime.now().isoformat(timespec="seconds")
    results = {
        clip.clip_id: ClipBuild(
            status="READY" if passed else "FAILED",
            open_findings=findings,
            key=clip_key(run, plan, clip) if passed else None,
            at=at,
        )
        for clip in plan.clips
    }
    update_state(run, lambda state: state.clips.update(results))
    built_from = clip_key(run, plan, plan.clips[0])[:12]
    attempt = count_attempt(run, f"build:{scene_id}" + ("" if passed else f":{built_from}"), failed=not passed)
    issues = [MistakeIssue(code=finding, severity="ERROR", target=scene_id, problem=finding) for finding in findings]
    mistakes.record(run, "build", "scene-builder", scene_id, issues if not passed else [], attempt or None)
    if passed:
        for clip in plan.clips:
            resolve_clip_requests(run, clip.clip_id)
    return results[plan.clips[0].clip_id]
