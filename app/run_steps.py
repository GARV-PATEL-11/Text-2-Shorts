"""Deterministic run-level steps that the run's Claude Code session calls (no LLM calls here).

The workflow is staged, and each stage starts only when the previous one is approved:
  1 requirements   brief.json                        `text-2-shorts new`, confirmed with the user
  2 script         script.json + script_review.json  the complete script; accuracy-reviewer → CP1
  3 visual plans   scenes/sNN/plan.json + plan_review.json   one plan per scene, split into clips; → CP2
  4 clips          scenes/sNN/clips/clip_MM.py       one clip-builder call per clip, in order; → CP3 per scene
  final            final.mp4                         → CP4
Ledger:
  runs/<id>/state.json              approvals (with fingerprints), per-clip build state, session transcripts
  runs/<id>/feedback.jsonl          human feedback, scoped to script | sNN | sNNcMM
  runs/<id>/log.jsonl               one row per tool call (PostToolUse hook)
  runs/<id>/scenes/sNN/audio/       clip_MM.mp3 + index.json (spoken text hash → seconds, beat start times)
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

from pydantic import ValidationError

from app import cli
from app import narration
from schemas.models import Brief, Critique, ReviewReport, ScenePlan, Script

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


# ── scene plans ─────────────────────────────────────────────────────


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
            != voice_key(run, narration.speakable_ssml(clip.ssml, pairs))
        }
    return stale_clip_ids


# ── voice: one audio file per clip, from its planned SSML (timings come from the real audio) ─────────────────────────


def handle_voice_command(arguments) -> None:
    run = Path(arguments.run)
    require_approval(run, "plan")
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
            text = narration.speakable_ssml(clip.ssml, pairs)  # the planned SSML, symbols spoken by name
            voice_hash = voice_key(run, text)
            audio_path = audio_directory / f"clip_{clip.index:02d}.mp3"
            if audio_index.get(clip.clip_id, {}).get("hash") == voice_hash and audio_path.exists():
                continue  # unchanged SSML → keep the audio
            synthesize_clip = synthesize_clip or narration.create_speech_synthesizer(brief)
            audio, marks = synthesize_clip(text)
            audio_path.write_bytes(audio)
            audio_index[clip.clip_id] = {
                "hash": voice_hash,
                "seconds": round(cli.probe_duration_seconds(audio_path), 2),
                "spoken": narration.to_plain(text),
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

CLIP_BUILDER_AGENT_PATH = cli.REPOSITORY_ROOT / "run-environment" / "agents" / "clip-builder.md"
STANDARDS_PATH = (
    cli.REPOSITORY_ROOT / "run-environment" / "skills" / "text-2-shorts-produce" / "references" / "standards.md"
)
REVIEW_FILES = {"script": "script_review.json", "plan": "plan_review.json"}
CHECKPOINTS = {"script": "CP1 (the complete script)", "plan": "CP2 (the scene visual plans)"}
WORD_BUDGET_TOLERANCE = 0.25  # spoken words per scene vs duration_seconds × target_wpm / 60


def format_validation_errors(validation_error: ValidationError) -> list[str]:
    return [f"{'.'.join(map(str, error['loc']))}: {error['msg']}" for error in validation_error.errors()]


def validate_brief(run: Path) -> list[str]:
    """Stage 1: brief.json holds the user's requirements."""
    try:
        Brief.model_validate_json((run / "brief.json").read_text())
    except FileNotFoundError:
        return ["brief.json does not exist"]
    except ValidationError as validation_error:
        return format_validation_errors(validation_error)
    return []


def load_script(run: Path) -> Script | None:
    try:
        return Script.model_validate_json((run / "script.json").read_text())
    except (FileNotFoundError, ValueError):
        return None


def spoken_text(scene) -> str:
    """What the voice says in one script scene: the bridge, then the narration (whitespace-normalised)."""
    return " ".join(f"{scene.bridge_in} {scene.narration}".split())


def validate_script(run: Path) -> list[str]:
    """Stage 2: script.json — every objective covered, every scene after the first bridged, each scene's narration
    sized for its duration, the whole video within ±20% of the requested length."""
    brief = cli.read_json(run / "brief.json") if (run / "brief.json").exists() else {}
    try:
        script = Script.model_validate_json((run / "script.json").read_text())
    except FileNotFoundError:
        return ["script.json does not exist"]
    except ValidationError as validation_error:
        return format_validation_errors(validation_error)
    covered = {index for scene in script.scenes for index in scene.covers}
    errors = [
        f"objective {index} is not covered by any scene: {objective!r}"
        for index, objective in enumerate(script.objectives, 1)
        if index not in covered
    ]
    errors += [
        f"brief objective missing from the script's objectives: {objective!r}"
        for objective in brief.get("objectives", [])
        if objective not in script.objectives
    ]
    for scene in script.scenes:
        budget = scene.duration_seconds * script.target_wpm / 60
        count = len([word for word in spoken_text(scene).split() if word != narration.PAUSE])
        if abs(count - budget) > WORD_BUDGET_TOLERANCE * budget:
            errors.append(
                f"{scene.scene_id} has {count} spoken words, but {scene.duration_seconds:g}s "
                f"at {script.target_wpm} wpm "
                f"needs about {budget:.0f} (±25%): rewrite the narration or change duration_seconds"
            )
    if minutes := brief.get("minutes"):
        total, target = sum(scene.duration_seconds for scene in script.scenes), minutes * 60
        if abs(total - target) > 0.2 * target:
            errors.append(
                f"scenes total {total:g}s but the target is {target:.0f}s (±20%): "
                "rescale duration_seconds, drop or merge scenes"
            )
    return errors


