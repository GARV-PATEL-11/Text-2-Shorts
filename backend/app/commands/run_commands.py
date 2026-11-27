"""Command handlers for `new` (provision a run) and `open` (start its jailed session)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from pydantic import ValidationError

from app.config import REPOSITORY_ROOT
from app.sandbox import build_jail_command, session_command
from app.utilities import cli_quote
from app.workflow.run_workspace import RunNotCreated, brief_from_arguments, create_run


def handle_new_command(arguments) -> None:
    try:
        run = create_run(brief_from_arguments(arguments))
    except ValidationError as error:
        sys.exit(f"Invalid requirements: {error}")
    except RunNotCreated as problem:
        sys.exit(str(problem))
    print(run.relative_to(REPOSITORY_ROOT))
    print(
        f"next: text-2-shorts serve (the website), or text-2-shorts open {run.relative_to(REPOSITORY_ROOT)}   "
        "(Claude Code in this run's isolated workspace)"
    )
    print(cli_quote("new"))


def handle_open_command(arguments) -> None:
    """Start an interactive Claude Code session for this run inside its jail, with the runtime-environment/ plugin
    and settings."""
    run = Path(arguments.run)
    if not (run / "brief.json").exists():
        sys.exit(f"{run} is not a run workspace (no brief.json) — create one with text-2-shorts new")
    command = arguments.command[1:] if arguments.command[:1] == ["--"] else arguments.command
    command = command or session_command()
    os.execvp("bwrap", build_jail_command(run.resolve(), command, interactive=True))
