"""The website's console: the user's messages to the run's Claude Code session, one turn at a time.

Each message runs one turn of the same session as `text-2-shorts open` (same jail, plugin, settings), resumed turn after
turn, with the console's own model and permission mode. Claude Code's stream-json events become ConsoleEntry lines
(EventReader), streamed to the page and kept in the run's console.jsonl. Permission prompts reach the page through
console_permissions; the page answers them. Python relays only: what to do is decided by the session and the skill.
"""

from __future__ import annotations

import asyncio
import fcntl
import json
import logging
import os
import re
import secrets
import signal
import subprocess
import tempfile
import threading
import time
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError
from schemas.api import ConsoleEntry, ConsoleSession, TurnStats
from schemas.run_state import ConsoleSettings

from app.sandbox import build_jail_command, console_claude_arguments
from app.utilities import now_text, read_json, read_jsonl, write_atomic
from app.web import usage
from app.workflow.ledger import append_jsonl, load_state, update_state

CONSOLE_FILE = "console.jsonl"
SESSION_FILE = ".console-session.json"  # the last init event's summary (model, cwd, commands, skills, agents)
KEPT_TEXT = 20_000  # a tool's input string or output beyond this is cut (the page never needs megabytes)
LIVE_ONLY = {"partial", "thinking"}  # sent while the turn runs, never stored
COALESCE = 0.08  # seconds of streamed text gathered into one entry (fewer lines to send, keep and redraw)
HEARTBEAT = 15  # seconds: a followed turn that is quiet (waiting on a permission prompt) still sends a blank line
log = logging.getLogger(__name__)


@dataclass
class TurnOptions:
    """How one turn runs: the console's settings, and where its permission prompts go."""

    model: str | None = None
    mode: str | None = None
    permission_url: str | None = None
    token: str | None = None
    config_dir: Path | None = None  # where the turn's owner-only MCP config (with the token) is written
    config_file: Path | None = None  # set when written; removed when the turn ends


def settings_path(run: Path) -> Path:
    """The console's model and mode for a run, kept beside the runs folder: outside the run folder, so nothing inside the
    jail (which may write the run folder) can change how its own turns run."""
    return run.parent.parent / "console" / f"{run.name}.json"


def load_settings(run: Path) -> ConsoleSettings:
    try:
        return ConsoleSettings.model_validate(read_json(settings_path(run)) or {})
    except ValidationError:
        log.warning("%s: unreadable console settings, using the defaults", run.name)
        return ConsoleSettings()


def save_settings(run: Path, settings: ConsoleSettings) -> None:
    settings_path(run).parent.mkdir(parents=True, exist_ok=True)
    write_atomic(settings_path(run), settings.model_dump_json(exclude={"allowed"}, indent=2))


def claude_turn_command(run: Path, message: str, session_id: str | None, options: TurnOptions) -> list[str]:
    """Claude Code for one console turn, inside the run's jail."""
    return build_jail_command(run.resolve(), console_claude_arguments(message, session_id, options))


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


def session_info(run: Path) -> ConsoleSession | None:
    data = read_json(run / SESSION_FILE)
    return ConsoleSession.model_validate(data) if isinstance(data, dict) else None


def cut(text: str) -> str:
    return text if len(text) <= KEPT_TEXT else f"{text[:KEPT_TEXT]}\n[{len(text) - KEPT_TEXT} more characters cut]"


def cut_input(tool_input: dict) -> dict:
    return {key: cut(value) if isinstance(value, str) else value for key, value in tool_input.items()}


def tool_line(name: str, tool_input: dict) -> str:
    """A tool call in one short line: the tool and its file, command or description."""
    detail = tool_input.get("file_path") or tool_input.get("command") or tool_input.get("description") or ""
    detail = Path(detail).name if tool_input.get("file_path") else str(detail)
    return f"{name} {detail[:200]}".strip()


