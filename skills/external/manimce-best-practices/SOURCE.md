# Source & customization status: REUSE WITH CUSTOMIZATION
- Upstream: https://github.com/adithya-s-k/manim_skill/tree/main/skills/manimce-best-practices
- Commit: cef045011722d285692e3381d12d4d637da56e18 (last upstream commit 2026-01-24 — BEFORE Manim 0.20.0, 2026-02-20, which rewrote MathTex)
- License: MIT (LICENSE.upstream). Vendored unmodified; customizations are listed, not applied, so upstream can be diffed.

## Verification against Manim 0.20.1 (tools/validate_manim_code.py, 2026-11-19)
- rules/*.md: every scene code block passes static API validation except rules/cli.md block 0 (shell text in a python fence).
- examples/*.py: all pass, except lorenz_attractor.py imports scipy (allowed by Manim, forbidden by this project's clip sandbox policy).
- Static validation does not prove behaviour. Known semantic gap: no guidance reflects the 0.20 MathTex rewrite
  (substrings_to_isolate no longer creates top-level parts) — see ../../custom/manim-ce-0-20-1-reference/topics/mathtex-indexing.md.

## Required customizations (PROPOSED, not applied)
1. Add a version pin to the description ("verified for Manim CE 0.20.1") and a note that the generated API cards win on conflicts.
2. Drop rules/cli.md block 0 or re-fence it as bash; drop 3d content from the default load set (3D is a v1 non-goal).
3. Do NOT load it inside the clip-builder agent (that agent runs with --safe-mode, which disables skills, and gets
   topic cards instead). Use it for developers working on prompts/topic cards.
4. Re-run tests/test_external_skill_examples (PROPOSED) whenever the pin changes.
