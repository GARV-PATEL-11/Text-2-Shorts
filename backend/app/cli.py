"""The `text-2-shorts` entry point: the argument parser and command dispatch."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import faraday_logging

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
    handle_validate_command,
)
from app.config import DEFAULT_TTS
from app.workflow.clips import prepare_clip
from app.workflow.run_workspace import resolve_run_path
from app.workflow.templates import choose_template, starter_templates


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="text-2-shorts")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    command_parser = subparsers.add_parser("new")
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
        choices=["zoom", "arc", "linear", "creative"],
        default="zoom",
        help="narrative structure: zoom (big picture → detail), arc (problem → solution), linear (lesson), "
        "creative (a structure designed for this topic, or the user's own)",
    )
    command_parser.add_argument("--minutes", type=float, default=2)
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

    command_parser = subparsers.add_parser("open")
    command_parser.add_argument("run")
    command_parser.add_argument(
        "command", nargs=argparse.REMAINDER, help="-- CMD…: run CMD instead of claude in the jail (debugging)"
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
        command_parser = subparsers.add_parser(name)
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
    subparsers.add_parser("hook", help="Claude Code hook entry point (reads the hook JSON on stdin)").set_defaults(
        handler=handle_hook_command
    )
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
    doc_parser.add_argument("--topics", default="", help="topic cards, e.g. mathtex-indexing,transforms")
    doc_parser.set_defaults(handler=handle_doc_command)
    command_parser = add_subcommand("next", handle_next_command)
    command_parser.add_argument("--json", action="store_true")
    command_parser = add_subcommand("preview", handle_preview_command)
    command_parser.add_argument("scene", help="sNN")
    command_parser = add_subcommand("hash", handle_hash_command)
    command_parser.add_argument("scene", help="script | sNN")
    command_parser.add_argument("kind", nargs="?", choices=["script", "plan", "video"])
    command_parser = add_subcommand("task", lambda arguments: print(prepare_clip(Path(arguments.run), arguments.clip)))
    command_parser.add_argument("clip", help="sNNcMM")
    command_parser = add_subcommand("accept", handle_accept_command)
    command_parser.add_argument("clip", help="sNNcMM")
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
