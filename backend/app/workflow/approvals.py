"""What blocks a checkpoint approval: the stage's own problems plus open change requests."""

from __future__ import annotations

import logging
from pathlib import Path

from schemas.interaction import CheckpointDecision
from schemas.run_state import Approval

from app.utilities import now_text
from app.workflow.artifacts import load_final_report, load_scene_plans, load_script
from app.workflow.change_requests import blocking_requests
from app.workflow.checkpoints import stage_approval_problem
from app.workflow.critiques import critique_problems, critique_subject_hash, review_problems
from app.workflow.fingerprints import STAGE_FINGERPRINTS, clip_key, fingerprint
from app.workflow.ledger import load_state, record_decision, update_state
from app.workflow.production import preview_problems
from app.workflow.templates import validate_template
from app.workflow.validation import (
    validate_brief,
    validate_content,
    validate_outline,
    validate_plan,
    validate_script,
    validate_topics,
)


def approval_problems(run: Path, target: str) -> list[str]:
    if target.startswith("start:"):
        return []
    return stage_problems(run, target) + blocking_requests(run, target)


def stage_problems(run: Path, target: str) -> list[str]:
    plans = load_scene_plans(run)
    if target == "template":  # the first stage: the look and sound, chosen before anything is written
        return validate_template(run)
    if target == "requirements":
        if problem := stage_approval_problem(run, "template"):
            return [problem]
        return validate_brief(run) + validate_topics(run) + validate_content(run)
    if target == "outline":
        return validate_topics(run) + validate_content(run) + validate_outline(run)
    if target == "script":
        return validate_script(run) or critique_problems(run, "script", "script") + review_problems(run, "script")
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
        report = load_final_report(run)
        current = report is not None and report.fingerprint == fingerprint(run, plans)
        return [] if current else ["final.mp4 is missing or out of date"]
    scene_id = target.removeprefix("scene:")
    plan = next((scene_plan for scene_plan in plans if scene_plan.scene_id == scene_id), None)
    if plan is None:
        return [f"{scene_id}: no valid plan"]
    clip_states = load_state(run).clips
    unbuilt = [
        f"{scene_id}: {clip.clip_id} is not built from its current inputs"
        for clip in plan.clips
        if (build := clip_states.get(clip.clip_id)) is None or build.key != clip_key(run, plan, clip)
    ]
    return unbuilt or preview_problems(run, plan) + critique_problems(run, scene_id, "video")


class ApprovalBlocked(Exception):
    """A checkpoint with open problems, approved only when the user accepts them (force)."""

    def __init__(self, target: str, problems: list[str]):
        super().__init__(f"cannot approve {target} yet: " + "; ".join(problems))
        self.target, self.problems = target, problems


def checkpoint_target(name: str) -> str:
    """The ledger key of a checkpoint: a stage, final, start:sNN, or scene:sNN for a scene's CP3."""
    return name if name in (*STAGE_FINGERPRINTS, "final") or name.startswith("start:") else f"scene:{name}"


log = logging.getLogger(__name__)


def approve_checkpoint(run: Path, name: str, notes: str = "", force: bool = False) -> CheckpointDecision:
    """The user's approval, bound to the fingerprint of exactly what they approved, and recorded as a decision.
    Open problems refuse it (ApprovalBlocked) unless the user accepts them (force=True, recorded as forced)."""
    target = checkpoint_target(name)
    problems = approval_problems(run, target)
    if problems and not force:
        log.warning("%s: %s blocked — %s", run.name, target, "; ".join(problems)[:1500])
        raise ApprovalBlocked(target, problems)
    plans = load_scene_plans(run)
    if target in STAGE_FINGERPRINTS:
        approved_fingerprint = STAGE_FINGERPRINTS[target](run)
    elif target.startswith("start:"):
        approved_fingerprint = critique_subject_hash(run, target.removeprefix("start:"), "plan")
    else:
        scope = plans if target == "final" else [plan for plan in plans if f"scene:{plan.scene_id}" == target]
        approved_fingerprint = fingerprint(run, scope) if scope else None
    entry = Approval(at=now_text(), fingerprint=approved_fingerprint)
    update_state(run, lambda state: state.approved.__setitem__(target, entry))
    log.info("%s: %s approved%s", run.name, target, " with open problems" if problems else "")
    return record_decision(
        run,
        target.removeprefix("scene:"),
        "approved_with_notes" if notes else "approved",
        notes,
        forced=bool(problems),
        fingerprint=approved_fingerprint,
    )
