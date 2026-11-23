---
name: text-2-shorts-produce
description: Use when working inside a Text-2-Shorts run workspace (a folder with brief.json) — starting a video, continuing or resuming one, revising an approved or finished run, or answering what is left to do.
---

# Producing a run

You do the reasoning; `text-2-shorts` decides the order and does the deterministic work. Goal: a `final.mp4` the
user approved: requirements → script → scene visual + audio plans → clips, scene by scene.

## The loop
Run `text-2-shorts next .` (it is also printed when the session starts) and do exactly the batch it returns, then
run it again. Each action says who does it:
- `write` — you write the named file, reading the listed references (by path);
- `subagent` — dispatch that subagent for the target with paths only; when the batch is `parallel`, dispatch all
  of them in one message (each clip-builder after its `before` command, then its `after` command);
- `command` — run it; `ask_user` — stop and ask the user, never answer for them.
Do not start work `next` did not list: it enforces the order (scenes in series, a scene's clips in parallel).

## Mandatory
- **Stages in order** (enforced by the commands); editing an approved artifact makes its checkpoint stale.
- **Ask the user at every checkpoint and whenever their input is needed; never approve for them**: CP1 script ·
  CP2 scene plans · CP3 each scene's preview · CP4 final video. `--force` only when the user accepts open problems.
- **Every artifact passes its gate**: the hook validates what you write; clip code reaches `clips/` only via `accept`.
- **Critic loops stop after 3 rounds per scene** (plans before CP2, video before CP3); what is still open then goes
  to the user.
- **The user's objective wins over defaults**; keep only what the gates require.

## Stages
| Stage | Output | Gate → checkpoint | Read (path) |
|---|---|---|---|
| 1 Requirements | `brief.json`: objectives, audience, style, approach, length, constraints | `validate . brief`; user confirms | `references/requirements.md` |
| 2 Script | `script.json`: index scene s01, then scenes with objective, key concepts, duration, bridge, narration; `script_review.json` (**accuracy-reviewer**) | objectives, index, bridges, word budget, length → **CP1** `approve . script` | `references/script-writing.md`, `references/narrative-structures.md`, `references/script-review.md`, `references/transitions.md` |
| 3 Plans | per scene `scenes/sNN/plan.json` (visuals + per-clip SSML), `plan_critique.json` (**plan-critic**, ≤ 3 rounds); `plan_review.json` (**accuracy-reviewer**) | narration = script word for word, valid SSML, critique passed → **CP2** `approve . plan` | `references/scene-visual-planning.md`, `references/audio-ssml.md` |
| 4 Clips + video | scene by scene: `voice` → all clips of the scene in parallel via **clip-builder** (`task` → `accept`, 720p30) → `preview` (`sync.json`) → **audio-refactorer** → **video-critic** (≤ 3 rounds) | in sync, critique passed → **CP3** `approve . sNN`; then the next scene | `references/scene-production.md` |
| Final | `final .` → 2560×1440 at 120 fps | media checks → **CP4** `approve . final` | — |

## References: by path, read once
Pass references and artifacts by path, never pasted. Read a reference when its stage starts; if this session
already holds it, use that copy and do not re-read it (re-read only after the file changed or the context was
compacted). Read `references/standards.md` before the script and keep it for the whole run (the session-wide
reference). Subagents get paths too: the clip-builder's folder lists what to read first. Give each step only its
inputs, never the project history.

## Adapting
- **The user's own outline, script or plans**: convert them into the stage's artifact (`approach: creative`) and
  list what you added; if their timings miss the length by more than 20%, show the numbers and ask.
- **Revisions**: wording → `script.json` (CP1 again), the affected plans (CP2 again), `voice`. One clip's visuals →
  `text-2-shorts feedback . sNNcMM --scope visual --text "…"` and rebuild it. Then preview, CP3, `final`, CP4.
- **Order**: scenes are produced one after another; the clips of the current scene are built in parallel.

## Finish
Report the `final.mp4` path, duration, clip count, media-check lines and `text-2-shorts report .`. Done when CP4
is approved.
