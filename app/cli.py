"""The `text-2-shorts` CLI entry point: provisioning (`text-2-shorts new`) and the run jail
(`text-2-shorts open`); deterministic steps only.
Reasoning (outline, clip plans, clip code, math review) is done by the Claude Code session that runs inside the
run workspace (run-environment/ plugin: skills, subagents, hooks); it calls these commands.
Run-level commands: app/run_steps.py. Speech synthesis: app/narration.py.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
RUN_ENVIRONMENT = (
    REPOSITORY_ROOT / "run-environment"
)  # the execution environment: Claude Code plugin + settings + workspace template
PYTHON_EXECUTABLE = sys.executable  # the venv interpreter — manim is installed here
FINAL_FRAME_RATE = int(
    os.environ.get("TEXT_2_SHORTS_FPS", 60)
)  # final render is always 2560x1440 (-qp, 16:9); 60–120 fps
MAX_PARALLEL_RENDERS = int(os.environ.get("TEXT_2_SHORTS_PARALLEL", 4))  # scenes at a time (user's call: 4)
USER_CACHE_DIRECTORY = Path.home() / ".cache"
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


# ── Schemas for new stages ────────────────────────────────────────────────────


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def probe_duration_seconds(path: Path) -> float:
    ffprobe_output = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return float(ffprobe_output.strip())


def run_in_parallel(function, items):
    with ThreadPoolExecutor(MAX_PARALLEL_RENDERS) as executor:
        return list(executor.map(function, items))


# ── Steps ─────────────────────────────────────────────────────────────────────


def handle_new_command(arguments) -> None:
    preflight = subprocess.run(
        [PYTHON_EXECUTABLE, str(REPOSITORY_ROOT / "tools" / "preflight.py")], capture_output=True, text=True
    )
    if preflight.returncode:  # fail before any paid call: missing LaTeX/ffmpeg/bwrap/… would only surface at render
        sys.exit(f"Preflight failed: {json.loads(preflight.stdout)['problems']}")
    if arguments.tts == "polly":
        import boto3

        if boto3.Session().get_credentials() is None:
            sys.exit(
                "AWS credentials not found for Polly — run `aws configure` or set AWS_PROFILE (or use --tts google)"
            )
    else:
        import google.auth

        try:
            google.auth.default()
        except google.auth.exceptions.DefaultCredentialsError:
            sys.exit(
                "Google credentials not found — run `gcloud auth application-default login` or set "
                "GOOGLE_APPLICATION_CREDENTIALS (or use --tts polly)"
            )
    families = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True).stdout
    if arguments.font and arguments.font.lower() not in {
        family_name.strip().lower() for line in families.splitlines() for family_name in line.split(",")
    }:
        sys.exit(f"Font not installed: {arguments.font!r} — pick one from `fc-list : family`")
    slug = re.sub(r"[^a-z0-9]+", "-", arguments.requirement.lower())[:40].strip("-")
    run = REPOSITORY_ROOT / "runs" / f"{datetime.now():%Y%m%d-%H%M%S}-{slug}"
    provision_run_workspace(
        run,
        {
            "requirement": arguments.requirement,
            "approach": arguments.approach,
            "minutes": arguments.minutes,
            "pace": arguments.pace,
            "audience": arguments.audience,
            "notes": arguments.notes,
            "tts": arguments.tts,
            "voice": arguments.voice,
            "engine": arguments.engine,
            "font": arguments.font,
        },
        json.loads(preflight.stdout),
    )
    print(run.relative_to(REPOSITORY_ROOT))
    print(
        f"next: text-2-shorts open {run.relative_to(REPOSITORY_ROOT)}   "
        "(starts Claude Code inside this run's isolated workspace)"
    )


def provision_run_workspace(run: Path, brief: dict, env_report: dict) -> None:
    """Create one run workspace from the environment definition in run-environment/
    (the run's own CLAUDE.md + inputs)."""
    run.mkdir(parents=True)
    write_json(run / "brief.json", brief)
    write_json(run / "environment_report.json", env_report)
    (run / "CLAUDE.md").write_text((RUN_ENVIRONMENT / "workspace" / "CLAUDE.md").read_text())


def build_jail_command(run: Path, command: list[str]) -> list[str]:
    """bwrap argv for one run session: system and repo read-only (the repo's .env blanked), only the run folder plus
    Claude Code's own state/caches writable, a private throwaway $HOME into which exactly the PATH folders, the
    install roots of claude and python, and the TTS credentials are mounted back read-only; own PID/IPC namespace;
    network kept for the API."""
    home = Path.home()
    is_within = lambda path, directory: path == directory or directory in path.parents  # noqa: E731
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


def handle_open_command(arguments) -> None:
    """Start an interactive Claude Code session for this run inside its jail, with the run-environment/ plugin
    and settings."""
    run = Path(arguments.run)
    if not (run / "brief.json").exists():
        sys.exit(f"{run} is not a run workspace (no brief.json) — create one with text-2-shorts new")
    command = arguments.command[1:] if arguments.command[:1] == ["--"] else arguments.command
    command = command or [
        "claude",
        "--plugin-dir",
        str(RUN_ENVIRONMENT),
        "--settings",
        str(RUN_ENVIRONMENT / "settings.json"),
        "--add-dir",
        str(RUN_ENVIRONMENT),
        "--add-dir",
        str(REPOSITORY_ROOT / "schemas"),
        "Produce this video: follow the text-2-shorts-produce skill from the current state.",
    ]
    os.execvp("bwrap", build_jail_command(run.resolve(), command))


def main() -> None:
    parser = argparse.ArgumentParser(prog="text-2-shorts")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    command_parser = subparsers.add_parser("new")
    command_parser.add_argument("requirement")
    command_parser.add_argument("--approach", choices=["zoom", "arc", "linear"], default="zoom")
    command_parser.add_argument("--minutes", type=float, default=2)
    command_parser.add_argument("--pace", choices=["slow", "medium", "fast"], default="medium")
    command_parser.add_argument("--audience", default="curious beginners")
    command_parser.add_argument("--notes", default="")
    command_parser.add_argument(
        "--tts",
        choices=["polly", "google"],
        default=os.environ.get("TEXT_2_SHORTS_TTS", "polly"),
        help="narration provider: AWS Polly or Google Cloud Text-to-Speech",
    )
    command_parser.add_argument(
        "--engine",
        choices=["neural", "generative", "standard"],
        default=os.environ.get("POLLY_ENGINE", "neural"),
        help="Polly engine (ignored for Google)",
    )
    command_parser.add_argument(
        "--font", help="font family for all Text (any name from `fc-list : family`); default: Manim's"
    )
    command_parser.add_argument(
        "--voice", help="Polly: Matthew, Joanna, Ruth, Stephen … · Google: en-US-Neural2-D, en-US-Studio-O …"
    )
    command_parser.set_defaults(handler=handle_new_command)

    command_parser = subparsers.add_parser("open")
    command_parser.add_argument("run")
    command_parser.add_argument(
        "command", nargs=argparse.REMAINDER, help="-- CMD…: run CMD instead of claude in the jail (debugging)"
    )
    command_parser.set_defaults(handler=handle_open_command)

    from app import run_steps  # run-level commands (they import this module, so register late)

    run_steps.register_subcommands(subparsers)
    arguments = parser.parse_args()
    if arguments.subcommand == "new" and not arguments.voice:
        arguments.voice = (
            os.environ.get("GOOGLE_VOICE", "en-US-Neural2-D")
            if arguments.tts == "google"
            else os.environ.get("POLLY_VOICE", "Matthew")
        )
    if getattr(arguments, "run", None):
        arguments.run = str(Path(arguments.run).resolve())
    arguments.handler(arguments)


if __name__ == "__main__":
    main()
