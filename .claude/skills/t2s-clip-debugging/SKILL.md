---
name: t2s-clip-debugging
description: Diagnose and fix a failing or ugly clip in a Text-to-Shorts run (render errors, OUT_OF_FRAME/OVERLAP/CLIP_TOO_SHORT findings, contract violations, a clip agent that keeps failing). Use when a developer asks why clip sNNcMM failed, wants to reproduce a clip locally, or wants to improve the clip-builder prompt from real failures.
---

# Debugging a clip

Status: PROPOSED (commands refer to the target layout; tools are implemented in `tools/`).

Work from evidence in the run directory, in this order — each step is cheaper than the next:
1. `runs/<id>/state.json` → the clip's `last_error`, attempts, validation statuses.
2. `scenes/sNN/clips_work/clip_MM/checks/*.json` → the exact deterministic findings (codes are stable, see
   Plan.md §16.3 repair table). Most failures end here.
3. Reproduce without any LLM:
   ```bash
   python tools/validate_manim_code.py scenes/sNN/clips/clip_MM.py --index $T2S_API_INDEX --clip-file --entry … --exit …
   python tools/scene_harness.py compose scenes/sNN --scene-id sNN
   python tools/layout_probe.py scenes/sNN/scene.py SceneNN --budget clip_MM=<audio seconds>
   python tools/scene_harness.py render scenes/sNN --scene-id sNN --target clip_MM
   ```
4. `log.jsonl` rows for the clip (stage `clip_build`, attempts, cost, cache_read/cache_write) and the saved prompt in
   `.prompts/` to see exactly what the agent was told.

Classify before fixing: is the finding (a) a tool false positive → fix the tool + add a test fixture;
(b) a planning defect (impossible budget, contract asks for something the previous clip doesn't leave) → feedback on
the clip plan, not the code; (c) a code defect → rebuild the clip. If the same code recurs across runs, add a
topic-card example or a validator rule — that is cheaper than more prompt text.
