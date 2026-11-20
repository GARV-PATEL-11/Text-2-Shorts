"""Deterministic clip-level steps that the run's Claude Code session calls (no LLM calls here).

The session writes outline.json, scenes/sNN/plan.json, math.json (math-reviewer subagent) and clip code
(clip-builder subagent); these commands validate them, synthesise narration, prepare and accept clips, render the
final video, and keep the ledger:
  runs/<id>/state.json              approvals, per-clip build state, session transcripts (for `text-2-shorts report`)
  runs/<id>/feedback.jsonl          human feedback, scoped to outline | sNN | sNNcMM
  runs/<id>/log.jsonl               one row per tool call (PostToolUse hook)
  runs/<id>/scenes/sNN/plan.json    ScenePlan
  runs/<id>/scenes/sNN/audio/       clip_MM.mp3 + index.json (spoken text hash → seconds, beat start times)
  runs/<id>/scenes/sNN/clips/       accepted clip_MM.py files (the harness composes scene.py from them)
  runs/<id>/scenes/sNN/work/clip_MM clip-builder folder: TASK.md/.json, API_CARDS.md, ./check, its own scene copy
A clip's key hashes everything it depends on (plan, audio, colours, feedback, the previous clip's code, the
clip-builder prompt), so `text-2-shorts status` lists exactly what a change made stale.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError

from app import cli
from app import narration
from app.outline_models.classic_linear_narrative import ClassicLinearNarrativeOutline
from app.outline_models.conceptual_zoom import ConceptualZoomOutline
from app.outline_models.problem_solution_arc import ProblemSolutionArcOutline
from schemas.models import ScenePlan

MANIM_VERSION = "0.20.1"  # pinned in pyproject.toml
TOOLS_DIRECTORY = cli.REPOSITORY_ROOT / "tools"
TOPICS_DIRECTORY = cli.REPOSITORY_ROOT / "run-environment" / "skills" / "manim-ce-0-20-1-reference" / "topics"
API_INDEX_PATH = (
    Path.home() / ".cache" / "text-2-shorts" / f"manim_api_{MANIM_VERSION}.json"
)  # writable inside the run jail
ALWAYS_LOADED_TOPICS = ["clip-structure", "timing-and-sync", "positioning-layout"]
VIDEO_STYLE = {
    "background": "#0e2733",
    "text": "WHITE",
    "focus": "YELLOW",
    "given": "BLUE",
    "derived": "GREEN",
    "warning": "RED",
    "secondary": "GREY_B",
}
VOICE_LEAD_IN_SECONDS, END_HOLD_SECONDS = (
    0.3,
    0.8,
)  # seconds of picture before the voice starts / after it ends, in every clip


class MathFinding(BaseModel):
    clip_id: str
    severity: Literal["ERROR", "WARN"]
    kind: Literal["FALSE", "UNSTATED", "NOTATION", "MISLEADING", "SPOKEN"]
    quote: str
    why: str
    fix: str


class MathReport(BaseModel):
    findings: list[MathFinding]


# ── Ledger: state.json + feedback.jsonl ─────────────────────────────────────────────────────────────────────────


def content_hash(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:16]


def load_state(run: Path) -> dict:
    state_path = run / "state.json"
    return json.loads(state_path.read_text()) if state_path.exists() else {"approved": {}, "clips": {}}


@contextmanager
def run_lock(run: Path):
    """Exclusive lock across processes (parallel `text-2-shorts accept`, hooks, approvals all write the ledger)."""
    with open(run / ".ledger.lock", "a") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        yield


def update_state(run: Path, modify) -> dict:
    """Read-modify-write under the run lock, written atomically (a crash never leaves a half-written state.json)."""
    with run_lock(run):
        state = load_state(run)
        modify(state)
        with tempfile.NamedTemporaryFile("w", dir=run, delete=False, suffix=".tmp") as temporary_file:
            temporary_file.write(json.dumps(state, indent=1))
        os.replace(temporary_file.name, run / "state.json")
        return state


def feedback_for(run: Path, *targets: str) -> list[dict]:
    feedback_path = run / "feedback.jsonl"
    rows = [json.loads(line) for line in feedback_path.read_text().splitlines()] if feedback_path.exists() else []
    return [row for row in rows if row["target"] in targets]


def feedback_text(rows: list[dict]) -> str:
    return "\n".join(f"- [{row['target']} · {row['scope']}] {row['text']}" for row in rows) or "none"


def load_scene_plans(run: Path) -> list[ScenePlan]:
    """The valid scene plans, in order. An invalid plan.json is skipped here; next_steps reports it."""
    plans = []
    for plan_path in sorted((run / "scenes").glob("s[0-9][0-9]/plan.json")):
        try:
            plans.append(ScenePlan.model_validate_json(plan_path.read_text()))
        except ValueError:
            continue
    return plans


def save_versioned(path: Path, text: str) -> bool:
    """Write text; keep the old content as name.vN.ext. Returns True if the content changed."""
    if path.exists() and path.read_text() == text:
        return False
    if path.exists():
        version = len(list(path.parent.glob(f"{path.stem}.v*{path.suffix}"))) + 1
        shutil.copy(path, path.with_name(f"{path.stem}.v{version}{path.suffix}"))
    path.write_text(text)
    return True


# ── clips: plan every scene as clips, then verify the math ─────────────────────────────────────────────────────


def scene_end_problems(plan: ScenePlan) -> list[str]:
    """Each scene renders as its own Manim Scene, so no object can cross a scene boundary."""
    problems = []
    if plan.clips[0].entry.persistent_objects:
        problems.append(f"{plan.clips[0].clip_id} entry must be empty (scenes start on an empty frame)")
    if plan.clips[-1].exit.persistent_objects:
        problems.append(f"{plan.clips[-1].clip_id} exit must be empty (scenes end with everything faded out)")
    return problems


def voice_key(run: Path, spoken: str) -> str:
    brief = cli.read_json(run / "brief.json")
    return content_hash(spoken, brief.get("tts", "polly"), brief.get("voice"), brief.get("engine"))


def stale_audio(run: Path, plans: list[ScenePlan]) -> set[str]:
    """Clips whose audio is missing or was made from different narration text/voice."""
    pairs = narration.case_pairs([clip.narration for plan in plans for clip in plan.clips])
    stale_clip_ids = set()
    for plan in plans:
        index_path = run / "scenes" / plan.scene_id / "audio" / "index.json"
        audio_index = cli.read_json(index_path) if index_path.exists() else {}
        stale_clip_ids |= {
            clip.clip_id
            for clip in plan.clips
            if audio_index.get(clip.clip_id, {}).get("hash")
            != voice_key(run, narration.speakable(clip.narration, pairs))
        }
    return stale_clip_ids


# ── voice: one narration file per clip (audio first: timings come from the real audio) ─────────────────────────


def handle_voice_command(arguments) -> None:
    run = Path(arguments.run)
    brief = cli.read_json(run / "brief.json")
    synthesize_clip = None
    plans = load_scene_plans(run)
    pairs = narration.case_pairs(
        [clip.narration for scene_plan in plans for clip in scene_plan.clips]
    )  # letters used as both M and m
    for plan in plans:
        audio_directory = run / "scenes" / plan.scene_id / "audio"
        audio_directory.mkdir(exist_ok=True)
        audio_index = cli.read_json(audio_directory / "index.json") if (audio_directory / "index.json").exists() else {}
        for clip in plan.clips:
            text = narration.speakable(clip.narration, pairs)
            voice_hash = voice_key(run, text)
            audio_path = audio_directory / f"clip_{clip.index:02d}.mp3"
            if audio_index.get(clip.clip_id, {}).get("hash") == voice_hash and audio_path.exists():
                continue  # unchanged text → keep the audio
            synthesize_clip = synthesize_clip or narration.create_speech_synthesizer(brief)
            audio, marks = synthesize_clip(text)
            audio_path.write_bytes(audio)
            audio_index[clip.clip_id] = {
                "hash": voice_hash,
                "seconds": round(cli.probe_duration_seconds(audio_path), 2),
                "spoken": text,
                "beat_times": narration.phrase_times(marks, clip.beats, pairs) if marks else None,
            }
            print(f"{clip.clip_id}: {audio_index[clip.clip_id]['seconds']}s")
        cli.write_json(audio_directory / "index.json", audio_index)
    total = sum(
        clip_audio["seconds"]
        for scene_plan in load_scene_plans(run)
        for clip_audio in cli.read_json(run / "scenes" / scene_plan.scene_id / "audio" / "index.json").values()
    )
    print(f"total narration: {total:.1f}s")


# ── build: one sandboxed agent per clip, gated by ./check, re-checked in a jail ─────────────────────────────────


def ensure_api_index() -> None:
    if not API_INDEX_PATH.exists():
        API_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [cli.PYTHON_EXECUTABLE, str(TOOLS_DIRECTORY / "build_manim_api_index.py"), "--out", str(API_INDEX_PATH)],
            check=True,
            capture_output=True,
        )


# ── deterministic stage commands for a Claude Code session: validate · task · accept · next steps ──────────────

OUTLINE_MODELS = {
    "zoom": ConceptualZoomOutline,
    "arc": ProblemSolutionArcOutline,
    "linear": ClassicLinearNarrativeOutline,
}
CLIP_BUILDER_AGENT_PATH = cli.REPOSITORY_ROOT / "run-environment" / "agents" / "clip-builder.md"
STANDARDS_PATH = (
    cli.REPOSITORY_ROOT / "run-environment" / "skills" / "text-2-shorts-produce" / "references" / "standards.md"
)


def format_validation_errors(validation_error: ValidationError) -> list[str]:
    return [f"{'.'.join(map(str, error['loc']))}: {error['msg']}" for error in validation_error.errors()]


def validate_outline(run: Path) -> list[str]:
    """outline.json against the brief's approach schema, plus the length rule (±20% of the requested minutes)."""
    brief = cli.read_json(run / "brief.json")
    try:
        outline = OUTLINE_MODELS[brief.get("approach", "zoom")].model_validate_json((run / "outline.json").read_text())
    except FileNotFoundError:
        return ["outline.json does not exist"]
    except ValidationError as validation_error:
        return format_validation_errors(validation_error)
    total, target = sum(scene.duration_seconds for scene in outline.outline), brief["minutes"] * 60
    return (
        []
        if abs(total - target) <= 0.2 * target
        else [
            f"scenes total {total}s but the target is {target:.0f}s (±20%): "
            "rescale duration_seconds, drop or merge scenes"
        ]
    )


