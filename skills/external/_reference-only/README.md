# Reviewed, not vendored

| Project | What it is | Decision | Why |
|---|---|---|---|
| [Yusuke710/manim-skill](https://github.com/Yusuke710/manim-skill) (MIT, commit a0048d9e265499038f34a9aa58ff16d306b5034c) | Claude Code plugin: plan → code → render → iterate in one interactive session; tools for TTS, subtitle lint, a video viewer. | Reference only | Same single-session design this project is moving away from (no clip contracts, no ledger, no deterministic gates). Its `tools/lint-subtitles.py` idea is noted for captions (future). |
| [vumichien/manim-skill](https://github.com/vumichien/manim-skill) | 4-role agent pipeline (researcher, planner, implementer) as Claude Code subagents. | Reference only | Spawns researcher/planner in parallel; this project requires sequential, ledger-driven execution. |
| [awesome-skills/manim-skill](https://github.com/awesome-skills/manim-skill) (MIT) | Agent-agnostic ManimCE playbook, ~3k lines. | Not adopted | Overlaps manimce-best-practices; size defeats the per-clip context budget. |
| [adithya-s-k/manim_skill](https://github.com/adithya-s-k/manim_skill) manim-composer | Scene-planning skill producing scenes.md. | Not adopted | Superseded by clip_planner@1 with typed contracts. |
| anthropics/skills mcp-builder | Build MCP servers. | Not needed now | Only if the review UI later exposes the ledger over MCP (future enhancement). |

Community skills can contain wrong claims: one indexed community reference states that VGroup(Text(...)) raises
TypeError on v0.20+; on the installed 0.20.1, VGroup(Text("a"), MathTex("x")) works (verified 2026-11-19).
Every adopted community instruction must pass the topic-card test harness first.
