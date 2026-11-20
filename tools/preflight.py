#!/usr/bin/env python3
"""preflight.py — fail-fast environment check; writes environment_report.json (EnvironmentReport schema).

Checks everything a run needs BEFORE any paid LLM call. Gaps found in the current app:
`dvisvgm` (needed by MathTex) was never checked; the Claude Code version was never checked although
the runner relies on flags that need recent builds.
Usage: python tools/preflight.py [--pin 0.20.1] [--out runs/<id>/environment_report.json] [--planning-only]
Exit 0 = ready; 1 = missing hard requirement. Status: IMPLEMENTED.
"""
from __future__ import annotations
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path

# Minimum Claude Code versions for flags the runner uses (code.claude.com/docs/en/cli-reference)
CLAUDE_MIN = {"--permission-prompts": (2, 1, 259), "__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__": (2, 1, 275),
              "--restricted": (2, 1, 248)}


def ver(cmd: list[str]) -> str | None:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        m = re.search(r"(\d+\.\d+\.\d+)", out.stdout + out.stderr)
        return m.group(1) if m else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pin", default="0.20.1")
    ap.add_argument("--out")
    ap.add_argument("--planning-only", action="store_true", help="only LLM planning; render tools optional")
    a = ap.parse_args()
    try:
        import manim; mv = manim.__version__
    except Exception:
        mv = None
    cc = ver(["claude", "--version"])
    report = {
        "manim_version": mv or "missing", "python_version": sys.version.split()[0], "claude_code_version": cc,
        "latex": bool(shutil.which("latex")), "dvisvgm": bool(shutil.which("dvisvgm")),
        "ffmpeg": bool(shutil.which("ffmpeg") and shutil.which("ffprobe")),
        "bwrap": bool(shutil.which("bwrap")), "socat": bool(shutil.which("socat")), "api_index_hash": "",
    }
    problems = []
    if not cc:
        problems.append("claude CLI not found")
    else:
        v = tuple(map(int, cc.split(".")))
        problems += [f"Claude Code {cc} < {'.'.join(map(str, need))} required for {flag}"
                     for flag, need in CLAUDE_MIN.items() if v < need]
    if not a.planning_only:
        if mv != a.pin:
            problems.append(f"manim {mv} installed, project pinned to {a.pin}")
        problems += [f"{k} missing" for k in ("latex", "dvisvgm", "ffmpeg", "bwrap", "socat") if not report[k]]
    report["problems"] = problems
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True); Path(a.out).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
