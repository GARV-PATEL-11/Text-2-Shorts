---
name: manim-ce-0-20-1-reference
description: Use when writing, reviewing or debugging Manim code for this project, or when asking whether a Manim class, method or argument exists, what its signature is, or how to do something in Manim CE 0.20.1 (clips, scenes, topic cards, validator rules).
---

# Manim CE 0.20.1 reference (project-pinned)

Answer Manim questions from the **installed package**, not from memory: training data mixes ManimGL, old and new
ManimCE, and hand-written lists drift. Patterns come from topic cards whose examples are executed by the test suite.

## Does X exist / how do I call X
Commands run from the repo root (inside a run session, the tools are also behind `./check doc Name` in a clip folder):
1. Index (once per Manim version; `text-2-shorts task` builds it automatically):
   `uv run python tools/build_manim_api_index.py --out ~/.cache/text-2-shorts/manim_api_0.20.1.json`
2. Cards: `uv run python tools/doc_cards.py --index ~/.cache/text-2-shorts/manim_api_0.20.1.json --names Axes,Axes.plot,MathTex`
   Classes, functions, constants and `Class.method` (inherited methods included) are resolved; a name listed under
   "NOT IN Manim" does not exist in this version — pick an alternative.
3. Patterns: read only the card you need from `topics/` (each < 1k tokens): `clip-structure` (this project's clip
   file convention — read first when writing a clip) · `timing-and-sync` · `positioning-layout` · `mathtex-indexing`
   · `text-and-latex` · `transforms` · `axes-and-graphs` · `camera` · `updaters-and-trackers` · `emphasis` ·
   `removed-apis` (old names and their replacements).

If neither the cards nor a topic answer it, inspect the installed package directly
(`uv run python -c "import manim, inspect; print(inspect.signature(manim.Axes.plot))"`) rather than guessing.

## Checking code
`scripts/` links to the repo's `tools/` (one source):
- Static, no render: `tools/validate_manim_code.py <file> --index <index> [--clip-file --entry a,b --exit c]`
- Layout + timing, dry run (~2 s): `tools/layout_probe.py scene.py SceneNN --budget clip_01=6.2`
- One clip with its exact entry state: `tools/scene_harness.py render <scene_dir> --scene-id sNN --target clip_02`

## Changing the pinned version
Bump `manim==` in `pyproject.toml` and `MANIM_VERSION` in `app/run_steps.py`; rebuild the index; run
`uv run pytest -q tests/test_topic_cards.py tests/test_api_index.py`; read the release notes for the versions in
between ([Manim releases](https://github.com/ManimCommunity/manim/releases)); update `topics/removed-apis.md` and the
REMOVED table in `tools/validate_manim_code.py`. Every clip's key changes with the clip-builder instructions, not with
the version — rebuild clips deliberately (`text-2-shorts status` per run).