def result_text(part: dict, extra: dict | None) -> str:
    content = part.get("content")
    if isinstance(content, list):
        content = "\n".join(str(block.get("text", "")) for block in content if block.get("type") == "text")
    text = str(content or "")
    stderr = (extra or {}).get("stderr") if isinstance(extra, dict) else ""
    if stderr and stderr not in text:
        text = f"{text}\n{stderr}".strip()
    return cut(text)


class EventReader:
    """One turn's Claude Code stream-json events → console entries. Keeps what a turn needs across events: when each
    tool started, the last request's context, how many tools ran."""

    def __init__(self, run: Path):
        self.run = run
        self.started: dict[str, tuple[float, str]] = {}  # tool_use id → (monotonic start, tool name)
        self.context = 0
        self.tools = 0
        self.thinking = False
        self.streamed = ""  # text streamed since Claude's last message: kept if the turn is stopped mid-sentence

    def entry(self, role: str, text: str, **fields) -> ConsoleEntry:
        return ConsoleEntry(at=now_text(), role=role, text=text, **fields)

    def read(self, event: dict) -> list[ConsoleEntry]:
        kind = event.get("type")
        if event.get("parent_tool_use_id"):  # a subagent's own work: shown as its Task/Agent call and its result
            return []
        if kind == "system" and event.get("subtype") == "init":
            self.keep_session(event)
            return []
        if kind == "system" and event.get("subtype") == "status" and event.get("status") == "compacting":
            return [self.entry("thinking", "Compacting the Conversation…")]
        if kind == "system" and event.get("subtype") == "compact_boundary":
            meta = event.get("compact_metadata") or {}
            sizes = f" ({meta['pre_tokens']:,} → {meta['post_tokens']:,} tokens)" if meta.get("post_tokens") else ""
            return [self.entry("system", f"Conversation Compacted{sizes}.")]
        if kind == "stream_event":
            return self.stream(event.get("event") or {})
        if kind == "assistant":
            return self.assistant(event.get("message") or {})
        if kind == "user":
            return self.results(event)
        if kind == "result":
            return [self.summary(event)]
        return []

    def keep_session(self, event: dict) -> None:
        session = ConsoleSession(
            session_id=str(event.get("session_id", "")),
            model=str(event.get("model", "")),
            cwd=str(event.get("cwd", "")),
            permission_mode=str(event.get("permissionMode", "")),
            slash_commands=[str(name) for name in event.get("slash_commands") or []],
            skills=[str(name) for name in event.get("skills") or []],
            agents=[str(name) for name in event.get("agents") or []],
            tools=[str(name) for name in event.get("tools") or []],
        )
        write_atomic(self.run / SESSION_FILE, session.model_dump_json(indent=2))

    def stream(self, event: dict) -> list[ConsoleEntry]:
        block, delta = event.get("content_block") or {}, event.get("delta") or {}
        if event.get("type") == "content_block_start" and block.get("type") == "thinking" and not self.thinking:
            self.thinking = True
            return [self.entry("thinking", "Thinking…")]
        if delta.get("type") == "text_delta" and delta.get("text"):
            self.thinking = False
            self.streamed += delta["text"]
            return [self.entry("partial", delta["text"])]
        return []

    def assistant(self, message: dict) -> list[ConsoleEntry]:
        usage_now = message.get("usage") or {}
        if usage_now:
            self.context = sum(int(usage_now.get(key) or 0) for key in
                               ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))  # fmt: skip
        shown = []
        for part in message.get("content") or []:
            if part.get("type") in ("text", "tool_use"):
                self.streamed = ""
            if part.get("type") == "text" and part.get("text", "").strip():
                self.thinking = False
                shown.append(self.entry("claude", part["text"].strip()))
            elif part.get("type") == "tool_use" and part.get("name") == "AskUserQuestion":
                for asked in (part.get("input") or {}).get("questions") or []:  # answerable with one click
                    header = f"**{asked['header']}** — " if asked.get("header") else ""
                    options = [str(option.get("label", "")) for option in asked.get("options") or []]
                    shown.append(self.entry("question", header + str(asked.get("question", "")), options=options))
            elif part.get("type") == "tool_use":
                name, tool_input = str(part.get("name", "tool")), part.get("input") or {}
                self.started[str(part.get("id"))] = (time.monotonic(), name)
                self.tools += 1
                shown.append(self.entry("tool", tool_line(name, tool_input), id=part.get("id"), tool=name,
                                        input=cut_input(tool_input)))  # fmt: skip
        return shown

    def results(self, event: dict) -> list[ConsoleEntry]:
        content = (event.get("message") or {}).get("content")
        if isinstance(content, str):  # a built-in command's output (/compact); other strings are Claude's own context
            found = re.fullmatch(r"\s*<local-command-stdout>(.*)</local-command-stdout>\s*", content, re.DOTALL)
            return [self.entry("system", found[1].strip() or "Done.")] if found else []
        shown = []
        for part in content or []:
            if not isinstance(part, dict) or part.get("type") != "tool_result":
                continue
            ident = str(part.get("tool_use_id"))
            began, name = self.started.pop(ident, (None, None))
            shown.append(
                self.entry(
                    "result",
                    result_text(part, event.get("tool_use_result")),
                    id=ident,
                    tool=name,
                    is_error=bool(part.get("is_error")),
                    duration_ms=round((time.monotonic() - began) * 1000) if began else None,
                )
            )
        return shown

    def summary(self, event: dict) -> ConsoleEntry:
        models = event.get("modelUsage") or {}
        model, details = next(iter(models.items()), ("", {}))
        stats = TurnStats(
            model=model,
            cost_usd=float(event.get("total_cost_usd") or 0),
            duration_ms=int(event.get("duration_ms") or 0),
            context_tokens=self.context,
            context_window=int(details.get("contextWindow") or 0),
            output_tokens=int((event.get("usage") or {}).get("output_tokens") or 0),
            tools=self.tools,
        )
        if event.get("is_error"):
            reason = str(event.get("result") or event.get("subtype") or "the turn failed")
            return self.entry("error", reason, stats=stats)
        return self.entry("system", "Turn Finished.", stats=stats)


