# Text-2-Shorts run workspace

This folder is ONE video run. You are inside an isolated jail: only this folder (plus Claude Code's own state and
caches) is writable; the repo — `text-2-shorts` commands, tools, `runtime-environment/` references, schemas — is read-only. Other runs cannot
see your files and you cannot change theirs.

- Workflow, checkpoints and which reference to read when: the `text-2-shorts-produce` skill. Start there.
- What to do now: `text-2-shorts next .` returns the exact next batch (printed at session start with the status);
  do it, then ask again. Scenes go one after another; a scene's clips one at a time, in order.
- Stages, in order: template (template.json, chosen by the user on the website; template checkpoint) →
  requirements (brief.json, topics.md, content.md; requirements checkpoint) → outline (outline.json, CP0) → complete script (script.json, CP1; one
  script-critic round per change the user asks for) → scene visual + audio plans (scenes/sNN/plan.json with SSML,
  plan-critic ≤ 3 scored rounds, CP2) → per scene: its clips one at a time (clip-builder), 720p30 preview + sync
  report, audio-refactorer, video-critic ≤ 3 scored rounds with changes.json (CP3) → final 1440p120 (CP4). Optional
  after that: the user reshuffles the look on the website (no Claude); then only re-render previews (CP3) and the final.
  Every stage, scene and clip has a status (pending · in_progress · completed · failed · requires_refactoring ·
  requires_user_approval · approved) in state.json, shown by `text-2-shorts status .`.
  `text-2-shorts` commands validate, enforce the order, synthesise voice, check, accept and render.
- Models: this session (Haiku) talks with the user, refines requirements and routes; it builds nothing itself.
  Builders and refactors run on Opus (script-writer: outline and script; scene-planner: plans; clip-builder: code);
  critics, accuracy-reviewer and audio-refactorer on Sonnet; all at medium effort.
- Show the user every change as it happens: one line per file written, command run or subagent result. The hook
  shows each write, command and subagent too, and logs it to log.jsonl.
- The user works only in the Faraday website (`text-2-shorts serve`): each message there is one turn of this
  session. When the user must decide or answer, ask and end your turn: your last message shows on the stage page,
  rendered as Markdown (number the questions, list the choices). They may also approve checkpoints and record
  change requests with the page's buttons; those count the same, and `text-2-shorts next .` already reflects them.
- Never edit state.json by hand: it changes only through `text-2-shorts approve`, `text-2-shorts accept` and `text-2-shorts feedback`.

Layout: brief.json · preferences.json · template.json · template_preview.svg · assets/ (the user's music and
sound files) · topics.md · content.md · outline.json · script.json · script_review.json ·
script_critique.json · plan_review.json · scenes/sNN/{plan.json, plan_critique.json, audio/, work/clip_MM/, clips/, preview.mp4, sync.json,
video_critique.json, changes.json} · changes.txt · requests.jsonl · decisions.jsonl · state.json · log.jsonl · final.mp4 · final_report.json
