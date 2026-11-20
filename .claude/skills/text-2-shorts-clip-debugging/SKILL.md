---
name: text-2-shorts-clip-debugging
description: Use when a Text-2-Shorts clip fails `text-2-shorts accept` or `./check`, keeps failing for the clip-builder, renders wrongly (overlap, out of frame, too short or long, wrong content), or when someone wants to reproduce or explain a clip failure.
---

# Debugging a clip

Find the cause from evidence, cheapest first, then fix it where it lives (tool, plan or code).

## Evidence, in order
1. `uv run text-2-shorts status runs/<id>` → the clip's status and `open_findings` codes.
2. `runs/<id>/scenes/sNN/work/clip_MM/checks/<gate>.json` → exact findings with times/lines. Most cases end here.
3. Reproduce without any LLM: `cd runs/<id>/scenes/sNN/work/clip_MM && ./check static` (then `probe`, `render`,
   `frames`). The folder holds `TASK.json`, the clip file and its own copy of the earlier clips.
4. `TASK.md` / `API_CARDS.md` (what the builder was told) and `runs/<id>/log.jsonl` (what the session ran).

## Rules the gates apply
| Code | Gate | Meaning |
|---|---|---|
| CLIP_TOO_SHORT (ERROR) | probe | target `CLIP_SECONDS` = 0.3 s lead-in + narration + 0.8 s hold; fails when duration + 0.5 < target. `checks/probe.json` → `clip.duration` vs `clip.budget` |
| CLIP_TOO_LONG (WARN) | probe | duration − target > 1.5 s |
| OVERLAP / OUT_OF_FRAME | probe | text boxes overlap / leave the frame within this clip's time window |
| TINY_TEXT (WARN) | probe | text below the readable height |
| CLIP_NOT_RUN | probe | the clip's function never executed (an earlier clip failed) |
| CONTRACT_* | static | ENTRY/EXIT registry names (`self.reg`) differ from the plan |
| REMOVED_API / UNKNOWN_* | static | name not in Manim 0.20.1 (see `manim-ce-0-20-1-reference`) |
| render failure | render | traceback in `checks/render.json` → `error` |
Definitions: `tools/layout_probe.py`, `tools/validate_manim_code.py`, `app/clip_gates.py`.

## Classify, then fix
- **Tool false positive** (the finding is wrong) → fix the tool, add a test fixture in `tests/`.
- **Plan defect** (impossible timing, contract the previous clip cannot satisfy, missing exit object) → edit the
  scene's `plan.json` (+ `text-2-shorts voice` if narration changed); it is not a code problem.
- **Code defect** → `uv run text-2-shorts feedback runs/<id> sNNcMM --scope visual --text "<precise fix>"`, then in the run
  session `text-2-shorts task` → clip-builder → `text-2-shorts accept`.
- **Recurring across clips/runs** → add a topic-card example or a validator rule; cheaper than more instructions.

Done when the cause is named with its evidence and the clip passes `text-2-shorts accept` (or the plan/tool is fixed).

Related: `manim-ce-0-20-1-reference` (API facts) · `text-2-shorts-prompt-maintenance` (changing builder instructions).