# ── turns ─────────────────────────────────────────────────────────────────────────────────────────────────


class Turn:
    """A running turn's entries so far, for whoever follows it (the page that sent it, or none), its Claude Code
    process (for stop) and the token its permission prompts must carry."""

    def __init__(self, run: Path):
        self.run = run
        self.entries: list[ConsoleEntry] = []
        self.changed = threading.Condition()
        self.finished = threading.Event()
        self.token = secrets.token_urlsafe(24)
        self.process: subprocess.Popen | None = None
        self.stopped = False
        self.ended = False  # set (under console_permissions.LOCK) once its prompts can no longer be answered
        self.writing = threading.Lock()

    def add(self, entry: ConsoleEntry) -> ConsoleEntry:
        """Show the entry to followers and, unless it is live-only, keep it in console.jsonl (several threads add:
        the turn and its permission prompts)."""
        with self.writing:
            if entry.role not in LIVE_ONLY:
                append_jsonl(self.run, CONSOLE_FILE, entry)
        with self.changed:
            self.entries.append(entry)
            self.changed.notify_all()
        return entry


TURNS: dict[Path, Turn] = {}  # run (resolved) → its running turn


def running(run: Path) -> Turn | None:
    return TURNS.get(run.resolve())


def start_turn(run: Path, message: str, base_url: str = "") -> Turn | None:
    """Start one turn in a background thread that owns the turn lock, the Claude Code process and console.jsonl;
    None when a turn of this run is already running. The page only follows it: a reload or a closed drawer never
    frees the lock while Claude Code is still working (H7)."""
    lock = turn_lock(run)
    if not lock.__enter__():
        lock.__exit__(None, None, None)
        return None
    turn = Turn(run)
    try:
        settings = load_settings(run)
        options = TurnOptions(
            model=settings.model,
            mode=settings.mode,
            permission_url=f"{base_url.rstrip('/')}/api/console-permission/{run.name}" if base_url else None,
            token=turn.token,
            config_dir=settings_path(run).parent,
        )
        TURNS[run.resolve()] = turn
        thread = threading.Thread(target=lambda: work(), name=f"console {run.name}", daemon=True)
    except Exception:
        lock.__exit__(None, None, None)
        raise

    def work():
        try:
            run_turn(run, message, turn, options)
        except Exception:
            log.exception("%s: console turn failed", run.name)
            turn.add(
                ConsoleEntry(at=now_text(), role="error", text="The Console Turn Failed; the Details Are in the Log.")
            )
        finally:
            TURNS.pop(run.resolve(), None)
            from app.web import console_permissions  # the prompts of this turn can no longer be answered

            console_permissions.end_turn(turn)
            lock.__exit__(None, None, None)
            with turn.changed:
                turn.finished.set()
                turn.changed.notify_all()

    thread.start()
    return turn


