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
      --topics-dir env/skills/manim-ce-0-20-1-reference/topics [--from-spec spec.json] [--max-methods 14]
Status: IMPLEMENTED in this package.
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

DOCS_BASE = "https://docs.manim.community/en/v{ver}/reference/{module}.{name}.html"
COMMON = {"animate", "move_to", "next_to", "to_edge", "to_corner", "shift", "scale", "set_color", "get_center",
          "arrange", "align_to", "copy", "become", "set_opacity", "get_part_by_tex", "set_color_by_tex",
          "plot", "c2p", "get_graph_label", "add_updater", "always", "match_height", "match_width"}


def names_from_spec(spec: dict) -> set[str]:
    """Pull every CapWords token out of a VisualSpecification's objects + steps."""
    text = json.dumps({"objects": spec.get("objects", {}), "steps": spec.get("steps", [])})
    return set(re.findall(r"\b([A-Z][A-Za-z0-9]+)\(", text)) | set(re.findall(r"'([A-Z][A-Za-z0-9]+)\b", text)) | \
        {v.split()[0] for v in spec.get("objects", {}).values() if v and v[0].isupper()}


def card(name: str, e: dict, ver: str, max_methods: int) -> str:
    if e["kind"] == "class":
        own = e.get("own_methods", [])
        shown = sorted(m for m in COMMON if m in e["methods"]) + [m for m in own if m not in COMMON]
        meths = ", ".join(shown[:max_methods]) + (" …" if len(shown) > max_methods else "")
        url = DOCS_BASE.format(ver=ver, module=e["module"], name=name)
        return (f"### {name}({e['init'].removeprefix('(self, ').removeprefix('(self') if e['init'] else '…'}\n"
                f"bases: {' → '.join(e['mro'][:4])}\n{e['doc']}\nmethods: {meths or '—'}\ndocs: {url}\n")
    if e["kind"] == "function":
        return f"### {name}{e['signature']}\n{e['doc']}\n"
    return f"### {name} = {e['repr']}\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--names", default="")
    ap.add_argument("--from-spec")
    ap.add_argument("--topics", default="")
    ap.add_argument("--topics-dir")
    ap.add_argument("--max-methods", type=int, default=14)
    a = ap.parse_args()
    idx = json.loads(Path(a.index).read_text()); ver = idx["manim_version"]; names = idx["names"]
    wanted = {n for n in a.names.split(",") if n}
    if a.from_spec:
        wanted |= names_from_spec(json.loads(Path(a.from_spec).read_text()))
    out = [f"## Manim CE {ver} — API cards (generated from the installed package; authoritative)\n"]
    unknown = sorted(n for n in wanted if n not in names)
    for n in sorted(wanted - set(unknown)):
        out.append(card(n, names[n], ver, a.max_methods))
    if unknown:
        out.append(f"!! NOT IN Manim {ver}: {', '.join(unknown)} — do not use; pick an existing alternative.\n")
    for t in [t for t in a.topics.split(",") if t]:
        p = Path(a.topics_dir or ".") / f"{t}.md"
        out.append(p.read_text() if p.exists() else f"!! unknown topic card: {t}\n")
    text = "\n".join(out)
    print(text)
    print(f"<!-- ~{len(text)//4} tokens, {len(wanted)} names, {len(a.topics.split(',')) if a.topics else 0} topics -->")


if __name__ == "__main__":
    main()
