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
  CLIP_METHODS      expected _clip_<n> methods missing (one per planned clip, scene_harness.py)

Usage:
    python backend/tools/validate_manim_code.py scene.py --index cache/manim_api/0.20.1/index.json \
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
# Renamed/removed APIs that appear constantly in LLM output: every name here is absent from the pinned Manim (checked
# against the installed package). Keep in sync with PART 3 of
# runtime-environment/skills/manim-ce-0-20-1-reference/topics/manim-vocabulary.md.
REMOVED_APIS = {
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
    "get_line_graph": "axes.plot_line_graph(...)",
    "get_parts_by_tex": "set_color_by_tex(...) or get_part_by_tex(...)",
    "OpenGLTexMobject": "MathTex(...)",
    "OpenGLTextMobject": "Text(...)",
    "FadeInFrom": "FadeIn(mob, shift=...)",
    "FadeInFromPoint": "FadeIn(mob, scale=...)",
    "FadeInFromLarge": "FadeIn(mob, scale=...)",
    "FadeOutAndShift": "FadeOut(mob, shift=...)",
    "FadeOutToPoint": "FadeOut(mob, scale=...)",
    "VFadeIn": "FadeIn(...)",
    "VFadeOut": "FadeOut(...)",
    "VFadeInThenOut": "FadeIn(...) then FadeOut(...)",
    "CircleIndicate": "Indicate(...) or Circumscribe(...)",
    "ShowCreationThenDestructionAround": "Circumscribe(...)",
    "ShowPassingFlashAround": "ShowPassingFlash(SurroundingRectangle(obj))",
    "AnimationOnSurroundingRectangle": "SurroundingRectangle + Create/FadeIn",
    "WiggleOutThenIn": "Wiggle(...)",
    "TurnInsideOut": "Transform(...)",
    "ShowPassingFlashWithThinningStroke": "ShowPassingFlashWithThinningStrokeWidth(...)",
    "VMobjectFromSVGPathstring": "VMobjectFromSVGPath(...)",
    "rotate_in_place": "rotate(...)",
    "scale_in_place": "scale(...)",
    "scale_about_point": "scale(..., about_point=...)",
    "SampleSpaceScene": "Scene + SampleSpace(...)",
    "ReconfigurableScene": "Scene",
    "InteractiveScene": "Scene (InteractiveScene is ManimGL only)",
    "LineGraph": "axes.plot_line_graph(...)",
    "Bezier": "CubicBezier(...)",
    "ImplicitCurve": "ImplicitFunction(...) or axes.plot_implicit_curve(...)",
    "TypstMath": "MathTex(...) (Typst needs Manim 0.21+)",
}
PYTHON_BUILTIN_METHODS = set(dir(list)) | set(dir(dict)) | set(dir(str)) | {"astype", "tolist", "reshape"}
PROJECT_SCENE_METHODS = {"beat", "content"}  # scene_harness.py: self.beat(n) marks beat n; self.content() lists content


def load_index(path: Path) -> dict:
    return json.loads(path.read_text())["names"]


