"""Critique rounds (script, plan, video): validation, scores against the threshold, the per-request script rule, the
refactor log (changes.json → changes.txt) and accuracy-review findings."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError
from schemas.reviews import ChangeLog, ChangeRecord, Critique, ReviewReport

from app.config import MAX_CRITIQUE_ROUNDS
from app.utilities import content_hash, format_validation_errors, read_json
from app.workflow.artifacts import load_scene_plans, load_script
from app.workflow.fingerprints import scene_video_hash, script_fingerprint
from app.workflow.ledger import load_decisions
from app.workflow.preferences import load_preferences
from app.workflow.validation import REVIEW_FILES, validate_review

CRITICS = {"script": "script-critic", "plan": "plan-critic", "video": "video-critic"}
CRITERION_PREFIX = {"script": "S", "plan": "P", "video": "V"}  # the rubric in each critic's agent file
ASPECTS = {
    "script": {"outline-fit", "clarity", "flow", "pacing", "speakability", "tone"},
    "plan": {"clarity", "sync", "constructability", "design"},
    "video": {"plan-match", "sync", "render", "design"},
}


def critique_file(scene_id: str, kind: str) -> str:
    """script_critique.json for the script (one per run); scenes/sNN/<kind>_critique.json for a scene."""
    return "script_critique.json" if kind == "script" else f"scenes/{scene_id}/{kind}_critique.json"


def critique_subject_hash(run: Path, scene_id: str, kind: str) -> str | None:
    """What a critique round must have reviewed: the script, the scene plan as it is now, or the scene's video."""
    if kind == "script":
        return script_fingerprint(run)
    if kind == "plan":  # without SSML, like CP2's fingerprint: re-timed audio is not a new plan
        plan = read_json(run / "scenes" / scene_id / "plan.json")
        if plan is None:
            return None
        clips = plan.get("clips") if isinstance(plan, dict) else None
        if isinstance(clips, list):
            plan = {
                **plan,
                "clips": [{k: v for k, v in c.items() if k != "ssml"} if isinstance(c, dict) else c for c in clips],
            }
        return content_hash(plan)
    return scene_video_hash(run, scene_id)


def validate_critique(run: Path, scene_id: str, kind: str) -> list[str]:
    name = critique_file(scene_id, kind)
    try:
        critique = Critique.model_validate_json((run / name).read_text())
    except FileNotFoundError:
        return [f"{name} does not exist: run the {CRITICS[kind]} subagent"]
    except ValidationError as validation_error:
        return [f"{name}: {error}" for error in format_validation_errors(validation_error)]
    errors = []
    if kind == "script" and len(critique.rounds) > (requested := script_changes_requested(run)):
        errors.append(
            f"{name} has {len(critique.rounds)} rounds: one critique round per change request raised at CP1 "
            f"({requested} so far)"
        )
    elif kind != "script" and len(critique.rounds) > MAX_CRITIQUE_ROUNDS:
        errors.append(f"{name} has {len(critique.rounds)} rounds: the loop stops after {MAX_CRITIQUE_ROUNDS} rounds")
    threshold = load_preferences(run).quality_threshold
    for number, critique_round in enumerate(critique.rounds, 1):
        basic_open = any(issue.tier == "basic" for issue in critique_round.issues)
        passes = critique_round.score >= threshold and not basic_open  # a basic need blocks at any score
        if passes != (critique_round.verdict == "pass"):
            errors.append(
                f"{name} round {number}: score {critique_round.score} against the quality threshold {threshold}"
                f"{' with a basic need open' if basic_open else ''} means verdict {'pass' if passes else 'revise'}"
            )
        for issue in critique_round.issues:
            if issue.criterion[0] != CRITERION_PREFIX[kind]:
                errors.append(f"{name}: {issue.criterion} is not a {kind} criterion ({CRITERION_PREFIX[kind]}-…)")
            if issue.aspect not in ASPECTS[kind]:
                errors.append(f"{name}: aspect {issue.aspect} is not one of {', '.join(sorted(ASPECTS[kind]))}")
    if kind == "script":
        script = load_script(run)
        known = {"script"} | ({scene.scene_id for scene in script.scenes} if script else set())
    else:
        plan = next((plan for plan in load_scene_plans(run) if plan.scene_id == scene_id), None)
        known = {scene_id} | ({clip.clip_id for clip in plan.clips} if plan else set())
    errors += [
        f"{name}: unknown target {issue.target}"
        for critique_round in critique.rounds
        for issue in critique_round.issues
        if issue.target not in known
    ]
    return errors


def script_changes_requested(run: Path) -> int:
    """How many times the user asked for changes at CP1: each buys exactly one script critique iteration."""
    return sum(d.checkpoint == "script" and d.decision == "changes_requested" for d in load_decisions(run))


def script_critique_problems(run: Path) -> list[str]:
    """The script is critiqued only when the user asks for modifications at CP1: one critic round per request, then
    the refactor applies the request and the script goes back to the user (no loop)."""
    if not (requested := script_changes_requested(run)):
        return []
    if errors := validate_critique(run, "script", "script"):
        return errors
    done = len(Critique.model_validate_json((run / "script_critique.json").read_text()).rounds)
    if done < requested:
        return [f"script: changes were requested at CP1 — run the script-critic (round {done + 1} of {requested})"]
    return []


