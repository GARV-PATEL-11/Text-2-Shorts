---
name: make-short
description: Turn a topic into a narrated Manim explainer video. Orchestrates app/pipeline.py (each LLM stage is a sandboxed `claude -p` with its own model/effort), asks the user at every review checkpoint, and presents the final MP4. Use when the user says /make-short, "make a video/short about X", or wants to resume/redo scenes of a run in runs/.
---

# make-short

You are the director. `app/pipeline.py` does the work; you run its steps, show results, and **ask the user (AskUserQuestion) at every checkpoint below. Never skip a checkpoint and never answer one yourself.**

All commands run from the repo root: `uv run python -m app.pipeline <step> ...`.
Run `outline`, `plan` and `render` with `run_in_background: true` (they take minutes) and wait for the completion notification; don't poll. If a step crashes, show the last lines of its output and `runs/<id>/log.jsonl`, then ask whether to retry.

Model/effort per stage lives in `STAGES` in `app/pipeline.py`. Scene agents run sandboxed (bubblewrap, no network, writes only in their scene folder).

## 0. Resume?
If the user names an existing run (`runs/<id>`), read its files to see which step is done (`brief.json` → `outline.json`/`narration.json` → `narration.mp3`s → `plan.md`s → `clip.mp4`s → `final.mp4`) and continue from the next checkpoint.

## 1. Clarify the topic — CHECKPOINT
Ask in one AskUserQuestion call (skip a question only if the user already answered it):
- **Approach**: `zoom` Conceptual Zoom (big picture → detail) · `arc` Problem → Solution · `linear` Classic linear lesson.
- **Audience / level**: e.g. curious beginners · students with high-school math · practitioners.
- **Length**: 1 · 2 · 3 · 5 minutes.
- **Voice** (Kokoro, local, default): af_heart (female, best) · af_bella (female) · am_michael (male) · bm_george (British male). Polly alternatives: Matthew/Joanna with `--engine neural`, Ruth/Stephen with `--engine generative`.

Then:
```
uv run python -m app.pipeline new "<topic in the user's words>" --approach <a> --minutes <m> --audience "<aud>" --voice <v> [--engine neural|generative] [--notes "<anything else they said>"]
```
First output line is the run folder (`runs/<id>`); use it for every later step.

## 2. Outline + narration — CHECKPOINT
`uv run python -m app.pipeline outline runs/<id>` (background). Show the printed scene table to the user as-is, plus the critic scores.
Ask: **Approve** · **Change something** (they type what). On change:
`... outline runs/<id> --feedback "<their words>"` and ask again. Loop until approved.

## 3. Voiceover
`uv run python -m app.pipeline tts runs/<id>` (foreground, quick). Report total narration seconds. First Kokoro run downloads ~350MB to `~/.cache/kokoro`. Polly AWS errors → tell the user to check `~/.aws` credentials / region.

## 4. Visual plans — CHECKPOINT
`... plan runs/<id>` (background). Show the table. For each scene, add one line of your own summarising what will be on screen (read `runs/<id>/scenes/NNN/plan.md`, skim only the overview section).
Ask: **Approve all** · **Change scenes** (they say which scenes and what). On change:
`... plan runs/<id> --scenes 2,4 --feedback "<their words>"` (one call per distinct feedback), then ask again.

## 5. Render — CHECKPOINT only if something failed
`... render runs/<id>` (background; can take 10–30 min). Show the status table.
For each FAILED scene ask: **Retry with a hint** (they type it) · **Simplify** · **Skip scene**.
- Retry: `... render runs/<id> --scenes N --feedback "<hint>"`
- Simplify: `... render runs/<id> --scenes N --feedback "Simplify: fewer objects, no LaTeX-heavy constructs, plain Text and basic shapes; keep the narration sync."`
- Skip: do nothing; assemble leaves it out (its narration is dropped too — say so).

## 6. Assemble + present — CHECKPOINT
`uv run python -m app.pipeline assemble runs/<id>`. Then present:
- the final path (clickable `runs/<id>/final.mp4`), duration, scene count, total Claude cost (printed);
- Read each `runs/<id>/scenes/NNN/thumb.png` and give one line per scene on what it shows and anything that looks off;
- open it: `xdg-open runs/<id>/final.mp4`.

Ask: **Looks good** · **Redo scenes** (which + what to change).
Redo → visual change only: `render --scenes N --feedback ...`; layout/content change: `plan --scenes N --feedback ...` then `render --scenes N`. Then assemble and present again. Loop until "Looks good".
