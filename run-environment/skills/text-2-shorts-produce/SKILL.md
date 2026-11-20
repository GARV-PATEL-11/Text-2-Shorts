---
name: text-2-shorts-produce
description: Use when working inside a Text-2-Shorts run workspace (a folder with brief.json) — starting a video, continuing or resuming one, revising an approved or finished run, or answering what is left to do.
---

# Producing a run

You do the reasoning (outline, clip plans, narration, clip code via subagents); `text-2-shorts` does the deterministic work.
The goal is a `final.mp4` the user approved, built from artifacts that pass every gate. How you get there adapts
to what the user brings and asks.

## Mandatory
- **Ask the user at the four checkpoints and never approve for them**: CP1 outline · CP2 clip plan + accuracy
  findings · CP3 each scene's preview · CP4 final video. `text-2-shorts approve` refuses unfinished checkpoints; use
  `--force` only when the user explicitly accepts the open problems.
- **Every artifact must pass its gate**: the hook validates `outline.json`, `scenes/sNN/plan.json` and `math.json`
  as you write them (fix every reported error); clip code reaches `clips/` only through `text-2-shorts accept`.
- **The user's objective wins over defaults**: their outline, wording, tone, colours or structure replace the
  defaults in the references; keep only what the gates require.
- **`text-2-shorts status .` is the source of truth** for what is done, stale or next — not your memory.

## The artifacts
| Artifact | Made by | Gate | Guidance (read when you reach it) |
|---|---|---|---|
| `outline.json` | you (from the brief or the user's own outline) | `text-2-shorts validate . outline` (schema, length ±20%) | `references/outline-<approach>.md`, `references/outline-review.md` |
| `scenes/sNN/plan.json` | you, scene by scene | `text-2-shorts validate . plan` (contracts, empty scene ends, one colour per symbol) | `references/clip-planning.md` |
| `math.json` | **math-reviewer** subagent — the accuracy check for any topic (math, science, history, facts); `{"findings": []}` is a valid result | `text-2-shorts validate . math`; ERRORs block CP2 | — |
| narration audio | `text-2-shorts voice .` (only changed clips) | — | — |
| `clips/clip_MM.py` | `text-2-shorts task . sNNcMM` → **clip-builder** subagent → `text-2-shorts accept . sNNcMM` | `./check` gates, re-run jailed | — |
| `final.mp4` | `text-2-shorts final .` | media checks (2560×1440, ≥ 60 fps, loudness) | — |

Read `references/standards.md` once before planning (style, palette, timing, narration convention). The default
explanation style is ELI5/Feynman unless the user or `brief.json` says otherwise. Schemas: the repo's `schemas/json/`.

## Adapting
- **User-supplied outline, script or plans**: convert them into the artifact format, fill required fields (e.g. talking
  points, visual plan) and list what you added; skip critique the user declined. Their structure replaces the
  approach's template; `brief.json` → `approach` only selects the schema. If their timings miss the requested length
  by more than 20%, show the numbers and ask whether to change the timings or `minutes` in `brief.json`.
- **Revisions after approval**: edit the narration in `plan.json` → `text-2-shorts voice .`. Change one object's look →
  `text-2-shorts feedback . sNNcMM --scope visual --text "…"`. Change a symbol's colour everywhere → edit `color_roles`
  in every plan. Then rebuild exactly the clips `text-2-shorts status .` lists as stale, re-run the math-reviewer if the
  meaning changed, re-ask CP3 for changed scenes (a quick "approve these changes?" is enough), `text-2-shorts final .`, CP4.
- **Parallelism**: scenes are independent (build several at once); clips within a scene go strictly in order.
- **A clip that fails `text-2-shorts accept` twice**: show the user the findings and ask for a hint before trying again.

## Finish
Report the `final.mp4` path, duration, clip count, media-check lines and `text-2-shorts report .` (tokens used). The user
opens the video in their own player. Done when CP4 is approved.
