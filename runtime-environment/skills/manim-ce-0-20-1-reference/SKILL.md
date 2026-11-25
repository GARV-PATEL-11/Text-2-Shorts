---
name: manim-ce-0-20-1-reference
description: Use when writing, reviewing or debugging Manim code for this project, or when asking whether a Manim class, method or argument exists, what its signature is, or how to do something in Manim CE 0.20.1 (clips, scenes, topic cards, validator rules).
---

# Manim CE 0.20.1 reference (project-pinned)

Answer Manim questions from the **installed package**, not from memory: training data mixes ManimGL, old and new
ManimCE, and hand-written lists drift. Patterns come from three reference files whose examples are executed by the
test suite.

## Does X exist / how do I call X
Commands run from the repo root (inside a run session, the tools are also behind `./check doc Name` in a clip folder):
1. Index (once per Manim version; `text-2-shorts task` builds it automatically):
   `uv run python backend/tools/build_manim_api_index.py --out ~/.cache/text-2-shorts/manim_api_0.20.1.json`
2. Cards: `uv run python backend/tools/doc_cards.py --index ~/.cache/text-2-shorts/manim_api_0.20.1.json --names Axes,Axes.plot,MathTex`
   Classes, functions, constants and `Class.method` (inherited methods included) are resolved; a name listed under
   "NOT IN Manim" does not exist in this version — pick an alternative.
3. Patterns: the three files in `topics/` (every scene task loads all three; about 20k tokens, one cacheable block):
   - `manim-construction-patterns.md`: how to write the code, rule IDs L, A, C, T, S, and **PART 9, this project's
     scene conventions** (scene_code.py, one `_clip_N` per clip, clip lengths, camera, safe area): read it first.
   - `manim-vocabulary.md`: which names exist, by intent, with tags (base, internal, version, colour defaults) and the
     banned names with their replacements (PART 3).
   - `manim-common-mistakes.md`: what still goes wrong (version traps, render errors, silent wrong output, timing,
     performance), each with wrong, right, why and how to detect it.

If neither the cards nor a topic answer it, inspect the installed package directly
(`uv run python -c "import manim, inspect; print(inspect.signature(manim.Axes.plot))"`) rather than guessing.

## Checking code
`scripts/` links to the repo's `backend/tools/` (one source):
- Static, no render: `backend/tools/validate_manim_code.py scene_code.py --index <index> --class-name SceneNN [--clips 1,2,3]`
- Layout + timing, dry run (~2 s): `backend/tools/layout_probe.py scene.py SceneNN --budget clip_01=6.2`
- One clip with its exact entry state: `backend/tools/scene_harness.py render <scene_dir> --scene-id sNN --target clip_02`

## Changing the pinned version
Bump `manim==` in `pyproject.toml` and `MANIM_VERSION` in `backend/app/config.py`; rebuild the index; run
`uv run pytest -q tests/test_topic_cards.py tests/test_api_index.py`; read the release notes for the versions in
between ([Manim releases](https://github.com/ManimCommunity/manim/releases)); update PART 3 of `topics/manim-vocabulary.md` and the
REMOVED table in `backend/tools/validate_manim_code.py`. Every clip's key changes with the scene-builder instructions, not with
the version — rebuild scenes deliberately (`text-2-shorts status` per run).
