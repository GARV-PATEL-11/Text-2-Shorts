# Text-2-Shorts run workspace

This folder is ONE video run. You are inside an isolated jail: only this folder (plus Claude Code's own state and
caches) is writable; the repo — `text-2-shorts` commands, tools, `run-environment/` references, schemas — is read-only. Other runs cannot
see your files and you cannot change theirs.

- Workflow, checkpoints and which reference to read when: the `text-2-shorts-produce` skill. Start there.
- What to do now: `text-2-shorts next .` returns the exact next batch (printed at session start with the status);
  do it, then ask again. Scenes go one after another; a scene's clips are built in parallel.
- Stages, in order: requirements (brief.json) → complete script (script.json, CP1) → scene visual + audio plans
  (scenes/sNN/plan.json with SSML, plan-critic ≤ 3 rounds, CP2) → per scene: all its clips in parallel (clip-builder),
  720p30 preview + sync report, audio-refactorer, video-critic ≤ 3 rounds (CP3) → final 1440p120 (CP4).
  `text-2-shorts` commands validate, enforce the order, synthesise voice, check, accept and render.
- Never edit state.json by hand: it changes only through `text-2-shorts approve`, `text-2-shorts accept` and `text-2-shorts feedback`.

Layout: brief.json · script.json · script_review.json · plan_review.json · scenes/sNN/{plan.json, plan_critique.json,
audio/, work/clip_MM/, clips/, preview.mp4, sync.json, video_critique.json} · feedback.jsonl · state.json ·
log.jsonl · final.mp4 · final_report.json