def script_fingerprint(run: Path) -> str | None:
    return content_hash(cli.read_json(run / "script.json")) if (run / "script.json").exists() else None


def plans_fingerprint(run: Path) -> str:
    """CP2 approves the visual plans; SSML is excluded because the audio is re-timed to the built video later."""
    return content_hash(
        [
            plan.model_dump(exclude={"clips": {index: {"ssml"} for index in range(len(plan.clips))}})
            for plan in load_scene_plans(run)
        ]
    )


STAGE_FINGERPRINTS = {"script": script_fingerprint, "plan": plans_fingerprint}


def stage_approval_problem(run: Path, stage: str) -> str | None:
    """None when the stage's checkpoint is approved for exactly the current artifacts, else why not."""
    if is_approval_current(load_state(run), stage, STAGE_FINGERPRINTS[stage](run)):
        return None
    checkpoint = CHECKPOINTS[stage]
    return f"{checkpoint} is not approved, or changed since it was approved: get {checkpoint.split()[0]} first"


def earlier_scene_problem(run: Path, scene_id: str) -> str | None:
    """Scenes are produced in series: a scene's clips and preview start once every earlier scene passed CP3."""
    state = load_state(run)
    for plan in load_scene_plans(run):
        if plan.scene_id >= scene_id:
            return None
        if not is_approval_current(state, f"scene:{plan.scene_id}", fingerprint(run, [plan])):
            return f"scenes are produced in series: finish {plan.scene_id} (CP3) before {scene_id}"
    return None


def require_earlier_scenes(run: Path, scene_id: str) -> None:
    if problem := earlier_scene_problem(run, scene_id):
        sys.exit(problem)


def require_approval(run: Path, stage: str) -> None:
    if problem := stage_approval_problem(run, stage):
        sys.exit(problem)


def validate_plan(run: Path, scene_id: str) -> list[str]:
    """Stage 3: scenes/sNN/plan.json — only after CP1; the clips speak exactly the approved script's text for the scene;
    scenes after the first describe their opening transition; empty scene boundaries; one colour per symbol."""
    if problem := stage_approval_problem(run, "script"):
        return [problem]
    try:
        plan = ScenePlan.model_validate_json((run / "scenes" / scene_id / "plan.json").read_text())
    except FileNotFoundError:
        return [f"scenes/{scene_id}/plan.json does not exist"]
    except ValidationError as validation_error:
        return format_validation_errors(validation_error)
    errors = [] if plan.scene_id == scene_id else [f"scene_id is {plan.scene_id}, expected {scene_id}"]
    script = load_script(run)
    script_scene = next((scene for scene in script.scenes if scene.scene_id == scene_id), None) if script else None
    if script_scene is None:
        errors.append(f"{scene_id} is not a scene of the approved script")
    else:
        if " ".join(" ".join(clip.narration for clip in plan.clips).split()) != spoken_text(script_scene):
            errors.append(
                f"{scene_id}: the clips' narration must be the script's spoken text for this scene (bridge_in, then "
                "narration), word for word and in order; to change what is said, edit script.json and get CP1 again"
            )
        for clip in plan.clips:
            if undescribed := [n for n in clip.entry.persistent_objects if n not in clip.entry.descriptions]:
                errors.append(
                    f"{clip.clip_id} entry: add {undescribed} to entry.descriptions (type, text or LaTeX, colour) — "
                    "clips are built in parallel and re-create what they take over when run alone"
                )
            if problems := narration.ssml_problems(clip.ssml):
                errors += [f"{clip.clip_id} ssml: {problem}" for problem in problems]
            elif [w for w in narration.ssml_words(clip.ssml) if w != narration.PAUSE] != [
                w for w in clip.narration.split() if w != narration.PAUSE
            ]:
                errors.append(
                    f"{clip.clip_id} ssml must speak exactly the clip's narration (add tags, never change words)"
                )
        if scene_id != "s01" and not plan.transition_in.strip():
            errors.append(
                f"{scene_id} transition_in is empty: describe how it opens from the previous scene's final image"
            )
    errors += scene_end_problems(plan)
    for earlier in (candidate for candidate in load_scene_plans(run) if candidate.scene_id < scene_id):
        errors += [
            f"`{symbol}` is {color} here but {earlier.color_roles[symbol]} in {earlier.scene_id}: one colour per symbol"
            for symbol, color in plan.color_roles.items()
            if earlier.color_roles.get(symbol, color) != color
        ]
    return errors


def validate_review(run: Path, stage: str) -> list[str]:
    """script_review.json (findings per scene) or plan_review.json (findings per clip), from the accuracy-reviewer."""
    name = REVIEW_FILES[stage]
    try:
        report = ReviewReport.model_validate_json((run / name).read_text())
    except FileNotFoundError:
        return [f"{name} does not exist: run the accuracy-reviewer subagent"]
    except ValidationError as validation_error:
        return [f"{name}: {error}" for error in format_validation_errors(validation_error)]
    if stage == "script":
        script = load_script(run)
        known = {scene.scene_id for scene in script.scenes} if script else set()
    else:
        known = {clip.clip_id for plan in load_scene_plans(run) for clip in plan.clips}
    return [f"{name}: unknown target {finding.target}" for finding in report.findings if finding.target not in known]


MAX_CRITIQUE_ROUNDS = 3
CRITICS = {"plan": "plan-critic", "video": "video-critic"}


def scene_video_hash(run: Path, scene_id: str) -> str | None:
    """The scene's current video: its clips' keys and their audio (filled in by the preview step)."""
    plan = next((plan for plan in load_scene_plans(run) if plan.scene_id == scene_id), None)
    return scene_fingerprint(run, plan) if plan else None


