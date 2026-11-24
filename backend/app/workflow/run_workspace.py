"""Run workspaces: creating one from the user's requirements and finding it from a path."""

from __future__ import annotations

import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from schemas.requirements import Brief, EnvironmentReport

from app.config import (
    DEFAULT_GOOGLE_VOICE,
    DEFAULT_POLLY_VOICE,
    PYTHON_EXECUTABLE,
    REPOSITORY_ROOT,
    RUN_ENVIRONMENT,
    RUNS_DIRECTORY,
    TOOLS_DIRECTORY,
)


def brief_from_arguments(arguments) -> Brief:
    """Stage 1: the user's requirements as a validated `Brief` (raises ValidationError when they are not valid)."""
    default_voice = DEFAULT_GOOGLE_VOICE if arguments.tts == "google" else DEFAULT_POLLY_VOICE
    return Brief.model_validate(
        {
            "requirement": arguments.requirement,
            "objectives": arguments.objective,
            "audience": arguments.audience,
            "style": arguments.style,
            "approach": arguments.approach,
            "minutes": arguments.minutes,
            "pace": arguments.pace,
            "notes": arguments.notes,
            "tts": arguments.tts,
            "voice": arguments.voice or default_voice,
            "engine": arguments.engine,
            "font": arguments.font,
        }
    )


class RunNotCreated(Exception):
    """Why a run cannot start (missing tools, credentials or font), in words the user can act on."""


def environment_check() -> EnvironmentReport:
    """What preflight finds on this machine (Manim, LaTeX, ffmpeg, bubblewrap, Claude Code)."""
    preflight = subprocess.run(
        [PYTHON_EXECUTABLE, str(TOOLS_DIRECTORY / "preflight.py")], capture_output=True, text=True
    )
    return EnvironmentReport.model_validate_json(preflight.stdout)


def voice_credentials_problem(tts: str) -> str | None:
    if tts == "polly":
        import boto3

        if boto3.Session().get_credentials() is None:
            return "AWS credentials not found for Polly — run `aws configure` or set AWS_PROFILE (or use Google)"
        return None
    import google.auth

    try:
        google.auth.default()
    except google.auth.exceptions.DefaultCredentialsError:
        return (
            "Google credentials not found — run `gcloud auth application-default login` or set "
            "GOOGLE_APPLICATION_CREDENTIALS (or use Polly)"
        )
    return None


def font_problem(font: str | None) -> str | None:
    if not font:
        return None
    families = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True).stdout
    installed = {name.strip().lower() for line in families.splitlines() for name in line.split(",")}
    return None if font.lower() in installed else f"Font not installed: {font!r} — pick one from `fc-list : family`"


def create_run(brief: Brief, runs_directory: Path = RUNS_DIRECTORY) -> Path:
    """A new run workspace for this brief, after the checks that would otherwise fail only at render time."""
    environment = environment_check()
    if environment.problems:
        raise RunNotCreated(f"Preflight failed: {', '.join(environment.problems)}")
    if problem := voice_credentials_problem(brief.tts) or font_problem(brief.font):
        raise RunNotCreated(problem)
    slug = re.sub(r"[^a-z0-9]+", "-", brief.requirement.lower())[:40].strip("-")
    run = runs_directory / f"{datetime.now():%Y%m%d-%H%M%S}-{slug}"
    provision_run_workspace(run, brief, environment)
    return run


def provision_run_workspace(run: Path, brief: Brief, environment: EnvironmentReport) -> None:
    """Create one run workspace from the environment definition in runtime-environment/
    (the run's own CLAUDE.md + inputs)."""
    run.mkdir(parents=True)
    (run / "brief.json").write_text(brief.model_dump_json(indent=2))
    (run / "environment_report.json").write_text(environment.model_dump_json(indent=2))
    (run / "CLAUDE.md").write_text((RUN_ENVIRONMENT / "workspace" / "CLAUDE.md").read_text())
    if (REPOSITORY_ROOT / "preferences.json").exists():  # standing preferences carry into every new run
        shutil.copy(REPOSITORY_ROOT / "preferences.json", run / "preferences.json")


def find_run_directory(*starts) -> Path | None:
    """The run folder (the one holding brief.json) at or above any of the given paths."""
    for start in filter(None, starts):
        start_path = Path(start).resolve()
        found = next(
            (directory for directory in [start_path, *start_path.parents] if (directory / "brief.json").exists()), None
        )
        if found:
            return found
    return None


def resolve_run_path(arguments):
    arguments.run = str(Path(arguments.run).resolve())
    return arguments