def validate_plan(run: Path, scene_id: str) -> list[str]:
    """scenes/sNN/plan.json: ScenePlan contracts, empty scene boundaries, symbol colours consistent with earlier
    scenes."""
    try:
        plan = ScenePlan.model_validate_json((run / "scenes" / scene_id / "plan.json").read_text())
    except FileNotFoundError:
        return [f"scenes/{scene_id}/plan.json does not exist"]
    except ValidationError as validation_error:
        return format_validation_errors(validation_error)
    errors = [] if plan.scene_id == scene_id else [f"scene_id is {plan.scene_id}, expected {scene_id}"]
    errors += scene_end_problems(plan)
    for earlier in (candidate for candidate in load_scene_plans(run) if candidate.scene_id < scene_id):
        errors += [
            f"`{symbol}` is {color} here but {earlier.color_roles[symbol]} in {earlier.scene_id}: one colour per symbol"
            for symbol, color in plan.color_roles.items()
            if earlier.color_roles.get(symbol, color) != color
        ]
    return errors


def validate_math(run: Path) -> list[str]:
    try:
        report = MathReport.model_validate_json((run / "math.json").read_text())
    except FileNotFoundError:
        return ["math.json does not exist"]
    except ValidationError as validation_error:
        return format_validation_errors(validation_error)
    known = {clip.clip_id for plan in load_scene_plans(run) for clip in plan.clips}
    return [f"unknown clip {finding.clip_id}" for finding in report.findings if finding.clip_id not in known]


