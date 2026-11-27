"""The website's console: the user's messages to the run's Claude Code session, one turn at a time.

Each message runs one turn of the same session as `text-2-shorts open` (same jail, plugin, settings, model), resumed
turn after turn. Claude Code's stream-json events become ConsoleEntry lines, streamed to the page and kept in the
run's console.jsonl. Python relays only: what to do is decided by the session and the workflow skill.
"""

from __future__ import annotations

import fcntl
import json
import logging
import subprocess
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from schemas.api import ConsoleEntry

from app.sandbox import build_jail_command, console_claude_arguments
from app.utilities import now_text, read_jsonl
from app.web import usage
from app.workflow.ledger import append_jsonl, load_state, update_state

CONSOLE_FILE = "console.jsonl"
log = logging.getLogger(__name__)


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
            elif part.get("type") == "tool_use" and part.get("name") == "AskUserQuestion":
                for asked in (part.get("input") or {}).get("questions") or []:  # shown on the stage page, answerable
                    header = f"**{asked['header']}** — " if asked.get("header") else ""
                    shown.append(
                        ConsoleEntry(
                            at=now_text(),
                            role="question",
                            text=header + str(asked.get("question", "")),
                            options=[str(option.get("label", "")) for option in asked.get("options") or []],
                        )
                    )
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


class Turn:
    """A running turn's entries so far, for whoever follows it (the page that sent it, or none)."""

    def __init__(self):
        self.entries: list[ConsoleEntry] = []
        self.changed = threading.Condition()
        self.finished = threading.Event()


def start_turn(run: Path, message: str) -> Turn | None:
    """Start one turn in a background thread that owns the turn lock, the Claude Code process and console.jsonl;
    None when a turn of this run is already running. The page only follows it: a reload or a closed drawer never
    frees the lock while Claude Code is still working (H7)."""
    lock = turn_lock(run)
    if not lock.__enter__():
        lock.__exit__(None, None, None)
        return None
    turn = Turn()

    def work():
        try:
            for entry in run_turn(run, message):
                with turn.changed:
                    turn.entries.append(entry)
                    turn.changed.notify_all()
        except Exception:
            log.exception("%s: console turn failed", run.name)
        finally:
            lock.__exit__(None, None, None)
            with turn.changed:
                turn.finished.set()
                turn.changed.notify_all()

    threading.Thread(target=work, name=f"console {run.name}", daemon=True).start()
    return turn


def follow(turn: Turn) -> Iterator[ConsoleEntry]:
    """The turn's entries as they come, until it finishes. Stopping early leaves the turn running."""
    shown = 0
    while True:
        with turn.changed:
            turn.changed.wait_for(lambda seen=shown: len(turn.entries) > seen or turn.finished.is_set(), timeout=30)
            new, finished = turn.entries[shown:], turn.finished.is_set()
        shown += len(new)
        yield from new
        if finished and shown == len(turn.entries):
            return


def run_turn(run: Path, message: str) -> Iterator[ConsoleEntry]:
    """One turn: the user's message, then Claude's text and tool calls as they happen. The caller holds turn_lock;
    the process is stopped if the turn ends early, and its stderr goes to a file (a full pipe would hang it)."""

    def keep(entry: ConsoleEntry) -> ConsoleEntry:
        append_jsonl(run, CONSOLE_FILE, entry)
        return entry

    yield keep(ConsoleEntry(at=now_text(), role="you", text=message))
    log.info("%s: console turn started (%d characters)", run.name, len(message))
    command = claude_turn_command(run, message, load_state(run).console_session)
    with tempfile.TemporaryFile("w+") as stderr:
        process = subprocess.Popen(command, cwd=run, stdout=subprocess.PIPE, stderr=stderr, text=True)
        assert process.stdout is not None
        try:
            for line in process.stdout:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("session_id") and event.get("type") == "system":
                    session_id = event["session_id"]
                    update_state(
                        run, lambda state, session_id=session_id: setattr(state, "console_session", session_id)
                    )
                usage.record(event)  # the usage limits on Home follow every turn
                if event.get("type") == "result" and (cost := event.get("total_cost_usd")):  # the profile's net spend
                    update_state(
                        run, lambda state, cost=cost: setattr(state, "spend_usd", state.spend_usd + float(cost))
                    )
                for entry in entries_from_event(event):
                    yield keep(entry)
            process.wait()
        finally:
            if process.poll() is None:  # the turn ended early: never leave Claude Code running unowned
                process.terminate()
                try:
                    process.wait(10)
                except subprocess.TimeoutExpired:
                    process.kill()
        if process.returncode == 0:
            log.info("%s: console turn finished", run.name)
        else:
            stderr.seek(0)
            tail = stderr.read()[-600:].strip()
            log.error("%s: Claude Code stopped (exit %s): %s", run.name, process.returncode, tail)
            yield keep(
                ConsoleEntry(
                    at=now_text(), role="error", text=f"Claude Code stopped (exit {process.returncode}). {tail}"
                )
            )
