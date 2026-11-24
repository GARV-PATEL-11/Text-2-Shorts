"""The website's console: the user's messages to the run's Claude Code session, one turn at a time.

Each message runs one turn of the same session as `text-2-shorts open` (same jail, plugin, settings, model), resumed
turn after turn. Claude Code's stream-json events become ConsoleEntry lines, streamed to the page and kept in the
run's console.jsonl. Python relays only: what to do is decided by the session and the workflow skill.
"""

from __future__ import annotations

import fcntl
import json
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from schemas.api import ConsoleEntry

from app.sandbox import build_jail_command, console_claude_arguments
from app.utilities import now_text, read_jsonl
from app.workflow.ledger import append_jsonl, load_state, update_state

CONSOLE_FILE = "console.jsonl"


def claude_turn_command(run: Path, message: str, session_id: str | None) -> list[str]:
    """Claude Code for one console turn, inside the run's jail."""
    return build_jail_command(run.resolve(), console_claude_arguments(message, session_id))


@contextmanager
def turn_lock(run: Path):
    """Yields True when this turn may run (no other turn of this run is running), else False."""
    with open(run / ".console.lock", "a") as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


def is_busy(run: Path) -> bool:
    with turn_lock(run) as acquired:
        return not acquired


def history(run: Path) -> list[ConsoleEntry]:
    return [ConsoleEntry.model_validate(row) for row in read_jsonl(run / CONSOLE_FILE)]


def tool_line(name: str, tool_input: dict) -> str:
    """A tool call in one short line: the tool and its file, command or description."""
    detail = tool_input.get("file_path") or tool_input.get("command") or tool_input.get("description") or ""
    detail = Path(detail).name if tool_input.get("file_path") else str(detail)
    return f"{name} {detail[:200]}".strip()


def entries_from_event(event: dict) -> list[ConsoleEntry]:
    """What a Claude Code stream-json event shows in the console (other events show nothing)."""
    if event.get("type") == "assistant":
        shown = []
        for part in (event.get("message") or {}).get("content") or []:
            if part.get("type") == "text" and part.get("text", "").strip():
                shown.append(ConsoleEntry(at=now_text(), role="claude", text=part["text"].strip()))
            elif part.get("type") == "tool_use":
                shown.append(
                    ConsoleEntry(
                        at=now_text(), role="tool", text=tool_line(part.get("name", "tool"), part.get("input") or {})
                    )
                )
        return shown
    if event.get("type") == "result":
        if event.get("is_error"):
            return [ConsoleEntry(at=now_text(), role="error", text=str(event.get("result") or event.get("subtype")))]
        return [ConsoleEntry(at=now_text(), role="system", text="Turn finished.")]
    return []


def run_turn(run: Path, message: str) -> Iterator[ConsoleEntry]:
    """One turn: the user's message, then Claude's text and tool calls as they happen. The caller holds turn_lock."""

    def keep(entry: ConsoleEntry) -> ConsoleEntry:
        append_jsonl(run, CONSOLE_FILE, entry)
        return entry

    yield keep(ConsoleEntry(at=now_text(), role="you", text=message))
    command = claude_turn_command(run, message, load_state(run).console_session)
    process = subprocess.Popen(command, cwd=run, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert process.stdout is not None
    for line in process.stdout:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("session_id") and event.get("type") == "system":
            session_id = event["session_id"]
            update_state(run, lambda state, session_id=session_id: setattr(state, "console_session", session_id))
        for entry in entries_from_event(event):
            yield keep(entry)
    if process.wait() != 0:
        tail = (process.stderr.read() if process.stderr else "")[-600:].strip()
        yield keep(
            ConsoleEntry(at=now_text(), role="error", text=f"Claude Code stopped (exit {process.returncode}). {tail}")
        )