def load_clip_plan(run: Path, clip_id: str):
    plan = ScenePlan.model_validate_json((run / "scenes" / clip_id[:3] / "plan.json").read_text())
    return plan, next(clip for clip in plan.clips if clip.clip_id == clip_id)


def clip_key(run: Path, plan: ScenePlan, clip) -> str:
    """Everything a clip's code depends on; the previous clip's installed code makes changes cascade in order."""
    scene_directory = run / "scenes" / plan.scene_id
    previous_clip_path = scene_directory / "clips" / f"clip_{clip.index - 1:02d}.py"
    audio_index_path = scene_directory / "audio" / "index.json"
    return content_hash(
        clip.model_dump(),
        cli.read_json(audio_index_path).get(clip.clip_id) if audio_index_path.exists() else None,
        plan.color_roles,
        feedback_for(run, plan.scene_id, clip.clip_id),
        previous_clip_path.read_text() if clip.index > 1 and previous_clip_path.exists() else "",
        cli.read_json(run / "brief.json").get("font"),
        CLIP_BUILDER_AGENT_PATH.read_text() if CLIP_BUILDER_AGENT_PATH.exists() else "",
    )


def prepare_clip(run: Path, clip_id: str) -> Path:
    """Set up scenes/sNN/work/clip_MM/ for the clip-builder: TASK.md/.json, API_CARDS.md, ./check, earlier clips."""
    plan, clip = load_clip_plan(run, clip_id)
    scene_directory, clip_name = run / "scenes" / plan.scene_id, f"clip_{clip.index:02d}"
    clip_states = load_state(run)["clips"]
    missing = [
        earlier.clip_id
        for earlier in plan.clips[: clip.index - 1]
        if clip_states.get(earlier.clip_id, {}).get("status") != "READY"
    ]
    if missing:
        sys.exit(f"build {missing[0]} first: {clip_id} starts from its exit state")
    audio = cli.read_json(scene_directory / "audio" / "index.json")[clip_id]
    brief = cli.read_json(run / "brief.json")
    math_findings = cli.read_json(run / "math.json")["findings"] if (run / "math.json").exists() else []
    math_notes = [
        f"{finding['kind']}: \"{finding['quote']}\" → {finding['fix']}"
        for finding in math_findings
        if finding["clip_id"] == clip_id
    ]
    ensure_api_index()
    work_directory = scene_directory / "work" / clip_name
    work_directory.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(work_directory / "scene", ignore_errors=True)
    shutil.rmtree(work_directory / "checks", ignore_errors=True)
    (work_directory / "scene" / "clips").mkdir(parents=True)
    (scene_directory / "clips").mkdir(exist_ok=True)
    for earlier in plan.clips[: clip.index - 1]:  # snapshot of the approved clips before this one
        shutil.copy(scene_directory / "clips" / f"clip_{earlier.index:02d}.py", work_directory / "scene" / "clips")
    if (scene_directory / "clips" / f"{clip_name}.py").exists() and not (work_directory / f"{clip_name}.py").exists():
        shutil.copy(
            scene_directory / "clips" / f"{clip_name}.py", work_directory
        )  # a rebuild starts from the approved version
    task = {
        "clip_name": clip_name,
        "clip_id": clip_id,
        "scene_id": plan.scene_id,
        "scene_class_name": "Scene" + plan.scene_id[1:],
        "clip_seconds": round(VOICE_LEAD_IN_SECONDS + audio["seconds"] + END_HOLD_SECONDS, 2),
        "entry": clip.entry.persistent_objects,
        "exit": clip.exit.persistent_objects,
        "api_index": str(API_INDEX_PATH),
        "background": VIDEO_STYLE["background"],
    }
    cli.write_json(work_directory / "TASK.json", task)
    beat_times = audio.get("beat_times") or [None] * len(clip.beats)  # word timings → when the voice says each phrase
    beats = "\n".join(
        f"  {i}. {'' if beat_time is None else f'@ {VOICE_LEAD_IN_SECONDS + beat_time:.1f}s  '}{beat}"
        for i, (beat, beat_time) in enumerate(zip(clip.beats, beat_times), 1)
    )
    (work_directory / "TASK.md").write_text(
        f"READ FIRST: {STANDARDS_PATH}, "
        + ", ".join(str(TOPICS_DIRECTORY / f"{topic}.md") for topic in ALWAYS_LOADED_TOPICS)
        + "\n"
        f"CLIP {clip_id}  (scene {plan.scene_id}, clip {clip.index} of {len(plan.clips)})   FILE: {clip_name}.py   "
        f"NARRATION_SECONDS: {audio['seconds']}   CLIP_SECONDS: {task['clip_seconds']} "
        f"(voice from {VOICE_LEAD_IN_SECONDS}s, hold {END_HOLD_SECONDS}s)\n"
        f"OBJECTIVE: {clip.objective}\nNARRATION (exact):\n  {clip.narration}\nVISUAL INTENT: {clip.visual_intent}\n"
        f"BEATS:\n{beats}\nON-SCREEN MATH (exact LaTeX): {json.dumps(clip.on_screen_math)}\n"
        f"ENTRY (already on screen, in self.reg): {json.dumps(clip.entry.model_dump())}\n"
        f"EXIT (must be in self.reg and on screen at the end): {json.dumps(clip.exit.model_dump())}\n"
        f"SYMBOL COLORS: {json.dumps(plan.color_roles)}   FONT: {brief.get('font') or 'Manim default'}\n"
        f"MATH NOTES (verified): {'; '.join(math_notes) or 'none'}\n"
        f"HUMAN_FEEDBACK:\n{feedback_text(feedback_for(run, plan.scene_id, clip_id))}\n"
        f"PREVIOUS ATTEMPT: "
        f"{clip_name + '.py exists — start from it' if (work_directory / f'{clip_name}.py').exists() else 'none'}\n"
    )
    topics = [topic for topic in dict.fromkeys(clip.manim_topics) if topic not in ALWAYS_LOADED_TOPICS]
    topic_cards = subprocess.run(
        [
            cli.PYTHON_EXECUTABLE,
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
    (work_directory / "check").write_text(
        f'#!/bin/sh\nexec "{cli.PYTHON_EXECUTABLE}" "{cli.REPOSITORY_ROOT / "app" / "clip_gates.py"}" "$@"\n'
    )
    (work_directory / "check").chmod(0o755)
    return work_directory


def accept_clip(run: Path, clip_id: str) -> dict:
    """Re-run every gate on the clip in a jail (it is LLM-written code); install it only if all pass."""
    plan, clip = load_clip_plan(run, clip_id)
    scene_directory, clip_name = run / "scenes" / plan.scene_id, f"clip_{clip.index:02d}"
    work_directory = scene_directory / "work" / clip_name
    passed = (work_directory / f"{clip_name}.py").exists() and subprocess.run(
        cli.RENDER_JAIL_PREFIX
        + [
            "--bind",
            str(work_directory),
            str(work_directory),
            cli.PYTHON_EXECUTABLE,
            str(cli.REPOSITORY_ROOT / "app" / "clip_gates.py"),
            "all",
        ],
        cwd=work_directory,
        capture_output=True,
    ).returncode == 0
    findings = [
        f"{gate.stem}: {finding['code']}"
        for gate in sorted((work_directory / "checks").glob("*.json"))
        for finding in cli.read_json(gate).get("findings", [])
        if finding.get("severity") == "ERROR"
    ]
    if passed:
        shutil.copy(work_directory / f"{clip_name}.py", scene_directory / "clips" / f"{clip_name}.py")
    result = {
        "status": "READY" if passed else "FAILED",
        "open_findings": findings,
        "key": clip_key(run, plan, clip) if passed else None,
        "at": datetime.now().isoformat(timespec="seconds"),
    }
    update_state(run, lambda state: state["clips"].__setitem__(clip_id, result))
    return result


def fingerprint(run: Path, plans: list[ScenePlan]) -> str:
    """The clip keys of these scenes: changes whenever any clip they contain would be rebuilt."""
    return content_hash([clip_key(run, plan, clip) for plan in plans for clip in plan.clips])


def is_approval_current(state: dict, target: str, expected_fingerprint: str) -> bool:
    approval = state["approved"].get(target)
    return isinstance(approval, dict) and approval.get("fingerprint") == expected_fingerprint


def next_steps(run: Path) -> list[str]:
    """What is left to do, in order — the resume point after any interruption. Approvals and the final render are
    compared with the current clip keys, so anything rebuilt since is asked again."""
    state, steps = load_state(run), []
    brief = cli.read_json(run / "brief.json") if (run / "brief.json").exists() else {}
    scene_count = 0
    if brief.get("approach"):
        outline_errors = validate_outline(run)
        steps += [f"outline: {error}" for error in outline_errors]
        if not outline_errors:
            scene_count = len(cli.read_json(run / "outline.json")["outline"])
        if "outline" not in state["approved"]:
            steps.append("CP1: approve the outline (text-2-shorts approve <run> outline)")
    scene_ids = sorted(
        {f"s{i:02d}" for i in range(1, scene_count + 1)}
        | {plan_path.parent.name for plan_path in (run / "scenes").glob("s[0-9][0-9]/plan.json")}
    )
    for scene_id in scene_ids:
        steps += [f"{scene_id} plan: {error}" for error in validate_plan(run, scene_id)]
    plans = load_scene_plans(run)
    if plans and "plan" not in state["approved"]:
        steps.append("CP2: math review + approve the clip plan (text-2-shorts approve <run> plan)")
    if stale := stale_audio(run, plans):
        steps.append(f"narration audio missing or outdated for {', '.join(sorted(stale))} (text-2-shorts voice <run>)")
    for plan in plans:
        if any(clip.clip_id in stale for clip in plan.clips):
            continue
        next_clip_id = next(
            (
                clip.clip_id
                for clip in plan.clips
                if state["clips"].get(clip.clip_id, {}).get("key") != clip_key(run, plan, clip)
            ),
            None,
        )
        if next_clip_id:
            steps.append(
                f"build {next_clip_id} (text-2-shorts task → clip-builder → text-2-shorts accept), "
                f"then the rest of {plan.scene_id}"
            )
        if not is_approval_current(state, f"scene:{plan.scene_id}", fingerprint(run, [plan])):
            steps.append(f"CP3: preview and approve {plan.scene_id}")
    if plans:
        current_fingerprint = fingerprint(run, plans)
        report = cli.read_json(run / "final_report.json") if (run / "final_report.json").exists() else {}
        if not (run / "final.mp4").exists() or report.get("fingerprint") != current_fingerprint:
            steps.append("text-2-shorts final <run>")
        elif not is_approval_current(state, "final", current_fingerprint):
            steps.append("CP4: approve the final video")
    return steps


# ── final: full-quality render per scene (sections → one file per clip), assembly, media checks ─────────────────


def handle_final_command(arguments) -> None:
    run = Path(arguments.run)
    state = load_state(run)
    plans = load_scene_plans(run)
    missing = [
        clip.clip_id
        for plan in plans
        for clip in plan.clips
        if state["clips"].get(clip.clip_id, {}).get("status") != "READY"
    ]
    if missing:
        sys.exit(f"Not built yet: {missing}. Run build first.")
    unapproved = [plan.scene_id for plan in plans if f"scene:{plan.scene_id}" not in state["approved"]]
    if unapproved and not arguments.force:
        sys.exit(f"Scene previews not approved (CP3): {unapproved} — `approve <run> sNN` (or --force).")
    if not 60 <= cli.FINAL_FRAME_RATE <= 120:
        sys.exit(f"TEXT_2_SHORTS_FPS={cli.FINAL_FRAME_RATE}: must be 60–120")

    def render_scene(plan: ScenePlan) -> dict:
        scene_directory = run / "scenes" / plan.scene_id
        subprocess.run(
            [
                cli.PYTHON_EXECUTABLE,
                str(TOOLS_DIRECTORY / "scene_harness.py"),
                "compose",
                str(scene_directory),
                "--scene-id",
                plan.scene_id,
            ],
            check=True,
            capture_output=True,
        )
        shutil.rmtree(scene_directory / "media_final", ignore_errors=True)
        render_process = subprocess.run(
            cli.RENDER_JAIL_PREFIX
            + [
                "--bind",
                str(scene_directory),
                str(scene_directory),
                "--setenv",
                "TEXT_2_SHORTS_BACKGROUND",
                VIDEO_STYLE["background"],
                cli.PYTHON_EXECUTABLE,
                str(TOOLS_DIRECTORY / "scene_harness.py"),
                "render",
                str(scene_directory),
                "--scene-id",
                plan.scene_id,
                "--quality",
                "p",
                "--fps",
                str(cli.FINAL_FRAME_RATE),
                "--media",
                "media_final",
            ],
            capture_output=True,
            text=True,
            timeout=7200,
        )
        try:
            return json.loads(render_process.stdout)
        except json.JSONDecodeError:
            return {"ok": False, "stderr_tail": render_process.stderr[-2000:]}

    scene_renders = dict(zip([plan.scene_id for plan in plans], cli.run_in_parallel(render_scene, plans)))
    failed = {
        scene_id: render_result.get("stderr_tail")
        for scene_id, render_result in scene_renders.items()
        if not render_result.get("ok")
    }
    if failed:
        sys.exit(f"Final render failed: {json.dumps(failed, indent=1)[:3000]}")
    manifest = {
        "scenes": [
            {
                "scene_id": plan.scene_id,
                "clips": [
                    {
                        "clip_id": clip.clip_id,
                        "video": str(
                            run
                            / "scenes"
                            / plan.scene_id
                            / next(
                                section["path"]
                                for section in scene_renders[plan.scene_id]["sections"]
                                if section["name"] == f"clip_{clip.index:02d}"
                            )
                        ),
                        "audio": str(run / "scenes" / plan.scene_id / "audio" / f"clip_{clip.index:02d}.mp3"),
                        "lead_in": VOICE_LEAD_IN_SECONDS,
                    }
                    for clip in plan.clips
                ],
            }
            for plan in plans
        ]
    }
    cli.write_json(run / "assembly.json", manifest)
    sys.path.insert(0, str(TOOLS_DIRECTORY))
    from assemble_clips import assemble  # noqa: E402  (tools/ is a script folder, not a package)

    report = assemble(manifest, run / "final.mp4", run / "assembly_work")
    report["checks"] = check_final_media(run / "final.mp4")
    report["fingerprint"] = fingerprint(run, plans)  # next_steps marks the video stale when any clip changes
    cli.write_json(run / "final_report.json", report)
    print(f"{run / 'final.mp4'}\nduration: {report['final_s']}s · clips: {len(report['clips'])}")
    for finding in report["checks"]:
        print(f"{finding['severity']} {finding['code']}: {finding['message']}")


def check_final_media(path: Path) -> list[dict]:
    """ffprobe streams + EBU R128 loudness + black frames (docs/architecture-plan.md §16.6)."""
    findings = []
    streams = json.loads(
        subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)], capture_output=True, text=True
        ).stdout
    )["streams"]
    video_stream = next((stream for stream in streams if stream["codec_type"] == "video"), {})
    if (video_stream.get("width"), video_stream.get("height")) != (2560, 1440):
        findings.append(
            {
                "severity": "ERROR",
                "code": "RESOLUTION",
                "message": f"{video_stream.get('width')}x{video_stream.get('height')}",
            }
        )
    numerator, _, denominator = (video_stream.get("avg_frame_rate") or "0/1").partition("/")
    if float(numerator) / float(denominator or 1) < 59.5:
        findings.append(
            {
                "severity": "ERROR",
                "code": "FRAME_RATE",
                "message": f"{video_stream.get('avg_frame_rate')} fps (minimum 60)",
            }
        )
    if not any(stream["codec_type"] == "audio" for stream in streams):
        findings.append({"severity": "ERROR", "code": "NO_AUDIO", "message": "no audio stream"})
    ffmpeg_log = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-af",
            "ebur128",
            "-vf",
            "blackdetect=d=1.0:pix_th=0.05",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    ).stderr
    lufs = [
        float(line.split("I:")[1].split("LUFS")[0])
        for line in ffmpeg_log.splitlines()
        if " I:" in line and "LUFS" in line
    ]
    if lufs and abs(lufs[-1] + 16) > 1.5:
        findings.append({"severity": "WARN", "code": "LOUDNESS", "message": f"{lufs[-1]} LUFS (target -16)"})
    blacks = [line for line in ffmpeg_log.splitlines() if "black_start" in line]
    if blacks:
        findings.append(
            {"severity": "WARN", "code": "BLACK_FRAMES", "message": f"{len(blacks)} black stretch(es) ≥ 1 s"}
        )
    return findings