def critique_problems(run: Path, scene_id: str, kind: str) -> list[str]:
    """Empty when the last critique round passed the current version; after 3 rounds the open issues go to the
    user, who accepts them (approve --force) or asks for fixes. The script has its own rule (above)."""
    if kind == "script":
        return script_critique_problems(run)
    if errors := validate_critique(run, scene_id, kind):
        return errors
    rounds = Critique.model_validate_json((run / critique_file(scene_id, kind)).read_text()).rounds
    last, current = rounds[-1], critique_subject_hash(run, scene_id, kind)
    if kind == "video":  # every refactor between two rounds is recorded (changes.json → changes.txt)
        if errors := validate_changes(run, scene_id):
            return errors
        recorded = {entry.iteration for entry in load_changes(run, scene_id)}
        if missing := [n for n in range(1, len(rounds)) if rounds[n - 1].verdict == "revise" and n not in recorded]:
            return [
                (
                    f"{scene_id}: record the refactor of iteration {missing[0]} in scenes/{scene_id}/changes.json "
                    "(what changed, files, rendering, audio timing, sync, validation)"
                )
            ]
    if last.verdict == "pass" and last.reviewed == current:
        return []
    if len(rounds) < MAX_CRITIQUE_ROUNDS:
        next_round = f"round {len(rounds) + 1} of {MAX_CRITIQUE_ROUNDS}"
        if last.reviewed != current:
            return [
                f"{scene_id}: the {kind} changed since the last critique round — run the {CRITICS[kind]} ({next_round})"
            ]
        return [f"{scene_id}: {kind} critique round {len(rounds)} asks for changes — refactor, then {next_round}"]
    issues = "; ".join(f"{issue.target} {issue.criterion} ({issue.tier}): {issue.problem}" for issue in last.issues)
    return [
        f"{scene_id}: REQUIRES ATTENTION — {MAX_CRITIQUE_ROUNDS} critique rounds below the quality threshold; "
        "open issues for the user to accept (approve --force) or fix: "
        + (issues or f"the last {kind} change was not critiqued")
    ]


def load_changes(run: Path, scene_id: str) -> list[ChangeRecord]:
    path = run / "scenes" / scene_id / "changes.json"
    return ChangeLog.model_validate_json(path.read_text()).entries if path.exists() else []


def validate_changes(run: Path, scene_id: str) -> list[str]:
    try:
        entries = load_changes(run, scene_id)
    except ValidationError as validation_error:
        return [f"scenes/{scene_id}/changes.json: {error}" for error in format_validation_errors(validation_error)]
    return [
        f"scenes/{scene_id}/changes.json: {entry.target} is not scene {scene_id} or one of its clips"
        for entry in entries
        if entry.target[:3] != scene_id
    ]


def write_changes_text(run: Path) -> Path:
    """The run's changes.txt: every recorded refactor iteration, scene by scene, for the user to read."""
    blocks = [
        f"{entry.target} — iteration {entry.iteration}\n"
        + "\n".join(
            f"  {label}: {value}"
            for label, value in (
                ("original issue", entry.issue),
                ("critique findings", "; ".join(entry.findings)),
                ("modification", entry.modification),
                ("files changed", ", ".join(entry.files_changed) or "none"),
                ("rendering changes", entry.rendering_changes),
                ("audio timing changes", entry.audio_timing_changes),
                ("sync adjustments", entry.sync_adjustments),
                ("validation results", entry.validation_results),
                ("final score", "pending" if entry.final_score is None else entry.final_score),
            )
        )
        for scene in sorted((run / "scenes").glob("s[0-9][0-9]"))
        if not validate_changes(run, scene.name)
        for entry in load_changes(run, scene.name)
    ]
    path = run / "changes.txt"
    path.write_text("\n\n".join(blocks) + "\n" if blocks else "no refactor iterations recorded\n")
    return path


def critique_state(run: Path, scene_id: str, kind: str) -> str:
    """missing · stale (the version changed since the last round) · revise · exhausted (3 rounds, issues left) ·
    done (the last round passed the current version)."""
    if validate_critique(run, scene_id, kind):
        return "missing"
    rounds = Critique.model_validate_json((run / critique_file(scene_id, kind)).read_text()).rounds
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
    findings = ReviewReport.model_validate_json((run / REVIEW_FILES[stage]).read_text()).findings
    return [f"accuracy ERROR in {f.target}: {f.why}" for f in findings if f.severity == "ERROR"]


def review_notes(run: Path, scene_id: str, clip_id: str) -> list[str]:
    """Accuracy findings that concern this clip (its scene in the script review, the clip in the plan review)."""
    findings = [
        finding
        for name in REVIEW_FILES.values()
        if (run / name).exists()
        for finding in ReviewReport.model_validate_json((run / name).read_text()).findings
        if finding.target in (scene_id, clip_id)
    ]
    return [f"{finding.kind}: \"{finding.quote}\" → {finding.fix}" for finding in findings]
