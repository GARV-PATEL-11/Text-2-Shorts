#!/usr/bin/env python3
"""preflight.py — fail-fast environment check; writes environment_report.json (EnvironmentReport schema).

Checks everything a run needs BEFORE any paid LLM call. Gaps found in the current app:
`dvisvgm` (needed by MathTex) was never checked; the Claude Code version was never checked although
the runner relies on flags that need recent builds.
Usage: python tools/preflight.py [--pin 0.20.1] [--out runs/<id>/environment_report.json] [--planning-only]
Exit 0 = ready; 1 = missing hard requirement. Status: IMPLEMENTED.
"""

from __future__ import annotations
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Minimum Claude Code versions for flags the runner uses (code.claude.com/docs/en/cli-reference)
CLAUDE_MIN = {
    "--permission-prompts": (2, 1, 259),
    "__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__": (2, 1, 275),
    "--restricted": (2, 1, 248),
}


def detect_version(command: list[str]) -> str | None:
    try:
        process = subprocess.run(command, capture_output=True, text=True, timeout=20)
        match = re.search(r"(\d+\.\d+\.\d+)", process.stdout + process.stderr)
        return match.group(1) if match else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pin", default="0.20.1")
    parser.add_argument("--out")
    parser.add_argument("--planning-only", action="store_true", help="only LLM planning; render tools optional")
    arguments = parser.parse_args()
    try:
        import manim

        manim_version = manim.__version__
    except Exception:
        manim_version = None
    claude_code_version = detect_version(["claude", "--version"])
    report = {
        "manim_version": manim_version or "missing",
        "python_version": sys.version.split()[0],
        "claude_code_version": claude_code_version,
        "latex": bool(shutil.which("latex")),
        "dvisvgm": bool(shutil.which("dvisvgm")),
        "ffmpeg": bool(shutil.which("ffmpeg") and shutil.which("ffprobe")),
        "bwrap": bool(shutil.which("bwrap")),
        "socat": bool(shutil.which("socat")),
        "api_index_hash": "",
    }
    problems = []
    if not claude_code_version:
        problems.append("claude CLI not found")
    else:
        installed = tuple(map(int, claude_code_version.split(".")))
        problems += [
            f"Claude Code {claude_code_version} < {'.'.join(map(str, need))} required for {flag}"
            for flag, need in CLAUDE_MIN.items()
            if installed < need
        ]
    if not arguments.planning_only:
        if manim_version != arguments.pin:
            problems.append(f"manim {manim_version} installed, project pinned to {arguments.pin}")
        problems += [f"{tool} missing" for tool in ("latex", "dvisvgm", "ffmpeg", "bwrap", "socat") if not report[tool]]
    report["problems"] = problems
    if arguments.out:
        Path(arguments.out).parent.mkdir(parents=True, exist_ok=True)
        Path(arguments.out).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
