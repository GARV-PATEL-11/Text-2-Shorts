"""Command handlers for the workflow: next, status, report, validate, hash, doc, approve, feedback, resolve."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pydantic import ValidationError

from app.config import API_INDEX_PATH, PYTHON_EXECUTABLE, TOOLS_DIRECTORY, TOPICS_DIRECTORY
from app.utilities import format_validation_errors
from app.workflow.approvals import ApprovalBlocked, approve_checkpoint, checkpoint_target
from app.workflow.change_requests import REQUEST_ROUTES, record_change_request, resolve_request
from app.workflow.critiques import critique_subject_hash, validate_changes, validate_critique
from app.workflow.driver import format_actions, next_actions
from app.workflow.preferences import validate_preferences
from app.workflow.scene_code import ensure_api_index
from app.workflow.status import status_text, sum_session_tokens
from app.workflow.validation import (
    review_subject_hash,
    validate_brief,
    validate_content,
    validate_outline,
    validate_plan,
    validate_review,
    validate_script,
    validate_topics,
)


def handle_next_command(arguments) -> None:
    batch = next_actions(Path(arguments.run))
    print(batch.model_dump_json(indent=1, exclude_none=True) if arguments.json else format_actions(batch))


def handle_feedback_command(arguments) -> None:
    """Record a change request (validated); with --checkpoint, also the decision 'changes requested' there."""
    try:
        request = record_change_request(
            Path(arguments.run), arguments.target, arguments.kind, arguments.text, arguments.checkpoint
        )
    except ValidationError as validation_error:
        sys.exit("invalid change request: " + "; ".join(format_validation_errors(validation_error)))
    print(
        f"{request.id} recorded for {request.target} ({request.kind}). Apply it: "
        f"{REQUEST_ROUTES[request.kind]}; then `text-2-shorts resolve <run> {request.id} applied`."
    )


def handle_resolve_command(arguments) -> None:
    try:
        resolve_request(Path(arguments.run), arguments.id, arguments.status, arguments.note)
    except LookupError as error:
        sys.exit(str(error))
    print(f"{arguments.id}: {arguments.status}")


def handle_approve_command(arguments) -> None:
    try:
        decision = approve_checkpoint(
            Path(arguments.run), arguments.target, getattr(arguments, "notes", "") or "", arguments.force, by="session"
        )
    except ApprovalBlocked as blocked:
        sys.exit(
            f"cannot approve {blocked.target} yet:\n"
            + "\n".join(f"  - {problem}" for problem in blocked.problems)
            + "\n(use --force only if the user explicitly accepts these)"
        )
    print(f"approved {checkpoint_target(arguments.target)}" + (" (forced)" if decision.forced else ""))


def handle_status_command(arguments) -> None:
    print(status_text(Path(arguments.run)))


def handle_report_command(arguments) -> None:
    totals = sum_session_tokens(Path(arguments.run))
    total_in = totals.input + totals.cache_read + totals.cache_write
    cached = f", {100 * totals.cache_read // total_in}% read from cache" if total_in else ""
    print(
        f"Claude Code sessions: {totals.messages} model responses · input {total_in} tokens (net {totals.input}, "
        f"cache read {totals.cache_read}, cache write {totals.cache_write}{cached}) · output {totals.output} tokens"
    )


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
            "topics": validate_topics,
            "content": validate_content,
            "outline": validate_outline,
            "preferences": validate_preferences,
            "script": validate_script,
            "script-review": lambda run: validate_review(run, "script"),
            "plan-review": lambda run: validate_review(run, "plan"),
            "script-critique": lambda run: validate_critique(run, "script", "script"),
            "plan-critique": lambda run: validate_critique(run, arguments.scene, "plan"),
            "video-critique": lambda run: validate_critique(run, arguments.scene, "video"),
            "changes": lambda run: validate_changes(run, arguments.scene),
        }[arguments.what](run)
    print("\n".join(errors) or f"{arguments.what}: OK")
    sys.exit(1 if errors else 0)


def handle_doc_command(arguments) -> None:
    """Manim 0.20.1 API cards (and topic cards) by name, from the installed package: for planning and critiques."""
    ensure_api_index()
    cards = subprocess.run(
        [
            PYTHON_EXECUTABLE,
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
    """The version id a critique round or an accuracy review records in `reviewed`."""
    if arguments.scene == "plans":  # the plan review covers every scene plan at once
        print(review_subject_hash(Path(arguments.run), "plan"))
        return
    kind = arguments.kind or ("script" if arguments.scene == "script" else "plan")
    print(critique_subject_hash(Path(arguments.run), arguments.scene, kind) or "missing")