class Validator(ast.NodeVisitor):
    def __init__(self, index: dict):
        self.index = index
        self.findings: list[dict] = []
        self.defined: set[str] = set(dir(builtins))
        self.all_methods: set[str] = set()
        for entry in index.values():
            if entry["kind"] == "class":
                self.all_methods.update(entry["methods"])

    def add_finding(self, severity, code, node, message):
        self.findings.append(
            {"severity": severity, "code": code, "line": getattr(node, "lineno", 0), "message": message}
        )

    # pass 1: collect local definitions so we don't flag them
    def collect_definitions(self, tree):
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                self.defined.add(node.name)
                if isinstance(node, ast.FunctionDef):
                    for argument in node.args.args + node.args.kwonlyargs:
                        self.defined.add(argument.arg)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                self.defined.add(node.id)
            elif isinstance(node, ast.arg):
                self.defined.add(node.arg)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    self.defined.add((alias.asname or alias.name).split(".")[0])
            elif isinstance(node, ast.comprehension):
                for target_node in ast.walk(node.target):
                    if isinstance(target_node, ast.Name):
                        self.defined.add(target_node.id)

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name.split(".")[0] not in ALLOWED_IMPORTS:
                self.add_finding("ERROR", "FORBIDDEN_IMPORT", node, f"import {alias.name} is not allowed in clip code")

    def visit_ImportFrom(self, node):
        if (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
            self.add_finding("ERROR", "FORBIDDEN_IMPORT", node, f"from {node.module} import ... is not allowed")

    def visit_Call(self, node):
        function = node.func
        if isinstance(function, ast.Name):
            if function.id in FORBIDDEN_CALLS:
                self.add_finding("ERROR", "FORBIDDEN_CALL", node, f"{function.id}() is not allowed in clip code")
            entry = self.index.get(function.id)
            if entry and entry["kind"] == "class" and entry.get("init"):
                init = entry["init"]
                if "**" not in init:
                    params = {
                        parameter.split(":")[0].split("=")[0].strip().lstrip("*")
                        for parameter in init.strip("()").split(",")
                    }
                    for keyword in node.keywords:
                        if keyword.arg and keyword.arg not in params:
                            self.add_finding(
                                "ERROR",
                                "UNKNOWN_KWARG",
                                node,
                                f"{function.id}() has no parameter '{keyword.arg}' (signature {init})",
                            )
        elif isinstance(function, ast.Attribute):
            method_name = function.attr
            if method_name in REMOVED_APIS:
                self.add_finding(
                    "ERROR",
                    "REMOVED_API",
                    node,
                    f".{method_name}() was renamed/removed → use {REMOVED_APIS[method_name]}",
                )
            elif (
                not method_name.startswith("_")
                and method_name not in self.all_methods
                and method_name not in self.defined
                and method_name not in PYTHON_BUILTIN_METHODS
                and method_name not in PROJECT_SCENE_METHODS
                and not (
                    isinstance(function.value, ast.Name) and function.value.id in {"np", "numpy", "math", "random"}
                )
            ):
                self.add_finding(
                    "WARN",
                    "UNKNOWN_METHOD",
                    node,
                    f".{method_name}() is not a method of any Manim class in the index — verify",
                )
        self.generic_visit(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id not in self.defined:
            if node.id in REMOVED_APIS:
                self.add_finding(
                    "ERROR", "REMOVED_API", node, f"{node.id} does not exist → use {REMOVED_APIS[node.id]}"
                )
            elif node.id not in self.index:
                self.add_finding(
                    "ERROR",
                    "UNKNOWN_NAME",
                    node,
                    f"'{node.id}' is not defined locally nor exported by `from manim import *`",
                )
        self.generic_visit(node)


def validate(source: str, index: dict, class_name: str | None, clips: list[int] | None) -> list[dict]:
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return [{"severity": "ERROR", "code": "SYNTAX", "line": error.lineno or 0, "message": str(error)}]
    validator = Validator(index)
    validator.collect_definitions(tree)
    validator.visit(tree)
    scene_bases = {
        name
        for name, entry in index.items()
        if entry["kind"] == "class" and ("Scene" in entry["mro"] or name == "Scene")
    }
    scenes = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and any(isinstance(base, ast.Name) and base.id in scene_bases for base in node.bases)
    ]
    if len(scenes) != 1 or (class_name and scenes[0].name != class_name):
        validator.findings.append(
            {
                "severity": "ERROR",
                "code": "SCENE_CLASS",
                "line": 0,
                "message": f"expected exactly one Scene subclass named {class_name}, "
                f"found {[scene.name for scene in scenes]}",
            }
        )
    if clips and scenes:
        method_names = {function.name for function in scenes[0].body if isinstance(function, ast.FunctionDef)}
        missing = [clip_number for clip_number in clips if f"_clip_{clip_number}" not in method_names]
        if missing:
            validator.findings.append(
                {
                    "severity": "ERROR",
                    "code": "CLIP_METHODS",
                    "line": scenes[0].lineno,
                    "message": f"missing clip methods: {[f'_clip_{clip_number}' for clip_number in missing]}",
                }
            )
    return validator.findings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--index", required=True)
    parser.add_argument("--class-name")
    parser.add_argument("--clips", help="comma-separated clip numbers expected as _clip_N methods")
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args()
    clips = [int(text) for text in arguments.clips.split(",")] if arguments.clips else None
    findings = validate(
        Path(arguments.file).read_text(), load_index(Path(arguments.index)), arguments.class_name, clips
    )
    if arguments.json:
        print(json.dumps(findings, indent=2))
    else:
        for finding in findings:
            print(f"{finding['severity']:5} {finding['code']:16} L{finding['line']:<4} {finding['message']}")
        print(
            f"{sum(finding['severity'] == 'ERROR' for finding in findings)} error(s), "
            f"{sum(finding['severity'] == 'WARN' for finding in findings)} warning(s)"
        )
    sys.exit(1 if any(finding["severity"] == "ERROR" for finding in findings) else 0)


if __name__ == "__main__":
    main()
