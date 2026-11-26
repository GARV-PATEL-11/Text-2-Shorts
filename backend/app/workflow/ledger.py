"""The run ledger: state.json (approvals, clip build state, sessions, statuses) under a lock, JSONL files, and the
checkpoint decisions. Every file is read and written through its Pydantic contract."""

from __future__ import annotations

import fcntl
import os
import tempfile
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path

from pydantic import BaseModel
from schemas.interaction import CheckpointDecision
from schemas.run_state import RunState

from app.utilities import now_text, read_jsonl


def load_state(run: Path) -> RunState:
    state_path = run / "state.json"
    return RunState.model_validate_json(state_path.read_text()) if state_path.exists() else RunState()


@contextmanager
def run_lock(run: Path):
    """Exclusive lock across processes (parallel `text-2-shorts accept`, hooks, approvals all write the ledger)."""
    with open(run / ".ledger.lock", "a") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        yield


def update_state(run: Path, modify: Callable[[RunState], object]) -> RunState:
    """Read-modify-write under the run lock, validated, written atomically (never a half-written state.json)."""
    with run_lock(run):
        state = load_state(run)
        modify(state)
        state = RunState.model_validate(state.model_dump())  # what is written always satisfies the contract
        with tempfile.NamedTemporaryFile("w", dir=run, delete=False, suffix=".tmp") as temporary_file:
            temporary_file.write(state.model_dump_json(indent=1))
        os.replace(temporary_file.name, run / "state.json")
        return state


def count_attempt(run: Path, name: str, failed: bool) -> int:
    """A loop's failed tries in a row (state.attempts): a failure adds one to `name`; a success clears every counter
    that starts with `name` (build:sNN clears build:sNN:<key> of every key). → the count now (0 after a success)."""

    def change(state: RunState) -> None:
        if failed:
            state.attempts[name] = state.attempts.get(name, 0) + 1
        else:
            state.attempts = {key: value for key, value in state.attempts.items() if not key.startswith(name)}

    return update_state(run, change).attempts.get(name, 0)


def append_jsonl(run: Path, name: str, row: BaseModel) -> None:
    with run_lock(run), (run / name).open("a") as jsonl_file:
        jsonl_file.write(row.model_dump_json() + "\n")


def load_decisions(run: Path) -> list[CheckpointDecision]:
    return [CheckpointDecision.model_validate(row) for row in read_jsonl(run / "decisions.jsonl")]


def record_decision(
    run: Path,
    checkpoint: str,
    decision: str,
    notes: str = "",
    requests: list[str] | None = None,
    forced: bool = False,
    fingerprint: str | None = None,
    by: str = "",
) -> CheckpointDecision:
    row = CheckpointDecision.model_validate(
        {
            "checkpoint": checkpoint,
            "decision": decision,
            "notes": notes,
            "requests": requests or [],
            "forced": forced,
            "fingerprint": fingerprint,
            "decided_at": now_text(),
            "by": by,
        }
    )
    append_jsonl(run, "decisions.jsonl", row)
    return row


def is_approval_current(state: RunState, target: str, expected_fingerprint: str | None) -> bool:
    """True when the target was approved for exactly these artifacts (nothing to approve is never approved)."""
    approval = state.approved.get(target)
    return expected_fingerprint is not None and approval is not None and approval.fingerprint == expected_fingerprint
