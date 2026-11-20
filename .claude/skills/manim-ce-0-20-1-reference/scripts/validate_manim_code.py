#!/usr/bin/env python3
"""validate_manim_code.py — deterministic pre-render gate for LLM-written Manim code.

Runs BEFORE any render and BEFORE any LLM repair call. Every check here is cheap
and exact, so a failure is routed to a *targeted* fix instead of a full regeneration.

Checks (each yields a finding with a stable `code` used by the repair router):
  SYNTAX            file does not parse
  FORBIDDEN_IMPORT  imports outside the allow-list (os, subprocess, socket, requests, ...)
  FORBIDDEN_CALL    open()/exec()/eval()/__import__ etc.
  UNKNOWN_NAME      a capitalised name/constant used but not defined locally and not in the API index
  REMOVED_API       a known renamed/removed API (get_graph, ShowCreation, GraphScene, ...)
  UNKNOWN_METHOD    `.foo(` where foo is not a method on ANY indexed class (likely invented)
  UNKNOWN_KWARG     constructor kwarg not accepted by a class whose __init__ has no **kwargs path
  SCENE_CLASS       not exactly one Scene subclass with the expected name
  CLIP_METHODS      expected clip_<n> methods missing (clip-level contract)
  CLIP_FILE         (--clip-file) file must define exactly one function named after the file
  CONTRACT_READ     (--entry) clip reads self.reg["x"] that is neither in its entry contract nor created in the clip
  CONTRACT_EXIT     (--exit) a name promised by the exit contract is never written to self.reg

Usage:
    python tools/validate_manim_code.py scene.py --index cache/manim_api/0.20.1/index.json \
        --class-name Scene003 [--clips 1,2,3] [--json]
Exit code 0 = no ERROR findings; 1 = at least one ERROR.

Status: IMPLEMENTED in this package (tested against manim==0.20.1).
"""
from __future__ import annotations

import argparse
import ast
import builtins
import json
import sys
from pathlib import Path

ALLOWED_IMPORTS = {"manim", "math", "numpy", "random", "itertools", "functools", "typing", "__future__"}
FORBIDDEN_CALLS = {"open", "exec", "eval", "compile", "__import__", "input", "breakpoint"}
# Renamed/removed APIs that appear constantly in LLM output (sourced from the Manim CE changelogs;
# keep in sync with knowledge/manim/0.20.1/removed_apis.md).
REMOVED = {
    "get_graph": "axes.plot(...)",
    "get_implicit_curve": "axes.plot_implicit_curve(...)",
    "get_parametric_curve": "axes.plot_parametric_curve(...)",
    "ShowCreation": "Create(...)",
    "GraphScene": "Scene + Axes(...)",
    "ShowCreationThenDestruction": "ShowPassingFlash(...)",
    "ShowCreationThenFadeAround": "ShowPassingFlash(SurroundingRectangle(obj))",
    "TextMobject": "Text(...) or Tex(...)",
    "TexMobject": "MathTex(...)",
    "ThoughtBubble": "primitive callout (RoundedRectangle + Text)",
    "SpeechBubble": "primitive callout (RoundedRectangle + Text)",
}
PY_COMMON_METHODS = set(dir(list)) | set(dir(dict)) | set(dir(str)) | {"astype", "tolist", "reshape"}


def load_index(path: Path) -> dict:
    return json.loads(path.read_text())["names"]


class Validator(ast.NodeVisitor):
    def __init__(self, index: dict):
        self.index = index
        self.findings: list[dict] = []
        self.defined: set[str] = set(dir(builtins))
        self.all_methods: set[str] = set()
        for v in index.values():
            if v["kind"] == "class":
                self.all_methods.update(v["methods"])

    def add(self, sev, code, node, msg):
        self.findings.append({"severity": sev, "code": code, "line": getattr(node, "lineno", 0), "message": msg})

    # pass 1: collect local definitions so we don't flag them
    def collect(self, tree):
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
                self.defined.add(n.name)
                if isinstance(n, ast.FunctionDef):
                    for a in n.args.args + n.args.kwonlyargs:
                        self.defined.add(a.arg)
            elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                self.defined.add(n.id)
            elif isinstance(n, ast.arg):
                self.defined.add(n.arg)
            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                for a in n.names:
                    self.defined.add((a.asname or a.name).split(".")[0])
            elif isinstance(n, ast.comprehension):
                for t in ast.walk(n.target):
                    if isinstance(t, ast.Name):
                        self.defined.add(t.id)

    def visit_Import(self, node):
        for a in node.names:
            if a.name.split(".")[0] not in ALLOWED_IMPORTS:
                self.add("ERROR", "FORBIDDEN_IMPORT", node, f"import {a.name} is not allowed in clip code")

    def visit_ImportFrom(self, node):
        if (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
            self.add("ERROR", "FORBIDDEN_IMPORT", node, f"from {node.module} import ... is not allowed")

    def visit_Call(self, node):
        f = node.func
        if isinstance(f, ast.Name):
            if f.id in FORBIDDEN_CALLS:
                self.add("ERROR", "FORBIDDEN_CALL", node, f"{f.id}() is not allowed in clip code")
            entry = self.index.get(f.id)
            if entry and entry["kind"] == "class" and entry.get("init"):
                init = entry["init"]
                if "**" not in init:
                    params = {p.split(":")[0].split("=")[0].strip().lstrip("*") for p in init.strip("()").split(",")}
                    for kw in node.keywords:
                        if kw.arg and kw.arg not in params:
                            self.add("ERROR", "UNKNOWN_KWARG", node, f"{f.id}() has no parameter '{kw.arg}' (signature {init})")
        elif isinstance(f, ast.Attribute):
            m = f.attr
            if m in REMOVED:
                self.add("ERROR", "REMOVED_API", node, f".{m}() was renamed/removed → use {REMOVED[m]}")
            elif (not m.startswith("_") and m not in self.all_methods and m not in self.defined and m not in PY_COMMON_METHODS
                  and not (isinstance(f.value, ast.Name) and f.value.id in {"np", "numpy", "math", "random"})):
                self.add("WARN", "UNKNOWN_METHOD", node, f".{m}() is not a method of any Manim class in the index — verify")
        self.generic_visit(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id not in self.defined:
            if node.id in REMOVED:
                self.add("ERROR", "REMOVED_API", node, f"{node.id} does not exist → use {REMOVED[node.id]}")
            elif node.id not in self.index:
                self.add("ERROR", "UNKNOWN_NAME", node, f"'{node.id}' is not defined locally nor exported by `from manim import *`")
        self.generic_visit(node)


def reg_access(tree) -> tuple[list[tuple[str, int]], set[str]]:
    """(reads, writes) of self.reg["name"] with constant string keys."""
    reads, writes = [], set()
    for n in ast.walk(tree):
        if (isinstance(n, ast.Subscript) and isinstance(n.value, ast.Attribute) and n.value.attr == "reg"
                and isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, str)):
            (writes.add(n.slice.value) if isinstance(n.ctx, ast.Store) else reads.append((n.slice.value, n.lineno)))
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in {"pop", "get"}
                and isinstance(n.func.value, ast.Attribute) and n.func.value.attr == "reg" and n.args
                and isinstance(n.args[0], ast.Constant)):
            reads.append((n.args[0].value, n.lineno))
    return reads, writes