# ── checkpoints: approve / feedback / status ────────────────────────────────────────────────────────────────────


def add_feedback(run: Path, target: str, scope: str, text: str) -> None:
    with run_lock(run), (run / "feedback.jsonl").open("a") as feedback_file:
        feedback_file.write(
            json.dumps(
                {"ts": datetime.now().isoformat(timespec="seconds"), "target": target, "scope": scope, "text": text}
            )
            + "\n"
        )


def handle_feedback_command(arguments) -> None:
    add_feedback(Path(arguments.run), arguments.target, arguments.scope, arguments.text)
    print(
        f"feedback recorded for {arguments.target} ({arguments.scope}). Apply it: "
        + (
            "edit the plan, then text-2-shorts validate and text-2-shorts voice"
            if arguments.scope in ("narration", "math", "plan")
            else "text-2-shorts task → clip-builder → text-2-shorts accept for that clip"
        )
        + "; text-2-shorts status lists what is now stale."
    )


def approval_problems(run: Path, target: str) -> list[str]:
    plans = load_scene_plans(run)
    if target == "outline":
        return validate_outline(run)
    if target == "plan":
        scene_count = len(cli.read_json(run / "outline.json")["outline"]) if not validate_outline(run) else 0
        problems = [
            f"s{i:02d}: {error}" for i in range(1, scene_count + 1) for error in validate_plan(run, f"s{i:02d}")
        ]
        problems += [f"math review: {error}" for error in validate_math(run)]
        if (run / "math.json").exists() and not validate_math(run):
            math_errors = [
                finding for finding in cli.read_json(run / "math.json")["findings"] if finding["severity"] == "ERROR"
            ]
            problems += [f"math ERROR in {finding['clip_id']}: {finding['why']}" for finding in math_errors]
        return problems or ([] if plans else ["no scene plans yet"])
    if target == "final":
        report = cli.read_json(run / "final_report.json") if (run / "final_report.json").exists() else {}
        return [] if report.get("fingerprint") == fingerprint(run, plans) else ["final.mp4 is missing or out of date"]
    scene_id = target.removeprefix("scene:")
    plan = next((scene_plan for scene_plan in plans if scene_plan.scene_id == scene_id), None)
    if plan is None:
        return [f"{scene_id}: no valid plan"]
    clip_states = load_state(run)["clips"]
    return [
        f"{scene_id}: {clip.clip_id} is not built from its current inputs"
        for clip in plan.clips
        if clip_states.get(clip.clip_id, {}).get("key") != clip_key(run, plan, clip)
    ]


