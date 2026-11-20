---
name: make-short
description: Turn a topic into a narrated Manim explainer video (2560x1440, 60–120 fps). Operates the `t2s` CLI (clip-level pipeline; each LLM stage is a sandboxed `claude -p`), asks the user at every review checkpoint, and presents the final MP4. Use when the user says /make-short, "make a video/short about X", or wants to resume, revise or check the status of a run in runs/.
---

# make-short

You are the operator. `t2s` does the work; you run one step at a time, show results, and **ask the user
(AskUserQuestion) at every checkpoint (CP1–CP4). Never skip a checkpoint and never answer one yourself.**
Do not write plans, narration or Manim code yourself — everything goes through `t2s` so it is logged, versioned and checked.

All commands run from the repo root as `uv run t2s <step> runs/<id> …`. Run `outline`, `clips`, `build` and `final`
with `run_in_background: true` and wait for the completion notification; don't poll. If a step crashes, show the
last lines of its output and of `runs/<id>/log.jsonl`, then ask whether to retry. `uv run t2s status runs/<id>`
shows approvals, every clip's state and spend; use it to resume after any interruption.

Units: a video has scenes (`s01`…), a scene has clips (`s01c01`…). Each clip has its own narration audio and its own
code file, built by one sandboxed agent. Re-running a step only redoes what changed (feedback, edited plan, earlier
clip) — unchanged work is reused.

## 0. Resume?
If the user names a run, run `status` and continue from the first unfinished checkpoint:
`outline.json` → `state.json` approved `outline` → `scenes/sNN/plan.json` + approved `plan` → `audio/index.json` →
all clips READY + approved `scene:sNN` → `final.mp4` + approved `final`.

## 1. Clarify the topic
Ask in one AskUserQuestion call (skip what the user already said):
- **Approach**: `zoom` Conceptual Zoom · `arc` Problem → Solution · `linear` Classic linear lesson.
- **Audience / level**: curious beginners · students with high-school math · practitioners.
- **Length**: 1 · 2 · 3 · 5 minutes.
- **Voice** (Kokoro, local): af_heart (female, best) · af_bella · am_michael (male) · bm_george (British male).
  Polly: Matthew/Joanna with `--engine neural`, Ruth/Stephen with `--engine generative`.
- **Font** for on-screen text (MathTex keeps LaTeX fonts): Roboto · Noto Sans · DejaVu Sans · Latin Modern Roman
  (full list: `fc-list : family`); skip for Manim's default.
```
uv run t2s new "<topic in the user's words>" --approach <a> --minutes <m> --audience "<aud>" --voice <v> [--font "<family>"] [--engine neural|generative] [--notes "<extra>"]
```
`new` runs a preflight first (LaTeX, ffmpeg, bubblewrap, Claude Code version) and stops with the fix if something is
missing. Its first output line is the run folder.

## 2. CP1 — Outline
`uv run t2s outline runs/<id>` (background). Show the scene table as printed.
Ask: **Approve** · **Change something**. Change → `outline runs/<id> --feedback "<their words>"`, ask again.
Approve → `uv run t2s approve runs/<id> outline`.

## 3. CP2 — Clip plan + math sheet
`uv run t2s clips runs/<id>` (background). Show the clip table and the math findings as printed.
- ERROR math findings block approval. For each, ask the user to accept the suggested fix or word their own, then
  `feedback runs/<id> sNNcMM --scope math --text "<fix>"` and `clips runs/<id> --scenes N`.
- Other changes: `clips runs/<id> --scenes N --feedback "<their words>"` (scene-level), or
  `feedback runs/<id> sNNcMM --scope narration --text "…"` then `clips --scenes N` (one clip).
Ask: **Approve plan** · **Change clips**. Approve → `uv run t2s approve runs/<id> plan`.

## 4. Voice
`uv run t2s voice runs/<id>` (foreground). Report the total narration seconds. The first Kokoro run downloads
~350 MB (hash-checked). Polly errors → check `~/.aws` credentials/region.

## 5. CP3 — Build and preview, per scene
`uv run t2s build runs/<id>` (background; 4 scenes at a time, clips in order). Show the status table.
For each scene, Read `scenes/sNN/work/clip_MM/frames/f_last.png` for every clip and describe in one line what it
shows and anything off. The draft video of a clip is `scenes/sNN/work/clip_MM/checks/render.json` → `video`.
Ask per scene: **Approve scene** · **Revise clips** (which + what) · for FAILED clips: **Retry with a hint**.
- Revise / retry: `build runs/<id> --clips sNNcMM --feedback "<their words>"` (only that clip and the ones after it
  in the scene are rebuilt).
- Approve: `uv run t2s approve runs/<id> sNN`.
A FAILED clip stops its scene (later clips need its exit state). Usage-limit errors are waited out automatically.

## 6. CP4 — Final
`uv run t2s final runs/<id>` (background): final 1440p render (`T2S_FPS`, 60–120, default 60), per-clip audio sync,
loudness normalisation, media checks, cost table. Present:
- `runs/<id>/final.mp4`, duration, clip count, Claude cost, any media-check WARN/ERROR lines;
- open it in Chrome: `google-chrome "file://$PWD/runs/<id>/final.mp4"`, and print that `file://` URL (spaces as `%20`).
Ask: **Looks good** · **Redo clips** (which + what). Redo → back to step 5 for those clips, then `final` again.
Looks good → `uv run t2s approve runs/<id> final`.
