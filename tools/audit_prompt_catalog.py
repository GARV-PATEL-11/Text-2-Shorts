#!/usr/bin/env python3
"""audit_prompt_catalog.py — check every Manim name mentioned in a prompt file against the API index.

Reports names that a prompt RECOMMENDS but which do not exist in the installed Manim
(dangerous), and names a prompt BANS that actually do exist (causes needless refactor loops).
Run it in CI whenever a prompt or the pinned Manim version changes.

Usage: python tools/audit_prompt_catalog.py app/graph/prompts/*.py --index <index.json>
Status: IMPLEMENTED in this package.
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

CLASS_RE = re.compile(r"\b([A-Z][a-z]+(?:[A-Z][a-z0-9]*)+|[A-Z][a-z]{2,}(?=\())")
METHOD_RE = re.compile(r"\.([a-z_][a-z0-9_]{2,})\(")
BAN_HINT = re.compile(r"BANNED|NEVER USE|DEPRECATED|REMOVED|never cite|must be|→ use|does not exist|RENAMED", re.I)
IGNORE = {"Manim", "ManimCE", "ManimGL", "Python", "PascalCase", "LaTeX", "MathJax", "JSON", "OpenGL", "Scene"}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("files", nargs="+"); ap.add_argument("--index", required=True)
    a = ap.parse_args()
    idx = json.loads(Path(a.index).read_text())["names"]
    methods = set().union(*(set(v["methods"]) for v in idx.values() if v["kind"] == "class"))
    report = {}
    for f in a.files:
        lines = Path(f).read_text().splitlines()
        missing, banned_but_exist = {}, {}
        for i, line in enumerate(lines, 1):
            ctx = " ".join(lines[max(0, i - 4):i])
            banned_ctx = bool(BAN_HINT.search(ctx))
            for name in set(CLASS_RE.findall(line)) - IGNORE:
                if name not in idx:
                    missing.setdefault(name, []).append((i, banned_ctx))
                elif banned_ctx and re.search(r"BANNED|NEVER USE", ctx):
                    banned_but_exist.setdefault(name, []).append(i)
            for m in set(METHOD_RE.findall(line)):
                if m not in methods and not m.startswith("_"):
                    missing.setdefault("." + m + "()", []).append((i, banned_ctx))
        report[f] = {
            "not_in_api_and_not_marked_banned": {k: [l for l, b in v] for k, v in missing.items() if not any(b for _, b in v)},
            "not_in_api_but_marked_banned_ok": sorted(k for k, v in missing.items() if any(b for _, b in v)),
            "banned_in_prompt_but_exists_in_api": banned_but_exist,
        }
    print(json.dumps(report, indent=1))

if __name__ == "__main__":
    main()