def critique_subject_hash(run: Path, scene_id: str, kind: str) -> str | None:
    """What a critique round must have reviewed: the scene plan as it is now, or the scene's current video."""
    if kind == "plan":
        path = run / "scenes" / scene_id / "plan.json"
        return content_hash(cli.read_json(path)) if path.exists() else None
    return scene_video_hash(run, scene_id)


def validate_critique(run: Path, scene_id: str, kind: str) -> list[str]:
    name = f"scenes/{scene_id}/{kind}_critique.json"
    try:
        critique = Critique.model_validate_json((run / name).read_text())
    except FileNotFoundError:
        return [f"{name} does not exist: run the {CRITICS[kind]} subagent"]
    except ValidationError as validation_error:
        return [f"{name}: {error}" for error in format_validation_errors(validation_error)]
    errors = []
    if len(critique.rounds) > MAX_CRITIQUE_ROUNDS:
        errors.append(f"{name} has {len(critique.rounds)} rounds: the loop stops after {MAX_CRITIQUE_ROUNDS} rounds")
    plan = next((plan for plan in load_scene_plans(run) if plan.scene_id == scene_id), None)
    known = {scene_id} | ({clip.clip_id for clip in plan.clips} if plan else set())
    errors += [
        f"{name}: unknown target {issue.target}"
        for critique_round in critique.rounds
        for issue in critique_round.issues
        if issue.target not in known
    ]
    return errors


def critique_problems(run: Path, scene_id: str, kind: str) -> list[str]:
    """Empty when the last critique round passed the current version; after 3 rounds the open issues go to the
    user, who accepts them (approve --force) or asks for fixes."""
    if errors := validate_critique(run, scene_id, kind):
        return errors
    rounds = Critique.model_validate_json((run / "scenes" / scene_id / f"{kind}_critique.json").read_text()).rounds
    last, current = rounds[-1], critique_subject_hash(run, scene_id, kind)
    if last.verdict == "pass" and last.reviewed == current:
        return []
    if len(rounds) < MAX_CRITIQUE_ROUNDS:
        next_round = f"round {len(rounds) + 1} of {MAX_CRITIQUE_ROUNDS}"
        if last.reviewed != current:
            return [
                f"{scene_id}: the {kind} changed since the last critique round — run the {CRITICS[kind]} ({next_round})"
            ]
        return [f"{scene_id}: {kind} critique round {len(rounds)} asks for changes — refactor, then {next_round}"]
    issues = "; ".join(f"{issue.target} {issue.aspect}: {issue.problem}" for issue in last.issues)
    return [
        f"{scene_id}: {MAX_CRITIQUE_ROUNDS} critique rounds used — open issues for the user to accept or fix: "
        + (issues or f"the last {kind} change was not critiqued")
    ]


def critique_state(run: Path, scene_id: str, kind: str) -> str:
    """missing · stale (the version changed since the last round) · revise · exhausted (3 rounds, issues left) ·
    done (the last round passed the current version)."""
    if validate_critique(run, scene_id, kind):
        return "missing"
    rounds = Critique.model_validate_json((run / "scenes" / scene_id / f"{kind}_critique.json").read_text()).rounds
    last, current = rounds[-1], critique_subject_hash(run, scene_id, kind)
    if last.verdict == "pass" and last.reviewed == current:
        return "done"
    if len(rounds) >= MAX_CRITIQUE_ROUNDS:
        return "exhausted"
    return "stale" if last.reviewed != current else "revise"


def review_problems(run: Path, stage: str) -> list[str]:
    """The review file's own errors, else its ERROR findings (which block the checkpoint)."""
    if errors := validate_review(run, stage):
        return errors
    findings = cli.read_json(run / REVIEW_FILES[stage])["findings"]
    return [f"accuracy ERROR in {f['target']}: {f['why']}" for f in findings if f["severity"] == "ERROR"]


def review_notes(run: Path, scene_id: str, clip_id: str) -> list[str]:
    """Accuracy findings that concern this clip (its scene in the script review, the clip in the plan review)."""
    findings = [
        finding
        for name in REVIEW_FILES.values()
        if (run / name).exists()
        for finding in cli.read_json(run / name)["findings"]
        if finding["target"] in (scene_id, clip_id)
    ]
    return [f"{finding['kind']}: \"{finding['quote']}\" → {finding['fix']}" for finding in findings]


def load_clip_plan(run: Path, clip_id: str):
    plan = ScenePlan.model_validate_json((run / "scenes" / clip_id[:3] / "plan.json").read_text())
    return plan, next(clip for clip in plan.clips if clip.clip_id == clip_id)


def clip_key(run: Path, plan: ScenePlan, clip) -> str:
    """Everything a clip's code depends on. Clips are independent (built in parallel; the entry contract is their
    interface), so another clip's code is not part of it; nor are its SSML and audio, which are re-timed to the
    built video."""
    return content_hash(
        clip.model_dump(exclude={"ssml"}),
        plan.color_roles,
        feedback_for(run, plan.scene_id, clip.clip_id),
        cli.read_json(run / "brief.json").get("font"),
        CLIP_BUILDER_AGENT_PATH.read_text() if CLIP_BUILDER_AGENT_PATH.exists() else "",
    )


