#!/usr/bin/env python3
"""audit_prompt_catalog.py — check every Manim name mentioned in a prompt file against the API index.

Reports names that a prompt RECOMMENDS but which do not exist in the installed Manim
(dangerous), and names a prompt BANS that actually do exist (causes needless refactor loops).
Run it in CI whenever a prompt or the pinned Manim version changes.

Usage: python tools/audit_prompt_catalog.py app/graph/prompts/*.py --index <index.json>
Status: IMPLEMENTED in this package.
"""

from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

CLASS_RE = re.compile(r"\b([A-Z][a-z]+(?:[A-Z][a-z0-9]*)+|[A-Z][a-z]{2,}(?=\())")
METHOD_RE = re.compile(r"\.([a-z_][a-z0-9_]{2,})\(")
BAN_HINT = re.compile(r"BANNED|NEVER USE|DEPRECATED|REMOVED|never cite|must be|→ use|does not exist|RENAMED", re.I)
IGNORE = {"Manim", "ManimCE", "ManimGL", "Python", "PascalCase", "LaTeX", "MathJax", "JSON", "OpenGL", "Scene"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+")
    parser.add_argument("--index", required=True)
    arguments = parser.parse_args()
    index = json.loads(Path(arguments.index).read_text())["names"]
    methods = set().union(*(set(hits["methods"]) for hits in index.values() if hits["kind"] == "class"))
    report = {}
    for path in arguments.files:
        lines = Path(path).read_text().splitlines()
        missing, banned_but_exist = {}, {}
        for i, line in enumerate(lines, 1):
            context = " ".join(lines[max(0, i - 4) : i])
            banned_ctx = bool(BAN_HINT.search(context))
            for name in set(CLASS_RE.findall(line)) - IGNORE:
                if name not in index:
                    missing.setdefault(name, []).append((i, banned_ctx))
                elif banned_ctx and re.search(r"BANNED|NEVER USE", context):
                    banned_but_exist.setdefault(name, []).append(i)
            for method_name in set(METHOD_RE.findall(line)):
                if method_name not in methods and not method_name.startswith("_"):
                    missing.setdefault("." + method_name + "()", []).append((i, banned_ctx))
        report[path] = {
            "not_in_api_and_not_marked_banned": {
                missing_name: [line_number for line_number, banned in hits]
                for missing_name, hits in missing.items()
                if not any(banned for _, banned in hits)
            },
            "not_in_api_but_marked_banned_ok": sorted(
                missing_name for missing_name, hits in missing.items() if any(banned for _, banned in hits)
            ),
            "banned_in_prompt_but_exists_in_api": banned_but_exist,
        }
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