async def follow_lines(turn: Turn) -> AsyncIterator[str]:
    """The turn as NDJSON lines for the page, without holding a server thread while it waits; a blank line every
    HEARTBEAT seconds keeps quiet connections (a prompt waiting for an answer) open."""
    shown, quiet = 0, 0.0
    while True:
        new, finished = turn.entries[shown:], turn.finished.is_set()
        shown += len(new)
        for entry in new:
            yield entry.model_dump_json() + "\n"
        if finished and shown == len(turn.entries):
            return
        if new:
            quiet = 0.0
        elif quiet >= HEARTBEAT:
            quiet = 0.0
            yield "\n"
        await asyncio.sleep(0.05)
        quiet += 0.05


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


def run_turn(run: Path, message: str, turn: Turn, options: TurnOptions) -> None:
    """One turn: the user's message, then what Claude Code does as it happens. The caller holds turn_lock; the process
    is stopped if the turn ends early, and its stderr goes to a file (a full pipe would hang it)."""
    turn.add(ConsoleEntry(at=now_text(), role="you", text=message))
    log.info("%s: console turn started (%d characters, %s, %s)", run.name, len(message), options.model, options.mode)
    command = claude_turn_command(run, message, load_state(run).console_session, options)
    reader = EventReader(run)
    pending: list[ConsoleEntry] = []  # streamed text not yet sent: one entry per COALESCE seconds, not per token

    flushed = [0.0]

    def flush():
        if pending:
            turn.add(pending[0].model_copy(update={"text": "".join(entry.text for entry in pending)}))
            pending.clear()
        flushed[0] = time.monotonic()

    with tempfile.TemporaryFile("w+") as stderr:
        process = subprocess.Popen(command, cwd=run, stdout=subprocess.PIPE, stderr=stderr, text=True)
        turn.process = process
        if turn.stopped:  # Stop came while it was starting
            process.terminate()
        assert process.stdout is not None
        try:
            for line in process.stdout:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("session_id") and event.get("type") == "system" and event.get("subtype") == "init":
                    session_id = event["session_id"]
                    update_state(
                        run, lambda state, session_id=session_id: setattr(state, "console_session", session_id)
                    )
                usage.record(event)  # the usage limits on Home follow every turn
                if event.get("type") == "result" and (cost := event.get("total_cost_usd")):  # the profile's net spend
                    update_state(
                        run, lambda state, cost=cost: setattr(state, "spend_usd", state.spend_usd + float(cost))
                    )
                try:
                    shown = reader.read(event)
                except Exception:  # one odd event never ends the turn
                    log.exception("%s: console event not shown: %s", run.name, str(event)[:300])
                    continue
                if pending and not shown and time.monotonic() - flushed[0] >= COALESCE:
                    flush()  # the end of a text block: its last words go out now, not with the next text
                for entry in shown:
                    if entry.role == "partial":
                        pending.append(entry)
                        if time.monotonic() - flushed[0] >= COALESCE:
                            flush()
                        continue
                    flush()
                    turn.add(entry)
            flush()
            process.wait()
        finally:
            if options.config_file:
                options.config_file.unlink(missing_ok=True)
            if process.poll() is None:  # the turn ended early: never leave Claude Code running unowned
                process.terminate()
                try:
                    process.wait(10)
                except subprocess.TimeoutExpired:
                    process.kill()
        if turn.stopped:
            log.info("%s: console turn stopped by the user", run.name)
            if reader.streamed.strip():  # what Claude was writing when stopped stays in the transcript
                turn.add(ConsoleEntry(at=now_text(), role="claude", text=reader.streamed.strip() + " …"))
            turn.add(
                ConsoleEntry(at=now_text(), role="system", text="Stopped by You. Claude Keeps What It Already Did.")
            )
        elif process.returncode == 0:
            log.info("%s: console turn finished", run.name)
        else:
            stderr.seek(0)
            tail = stderr.read()[-600:].strip()
            log.error("%s: Claude Code stopped (exit %s): %s", run.name, process.returncode, tail)
            turn.add(
                ConsoleEntry(
                    at=now_text(),
                    role="error",
                    text=f"Claude Code Stopped Unexpectedly (Exit {process.returncode}). The Details Are in the Log.",
                )
            )


