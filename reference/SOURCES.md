# Sources and references (accessed 2026-11-19)

## Manim Community Edition
- Changelog index — https://docs.manim.community/en/stable/changelog.html
- v0.20.0 changelog (2026-02-20; MathTex rewrite PR #4515, `Mobject.always` PR #4594, `--seed`) — https://docs.manim.community/en/stable/changelog/0.20.0-changelog.html
- v0.20.1 changelog (2026-02-27) — https://docs.manim.community/en/stable/changelog/0.20.1-changelog.html
- Reference manual (stable = v0.20.1 at access time) — https://docs.manim.community/en/stable/reference.html
- MathTex — https://docs.manim.community/en/stable/reference/manim.mobject.text.tex_mobject.MathTex.html
- Rendering text & formulas guide — https://docs.manim.community/en/stable/guides/using_text.html
- Versioned docs build for tag v0.20.1 (Read the Docs) — https://app.readthedocs.org/projects/manimce/builds/31583943/
- Source — https://github.com/ManimCommunity/manim
Behavioural facts in Plan.md §14.2 were verified by executing code against `manim==0.20.1` (see tests/).

## Claude Code
- CLI reference (flags used by the runner: `--restricted`, `--permission-prompts`, `--safe-mode`, `--json-schema`,
  `--max-budget-usd`, `--append-system-prompt-file`, `--exclude-dynamic-system-prompt-sections`,
  `__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__`, `--effort` levels) — https://code.claude.com/docs/en/cli-reference
  (fetched in its Portuguese rendering: https://code.claude.com/docs/pt/cli-reference)
- Settings / sandboxing (`sandbox.enabled`, `autoAllowBashIfSandboxed`, `allowUnsandboxedCommands`, `failIfUnavailable`,
  `filesystem.allowWrite/denyRead`) — https://code.claude.com/docs/en/settings · https://code.claude.com/docs/en/sandboxing
- Docs index — https://code.claude.com/docs/llms.txt

## Claude API (via vendored skill snapshot)
- anthropics/skills `claude-api` skill: `shared/models.md` (pricing used in Plan.md §18.5), `shared/prompt-caching.md`
  (cache minimums, TTL economics). Verify live: https://docs.claude.com

## Skills
- Anthropic skills repository — https://github.com/anthropics/skills (commit recorded in each vendored SOURCE.md)
- Agent Skills specification — https://agentskills.io/specification
- adithya-s-k/manim_skill (manimce-best-practices, MIT) — https://github.com/adithya-s-k/manim_skill
- Reviewed only: https://github.com/Yusuke710/manim-skill · https://github.com/vumichien/manim-skill ·
  https://github.com/awesome-skills/manim-skill

## AWS Polly (TTS engine already used)
- Speech marks (word timings, proposed use) — https://docs.aws.amazon.com/polly/latest/dg/speechmarks.html

## Inputs provided by the user
- `app.zip` (audited; not redistributed in this package), `Instructions`, `Agentic_Mathematical_Video_Generation_Implementation_Plan (1).md`
  (earlier generic blueprint; where this package deviates — LangGraph, 26 agents, parallel production — Plan.md §5.2 states why).
