"""Clip building: the clip-builder's task folder (TASK.md, API cards, ./check) and the jailed acceptance of a clip."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from schemas.media import ClipTask, GateResult
from schemas.run_state import ClipBuild

from app.config import (
    ALWAYS_LOADED_TOPICS,
    API_INDEX_PATH,
    CLIP_GATES_PATH,
    END_HOLD_SECONDS,
    PYTHON_EXECUTABLE,
    STANDARDS_PATH,
    TOOLS_DIRECTORY,
    TOPICS_DIRECTORY,
    VOICE_LEAD_IN_SECONDS,
)
from app.sandbox import RENDER_JAIL_PREFIX
from app.workflow.artifacts import load_audio_index, load_clip_plan
from app.workflow.change_requests import requests_for, requests_text, resolve_clip_requests
from app.workflow.checkpoints import require_approval, require_earlier_scenes
from app.workflow.critiques import review_notes
from app.workflow.fingerprints import clip_key
from app.workflow.ledger import load_state, update_state
from app.workflow.templates import drawing, look_brief


def ensure_api_index() -> None:
    if not API_INDEX_PATH.exists():
        API_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [PYTHON_EXECUTABLE, str(TOOLS_DIRECTORY / "build_manim_api_index.py"), "--out", str(API_INDEX_PATH)],
            check=True,
            capture_output=True,
        )


def prepare_clip(run: Path, clip_id: str) -> Path:
    """Set up scenes/sNN/work/clip_MM/ for the clip-builder: TASK.md/.json, API_CARDS.md, ./check, earlier clips."""
    require_approval(run, "plan")
    plan, clip = load_clip_plan(run, clip_id)
    require_earlier_scenes(run, plan.scene_id)
    builds = load_state(run).clips
    earlier = [c for c in plan.clips if c.index < clip.index]
    if waiting := [
        c.clip_id for c in earlier if (build := builds.get(c.clip_id)) is None or build.key != clip_key(run, plan, c)
    ]:
        raise SystemExit(f"build {waiting[0]} first: a scene's clips are built one at a time, in order")
    scene_directory, clip_name = run / "scenes" / plan.scene_id, f"clip_{clip.index:02d}"
    audio = load_audio_index(run, plan.scene_id)[clip_id]
    accuracy_notes = review_notes(run, plan.scene_id, clip_id)
    ensure_api_index()
    work_directory = scene_directory / "work" / clip_name
    work_directory.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(work_directory / "scene", ignore_errors=True)
    shutil.rmtree(work_directory / "checks", ignore_errors=True)
    (work_directory / "scene" / "clips").mkdir(parents=True)
    (scene_directory / "clips").mkdir(exist_ok=True)
    for earlier_clip in earlier:  # the accepted clips before it: the clip starts from their real end state
        shutil.copy(scene_directory / "clips" / f"clip_{earlier_clip.index:02d}.py", work_directory / "scene" / "clips")
    if (scene_directory / "clips" / f"{clip_name}.py").exists() and not (work_directory / f"{clip_name}.py").exists():
        shutil.copy(
            scene_directory / "clips" / f"{clip_name}.py", work_directory
        )  # a rebuild starts from the approved version
    task = ClipTask(
        clip_name=clip_name,
        clip_id=clip_id,
        scene_id=plan.scene_id,
        scene_class_name="Scene" + plan.scene_id[1:],
        clip_seconds=round(VOICE_LEAD_IN_SECONDS + audio.seconds + END_HOLD_SECONDS, 2),
        entry=clip.entry.persistent_objects,
        exit=clip.exit.persistent_objects,
        api_index=str(API_INDEX_PATH),
        beats=len(clip.beats),
        look=drawing(run),
    )
    (work_directory / "TASK.json").write_text(task.model_dump_json(indent=2))
    beat_times = audio.beat_times or [None] * len(clip.beats)  # word timings → when the voice says each phrase
    beats = "\n".join(
        f"  {i}. {'' if beat_time is None else f'@ {VOICE_LEAD_IN_SECONDS + beat_time:.1f}s  '}{beat}"
        for i, (beat, beat_time) in enumerate(zip(clip.beats, beat_times), 1)
    )
    (work_directory / "TASK.md").write_text(
        f"READ FIRST: {STANDARDS_PATH}, "
        + ", ".join(str(TOPICS_DIRECTORY / f"{topic}.md") for topic in ALWAYS_LOADED_TOPICS)
        + "\n"
        f"CLIP {clip_id}  (scene {plan.scene_id}, clip {clip.index} of {len(plan.clips)})   FILE: {clip_name}.py   "
        f"NARRATION_SECONDS: {audio.seconds}   CLIP_SECONDS: {task.clip_seconds} "
        f"(voice from {VOICE_LEAD_IN_SECONDS}s, hold {END_HOLD_SECONDS}s)\n"
        f"OBJECTIVE: {clip.objective}\nNARRATION (exact):\n  {clip.narration}\nVISUAL INTENT: {clip.visual_intent}\n"
        f"BEATS (call self.beat(n) where beat n starts):\n{beats}\n"
        f"ON-SCREEN MATH (exact LaTeX): {json.dumps(clip.on_screen_math)}\n"
        f"ENTRY (take each object with self.entry(name, lambda: <object as described>): in the scene it is the "
        f"previous clip's object; when this clip runs alone it is built from the description): "
        f"{json.dumps(clip.entry.model_dump())}\n"
        f"EXIT (must be in self.reg and on screen at the end): {json.dumps(clip.exit.model_dump())}\n"
        f"SYMBOL COLORS (symbol → colour role): {json.dumps(plan.color_roles)}\n"
        f"{look_brief(run)}\n"
        f"ACCURACY NOTES (verified): {'; '.join(accuracy_notes) or 'none'}\n"
        f"HUMAN_FEEDBACK (change requests for this scene or clip):\n"
        f"{requests_text(requests_for(run, plan.scene_id, clip_id))}\n"
        f"PREVIOUS ATTEMPT: "
        f"{clip_name + '.py exists — start from it' if (work_directory / f'{clip_name}.py').exists() else 'none'}\n"
    )
    topics = [topic for topic in dict.fromkeys(clip.manim_topics) if topic not in ALWAYS_LOADED_TOPICS]
    topic_cards = subprocess.run(
        [
            PYTHON_EXECUTABLE,
            str(TOOLS_DIRECTORY / "doc_cards.py"),
            "--index",
            str(API_INDEX_PATH),
            "--topics",
            ",".join(topics),
            "--topics-dir",
            str(TOPICS_DIRECTORY),
        ],
        capture_output=True,
        text=True,
    )
    (work_directory / "API_CARDS.md").write_text(
        topic_cards.stdout
        if topics
        else "No extra topic cards for this clip. Check any other name with ./check doc Name.\n"
    )
    (work_directory / "check").write_text(f'#!/bin/sh\nexec "{PYTHON_EXECUTABLE}" "{CLIP_GATES_PATH}" "$@"\n')
    (work_directory / "check").chmod(0o755)
    return work_directory


def accept_clip(run: Path, clip_id: str) -> ClipBuild:
    """Re-run every gate on the clip in a jail (it is LLM-written code); install it only if all pass."""
    plan, clip = load_clip_plan(run, clip_id)
    scene_directory, clip_name = run / "scenes" / plan.scene_id, f"clip_{clip.index:02d}"
    work_directory = scene_directory / "work" / clip_name
    passed = (work_directory / f"{clip_name}.py").exists() and subprocess.run(
        RENDER_JAIL_PREFIX
        + [
            "--bind",
            str(work_directory),
            str(work_directory),
            PYTHON_EXECUTABLE,
            str(CLIP_GATES_PATH),
            "all",
        ],
        cwd=work_directory,
        capture_output=True,
    ).returncode == 0
    findings = [
        f"{gate.stem}: {finding.code}"
        for gate in sorted((work_directory / "checks").glob("*.json"))
        for finding in GateResult.model_validate_json(gate.read_text()).findings
        if finding.severity == "ERROR"
    ]
    if passed:
        shutil.copy(work_directory / f"{clip_name}.py", scene_directory / "clips" / f"{clip_name}.py")
    result = ClipBuild(
        status="READY" if passed else "FAILED",
        open_findings=findings,
        key=clip_key(run, plan, clip) if passed else None,
        at=datetime.now().isoformat(timespec="seconds"),
    )
    update_state(run, lambda state: state.clips.__setitem__(clip_id, result))
    if passed:
        resolve_clip_requests(run, clip_id)
    return result