def handle_approve_command(arguments) -> None:
    run = Path(arguments.run)
    target = arguments.target if arguments.target in ("outline", "plan", "final") else f"scene:{arguments.target}"
    problems = approval_problems(run, target)
    if problems and not arguments.force:
        sys.exit(
            f"cannot approve {target} yet:\n"
            + "\n".join(f"  - {problem}" for problem in problems)
            + "\n(use --force only if the user explicitly accepts these)"
        )
    plans = load_scene_plans(run)
    scope = plans if target == "final" else [plan for plan in plans if f"scene:{plan.scene_id}" == target]
    entry = {
        "at": datetime.now().isoformat(timespec="seconds"),
        "fingerprint": fingerprint(run, scope) if scope else None,
    }
    update_state(run, lambda state: state["approved"].__setitem__(target, entry))
    print(f"approved {target}" + (" (forced)" if problems else ""))


def status_text(run: Path) -> str:
    state = load_state(run)
    lines = [f"approved: {', '.join(state['approved']) or 'nothing yet'}"]
    clips = [
        (clip.clip_id, state["clips"].get(clip.clip_id, {})) for plan in load_scene_plans(run) for clip in plan.clips
    ]
    if clips:
        lines += ["| clip | status | open findings |", "|---|---|---|"]
        lines += [
            f"| {clip_id} | {clip_state.get('status', 'not built')} | "
            f"{', '.join(clip_state.get('open_findings', []))[:100]} |"
            for clip_id, clip_state in clips
        ]
    steps = next_steps(run)
    lines += (["next:"] + [f"  - {step}" for step in steps]) if steps else ["next: nothing — the video is done."]
    return "\n".join(lines)


