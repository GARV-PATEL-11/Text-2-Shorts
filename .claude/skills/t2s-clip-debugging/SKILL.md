---
name: t2s-clip-debugging
description: Diagnose and fix a failing or ugly clip in a Text-to-Shorts run (render errors, OUT_OF_FRAME/OVERLAP/CLIP_TOO_SHORT findings, contract violations, a clip agent that keeps failing). Use when a developer asks why clip sNNcMM failed, wants to reproduce a clip locally, or wants to improve the clip-builder prompt from real failures.
---

# Debugging a clip

Work from evidence in the run directory, in this order — each step is cheaper than the next:
1. `uv run t2s status runs/<id>` and `runs/<id>/state.json` → the clip's status, `notes` and `open_findings`.
2. `scenes/sNN/work/clip_MM/checks/*.json` → the exact deterministic findings (codes are stable, see
   Plan.md §16.3 repair table). Most failures end here.
3. Reproduce without any LLM, from the clip's work folder (it holds TASK.json and its own scene copy):
   ```bash
   cd runs/<id>/scenes/sNN/work/clip_MM && ./check static && ./check probe && ./check render && ./check frames
   ```
4. `log.jsonl` end rows for the clip (stage `clip_build`/`clip_build_retry`: `outcome`, `notes`, `turns`,
   `permission_denials`, cost) and `TASK.md` / `API_CARDS.md` in the work folder — exactly what the agent was told.

Classify before fixing: is the finding (a) a tool false positive → fix the tool + add a test fixture;
(b) a planning defect (impossible budget, contract asks for something the previous clip doesn't leave) → feedback on
the clip plan, not the code; (c) a code defect → `t2s build runs/<id> --clips sNNcMM --feedback "…"`. If the same code recurs across runs, add a
topic-card example or a validator rule — that is cheaper than more prompt text.