def claude_process(root: int) -> int:
    """The Claude Code process under the turn's bwrap (the deepest descendant named claude), else the root."""
    children: dict[int, list[int]] = {}
    names: dict[int, str] = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text().rsplit(")", 1)[1].split()
            names[int(entry.name)] = (entry / "comm").read_text().strip()
            children.setdefault(int(fields[1]), []).append(int(entry.name))
        except (OSError, IndexError, ValueError):
            continue
    queue = [root]
    while queue:  # breadth first: the shallowest claude is the one the jail started
        pid = queue.pop(0)
        if names.get(pid) == "claude":
            return pid
        queue += children.get(pid, [])
    return root


def stop_turn(run: Path) -> bool:
    """Interrupt the run's turn: SIGINT to Claude Code (it ends the turn and keeps the session resumable), then
    SIGTERM to the jail after 5 s if it is still running. False when no turn runs."""
    turn = running(run)
    if turn is None or turn.finished.is_set() or (turn.process is not None and turn.process.poll() is not None):
        return False
    turn.stopped = True
    if turn.process is None:  # asked before Claude Code started: run_turn stops it as soon as it exists
        return True
    try:
        os.kill(claude_process(turn.process.pid), signal.SIGINT)
    except ProcessLookupError:
        pass  # it ended meanwhile; the jail is still made sure of below

    def escalate(process=turn.process):
        try:
            process.wait(5)
        except subprocess.TimeoutExpired:
            process.terminate()

    threading.Thread(target=escalate, daemon=True).start()
    return True


def clear(run: Path) -> None:
    """/clear: the next message starts a new Claude Code session; this session's allowances end with it."""

    from app.web import console_permissions

    update_state(run, lambda state: setattr(state, "console_session", None))
    console_permissions.forget(run)
    append_jsonl(run, CONSOLE_FILE, ConsoleEntry(at=now_text(), role="system", text="New Conversation."))


def run_files(run: Path, query: str, limit: int = 30) -> list[str]:
    """@ autocomplete: the run's files (relative paths), hidden ones left out, matching the query."""
    query = query.strip().lower()
    if ".." in query:
        return []
    found = []
    for folder, folders, names in os.walk(run):
        folders[:] = sorted(name for name in folders if not name.startswith("."))  # hidden folders are never walked
        for name in sorted(names):
            relative = (Path(folder) / name).relative_to(run).as_posix()
            if not name.startswith(".") and query in relative.lower():
                found.append(relative)
                if len(found) >= limit:
                    return found
    return found
