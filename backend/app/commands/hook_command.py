"""The Claude Code hook entry point (SessionStart and PostToolUse)."""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

import faraday_logging
from pydantic import ValidationError
from schemas.reviews import MistakeIssue, ReviewReport
from schemas.run_state import LogEntry
from schemas.session import HookEvent, HookOutput, SessionStartContext

from app.utilities import now_text
from app.workflow import mistakes
from app.workflow.critiques import review_problems, validate_changes, validate_critique, write_changes_text
from app.workflow.driver import format_actions, next_actions
from app.workflow.ledger import append_jsonl, count_attempt, update_state
from app.workflow.preferences import validate_preferences
from app.workflow.run_workspace import find_run_directory
from app.workflow.status import status_text
from app.workflow.templates import validate_template
from app.workflow.validation import (
    validate_brief,
    validate_content,
    validate_outline,
    validate_plan,
    validate_review,
    validate_script,
    validate_topics,
)


def handle_hook_command(arguments) -> None:
    """Claude Code hooks (runtime-environment/hooks/hooks.json): SessionStart → record transcript + print status into
    context; PostToolUse → log the tool call; validate brief, script, plan and review files right after they are
    written (exit 2 feeds the errors back to Claude)."""
    try:
        hook_event = HookEvent.model_validate_json(sys.stdin.read())
    except ValidationError:
        return  # not a hook event this command understands
    tool_input = hook_event.tool_input
    if hook_event.hook_event_name == "PreToolUse":  # approving is the user's decision, relayed by the session (M31)
        if hook_event.agent_id and re.search(r"\btext-2-shorts\s+approve\b", tool_input.command or ""):
            print(
                "Only the user approves a checkpoint. Finish your task and report back; the session asks the user.",
                file=sys.stderr,
            )
            sys.exit(2)
        return
    run = find_run_directory(hook_event.cwd, tool_input.file_path)
    if run is None:
        return  # not inside a run workspace
    faraday_logging.configure("runtime", run, console=False)  # stderr would reach Claude: the run's file only
    log = logging.getLogger("app.hook")
    if hook_event.hook_event_name == "SessionStart":
        log.info("session started: %s", hook_event.transcript_path)
        transcript_path = hook_event.transcript_path
        if transcript_path:
            update_state(run, lambda state: transcript_path in state.sessions or state.sessions.append(transcript_path))
        summary = f"Text-2-Shorts run {run.name}\n{status_text(run)}\n\nNEXT BATCH\n{format_actions(next_actions(run))}"
        output = HookOutput(systemMessage=summary, hookSpecificOutput=SessionStartContext(additionalContext=summary))
        print(output.model_dump_json(exclude_none=True))
    elif hook_event.hook_event_name == "PostToolUse":
        detail = tool_input.file_path or tool_input.command or tool_input.description or ""
        tool, agent = hook_event.tool_name, tool_input.subagent_type
        row = LogEntry(ts=now_text(), tool=tool, detail=str(detail)[:300], agent=agent)
        written_path = Path(tool_input.file_path or "")
        validators = {
            "brief.json": lambda: validate_brief(run),
            "topics.md": lambda: validate_topics(run),
            "content.md": lambda: validate_content(run),
            "outline.json": lambda: validate_outline(run),
            "preferences.json": lambda: validate_preferences(run),
            "template.json": lambda: validate_template(run),
            "script.json": lambda: validate_script(run),
            "script_review.json": lambda: validate_review(run, "script"),
            "plan_review.json": lambda: validate_review(run, "plan"),
        }
        in_scene = written_path.parent.parent.name == "scenes"
        if written_path.name == "plan.json" and in_scene:
            errors = validate_plan(run, written_path.parent.name)
        elif written_path.name == "script_critique.json":
            errors = validate_critique(run, "script", "script")
        elif written_path.name in ("plan_critique.json", "video_critique.json") and in_scene:
            errors = validate_critique(run, written_path.parent.name, written_path.name.split("_")[0])
        elif written_path.name == "changes.json" and in_scene:
            if not (errors := validate_changes(run, written_path.parent.name)):
                write_changes_text(run)
        else:
            errors = validators.get(written_path.name, list)()
        if tool_input.file_path:
            shown = written_path.relative_to(run) if written_path.is_relative_to(run) else written_path
            validated = written_path.name in validators or written_path.name.endswith(("plan.json", "critique.json"))
            message = f"{tool} {shown}" + (" — valid" if validated and not errors else "")
            if written_path.name == "changes.json" and not errors:
                message += " — changes.txt updated"
        elif agent:
            message = f"subagent {agent}: {detail}"
        else:
            message = f"{tool}: {detail}"
        row.shown = message + (f" — INVALID: {'; '.join(errors)}" if errors else "")
        (log.warning if errors else log.info)("%s", row.shown[:2000])
        append_jsonl(run, "log.jsonl", row)
        if errors:
            mistakes.record_invalid(run, written_path, errors)
            print(f"{written_path.name} is invalid — fix it:\n" + "\n".join(errors), file=sys.stderr)
            sys.exit(2)
        if written_path.name in ("script_review.json", "plan_review.json"):
            stage = written_path.name.split("_")[0]
            attempt = count_attempt(run, f"review:{stage}", failed=bool(review_problems(run, stage)))
            findings = ReviewReport.model_validate_json(written_path.read_text()).findings
            issues = [MistakeIssue(code=f"accuracy:{f.kind}", severity=f.severity, target=f.target,
                                   problem=f"{f.why} (\"{f.quote}\")", fix=f.fix) for f in findings]  # fmt: skip
            mistakes.record(run, f"review:{stage}", "script-writer" if stage == "script" else "scene-planner",
                            stage, issues, attempt or None)  # fmt: skip
        print(HookOutput(systemMessage="text-2-shorts · " + message).model_dump_json(exclude_none=True))
