"""Checkpoint gates: whether a stage is approved for its current artifacts."""

from __future__ import annotations

import sys
from pathlib import Path

from app.workflow.fingerprints import STAGE_FINGERPRINTS, upstream_fingerprints
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
    approval = load_state(run).approved.get(stage)
    current = upstream_fingerprints(run, stage)
    on_current_upstream = approval is not None and all(current.get(k) == v for k, v in approval.upstream.items())
    if is_approval_current(load_state(run), stage, STAGE_FINGERPRINTS[stage](run)) and on_current_upstream:
        return None  # an approval from before upstream binding records no upstream: it is honoured as it is
    checkpoint = CHECKPOINTS[stage]
    short = checkpoint.split(" (")[0]
    return f"{checkpoint} is not approved, or changed since it was approved: get {short} first"


def require_approval(run: Path, stage: str) -> None:
    if problem := stage_approval_problem(run, stage):
        sys.exit(problem)
