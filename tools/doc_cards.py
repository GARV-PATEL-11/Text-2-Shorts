#!/usr/bin/env python3
"""doc_cards.py — deterministic, version-pinned documentation retrieval for ONE clip.

The code generator never receives the whole Manim reference. It receives:
  1. API cards for exactly the Manim names the clip's VisualSpecification uses
     (signature, bases, first doc line, own methods, docs URL) — generated from the API index,
     so they cannot disagree with the installed version;
  2. topic cards (curated, executable-verified markdown) for the topics the Clip Planner tagged
     (ClipPlan.manim_topics), e.g. mathtex-indexing, timing-and-sync.

No embeddings or LLM calls are involved: names come from the spec, topics from a closed vocabulary.
Output is stable for stable inputs, so it is cacheable and prompt-cache friendly.

Usage:
  python tools/doc_cards.py --index cache/manim_api/0.20.1/index.json \
      --names MathTex,TransformMatchingTex,SurroundingRectangle --topics mathtex-indexing,timing-and-sync \
      --topics-dir run-environment/skills/manim-ce-0-20-1-reference/topics [--from-spec spec.json] [--max-methods 14]
Status: IMPLEMENTED in this package.
"""

from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

DOCS_BASE = "https://docs.manim.community/en/v{ver}/reference/{module}.{name}.html"
COMMON_METHODS = {
    "animate",
    "move_to",
    "next_to",
    "to_edge",
    "to_corner",
    "shift",
    "scale",
    "set_color",
    "get_center",
    "arrange",
    "align_to",
    "copy",
    "become",
    "set_opacity",
    "get_part_by_tex",
    "set_color_by_tex",
    "plot",
    "c2p",
    "get_graph_label",
    "add_updater",
    "always",
    "match_height",
    "match_width",
}


def names_from_spec(spec: dict) -> set[str]:
    """Pull every CapWords token out of a VisualSpecification's objects + steps."""
    text = json.dumps({"objects": spec.get("objects", {}), "steps": spec.get("steps", [])})
    return (
        set(re.findall(r"\b([A-Z][A-Za-z0-9]+)\(", text))
        | set(re.findall(r"'([A-Z][A-Za-z0-9]+)\b", text))
        | {
            description.split()[0]
            for description in spec.get("objects", {}).values()
            if description and description[0].isupper()
        }
    )


def api_card(name: str, entry: dict, manim_version: str, max_methods: int) -> str:
    if entry["kind"] == "class":
        own_methods = entry.get("own_methods", [])
        shown = sorted(method for method in COMMON_METHODS if method in entry["methods"]) + [
            method for method in own_methods if method not in COMMON_METHODS
        ]
        method_list = ", ".join(shown[:max_methods]) + (" …" if len(shown) > max_methods else "")
        url = DOCS_BASE.format(ver=manim_version, module=entry["module"], name=name)
        return (
            f"### {name}({entry['init'].removeprefix('(self, ').removeprefix('(self') if entry['init'] else '…'}\n"
            f"bases: {' → '.join(entry['mro'][:4])}\n{entry['doc']}\nmethods: {method_list or '—'}\ndocs: {url}\n"
        )
    if entry["kind"] == "function":
        return f"### {name}{entry['signature']}\n{entry['doc']}\n"
    return f"### {name} = {entry['repr']}\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", required=True)
    parser.add_argument("--names", default="")
    parser.add_argument("--from-spec")
    parser.add_argument("--topics", default="")
    parser.add_argument("--topics-dir")
    parser.add_argument("--max-methods", type=int, default=14)
    arguments = parser.parse_args()
    index = json.loads(Path(arguments.index).read_text())
    manim_version = index["manim_version"]
    names = index["names"]
    wanted = {name for name in arguments.names.split(",") if name}
    if arguments.from_spec:
        wanted |= names_from_spec(json.loads(Path(arguments.from_spec).read_text()))
    sections = [f"## Manim CE {manim_version} — API cards (generated from the installed package; authoritative)\n"]

    def method_signature(
        name,
    ):  # "Axes.plot" → the method's signature, if the class has it (inherited methods included)
        class_name, _, method_name = name.partition(".")
        return names.get(class_name, {}).get("methods", {}).get(method_name) if method_name else None

    unknown = sorted(name for name in wanted if name not in names and method_signature(name) is None)
    for name in sorted(wanted - set(unknown)):
        sections.append(
            api_card(name, names[name], manim_version, arguments.max_methods)
            if name in names
            else f"### {name}{method_signature(name)}\nmethod of {name.partition('.')[0]}\n"
        )
    if unknown:
        sections.append(
            f"!! NOT IN Manim {manim_version}: {', '.join(unknown)} — do not use; pick an existing alternative.\n"
        )
    for topic in [topic for topic in arguments.topics.split(",") if topic]:
        topic_path = Path(arguments.topics_dir or ".") / f"{topic}.md"
        sections.append(topic_path.read_text() if topic_path.exists() else f"!! unknown topic card: {topic}\n")
    text = "\n".join(sections)
    print(text)
    print(
        f"<!-- ~{len(text) // 4} tokens, {len(wanted)} names, "
        f"{len(arguments.topics.split(',')) if arguments.topics else 0} topics -->"
    )


if __name__ == "__main__":
    main()
