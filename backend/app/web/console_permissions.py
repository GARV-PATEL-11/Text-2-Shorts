"""Permission prompts for console turns: Claude Code's --permission-prompt-tool, served as a tiny MCP server over HTTP
by Faraday itself (POST /api/console-permission/<run>).

Claude Code (inside the run's jail) asks; the call carries the running turn's random token (in an owner-only config
file, never on a command line), so nothing else can ask. The prompt is shown in the console and held until the signed-in
page answers (Allow Once, Allow for This Session, Deny with a note), the turn ends, or ANSWER_SECONDS pass (deny).
Everything that decides is held by the server: answers come only from the signed-in page, and session allowances live
in this process's memory, never in the run folder the jail can write. Claude Code enforces the decision. Contract
probed on Claude Code 2.1.332 (docs/console/CONSOLE_REFERENCE_AND_GAP_ANALYSIS.md §2).
"""

from __future__ import annotations

import json
import re
import secrets
import shlex
import threading
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from schemas.api import ConsoleEntry

from app.utilities import now_text
from app.web import console

TOOL_NAME = "permission"  # → mcp__faraday__permission
ANSWER_SECONDS = 600
MAX_WAITING = 4  # prompts one turn may hold open at once (each holds a server thread); more are denied
ANSWERED_ELSEWHERE = {"AskUserQuestion", "ExitPlanMode"}  # the page shows these; the user answers in the console
SHELL_OPERATORS = re.compile(r"[;&|`<>]|\$\(|\$\{|\n")
WRAPPERS = {  # run whatever follows them: never allowed for a session
    "bash", "sh", "zsh", "dash", "fish", "env", "xargs", "sudo", "su", "doas", "eval", "exec", "nohup", "timeout",
    "nice", "ionice", "time", "find", "command", "builtin", "watch", "parallel", "ssh", "awk", "sed", "busybox",
}  # fmt: skip
FILE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
TOOL = {
    "name": TOOL_NAME,
    "description": "Asks the Faraday user to allow or deny a tool call.",
    "inputSchema": {
        "type": "object",
        "properties": {"tool_name": {"type": "string"}, "input": {"type": "object"}, "tool_use_id": {"type": "string"}},
        "required": ["tool_name", "input"],
    },
}


@dataclass
class Prompt:
    entry: ConsoleEntry
    turn: console.Turn
    tool_input: dict
    answered: threading.Event = field(default_factory=threading.Event)
    decision: str = "deny"
    note: str = ""


PROMPTS: dict[str, Prompt] = {}  # prompt id → the prompt waiting for the page
ALLOWED: dict[Path, list[str]] = {}  # run (resolved) → this session's allowances (memory only; /clear forgets)
LOCK = threading.Lock()


def allowed(run: Path) -> list[str]:
    with LOCK:
        return list(ALLOWED.get(run.resolve(), []))


def forget(run: Path) -> None:
    with LOCK:
        ALLOWED.pop(run.resolve(), None)


def command_words(command: str) -> list[str] | None:
    """A single plain command's words; None for anything compound, substituted or unparsable."""
    command = command.strip()
    if not command or SHELL_OPERATORS.search(command):
        return None
    try:
        words = shlex.split(command)
    except ValueError:
        return None
    return words or None


def is_wrapper(word: str) -> bool:
    """A command that runs whatever follows it, by name or by path (`/usr/bin/env`), or a VAR=value prefix."""
    return Path(word).name in WRAPPERS or "=" in word


def inside(path: object, run: Path) -> bool:
    try:
        return Path(str(path)).resolve().is_relative_to(run.resolve())
    except (OSError, ValueError):
        return False


