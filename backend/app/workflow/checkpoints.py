"""Checkpoint gates: whether a stage is approved for its current artifacts, and the series rule for scenes."""

from __future__ import annotations

import sys
from pathlib import Path

from app.workflow.artifacts import load_scene_plans
from app.workflow.fingerprints import STAGE_FINGERPRINTS, fingerprint
from app.workflow.ledger import is_approval_current, load_state

CHECKPOINTS = {
    "requirements": "the requirements checkpoint (brief, topics, content)",
    "template": "the template checkpoint (template.json)",
    "outline": "CP0 (the outline)",
    "script": "CP1 (the complete script)",
    "plan": "CP2 (the scene visual plans)",
}


def stage_approval_problem(run: Path, stage: str) -> str | None:
    """None when the stage's checkpoint is approved for exactly the current artifacts, else why not."""
    if is_approval_current(load_state(run), stage, STAGE_FINGERPRINTS[stage](run)):
        return None
    checkpoint = CHECKPOINTS[stage]
    short = checkpoint.split(" (")[0]
    return f"{checkpoint} is not approved, or changed since it was approved: get {short} first"


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
