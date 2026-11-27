"""How processes are launched in isolation: the bubblewrap jail of a run session, the network-less render jail, and the
Claude Code session command."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from app.config import (
    EFFORT,
    REPOSITORY_ROOT,
    RUN_ENVIRONMENT,
    SCHEMAS_DIRECTORY,
    SESSION_MODEL,
    USER_CACHE_DIRECTORY,
    runtime_template_directory,
)

RENDER_JAIL_PREFIX = [
    "bwrap",
    "--ro-bind",
    "/",
    "/",
    "--dev",
    "/dev",
    "--proc",
    "/proc",
    "--tmpfs",
    "/tmp",
    "--bind",
    str(USER_CACHE_DIRECTORY),
    str(USER_CACHE_DIRECTORY),
    "--unshare-net",
    "--die-with-parent",
]


def render_jail_prefix() -> list[str]:
    """The render jail, plus the chosen template's copy when it lives outside the repo (tests move it to /tmp)."""
    template = runtime_template_directory()
    if template.is_dir() and REPOSITORY_ROOT not in template.resolve().parents:
        return [*RENDER_JAIL_PREFIX, "--ro-bind", str(template), str(template)]
    return list(RENDER_JAIL_PREFIX)


def build_jail_command(run: Path, command: list[str]) -> list[str]:
    """bwrap argv for one run session: system and repo read-only (the repo's .env blanked), only the run folder plus
    Claude Code's own state/caches writable, a private throwaway $HOME into which exactly the PATH folders, the
    install roots of claude and python, and the TTS credentials are mounted back read-only; own PID/IPC namespace;
    network kept for the API."""
    home = Path.home()
    is_within = lambda path, directory: path == directory or directory in path.parents
    mounts = {
        Path(directory)
        for directory in os.environ.get("PATH", "").split(":")
        if directory.startswith(f"{home}/")
        and Path(directory).is_dir()
        and not is_within(Path(directory), REPOSITORY_ROOT)
    }
    claude_executable = Path(shutil.which("claude") or "/").resolve()
    mounts |= {
        claude_executable.parents[1] if len(claude_executable.parents) > 1 else claude_executable,
        Path(sys.base_prefix),
    }
    mounts |= {home / ".aws", home / ".config" / "gcloud"}
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        mounts.add(Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]))
    argv = [
        "bwrap",
        "--ro-bind",
        "/",
        "/",
        "--dev",
        "/dev",
        "--proc",
        "/proc",
        "--tmpfs",
        "/tmp",
        "--tmpfs",
        str(home),
        "--unshare-pid",
        "--unshare-ipc",
    ]
    for directory in sorted(mount for mount in mounts if is_within(mount, home)):
        argv += ["--ro-bind-try", str(directory), str(directory)]
    argv += ["--ro-bind", str(REPOSITORY_ROOT), str(REPOSITORY_ROOT)]
    if (REPOSITORY_ROOT / ".env").exists():
        argv += ["--ro-bind", "/dev/null", str(REPOSITORY_ROOT / ".env")]  # repo secrets stay outside the session
    template = runtime_template_directory()  # the chosen template's copy; already in the repo unless moved (tests)
    if template.is_dir() and not is_within(template.resolve(), REPOSITORY_ROOT):
        argv += ["--ro-bind", str(template), str(template)]
    argv += ["--bind", str(run), str(run)]
    for directory in (home / ".claude", home / ".cache"):
        directory.mkdir(exist_ok=True)
        argv += ["--bind", str(directory), str(directory)]
    argv += [
        "--ro-bind-try",
        str(home / ".claude.json"),
        str(home / ".claude.json.host"),
        "--setenv",
        "PATH",
        f"{REPOSITORY_ROOT / '.venv' / 'bin'}:{os.environ.get('PATH', '')}",
        "--chdir",
        str(run),
        "--die-with-parent",
        "--",
        "sh",
        "-c",
        'cp ~/.claude.json.host ~/.claude.json 2>/dev/null; exec "$@"',
        "sh",
        *command,
    ]
    return argv


KICKOFF_PROMPT = "Produce this video: follow the text-2-shorts-produce skill from the current state."


def session_flags() -> list[str]:
    """What every run session gets: the model and effort, the run environment plugin, its settings and references."""
    return [
        "--model",
        SESSION_MODEL,
        "--effort",
        EFFORT,
        "--plugin-dir",
        str(RUN_ENVIRONMENT),
        "--settings",
        str(RUN_ENVIRONMENT / "settings.json"),
        "--add-dir",
        str(RUN_ENVIRONMENT),
        "--add-dir",
        str(SCHEMAS_DIRECTORY),
    ]


def session_command() -> list[str]:
    """The interactive run session (`text-2-shorts open`): verbose, so every tool call is shown as it happens."""
    return ["claude", *session_flags(), "--verbose", KICKOFF_PROMPT]


def console_claude_arguments(message: str, session_id: str | None) -> list[str]:
    """One turn of the run session from the website's console: the user's message, streamed back as JSON events,
    resuming the same session each turn. With usage_check_arguments, the only places Python starts Claude Code with a
    message: here the message is always the user's own (no prompts are written here)."""
    arguments = ["claude", "-p", "--output-format", "stream-json", "--verbose", *session_flags()]
    resume = ["--resume", session_id] if session_id else []
    return [*arguments, *resume, "--", message]  # "--": a message starting with "-" is never read as an option


USAGE_CHECK_MESSAGE = "Reply with OK."


def usage_check_arguments() -> list[str]:
    """A one-line Haiku turn, no tools, used only for the rate_limit_event Claude Code streams with every turn (Home's
    usage limits, app/web/usage.py). Its fixed message asks for nothing; no run, plugin or prompt is involved."""
    return [
        "claude",
        "-p",
        USAGE_CHECK_MESSAGE,
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        "haiku",
        "--tools",
        "",
    ]