def rule_for(tool: str, tool_input: dict, run: Path) -> str | None:
    """The allowance "Allow for This Session" would add, as narrow as Claude Code's own: Bash by its command and first
    argument (never a wrapper, an inline-code flag, a variable assignment or a compound command); a file tool only for
    files inside this run; WebFetch by domain; another tool by name. None: Allow Once only."""
    if tool == "Bash":
        words = command_words(str(tool_input.get("command", "")))
        if not words or is_wrapper(words[0]):
            return None
        if len(words) == 1:
            return f"Bash({words[0]})"  # exactly this command: `make` never covers `make -f other.mk`
        if words[1].startswith("-"):
            return None  # "python3 -c …", "git -c …": the flag can change everything that follows
        return f"Bash({words[0]} {words[1]} *)"
    if tool in FILE_TOOLS:
        path = tool_input.get("file_path") or tool_input.get("notebook_path")
        return f"{tool}({run.name}/**)" if path and inside(path, run) else None
    if tool == "WebFetch":
        host = urlparse(str(tool_input.get("url", ""))).hostname
        return f"WebFetch(domain:{host})" if host else None
    return tool or None


def allows(rule: str, tool: str, tool_input: dict, run: Path) -> bool:
    """Whether a session allowance covers this call."""
    if tool == "Bash":
        found = re.fullmatch(r"Bash\((.+?)( \*)?\)", rule)
        words = command_words(str(tool_input.get("command", "")))
        if not found or not words or is_wrapper(words[0]):
            return False
        prefix = found[1].split(" ")
        return words[: len(prefix)] == prefix if found[2] else words == prefix
    if tool in FILE_TOOLS:
        path = tool_input.get("file_path") or tool_input.get("notebook_path")
        return rule == f"{tool}({run.name}/**)" and bool(path) and inside(path, run)
    if tool == "WebFetch":
        return rule == f"WebFetch(domain:{urlparse(str(tool_input.get('url', ''))).hostname})"
    return rule == tool


def describe(tool: str, tool_input: dict) -> str:
    if tool == "Bash":
        return f"Run a shell command: `{tool_input.get('command', '')}`"
    if tool in FILE_TOOLS:
        verb = "Create" if tool == "Write" else "Edit"
        return f"{verb} `{tool_input.get('file_path') or tool_input.get('notebook_path', '')}`"
    if tool == "WebFetch":
        return f"Fetch `{tool_input.get('url', '')}`"
    if tool == "WebSearch":
        return f"Search the web for “{tool_input.get('query', '')}”"
    return f"Use {tool}"


