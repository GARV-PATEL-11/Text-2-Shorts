---
name: make-short
description: Operate the Text-to-Shorts generator from Claude Code — create a video from a topic, walk the user through every approval checkpoint (outline, clip plan + math sheet, per-scene clip previews, final video), and turn their feedback into scoped regeneration of only the affected clips. Use when the user asks to make, continue, revise or check the status of an explainer video / short, or mentions a runs/<id> directory.
---

# make-short — operator skill

Status: PROPOSED. `pipeline.py` refers to `.claude/skills/make-short/SKILL.md`, which was not in the audited
`app.zip`. This is a reconstruction for the TARGET CLI (`t2s ...`, Plan.md §20). Section "Current CLI" maps the
same flow onto today's `python -m app.pipeline` commands so the skill is usable before the refactor.

## Ground rules (why they matter)
- **You are the operator, not the generator.** Every LLM-generation step runs inside the CLI (it records cost,
  prompts, versions and cache keys in the run ledger). Do not write plans, narration or Manim code yourself in this
  session — work done here is invisible to the ledger and will be overwritten or, worse, rendered unvalidated.
- **One step at a time, sequentially.** Run one command, read its summary, report to the user, wait at checkpoints.
- **Never claim success the ledger doesn't show.** Use `t2s status` as the source of truth.
- **Feedback is scoped.** Always attach feedback to the smallest target (a clip and a scope), never to "the video".

## Flow
1. `t2s new "<topic>" --approach zoom|arc|linear --minutes N --audience "…" [--aspect 9:16]`
   → runs preflight, refine, outline, outline review. Show the outline table and reviewer WARNs.
2. **CP1 outline (mandatory).** Ask: approve, or what to change. Changes → `t2s feedback outline --text "…"`.
   Approve → `t2s approve outline`.
3. `t2s plan` → clip plans per scene + math verification. Show the clip table (scene, clip, seconds, narration
   excerpt) and the math sheet. ERROR math findings must be resolved before approval.
4. **CP2 plan (mandatory).** Clip-level edits: `t2s feedback clip s02c03 --scope narration|math|visual --text "…"`.
   Approve → `t2s approve plan`. (Approving freezes narration → TTS runs once per clip and is cached.)
5. `t2s build --scene s01` (one scene at a time). Report per clip: READY/FAILED, renders, cost. Link draft previews
   and the contact sheet `runs/<id>/scenes/s01/review/contact.png`.
6. **CP3 scene preview (mandatory per scene).** For each clip: approve / revise (with scope) / reject.
   `t2s feedback clip s01c02 --scope visual --text "highlight c, not b"` then `t2s build --scene s01` again —
   only invalidated clips rebuild (`t2s explain s01c02` shows exactly what will rebuild and why).
   `t2s approve scene s01` when all its clips are approved.
7. After all scenes: `t2s final` → final-quality renders, assembly, loudness, final checks.
8. **CP4 final (mandatory).** Approve → `t2s approve final`; deliver `runs/<id>/delivery/final.mp4` + cost report.

## Status and recovery
- `t2s status` — phase, clip states, open feedback, spend vs budget. Resume after any interruption by running the
  step it names; completed and cached work is reused automatically.
- A clip FAILED twice → show its open finding codes and ask the user whether to simplify the clip (feedback with
  scope visual) or accept a fallback (static frame + narration). Do not loop.
- Budget stop → report spend and the cheapest next step; never raise the budget without the user.

## Current CLI (before the clip-level refactor)
`python -m app.pipeline new "<topic>" --approach zoom --minutes 2 --voice af_heart` → `outline <run> [--feedback]`
→ (approve) → `tts <run>` → `plan <run> [--scenes 2,3] [--feedback]` → `render <run> [--scenes 2] [--feedback]` →
`assemble <run>`. Feedback there is scene-level and NOT persisted; after `outline --feedback`, re-run `tts` and
`plan`/`render` for every scene, because old plan.md/scene.py files are not invalidated automatically.