def handle_status_command(arguments) -> None:
    print(status_text(Path(arguments.run)))


def sum_session_tokens(run: Path) -> dict:
    """Token totals from this run's Claude Code transcripts (recorded by the SessionStart hook), subagents included.
    Streaming writes one transcript line per content block with the same message id — count each message once."""
    totals, seen = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "messages": 0}, set()
    for transcript in load_state(run).get("sessions", []):
        transcript_path = Path(transcript)
        for transcript_file in (
            ([transcript_path] + sorted(transcript_path.with_suffix("").glob("**/*.jsonl")))
            if transcript_path.exists()
            else []
        ):
            for line in transcript_file.read_text().splitlines():
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                message = entry.get("message") or {}
                usage = message.get("usage")
                if entry.get("type") != "assistant" or not usage or message.get("id") in seen:
                    continue
                seen.add(message.get("id"))
                totals["input"] += usage.get("input_tokens", 0)
                totals["output"] += usage.get("output_tokens", 0)
                totals["cache_read"] += usage.get("cache_read_input_tokens", 0)
                totals["cache_write"] += usage.get("cache_creation_input_tokens", 0)
                totals["messages"] += 1
    return totals


def handle_report_command(arguments) -> None:
    totals = sum_session_tokens(Path(arguments.run))
    total_in = totals["input"] + totals["cache_read"] + totals["cache_write"]
    cached = f", {100 * totals['cache_read'] // total_in}% read from cache" if total_in else ""
    print(
        f"Claude Code sessions: {totals['messages']} model responses · input {total_in} tokens (net {totals['input']}, "
        f"cache read {totals['cache_read']}, cache write {totals['cache_write']}{cached}) "
        f"· output {totals['output']} tokens"
    )


