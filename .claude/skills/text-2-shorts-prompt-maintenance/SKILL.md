---
name: text-2-shorts-prompt-maintenance
description: Use when changing how Text-2-Shorts behaves — tone or explanation style, outline approaches, planning or clip-building instructions, subagents and their models, hooks, session sandbox or permissions, schemas, validators or topic cards — or when improving output quality or token use.
---

# Changing the run environment

The run session's behaviour lives in `run-environment/` (a Claude Code plugin + settings); what it must produce is checked by
schemas and validators in `app/`. Change both sides together and prove it with tests.

## Where each kind of change lives
| Change | Files (all of them) |
|---|---|
| Tone / explanation style | ask first: for every video → `run-environment/skills/text-2-shorts-produce/references/standards.md` (EXPLANATION STYLE); for one run → `--notes` or the user's request in that session |
| Visual standards (palette, sizes, timing) | `standards.md` **and** `VIDEO_STYLE` / `VOICE_LEAD_IN_SECONDS` / `END_HOLD_SECONDS` in `app/run_steps.py` (a test keeps them equal) |
| New outline approach | `references/outline-<name>.md`; model in `app/outline_models/` + `OUTLINE_MODELS` (`app/run_steps.py`); `--approach` choices (`app/cli.py`); `Brief.approach` (`schemas/models.py`) → `uv run python schemas/export_json_schemas.py`; `make-short` table; tests |
| Planning rules | `references/clip-planning.md` + `validate_plan` + `ScenePlan` |
| Clip-builder / math-reviewer | `run-environment/agents/*.md` (frontmatter `model`, `tools`). A different model for some clips: agree with the user how those clips are chosen (a list, or a field added to `ClipPlan`), add a second agent file, say in `text-2-shorts-produce` when to use it, and add that file to `clip_key` (`CLIP_BUILDER_AGENT_PATH` in `app/run_steps.py`) so its edits mark clips stale |
| Workflow, checkpoints | `run-environment/skills/text-2-shorts-produce/SKILL.md` (+ `text-2-shorts` commands in `app/`) |
| Hooks, sandbox, permissions | `run-environment/hooks/hooks.json`, `run-environment/settings.json`; jail mounts: `build_jail_command` in `app/cli.py` |
| Manim knowledge | `run-environment/skills/manim-ce-0-20-1-reference/topics/` (examples are executed by tests) |

## Rules
- **Contract first**: never instruct a format a schema or validator rejects; after schema edits regenerate
  `schemas/json/`.
- **Keep always-loaded text small**: `run-environment/workspace/CLAUDE.md` and SKILL.md bodies load every session; detail goes in
  a reference named at the step that needs it.
- **No hand-written Manim API lists**: use generated cards and tested topic cards.
- **Editing `run-environment/agents/clip-builder.md` marks every clip stale** (it is part of each clip's key): say so first on a
  run in progress.
- **Model choice**: frontmatter `model`; ask the user before switching any agent to a more expensive model.

## Validate
`uv run pytest -q` (layout, schemas, jail, hooks, docs) · `tests/test_topic_cards.py` for topic edits · on a short
test run, compare `uv run text-2-shorts report runs/<id>` (tokens, cache share) and CP3 rejection notes before vs after.

References: Claude Code [skills](https://code.claude.com/docs/en/skills) ·
[subagents](https://code.claude.com/docs/en/sub-agents) · [hooks](https://code.claude.com/docs/en/hooks) ·
[plugins](https://code.claude.com/docs/en/plugins) · [settings](https://code.claude.com/docs/en/settings) ·
[sandboxing](https://code.claude.com/docs/en/sandboxing) · [CLAUDE.md](https://code.claude.com/docs/en/memory) ·
[agent skills spec](https://agentskills.io/specification).