def prepare_clip(run: Path, clip_id: str) -> Path:
    """Set up scenes/sNN/work/clip_MM/ for the clip-builder: TASK.md/.json, API_CARDS.md, ./check, earlier clips."""
    require_approval(run, "plan")
    plan, clip = load_clip_plan(run, clip_id)
    require_earlier_scenes(run, plan.scene_id)
    scene_directory, clip_name = run / "scenes" / plan.scene_id, f"clip_{clip.index:02d}"
    audio = cli.read_json(scene_directory / "audio" / "index.json")[clip_id]
    brief = cli.read_json(run / "brief.json")
    accuracy_notes = review_notes(run, plan.scene_id, clip_id)
    ensure_api_index()
    work_directory = scene_directory / "work" / clip_name
    work_directory.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(work_directory / "scene", ignore_errors=True)
    shutil.rmtree(work_directory / "checks", ignore_errors=True)
    (work_directory / "scene" / "clips").mkdir(parents=True)
    (scene_directory / "clips").mkdir(exist_ok=True)  # the clip is built and checked on its own (no earlier clips)
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
        "beats": len(clip.beats),
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
        f"BEATS (call self.beat(n) where beat n starts):\n{beats}\n"
        f"ON-SCREEN MATH (exact LaTeX): {json.dumps(clip.on_screen_math)}\n"
        f"ENTRY (take each object with self.entry(name, lambda: <object as described>): in the scene it is the "
        f"previous clip's object; when this clip runs alone it is built from the description): "
        f"{json.dumps(clip.entry.model_dump())}\n"
        f"EXIT (must be in self.reg and on screen at the end): {json.dumps(clip.exit.model_dump())}\n"
        f"SYMBOL COLORS: {json.dumps(plan.color_roles)}   FONT: {brief.get('font') or 'Manim default'}\n"
        f"ACCURACY NOTES (verified): {'; '.join(accuracy_notes) or 'none'}\n"
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


def scene_fingerprint(run: Path, plan: ScenePlan) -> str:
    """A scene's video and audio as they are now: its clip keys plus each clip's audio."""
    audio_index_path = run / "scenes" / plan.scene_id / "audio" / "index.json"
    audio_index = cli.read_json(audio_index_path) if audio_index_path.exists() else {}
    return content_hash(
        [clip_key(run, plan, clip) for clip in plan.clips], [audio_index.get(clip.clip_id) for clip in plan.clips]
    )


def fingerprint(run: Path, plans: list[ScenePlan]) -> str:
    """These scenes' videos and audio: changes whenever a clip would be rebuilt or its audio changes."""
    return content_hash([scene_fingerprint(run, plan) for plan in plans])


def is_approval_current(state: dict, target: str, expected_fingerprint: str | None) -> bool:
    """True when the target was approved for exactly these artifacts (nothing to approve is never approved)."""
    approval = state["approved"].get(target)
    return (
        expected_fingerprint is not None
        and isinstance(approval, dict)
        and approval.get("fingerprint") == expected_fingerprint
    )


def next_steps(run: Path) -> list[str]:
    """What is left to do, in order — the resume point after any interruption. Approvals and the final render are
    compared with the current clip keys, so anything rebuilt since is asked again."""
    state = load_state(run)
    steps = [f"brief: {error}" for error in validate_brief(run)]
    script_errors = validate_script(run)
    steps += [f"script: {error}" for error in script_errors]
    if not script_errors:
        steps += [f"script review: {problem}" for problem in review_problems(run, "script")]
    if stage_approval_problem(run, "script"):
        steps.append(
            "CP1: show the user the complete script and the accuracy findings; approve with "
            "`text-2-shorts approve <run> script`"
        )
        return steps  # no visual planning before the script is approved
    script = load_script(run)
    plan_errors = [
        f"{scene.scene_id} plan: {error}"
        for scene in (script.scenes if script else [])
        for error in validate_plan(run, scene.scene_id)
    ]
    steps += plan_errors
    steps += [
        f"plan critique: {problem}"
        for scene in (script.scenes if script else [])
        if not validate_plan(run, scene.scene_id)
        for problem in critique_problems(run, scene.scene_id, "plan")
    ]
    if not plan_errors:
        steps += [f"plan review: {problem}" for problem in review_problems(run, "plan")]
    if stage_approval_problem(run, "plan"):
        steps.append(
            "CP2: show the user every scene's visual plan and the accuracy findings; approve with "
            "`text-2-shorts approve <run> plan`"
        )
        return steps  # no voice or clip code before the visual plans are approved
    plans = load_scene_plans(run)
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
        else:
            steps += preview_problems(run, plan) or [
                f"video critique: {problem}" for problem in critique_problems(run, plan.scene_id, "video")
            ]
        if not is_approval_current(state, f"scene:{plan.scene_id}", fingerprint(run, [plan])):
            steps.append(f"CP3: preview and approve {plan.scene_id}")
            break  # scenes are produced in series: later scenes wait for this one
    if plans:
        current_fingerprint = fingerprint(run, plans)
        report = cli.read_json(run / "final_report.json") if (run / "final_report.json").exists() else {}
        if not (run / "final.mp4").exists() or report.get("fingerprint") != current_fingerprint:
            steps.append("text-2-shorts final <run>")
        elif not is_approval_current(state, "final", current_fingerprint):
            steps.append("CP4: approve the final video")
    return steps


# ── the driver: exactly the next batch of work, in order (scenes in series, a scene's clips in parallel) ─────────

REFERENCES_DIRECTORY = STANDARDS_PATH.parent