def reply(ident, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": ident, "result": result}


def verdict(ident, behavior: str, **fields) -> dict:
    return reply(ident, {"content": [{"type": "text", "text": json.dumps({"behavior": behavior, **fields})}]})


def handle(run: Path, token: str | None, message: dict) -> dict | None:
    """One MCP JSON-RPC message from the turn's Claude Code → its reply (None for a notification). Raises
    PermissionError when the token is not the running turn's (or no turn runs)."""
    turn = console.running(run)
    if turn is None or turn.finished.is_set() or not token or not secrets.compare_digest(token, turn.token):
        raise PermissionError("not this run's running turn")
    method, ident = message.get("method"), message.get("id")
    if ident is None:
        return None
    if method == "initialize":
        version = (message.get("params") or {}).get("protocolVersion", "2025-11-25")
        return reply(ident, {"protocolVersion": version, "capabilities": {"tools": {}},
                             "serverInfo": {"name": "faraday", "version": "1"}})  # fmt: skip
    if method == "tools/list":
        return reply(ident, {"tools": [TOOL]})
    if method != "tools/call":
        return reply(ident, {})
    arguments = (message.get("params") or {}).get("arguments") or {}
    tool_input = arguments.get("input") if isinstance(arguments.get("input"), dict) else {}
    return ask(turn, ident, str(arguments.get("tool_name", "")), tool_input, str(arguments.get("tool_use_id") or ""))


def ask(turn: console.Turn, ident, tool: str, tool_input: dict, tool_use_id: str = "") -> dict:
    if tool in ANSWERED_ELSEWHERE:
        return verdict(
            ident, "deny", message="The user sees this in the Faraday console and answers in their next message."
        )
    if any(allows(rule, tool, tool_input, turn.run) for rule in allowed(turn.run)):
        return verdict(ident, "allow", updatedInput=tool_input)
    rule = rule_for(tool, tool_input, turn.run)
    with LOCK:
        if turn.finished.is_set() or turn.ended:
            return verdict(ident, "deny", message="The turn has ended.")
        if sum(prompt.turn is turn for prompt in PROMPTS.values()) >= MAX_WAITING:
            return verdict(ident, "deny", message="Too many permission prompts are open at once. Ask one at a time.")
        fresh = re.fullmatch(r"[A-Za-z0-9_-]{1,80}", tool_use_id) and tool_use_id not in PROMPTS
        prompt_id = tool_use_id if fresh else secrets.token_hex(6)  # the call's own id: shown on that call's line
        entry = ConsoleEntry(at=now_text(), role="permission", text=describe(tool, tool_input), id=prompt_id, tool=tool,
                             input=console.cut_input(tool_input), rule=rule)  # fmt: skip
        prompt = Prompt(entry=entry, turn=turn, tool_input=tool_input)
        PROMPTS[prompt_id] = prompt
    turn.add(entry)
    answered = prompt.answered.wait(ANSWER_SECONDS)
    with LOCK:
        PROMPTS.pop(prompt_id, None)
        if not answered:
            prompt.answered.set()  # a late click finds it answered
    if not answered:
        turn.add(
            ConsoleEntry(at=now_text(), role="answer", text="Denied: Nobody Answered in 10 Minutes.", id=prompt_id)
        )
        return verdict(ident, "deny", message="Nobody answered the permission prompt in time. Ask the user what to do.")
    if prompt.decision in ("once", "session"):
        return verdict(ident, "allow", updatedInput=tool_input)
    note = f" The user says: {prompt.note}" if prompt.note else ""
    return verdict(ident, "deny", message=f"The user denied this.{note}")


def pending(run: Path) -> list[ConsoleEntry]:
    with LOCK:
        return [prompt.entry for prompt in PROMPTS.values() if prompt.turn.run.resolve() == run.resolve()]


def answer(run: Path, prompt_id: str, decision: str, note: str = "") -> None:
    """The page's decision. KeyError: no such open prompt for this run; ValueError: "session" where none is offered."""
    with LOCK:
        prompt = PROMPTS.get(prompt_id)
        if prompt is None or prompt.turn.run.resolve() != run.resolve() or prompt.answered.is_set():
            raise KeyError(prompt_id)
        rule = prompt.entry.rule
        if decision == "session" and not rule:
            raise ValueError("This call can only be allowed once.")
        if decision == "session" and rule not in ALLOWED.setdefault(run.resolve(), []):
            ALLOWED[run.resolve()].append(rule)
        prompt.decision, prompt.note = decision, note
        prompt.answered.set()  # inside the lock: two clicks never both count
    text = {
        "once": "Allowed Once.",
        "session": f"Allowed for This Session: {rule}.",
        "deny": f"Denied.{' ' + note if note else ''}",
    }[decision]
    prompt.turn.add(ConsoleEntry(at=now_text(), role="answer", text=text, id=prompt_id, tool=prompt.entry.tool))


def end_turn(turn: console.Turn) -> None:
    """The turn ended (finished, stopped or failed): its open prompts are denied and say so in the transcript."""
    with LOCK:
        turn.ended = True
        open_prompts = [(prompt_id, prompt) for prompt_id, prompt in PROMPTS.items()
                        if prompt.turn is turn and not prompt.answered.is_set()]  # fmt: skip
        for _, prompt in open_prompts:
            prompt.decision = "deny"
            prompt.answered.set()
    for prompt_id, _ in open_prompts:
        turn.add(
            ConsoleEntry(
                at=now_text(), role="answer", text="Ended: The Turn Stopped Before You Answered.", id=prompt_id
            )
        )