def find_run_directory(*starts) -> Path | None:
    """The run folder (the one holding brief.json) at or above any of the given paths."""
    for start in filter(None, starts):
        start_path = Path(start).resolve()
        found = next(
            (directory for directory in [start_path, *start_path.parents] if (directory / "brief.json").exists()), None
        )
        if found:
            return found
    return None


def handle_hook_command(arguments) -> None:
    """Claude Code hooks (run-environment/hooks/hooks.json): SessionStart → record transcript + print status into
    context; PostToolUse → log the tool call; validate outline/plan/math files right after they are written (exit 2
    feeds the errors back to Claude)."""
    try:
        hook_event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    tool_input = hook_event.get("tool_input") or {}
    run = find_run_directory(hook_event.get("cwd"), tool_input.get("file_path"))
    if run is None:
        return  # not inside a run workspace
    if hook_event.get("hook_event_name") == "SessionStart":
        transcript_path = hook_event.get("transcript_path")
        if transcript_path:
            update_state(
                run,
                lambda state: (
                    state.setdefault("sessions", []).count(transcript_path) or state["sessions"].append(transcript_path)
                ),
            )
        print(f"Text-2-Shorts run {run.name}\n{status_text(run)}")
    elif hook_event.get("hook_event_name") == "PostToolUse":
        detail = tool_input.get("file_path") or tool_input.get("command") or tool_input.get("description") or ""
        with run_lock(run), (run / "log.jsonl").open("a") as log_file:
            log_file.write(
                json.dumps(
                    {
                        "ts": datetime.now().isoformat(timespec="seconds"),
                        "event": "tool",
                        "tool": hook_event.get("tool_name"),
                        "detail": str(detail)[:300],
                    }
                )
                + "\n"
            )
        written_path = Path(tool_input.get("file_path") or "")
        errors = (
            validate_outline(run)
            if written_path.name == "outline.json"
            else validate_plan(run, written_path.parent.name)
            if written_path.name == "plan.json" and written_path.parent.parent.name == "scenes"
            else validate_math(run)
            if written_path.name == "math.json"
            else []
        )
        if errors:
            print(f"{written_path.name} is invalid — fix it:\n" + "\n".join(errors), file=sys.stderr)
            sys.exit(2)