def next_actions(run: Path) -> dict:
    """The one batch to do now. The session runs it (in parallel when `parallel`), then asks again. Each action names
    who does it (you, a subagent, a command, the user), its target, and the files to read — by path."""

    def references(*names):
        return [str(REFERENCES_DIRECTORY / name) for name in names]

    def batch(stage, actions, parallel=False):
        return {"stage": stage, "parallel": parallel, "actions": actions}

    def reviewer(stage, mode, file, problems):
        if validate_review(run, stage):
            return [{"do": "subagent", "agent": "accuracy-reviewer", "target": mode, "what": f"{mode} mode → {file}"}]
        return [
            {
                "do": "write",
                "file": "script.json" if stage == "script" else "scenes/*/plan.json",
                "what": "fix: " + "; ".join(problems),
            },
            {"do": "subagent", "agent": "accuracy-reviewer", "target": mode, "what": f"{mode} mode again → {file}"},
        ]

    def critic_loop(scene_id, kind, refactor_file, read):
        state = critique_state(run, scene_id, kind)
        critic = {
            "do": "subagent",
            "agent": CRITICS[kind],
            "target": scene_id,
            "what": f"one critique round → scenes/{scene_id}/{kind}_critique.json",
        }
        if state in ("missing", "stale"):
            return [critic]
        if state == "revise":
            return [
                {
                    "do": "write",
                    "file": refactor_file,
                    "read": read,
                    "what": f"fix the issues of the last {kind} critique round of {scene_id}",
                },
                critic,
            ]
        return []

    if errors := validate_brief(run):
        return batch(
            "1 requirements",
            [
                {
                    "do": "ask_user",
                    "file": "brief.json",
                    "read": references("requirements.md"),
                    "what": "complete and confirm the requirements: " + "; ".join(errors),
                }
            ],
        )
    if errors := validate_script(run):
        return batch(
            "2 script",
            [
                {
                    "do": "write",
                    "file": "script.json",
                    "what": "; ".join(errors[:3]),
                    "read": references(
                        "standards.md", "script-writing.md", "narrative-structures.md", "transitions.md"
                    ),
                }
            ],
        )
    if problems := review_problems(run, "script"):
        return batch("2 script", reviewer("script", "script", "script_review.json", problems))
    if stage_approval_problem(run, "script"):
        return batch(
            "2 script",
            [
                {
                    "do": "ask_user",
                    "what": "CP1: self-review, then show the scene table, the full "
                    "narration and the accuracy findings; on approval `text-2-shorts approve . script`",
                    "read": references("script-review.md"),
                }
            ],
        )
    script = load_script(run)
    for scene in script.scenes if script else []:  # plans: one scene at a time, each through its critic loop
        plan_file = f"scenes/{scene.scene_id}/plan.json"
        planning = references("scene-visual-planning.md", "audio-ssml.md", "transitions.md")
        if errors := validate_plan(run, scene.scene_id):
            return batch(
                "3 plans",
                [
                    {
                        "do": "write",
                        "file": plan_file,
                        "target": scene.scene_id,
                        "read": planning,
                        "what": "; ".join(errors[:3]),
                    }
                ],
            )
        if loop := critic_loop(scene.scene_id, "plan", plan_file, planning):
            return batch("3 plans", loop)
    if problems := review_problems(run, "plan"):
        return batch("3 plans", reviewer("plan", "plan", "plan_review.json", problems))
    if stage_approval_problem(run, "plan"):
        return batch(
            "3 plans",
            [
                {
                    "do": "ask_user",
                    "what": "CP2: show each scene's composition, transition_in, clip "
                    "table and last critique round; on approval `text-2-shorts approve . plan`",
                }
            ],
        )
    plans = load_scene_plans(run)
    state = load_state(run)
    production = references("scene-production.md")
    for plan in plans:  # production: scenes in series
        scene_id = plan.scene_id
        if is_approval_current(state, f"scene:{scene_id}", fingerprint(run, [plan])):
            continue
        if stale_audio(run, [plan]):
            return batch(
                "4 production",
                [
                    {
                        "do": "command",
                        "command": "text-2-shorts voice .",
                        "target": scene_id,
                        "what": "narration audio from the planned SSML",
                    }
                ],
            )
        unbuilt = [c for c in plan.clips if state["clips"].get(c.clip_id, {}).get("key") != clip_key(run, plan, c)]
        if unbuilt:
            return batch(
                "4 production",
                [
                    {
                        "do": "subagent",
                        "agent": "clip-builder",
                        "target": clip.clip_id,
                        "before": f"text-2-shorts task . {clip.clip_id}",
                        "after": f"text-2-shorts accept . {clip.clip_id}",
                        "what": f"build {clip.clip_id} in its prepared folder (scenes/{scene_id}/work/"
                        f"clip_{clip.index:02d}); a clip that fails accept twice → ask the user",
                    }
                    for clip in unbuilt
                ],
                parallel=True,
            )
        if problems := preview_problems(run, plan):
            if "out of date" in problems[0]:
                return batch(
                    "4 production",
                    [
                        {
                            "do": "command",
                            "command": f"text-2-shorts preview . {scene_id}",
                            "target": scene_id,
                            "what": "720p30 scene preview + sync.json",
                        }
                    ],
                )
            return batch(
                "4 production",
                [
                    {
                        "do": "subagent",
                        "agent": "audio-refactorer",
                        "target": scene_id,
                        "read": production,
                        "what": "; ".join(problems[:3]),
                    }
                ],
            )
        if loop := critic_loop(
            scene_id,
            "video",
            f"scenes/{scene_id} (sync → audio-refactorer; other issues → `text-2-shorts feedback` + rebuild that clip)",
            production,
        ):
            return batch("4 production", loop)
        return batch(
            "4 production",
            [
                {
                    "do": "ask_user",
                    "target": scene_id,
                    "what": f"CP3: give the user "
                    f"scenes/{scene_id}/preview.mp4, the sync summary and the last critique "
                    f"round; on approval `text-2-shorts approve . {scene_id}`",
                }
            ],
        )
    report = cli.read_json(run / "final_report.json") if (run / "final_report.json").exists() else {}
    if not (run / "final.mp4").exists() or report.get("fingerprint") != fingerprint(run, plans):
        return batch(
            "final",
            [{"do": "command", "command": "text-2-shorts final .", "what": "2560×1440, 120 fps delivery render"}],
        )
    if not is_approval_current(state, "final", fingerprint(run, plans)):
        return batch(
            "final",
            [
                {
                    "do": "ask_user",
                    "what": "CP4: give the user final.mp4 and the media checks; on "
                    "approval `text-2-shorts approve . final`",
                }
            ],
        )
    return batch("done", [])


