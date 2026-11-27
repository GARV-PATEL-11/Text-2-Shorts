"""The `text-2-shorts` entry point: the argument parser and command dispatch."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import faraday_logging
from schemas.outline_models.approaches import APPROACHES, MINUTES

from app.commands.hook_command import handle_hook_command
from app.commands.production_commands import (
    handle_accept_command,
    handle_final_command,
    handle_preview_command,
    handle_voice_command,
)
from app.commands.run_commands import handle_new_command, handle_open_command
from app.commands.serve_command import handle_serve_command
from app.commands.workflow_commands import (
    handle_approve_command,
    handle_doc_command,
    handle_feedback_command,
    handle_hash_command,
    handle_next_command,
    handle_report_command,
    handle_resolve_command,
    handle_status_command,
    handle_usage_ok_command,
    handle_validate_command,
)
from app.config import DEFAULT_TTS, REPORTS_DIRECTORY, RUNS_DIRECTORY
from app.utilities import cli_quote
from app.workflow import visual_director
from app.workflow.mistakes import write_report
from app.workflow.run_workspace import resolve_run_path
from app.workflow.scene_code import prepare_scene
from app.workflow.templates import choose_template, starter_templates

COMMAND_HELP = {
    "new": "start a new run from a topic",
    "open": "open Claude Code in a run's isolated workspace",
    "voice": "make the narration audio for a run",
    "template": "choose the look and sound of a run",
    "final": "assemble the final video",
    "status": "show where a run stands",
    "report": "show the Claude usage of a run",
    "validate": "check a file Claude wrote",
    "next": "show what happens next in a run",
    "preview": "make a preview of one scene",
    "hash": "show the version marker of a script, plan or scene",
    "task": "show the instructions for building one scene",
    "accept": "check a built scene",
    "usage-ok": "continue one step although Claude usage is high",
    "resolve": "mark a change request as applied or declined",
}


def video_minutes(text: str) -> float:
    """--minutes: a new video's teaching length (MINUTES)."""
    minutes = float(text)
    if not MINUTES[0] <= minutes <= MINUTES[1]:
        raise argparse.ArgumentTypeError(f"a video is {MINUTES[0]}–{MINUTES[1]} minutes of teaching")
    return minutes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="text-2-shorts", epilog=cli_quote("help"))
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    command_parser = subparsers.add_parser("new", help=COMMAND_HELP["new"])
    command_parser.add_argument("requirement")
    command_parser.add_argument(
        "--objective",
        action="append",
        default=[],
        help="what the viewer should be able to do or explain afterwards (repeat for several)",
    )
    command_parser.add_argument("--style", default="ELI5 / Feynman", help="explanation style and tone")
    command_parser.add_argument(
        "--approach",
        choices=list(APPROACHES),
        default="visual_intuition",
        help="how the topic is taught: "
        + ", ".join(f"{key} ({approach.name}, {approach.form})" for key, approach in APPROACHES.items()),
    )
    command_parser.add_argument(
        "--minutes", type=video_minutes, default=4, help="teaching narration, 3–20 (intro, bridges, closing extra)"
    )
    command_parser.add_argument("--pace", choices=["slow", "medium", "fast"], default="medium")
    command_parser.add_argument("--audience", default="curious beginners")
    command_parser.add_argument("--notes", default="")
    command_parser.add_argument(
        "--tts",
        choices=["polly", "google"],
        default=DEFAULT_TTS,
        help="narration provider: AWS Polly or Google Cloud Text-to-Speech (voice, speed and look: the template)",
    )
    command_parser.set_defaults(handler=handle_new_command)

    command_parser = subparsers.add_parser("open", help=COMMAND_HELP["open"])
    command_parser.add_argument("run")
    command_parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="-- CMD…: run CMD instead of Claude Code in the isolated workspace (for debugging)",
    )
    command_parser.set_defaults(handler=handle_open_command)

    register_subcommands(subparsers)
    return parser


def main() -> None:
    arguments = build_parser().parse_args()
    if getattr(arguments, "run", None):
        arguments.run = str(Path(arguments.run).resolve())
    if arguments.subcommand == "serve":
        faraday_logging.configure("backend")
    elif arguments.subcommand != "hook":  # the hook finds its run itself; stderr would reach Claude's context
        run = Path(arguments.run) if getattr(arguments, "run", None) and Path(arguments.run).is_dir() else None
        faraday_logging.configure("runtime", run, console=False)
    log = logging.getLogger("app.cli")
    log.info("text-2-shorts %s", " ".join(sys.argv[1:])[:500])
    try:
        arguments.handler(arguments)
    except SystemExit as stopped:
        if stopped.code not in (None, 0):
            log.warning("%s stopped: %s", arguments.subcommand, str(stopped.code)[:2000])
        raise
    except Exception:
        log.exception("%s failed", arguments.subcommand)
        raise


