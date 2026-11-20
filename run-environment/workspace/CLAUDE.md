# Text-2-Shorts run workspace

This folder is ONE video run. You are inside an isolated jail: only this folder (plus Claude Code's own state and
caches) is writable; the repo — `text-2-shorts` commands, tools, `run-environment/` references, schemas — is read-only. Other runs cannot
see your files and you cannot change theirs.

- Workflow, checkpoints and which reference to read when: the `text-2-shorts-produce` skill. Start there.
- Where you are: `text-2-shorts status .` (printed automatically at session start) lists approvals, clip states and next steps.
- You write the reasoning artifacts (outline.json, scenes/sNN/plan.json, clip code via the clip-builder subagent,
  math.json via the math-reviewer subagent); `text-2-shorts` commands validate, synthesise voice, check, accept and render.
- Never edit state.json by hand: it changes only through `text-2-shorts approve`, `text-2-shorts accept` and `text-2-shorts feedback`.

Layout: brief.json · outline.json · scenes/sNN/{plan.json, audio/, work/clip_MM/, clips/} · math.json ·
feedback.jsonl · state.json · log.jsonl · final.mp4 · final_report.json