def format_actions(batch: dict) -> str:
    lines = [f"stage {batch['stage']}" + (" — run these in parallel:" if batch["parallel"] else ":")]
    for action in batch["actions"]:
        who = action.get("agent") or action.get("command") or action["do"]
        line = f"  - [{action['do']}] {who}" + (f" · {action['target']}" if action.get("target") else "")
        line += f" — {action['what']}"
        if action.get("before"):
            line += f" (first `{action['before']}`, then `{action['after']}`)"
        if action.get("read"):
            line += f"\n      read: {', '.join(action['read'])}"
        lines.append(line)
    return "\n".join(lines) if batch["actions"] else "done: the video is approved."


def handle_next_command(arguments) -> None:
    batch = next_actions(Path(arguments.run))
    print(json.dumps(batch, indent=1) if arguments.json else format_actions(batch))


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
        return render_scene_sections(run, plan, "p", cli.FINAL_FRAME_RATE, "media_final")

    scene_renders = dict(zip([plan.scene_id for plan in plans], cli.run_in_parallel(render_scene, plans)))
    failed = {
        scene_id: render_result.get("stderr_tail")
        for scene_id, render_result in scene_renders.items()
        if not render_result.get("ok")
    }
    if failed:
        sys.exit(f"Final render failed: {json.dumps(failed, indent=1)[:3000]}")
    manifest = {"scenes": [scene_manifest(run, plan, scene_renders[plan.scene_id]) for plan in plans]}
    cli.write_json(run / "assembly.json", manifest)
    sys.path.insert(0, str(TOOLS_DIRECTORY))
    from assemble_clips import assemble  # tools/ is a script folder, not a package

    report = assemble(manifest, run / "final.mp4", run / "assembly_work")
    report["checks"] = check_final_media(run / "final.mp4")
    report["fingerprint"] = fingerprint(run, plans)  # next_steps marks the video stale when any clip changes
    cli.write_json(run / "final_report.json", report)
    print(f"{run / 'final.mp4'}\nduration: {report['final_s']}s · clips: {len(report['clips'])}")
    for finding in report["checks"]:
        print(f"{finding['severity']} {finding['code']}: {finding['message']}")


def render_scene_sections(run: Path, plan: ScenePlan, quality: str, fps: int | None, media: str) -> dict:
    """Compose the scene from its accepted clips and render every clip as a section, in a network-less jail."""
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
    shutil.rmtree(scene_directory / media, ignore_errors=True)
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
            quality,
            "--media",
            media,
        ]
        + (["--fps", str(fps)] if fps else []),
        capture_output=True,
        text=True,
        timeout=7200,
    )
    try:
        return json.loads(render_process.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "stderr_tail": render_process.stderr[-2000:]}


def scene_manifest(run: Path, plan: ScenePlan, render: dict) -> dict:
    """One scene for tools/assemble_clips.py: each clip's section video with its narration audio."""
    scene_directory = run / "scenes" / plan.scene_id
    sections = {section["name"]: section["path"] for section in render["sections"]}
    return {
        "scene_id": plan.scene_id,
        "clips": [
            {
                "clip_id": clip.clip_id,
                "video": str(scene_directory / sections[f"clip_{clip.index:02d}"]),
                "audio": str(scene_directory / "audio" / f"clip_{clip.index:02d}.mp3"),
                "lead_in": VOICE_LEAD_IN_SECONDS,
            }
            for clip in plan.clips
        ],
    }


# ── scene preview (720p30) + audio-video sync report: what the audio-refactorer and the video-critic work from ──

DRAFT_QUALITY = "m"  # Manim -qm: 1280×720 at 30 fps — every draft and preview; only `final` renders 1440p
SYNC_TOLERANCE_SECONDS = 0.35


def sync_report(run: Path, plan: ScenePlan, video_seconds: dict[str, float]) -> dict:
    """Per clip and beat: when the voice says the beat's phrase vs when the animation marks it (self.beat), whether
    the audio fits the clip's video, and the clip-builder's notes on what it changed from the plan."""
    scene_directory = run / "scenes" / plan.scene_id
    audio_index_path = scene_directory / "audio" / "index.json"
    audio_index = cli.read_json(audio_index_path) if audio_index_path.exists() else {}
    clips, problems = [], []
    for clip in plan.clips:
        work_directory = scene_directory / "work" / f"clip_{clip.index:02d}"
        probe_path = work_directory / "checks" / "probe.json"
        shown = cli.read_json(probe_path).get("beats", {}) if probe_path.exists() else {}
        audio = audio_index.get(clip.clip_id, {})
        beats = []
        for number, (beat, spoken) in enumerate(
            zip(clip.beats, audio.get("beat_times") or [None] * len(clip.beats)), 1
        ):
            spoken_at = None if spoken is None else round(VOICE_LEAD_IN_SECONDS + spoken, 2)
            shown_at = shown.get(str(number))
            offset = None if spoken_at is None or shown_at is None else round(shown_at - spoken_at, 2)
            beats.append({"beat": number, "plan": beat, "spoken_at": spoken_at, "shown_at": shown_at, "offset": offset})
            if offset is not None and abs(offset) > SYNC_TOLERANCE_SECONDS:
                when = "after" if offset > 0 else "before"
                problems.append(f"{clip.clip_id} beat {number}: shown {abs(offset):.2f}s {when} the voice says it")
        audio_seconds, video = audio.get("seconds"), video_seconds.get(clip.clip_id)
        audio_fits = None
        if audio_seconds is not None and video is not None:
            audio_fits = VOICE_LEAD_IN_SECONDS + audio_seconds <= video + 0.2
            if not audio_fits:
                problems.append(
                    f"{clip.clip_id}: the voice ({VOICE_LEAD_IN_SECONDS + audio_seconds:.2f}s with lead-in) runs past "
                    f"its animation ({video:.2f}s)"
                )
        changes_path = work_directory / "CHANGES.md"
        clips.append(
            {
                "clip_id": clip.clip_id,
                "video_seconds": video,
                "audio_seconds": audio_seconds,
                "audio_fits": audio_fits,
                "beats": beats,
                "changes": changes_path.read_text().strip() if changes_path.exists() else "",
            }
        )
    return {
        "scene_id": plan.scene_id,
        "tolerance": SYNC_TOLERANCE_SECONDS,
        "clips": clips,
        "problems": problems,
        "in_sync": not problems,
    }