def register_subcommands(subparsers) -> None:
    def add_subcommand(name, handler, *, scenes=False, clips=False, feedback=False, force=False):
        command_parser = subparsers.add_parser(name, help=COMMAND_HELP.get(name))
        command_parser.add_argument("run")
        if scenes:
            command_parser.add_argument("--scenes", help="comma-separated scene numbers")
        if clips:
            command_parser.add_argument("--clips", help="comma-separated clip ids to rebuild, e.g. s01c02")
        if feedback:
            command_parser.add_argument("--feedback")
        if force:
            command_parser.add_argument("--force", action="store_true")
        command_parser.set_defaults(handler=lambda arguments: handler(resolve_run_path(arguments)))
        return command_parser

    add_subcommand("voice", handle_voice_command)
    serve_parser = subparsers.add_parser(
        "serve", help="the web view: follow runs, approve checkpoints, ask for changes (this machine)"
    )
    serve_parser.add_argument("--port", type=int, default=8765)
    serve_parser.set_defaults(handler=handle_serve_command)
    subparsers.add_parser("templates", help="the starter templates").set_defaults(
        handler=lambda arguments: print(
            "\n".join(f"{template.name}: {template.description}" for template in starter_templates())
        )
    )
    command_parser = add_subcommand(
        "template", lambda arguments: print(choose_template(Path(arguments.run), arguments.name, arguments.set))
    )
    command_parser.add_argument("name")
    command_parser.add_argument(
        "--set",
        action="append",
        default=[],
        help="element=variant · custom.element=value · key=value, e.g. accent_color=coral, custom.text_font=Lato",
    )
    add_subcommand("final", handle_final_command, force=True)
    add_subcommand("status", handle_status_command)
    add_subcommand("report", handle_report_command)
    mistakes_parser = subparsers.add_parser(
        "mistakes", help="which mistakes each helper makes, across all runs; written to artifacts/reports/"
    )
    mistakes_parser.add_argument("--runs", default=str(RUNS_DIRECTORY), help="the runs folder to read")
    mistakes_parser.add_argument("--out", default=str(REPORTS_DIRECTORY), help="where to write the report")
    mistakes_parser.set_defaults(
        handler=lambda arguments: print("\n".join(map(str, write_report(Path(arguments.runs), Path(arguments.out)))))
    )
    subparsers.add_parser("hook", help="Claude Code hook entry point (reads the hook JSON on stdin)").set_defaults(
        handler=handle_hook_command
    )
    command_parser = add_subcommand(  # the Visual Director's filled prompt for one scene, for the scene-planner
        "plan-task", lambda arguments: print(visual_director.task(Path(arguments.run), arguments.scene))
    )
    command_parser.add_argument("--scene", required=True, help="sNN")
    command_parser = add_subcommand("validate", handle_validate_command)
    command_parser.add_argument(
        "what",
        choices=[
            "brief",
            "topics",
            "content",
            "outline",
            "preferences",
            "script",
            "script-review",
            "plan",
            "plan-review",
            "script-critique",
            "plan-critique",
            "video-critique",
            "changes",
        ],
    )
    command_parser.add_argument("--scene", help="sNN (plan: default every scene; critiques: required)")
    doc_parser = subparsers.add_parser("doc", help="Manim API cards by name, e.g. MathTex,Axes.plot")
    doc_parser.add_argument("names")
    doc_parser.add_argument("--topics", default="", help="reference files, e.g. manim-vocabulary,manim-common-mistakes")
    doc_parser.set_defaults(handler=handle_doc_command)
    command_parser = add_subcommand("next", handle_next_command)
    command_parser.add_argument("--json", action="store_true")
    command_parser = add_subcommand("preview", handle_preview_command)
    command_parser.add_argument("scene", help="sNN")
    command_parser = add_subcommand("hash", handle_hash_command)
    command_parser.add_argument("scene", help="script | plans | sNN")
    command_parser.add_argument("kind", nargs="?", choices=["script", "plan", "video"])
    command_parser = add_subcommand(
        "task", lambda arguments: print(prepare_scene(Path(arguments.run), arguments.scene))
    )
    command_parser.add_argument("scene", help="sNN")
    command_parser = add_subcommand("accept", handle_accept_command)
    command_parser.add_argument("scene", help="sNN")
    add_subcommand("usage-ok", handle_usage_ok_command)  # the user's go-ahead past the usage gate, one step
    command_parser = add_subcommand("approve", handle_approve_command, force=True)
    command_parser.add_argument(
        "target", help="requirements | template | outline | script | plan | sNN | final | start:sNN"
    )
    command_parser.add_argument("--notes", default="", help="the user's notes with the approval")
    command_parser = add_subcommand("feedback", handle_feedback_command)
    command_parser.add_argument("target", help="outline | script | plan | final | sNN | sNNcMM")
    command_parser.add_argument(
        "--kind",
        default="visual",
        choices=["wording", "visual", "audio-timing", "accuracy", "structure", "style", "other"],
    )
    command_parser.add_argument("--text", required=True, help="the user's request, in their words")
    command_parser.add_argument("--checkpoint", help="the checkpoint it was raised at (records 'changes requested')")
    command_parser = add_subcommand("resolve", handle_resolve_command)
    command_parser.add_argument("id", help="r001, r002, …")
    command_parser.add_argument("status", choices=["applied", "declined"])
    command_parser.add_argument("--note", default="")


if __name__ == "__main__":
    main()