def handle_validate_command(arguments) -> None:
    run = Path(arguments.run)
    if arguments.what == "plan":
        scene_ids = (
            [arguments.scene]
            if arguments.scene
            else [plan_path.parent.name for plan_path in sorted((run / "scenes").glob("s[0-9][0-9]/plan.json"))]
        )
        errors = [f"{scene_id}: {error}" for scene_id in scene_ids for error in validate_plan(run, scene_id)]
    else:
        errors = validate_outline(run) if arguments.what == "outline" else validate_math(run)
    print("\n".join(errors) or f"{arguments.what}: OK")
    sys.exit(1 if errors else 0)


def handle_accept_command(arguments) -> None:
    result = accept_clip(Path(arguments.run), arguments.clip)
    print(
        f"{arguments.clip}: {result['status']}"
        + (f" — {', '.join(result['open_findings'])}" if result["open_findings"] else "")
    )
    sys.exit(0 if result["status"] == "READY" else 1)


def register_subcommands(subparsers) -> None:
    def add_subcommand(name, handler, *, scenes=False, clips=False, feedback=False, force=False):
        command_parser = subparsers.add_parser(name)
        command_parser.add_argument("run")
        if scenes:
            command_parser.add_argument("--scenes", help="comma-separated scene numbers")
        if clips:
            command_parser.add_argument("--clips", help="comma-separated clip ids to rebuild, e.g. s01c02")
        if feedback:
            command_parser.add_argument("--feedback")
        if force:
            command_parser.add_argument("--force", action="store_true")
        command_parser.set_defaults(handler=lambda arguments: handler(resolve_run_path(arguments)))
        return command_parser

    add_subcommand("voice", handle_voice_command)
    add_subcommand("final", handle_final_command, force=True)
    add_subcommand("status", handle_status_command)
    add_subcommand("report", handle_report_command)
    subparsers.add_parser("hook", help="Claude Code hook entry point (reads the hook JSON on stdin)").set_defaults(
        handler=handle_hook_command
    )
    command_parser = add_subcommand("validate", handle_validate_command)
    command_parser.add_argument("what", choices=["outline", "plan", "math"])
    command_parser.add_argument("--scene", help="sNN (plan only; default: every scene plan)")
    command_parser = add_subcommand("task", lambda arguments: print(prepare_clip(Path(arguments.run), arguments.clip)))
    command_parser.add_argument("clip", help="sNNcMM")
    command_parser = add_subcommand("accept", handle_accept_command)
    command_parser.add_argument("clip", help="sNNcMM")
    command_parser = add_subcommand("approve", handle_approve_command, force=True)
    command_parser.add_argument("target", help="outline | plan | sNN | final")
    command_parser = add_subcommand("feedback", handle_feedback_command)
    command_parser.add_argument("target", help="outline | sNN | sNNcMM")
    command_parser.add_argument("--scope", default="visual", choices=["narration", "math", "visual", "plan"])
    command_parser.add_argument("--text", required=True)


def resolve_run_path(arguments):
    arguments.run = str(Path(arguments.run).resolve())
    return arguments