def preview_problems(run: Path, plan: ScenePlan) -> list[str]:
    sync_path = run / "scenes" / plan.scene_id / "sync.json"
    report = cli.read_json(sync_path) if sync_path.exists() else {}
    if report.get("scene_hash") != scene_video_hash(run, plan.scene_id):
        return [f"{plan.scene_id}: preview missing or out of date (text-2-shorts preview <run> {plan.scene_id})"]
    return [f"{plan.scene_id} out of sync — {problem} (audio-refactorer)" for problem in report["problems"]]


def handle_preview_command(arguments) -> None:
    """The whole scene (with its transitions) at 720p30 with its audio, the sync report and contact sheets."""
    run, scene_id = Path(arguments.run), arguments.scene
    require_approval(run, "plan")
    plan = next((plan for plan in load_scene_plans(run) if plan.scene_id == scene_id), None)
    if plan is None:
        sys.exit(f"{scene_id}: no valid plan")
    require_earlier_scenes(run, scene_id)
    clip_states = load_state(run)["clips"]
    if unbuilt := [
        c.clip_id for c in plan.clips if clip_states.get(c.clip_id, {}).get("key") != clip_key(run, plan, c)
    ]:
        sys.exit(f"build these clips first: {unbuilt}")
    if stale := stale_audio(run, [plan]):
        sys.exit(f"audio missing or outdated for {sorted(stale)}: text-2-shorts voice <run>")
    render = render_scene_sections(run, plan, DRAFT_QUALITY, None, "media_preview")
    if not render.get("ok"):
        sys.exit(f"preview render failed: {render.get('stderr_tail')}")
    scene_directory = run / "scenes" / plan.scene_id
    sys.path.insert(0, str(TOOLS_DIRECTORY))
    from assemble_clips import assemble  # tools/ is a script folder, not a package

    assemble(
        {"scenes": [scene_manifest(run, plan, render)]},
        scene_directory / "preview.mp4",
        scene_directory / "preview_work",
    )
    for sheet in scene_directory.glob("preview_sheet_*.png"):
        sheet.unlink()
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(scene_directory / "preview.mp4"),
            "-vf",
            "fps=1/2,scale=480:-1,tile=4x3",
            str(scene_directory / "preview_sheet_%02d.png"),
        ],
        check=False,
    )
    sections = {section["name"]: section["duration"] for section in render["sections"]}
    report = sync_report(run, plan, {clip.clip_id: sections[f"clip_{clip.index:02d}"] for clip in plan.clips})
    report["scene_hash"] = scene_video_hash(run, scene_id)
    cli.write_json(scene_directory / "sync.json", report)
    print(
        f"{scene_directory / 'preview.mp4'} (720p30) · sync: "
        + ("in sync" if report["in_sync"] else "\n  " + "\n  ".join(report["problems"]))
    )


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
    if float(numerator) / float(denominator or 1) < cli.FINAL_FRAME_RATE - 0.5:
        findings.append(
            {
                "severity": "ERROR",
                "code": "FRAME_RATE",
                "message": f"{video_stream.get('avg_frame_rate')} fps (expected {cli.FINAL_FRAME_RATE})",
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
            "change what is said in script.json (CP1 again, then the scene plans and CP2), then text-2-shorts voice"
            if arguments.scope in ("narration", "math")
            else "edit the scene plan, then CP2 again"
            if arguments.scope == "plan"
            else "text-2-shorts task → clip-builder → text-2-shorts accept for that clip"
        )
        + "; text-2-shorts status lists what is now stale."
    )


def approval_problems(run: Path, target: str) -> list[str]:
    plans = load_scene_plans(run)
    if target == "script":
        return validate_script(run) or review_problems(run, "script")
    if target == "plan":
        if problem := stage_approval_problem(run, "script"):
            return [problem]
        script = load_script(run)
        scene_ids = [scene.scene_id for scene in script.scenes] if script else []
        problems = [f"{scene_id}: {error}" for scene_id in scene_ids for error in validate_plan(run, scene_id)]
        problems += [
            problem
            for scene_id in scene_ids
            if not validate_plan(run, scene_id)
            for problem in critique_problems(run, scene_id, "plan")
        ]
        problems += [
            f"{plan_path.parent.name}: has a plan but is not a scene of the script — delete it"
            for plan_path in sorted((run / "scenes").glob("s[0-9][0-9]/plan.json"))
            if plan_path.parent.name not in scene_ids
        ]
        return problems + review_problems(run, "plan")
    if target == "final":
        report = cli.read_json(run / "final_report.json") if (run / "final_report.json").exists() else {}
        return [] if report.get("fingerprint") == fingerprint(run, plans) else ["final.mp4 is missing or out of date"]
    scene_id = target.removeprefix("scene:")
    plan = next((scene_plan for scene_plan in plans if scene_plan.scene_id == scene_id), None)
    if plan is None:
        return [f"{scene_id}: no valid plan"]
    clip_states = load_state(run)["clips"]
    unbuilt = [
        f"{scene_id}: {clip.clip_id} is not built from its current inputs"
        for clip in plan.clips
        if clip_states.get(clip.clip_id, {}).get("key") != clip_key(run, plan, clip)
    ]
    return unbuilt or preview_problems(run, plan) + critique_problems(run, scene_id, "video")