def validate_clip_file(src: str, index: dict, name: str, entry: set[str] | None, exit_: set[str] | None) -> list[dict]:
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [{"severity": "ERROR", "code": "SYNTAX", "line": e.lineno or 0, "message": str(e)}]
    v = Validator(index); v.collect(tree); v.visit(tree)
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if len(funcs) != 1 or funcs[0].name != name:
        v.findings.append({"severity": "ERROR", "code": "CLIP_FILE", "line": 0,
                           "message": f"clip file must define exactly one function '{name}', found {[f.name for f in funcs]}"})
    reads, writes = reg_access(tree)
    if entry is not None:
        for key, line in reads:
            if key not in entry and key not in writes:
                v.findings.append({"severity": "ERROR", "code": "CONTRACT_READ", "line": line,
                                   "message": f"self.reg['{key}'] is not in the entry contract {sorted(entry)}"})
    if exit_ is not None:
        carried = entry or set()
        popped = {k for k, _ in reads} & carried
        for key in sorted(exit_):
            if key not in writes and key not in carried:
                v.findings.append({"severity": "ERROR", "code": "CONTRACT_EXIT", "line": 0,
                                   "message": f"exit contract promises '{key}' but the clip never sets self.reg['{key}']"})
    return v.findings


def validate(src: str, index: dict, class_name: str | None, clips: list[int] | None) -> list[dict]:
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [{"severity": "ERROR", "code": "SYNTAX", "line": e.lineno or 0, "message": str(e)}]
    v = Validator(index)
    v.collect(tree)
    v.visit(tree)
    scene_bases = {n for n, e in index.items() if e["kind"] == "class" and ("Scene" in e["mro"] or n == "Scene")}
    scenes = [n for n in tree.body if isinstance(n, ast.ClassDef)
              and any(isinstance(b, ast.Name) and b.id in scene_bases for b in n.bases)]
    if len(scenes) != 1 or (class_name and scenes[0].name != class_name):
        v.findings.append({"severity": "ERROR", "code": "SCENE_CLASS", "line": 0,
                           "message": f"expected exactly one Scene subclass named {class_name}, found {[s.name for s in scenes]}"})
    if clips and scenes:
        have = {f.name for f in scenes[0].body if isinstance(f, ast.FunctionDef)}
        missing = [c for c in clips if f"clip_{c:02d}" not in have]
        if missing:
            v.findings.append({"severity": "ERROR", "code": "CLIP_METHODS", "line": scenes[0].lineno,
                               "message": f"missing clip methods: {[f'clip_{c:02d}' for c in missing]}"})
    return v.findings


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--index", required=True)
    ap.add_argument("--class-name")
    ap.add_argument("--clips", help="comma-separated clip numbers expected as clip_NN methods")
    ap.add_argument("--clip-file", action="store_true", help="validate a clips/clip_NN.py file instead of a scene")
    ap.add_argument("--entry", help="comma-separated registry names in the entry contract ('' = none)")
    ap.add_argument("--exit", help="comma-separated registry names in the exit contract ('' = none)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    clips = [int(x) for x in a.clips.split(",")] if a.clips else None
    split = lambda x: None if x is None else {n for n in x.split(",") if n}
    if a.clip_file:
        findings = validate_clip_file(Path(a.file).read_text(), load_index(Path(a.index)), Path(a.file).stem,
                                      split(a.entry), split(a.exit))
    else:
        findings = validate(Path(a.file).read_text(), load_index(Path(a.index)), a.class_name, clips)
    if a.json:
        print(json.dumps(findings, indent=2))
    else:
        for f in findings:
            print(f"{f['severity']:5} {f['code']:16} L{f['line']:<4} {f['message']}")
        print(f"{sum(f['severity'] == 'ERROR' for f in findings)} error(s), {sum(f['severity'] == 'WARN' for f in findings)} warning(s)")
    sys.exit(1 if any(f["severity"] == "ERROR" for f in findings) else 0)


if __name__ == "__main__":
    main()
