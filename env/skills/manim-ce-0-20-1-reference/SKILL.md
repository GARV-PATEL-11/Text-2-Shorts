---
name: manim-ce-0-20-1-reference
description: Version-pinned Manim Community Edition 0.20.1 reference for the Text-to-Shorts project. Use whenever writing, reviewing or debugging Manim code or prompts for this repo — clip files (clips/clip_NN.py), topic cards, validator rules — or when a question is "does X exist / what is the signature of X in our Manim". Generated API cards from the installed package win over memory, blog posts and other skills.
---

# Manim CE 0.20.1 reference (project-pinned)

Status: IMPLEMENTED (scripts and topic cards are tested by `tests/` in the development package).

## Why this skill exists
LLM training data mixes ManimGL, early ManimCE and current ManimCE. Hand-written catalogs drift (the app's own
"verified v0.20.1" catalog recommends `get_line_graph`, which does not exist in 0.20.1). This skill answers API
questions from the **installed package** and teaches patterns only through examples that are executed in CI.

## Answering "does X exist / how do I call X"
1. Build (once per Manim version) the index: `python scripts/build_manim_api_index.py --out cache/manim_api/<ver>/index.json`
2. Cards for exact names: `python scripts/doc_cards.py --index <index> --names MathTex,Axes`
   A name printed under "NOT IN Manim" does not exist — choose another.
3. Patterns: read only the topic card you need from `topics/` (each is < 1k tokens):
   clip-structure (project convention, read first when writing a clip) · mathtex-indexing · text-and-latex ·
   positioning-layout · timing-and-sync · transforms · axes-and-graphs · camera · updaters-and-trackers ·
   emphasis · removed-apis

## Checking code
- Static (no render): `python scripts/validate_manim_code.py <file> --index <index> [--clip-file --entry a,b --exit a]`
- Layout + per-clip timing (dry run, ~2 s): `python scripts/layout_probe.py scene.py SceneNN --budget clip_01=6.2`
- Render a single clip with exact entry state: `python scripts/scene_harness.py render scenes/sNN --scene-id sNN --target clip_02`

## Changing the pinned version
Rebuild the index, run `pytest tests/test_topic_cards.py tests/test_api_index.py`, read the Manim changelog
(https://docs.manim.community/en/stable/changelog.html) for the versions in between, update `topics/removed-apis.md`
and the REMOVED table in `validate_manim_code.py`, then bump `api:all` (invalidates generated code, not plans/audio).