def handle_approve_command(arguments) -> None:
    run = Path(arguments.run)
    target = arguments.target if arguments.target in ("script", "plan", "final") else f"scene:{arguments.target}"
    problems = approval_problems(run, target)
    if problems and not arguments.force:
        sys.exit(
            f"cannot approve {target} yet:\n"
            + "\n".join(f"  - {problem}" for problem in problems)
            + "\n(use --force only if the user explicitly accepts these)"
        )
    plans = load_scene_plans(run)
    if target in STAGE_FINGERPRINTS:
        approved_fingerprint = STAGE_FINGERPRINTS[target](run)
    else:
        scope = plans if target == "final" else [plan for plan in plans if f"scene:{plan.scene_id}" == target]
        approved_fingerprint = fingerprint(run, scope) if scope else None
    entry = {"at": datetime.now().isoformat(timespec="seconds"), "fingerprint": approved_fingerprint}
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
    context; PostToolUse → log the tool call; validate brief, script, plan and review files right after they are
    written (exit 2 feeds the errors back to Claude)."""
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
        print(f"Text-2-Shorts run {run.name}\n{status_text(run)}\n\nNEXT BATCH\n{format_actions(next_actions(run))}")
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
        validators = {
            "brief.json": lambda: validate_brief(run),
            "script.json": lambda: validate_script(run),
            "script_review.json": lambda: validate_review(run, "script"),
            "plan_review.json": lambda: validate_review(run, "plan"),
        }
        in_scene = written_path.parent.parent.name == "scenes"
        if written_path.name == "plan.json" and in_scene:
            errors = validate_plan(run, written_path.parent.name)
        elif written_path.name in ("plan_critique.json", "video_critique.json") and in_scene:
            errors = validate_critique(run, written_path.parent.name, written_path.name.split("_")[0])
        else:
            errors = validators.get(written_path.name, list)()
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
        errors = {
            "brief": validate_brief,
            "script": validate_script,
            "script-review": lambda run: validate_review(run, "script"),
            "plan-review": lambda run: validate_review(run, "plan"),
            "plan-critique": lambda run: validate_critique(run, arguments.scene, "plan"),
            "video-critique": lambda run: validate_critique(run, arguments.scene, "video"),
        }[arguments.what](run)
    print("\n".join(errors) or f"{arguments.what}: OK")
    sys.exit(1 if errors else 0)


def handle_doc_command(arguments) -> None:
    """Manim 0.20.1 API cards (and topic cards) by name, from the installed package: for planning and critiques."""
    ensure_api_index()
    cards = subprocess.run(
        [
            cli.PYTHON_EXECUTABLE,
            str(TOOLS_DIRECTORY / "doc_cards.py"),
            "--index",
            str(API_INDEX_PATH),
            "--names",
            arguments.names,
            "--topics",
            arguments.topics,
            "--topics-dir",
            str(TOPICS_DIRECTORY),
        ],
        capture_output=True,
        text=True,
    )
    print(cards.stdout or cards.stderr)


def handle_hash_command(arguments) -> None:
    """The version id a critique round records in `reviewed`."""
    print(critique_subject_hash(Path(arguments.run), arguments.scene, arguments.kind) or "missing")


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
    command_parser.add_argument(
        "what", choices=["brief", "script", "script-review", "plan", "plan-review", "plan-critique", "video-critique"]
    )
    command_parser.add_argument("--scene", help="sNN (plan: default every scene; critiques: required)")
    doc_parser = subparsers.add_parser("doc", help="Manim API cards by name, e.g. MathTex,Axes.plot")
    doc_parser.add_argument("names")
    doc_parser.add_argument("--topics", default="", help="topic cards, e.g. mathtex-indexing,transforms")
    doc_parser.set_defaults(handler=handle_doc_command)
    command_parser = add_subcommand("next", handle_next_command)
    command_parser.add_argument("--json", action="store_true")
    command_parser = add_subcommand("preview", handle_preview_command)
    command_parser.add_argument("scene", help="sNN")
    command_parser = add_subcommand("hash", handle_hash_command)
    command_parser.add_argument("scene", help="sNN")
    command_parser.add_argument("kind", choices=["plan", "video"])
    command_parser = add_subcommand("task", lambda arguments: print(prepare_clip(Path(arguments.run), arguments.clip)))
    command_parser.add_argument("clip", help="sNNcMM")
    command_parser = add_subcommand("accept", handle_accept_command)
    command_parser.add_argument("clip", help="sNNcMM")
    command_parser = add_subcommand("approve", handle_approve_command, force=True)
    command_parser.add_argument("target", help="script | plan | sNN | final")
    command_parser = add_subcommand("feedback", handle_feedback_command)
    command_parser.add_argument("target", help="script | sNN | sNNcMM")
    command_parser.add_argument("--scope", default="visual", choices=["narration", "math", "visual", "plan"])
    command_parser.add_argument("--text", required=True)


def resolve_run_path(arguments):
    arguments.run = str(Path(arguments.run).resolve())
    return arguments
