---
name: text-2-shorts-produce
description: Use when working inside a Text-2-Shorts run workspace (a folder with brief.json) — starting a video, continuing or resuming one, revising an approved or finished run, or answering what is left to do.
---

# Producing a run

You talk with the user and route the work to subagents; `text-2-shorts` decides the order and does the deterministic work. Goal: a `final.mp4` the
user approved: requirements → outline → script → scene visual + audio plans → clips, scene by scene.

## The loop
Run `text-2-shorts next .` (also printed at session start), do exactly the batch it returns, run it again:
- `write` — write the named file, reading the listed references (by path);
- `subagent` — dispatch that subagent for its target with paths only (a scene-builder after its `before`
  command, then its `after` command); a `parallel` batch goes out in one message;
- `command` — run it; `ask_user` — stop and ask the user, never answer for them.
Start no work `next` did not list: it enforces the order (scenes in series).

## Mandatory
- **Every checkpoint is the user's**: template · requirements · CP0 outline · CP1 script · CP2 scene plans ·
  CP3 each scene's preview · CP4 final. `--force` only when the user accepts the open problems. Editing an approved artifact makes it stale.
- **Show every change**: after each action, one line to the user: what changed (file, command, subagent, result).
- **Every artifact passes its gate** (the hook validates what you write); clip code reaches `clips/` only via `accept`.
- **Plan and video critiques are scored** (pass ≥ `quality_threshold`, default 85), at most 3 rounds; then
  REQUIRES ATTENTION goes to the user. Record each video refactor in `scenes/sNN/changes.json`.

## Stages
| Stage | Output | Gate → checkpoint | Read |
|---|---|---|---|
| 1 Template, Requirements | `template.json` (the user's, on the website) first; `brief.json`; `topics.md` (numbered); `content.md` (one `## topic` section each) | `approve . template`, then `approve . requirements` | `references/requirements.md`, `references/topic-list.md` |
| 2 Outline | `outline.json` in the approach's model, by the **script-writer** | order, timing, visual-plan rules → **CP0** `approve . outline` | `references/outline-<approach>.md` (eli5 · visual_intuition · story_driven · step_by_step · feynman · technical · case_study · custom) |
| 3 Script | `script.json` by the **script-writer**: index scene, then one scene per outline segment with bridge, narration, on-screen/animation/audio/transition needs; `script_review.json` (**accuracy-reviewer**); changes at CP1 → one **script-critic** round, then refactor | objectives, mapping, word budget → **CP1** `approve . script` | `references/standards.md`, `references/script-writing.md`, `references/script-review.md`, `references/transitions.md`, `references/critique-protocol.md` |
| 4 Plans | `plan.json` (execution plan first) by the **scene-planner**; **plan-critic**; `plan_review.json` | script word for word, SSML, critique → **CP2** `approve . plan` | `references/visual-director-system.md`, `references/visual-director-output-spec.md`, `references/scene-visual-planning.md`, `references/audio-ssml.md`, `references/critique-protocol.md` |
| 5 Production | per scene: `voice` → `scene_code.py` (**scene-builder**) → `preview` → **audio-refactorer** → **video-critic** + `changes.json` | in sync → **CP3** `approve . sNN`, then the next scene | `references/scene-production.md`, `references/codegen-system.md`, `references/codegen-task.md`, `references/critique-protocol.md` |
| Final | `final .` → 2560×1440, 120 fps; template transitions, music, sound effects | media and delivery checks → **CP4** `approve . final` | — |

References: pass them by path, read each when its stage starts, reuse the copy already in this session (re-read
only if it changed or after compaction); keep `references/standards.md` all run.

## The user's tweaks and decisions
- **A change request** (any time): `text-2-shorts feedback . <target> --kind
  wording|visual|audio-timing|accuracy|structure|style|other --text "<their words>"` (add `--checkpoint <name>` when
  raised at a checkpoint). `next` routes it; when applied: `text-2-shorts resolve . rNNN applied` (or `declined`
  with the user's agreement). Open requests block their checkpoint; a clip's visual request resolves on accept.
- **A decision**: `text-2-shorts approve . <checkpoint> [--notes "<their notes>"]` — every decision is recorded.
- **Standing preferences** (`preferences.json`: tone, palette, background, font, voice rate, pause length,
  confirm each scene): edit when the user asks for a lasting change; every stage applies them.
- **The user's own outline or script**: convert it (`approach: custom`) and list what you added.

## Finish
Report the `final.mp4` path, duration, clip count, media-check lines and `text-2-shorts report .`. Done when CP4
is approved.
