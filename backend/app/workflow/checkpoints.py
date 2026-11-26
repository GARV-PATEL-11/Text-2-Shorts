"""Checkpoint gates: whether a stage is approved for its current artifacts."""

from __future__ import annotations

import sys
from pathlib import Path

from app.workflow.fingerprints import STAGE_FINGERPRINTS
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


def require_approval(run: Path, stage: str) -> None:
    if problem := stage_approval_problem(run, stage):
        sys.exit(problem)
