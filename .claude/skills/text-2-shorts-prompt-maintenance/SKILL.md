---
name: text-2-shorts-prompt-maintenance
description: Use when changing how Text-2-Shorts behaves — tone or explanation style, requirements, script rules or narrative structures, scene visual planning or transitions, clip-building instructions, subagents and their models, hooks, session sandbox or permissions, schemas, validators or topic cards — or when improving output quality or token use.
---

# Changing the run environment

The run session's behaviour lives in `runtime-environment/` (a Claude Code plugin + settings); what it must produce is checked by
schemas and validators in `backend/app/`. Change both sides together and prove it with tests.

## Where each kind of change lives
| Change | Files (all of them) |
|---|---|
| Tone / explanation style | ask first: for every video → `runtime-environment/skills/text-2-shorts-produce/references/standards.md` (EXPLANATION STYLE); for one run → `--notes` or the user's request in that session |
| Visual standards (palette, sizes, timing) | `standards.md` **and** `VIDEO_STYLE` / `VOICE_LEAD_IN_SECONDS` / `END_HOLD_SECONDS` in `backend/app/config.py` (a test keeps them equal) |
| Requirements (what is asked at the start) | `references/requirements.md` + `Brief` (`backend/schemas/requirements.py`) + `new` flags (`backend/app/cli.py`; `brief_from_arguments` in `backend/app/workflow/run_workspace.py`) |
| Topic list and outline prompts | `runtime-environment/prompts/script_prompts/` (shared rules in `_shared.py`) → `uv run python runtime-environment/prompts/export_references.py` (a test fails on drift); outline schemas `backend/schemas/outline_models/` + `OUTLINE_MODELS`, rules `validate_outline` (`backend/app/workflow/validation.py`) |
| Change requests, decisions, preferences, templates | `ChangeRequest`, `CheckpointDecision` (`backend/schemas/interaction.py`), `Preferences`, `VideoTemplate` (`backend/schemas/requirements.py`), starter templates `runtime-environment/templates/` + `backend/app/workflow/templates.py`; routing `request_route`, blockers `blocking_requests` (`backend/app/workflow/change_requests.py`), style `video_style` (`templates.py`), speech `clip_speech` (`backend/app/workflow/preferences.py`) |
| Script rules, narrative structures | `references/script-writing.md`, `narrative-structures.md` (a new fixed structure: a section there + `--approach` / `Brief.approach` choices + `make-short` table), `script-review.md`; gate: `Script` + `validate_script` |
| Scene visual + audio planning, transitions | `references/scene-visual-planning.md`, `audio-ssml.md` (SSML tags: `SSML_TAGS` in `backend/app/narration.py`), `transitions.md`; gate: `ScenePlan` + `validate_plan` |
| Models and effort | `SESSION_MODEL`, `PLANNING_AND_CODE_MODEL`, `EFFORT` (`backend/app/config.py`), `session_command()` (`backend/app/sandbox.py`) + `model`/`effort` in each `runtime-environment/agents/*.md` |
| Order of work, batches | `next_actions()` (`backend/app/workflow/driver.py`, the `next` command) + the loop in `text-2-shorts-produce`; series rule `earlier_scene_problem()` (`checkpoints.py`); clips in order `prepare_clip()` (`clips.py`); statuses `update_statuses()` (`status.py`) |
| Critic loops, clip production, sync | rubrics (criterion ids S-/P-/V-, tiers B/G/X) in `runtime-environment/agents/script-critic.md`, `plan-critic.md`, `video-critic.md`; shared tiers, scoring and refactor rules `references/critique-protocol.md` + `CritiqueRound`/`CritiqueIssue` (`backend/schemas/reviews.py`, penalties `TIER_PENALTY`) + `CRITERION_PREFIX`/`ASPECTS` (`critiques.py`); `audio-refactorer.md`; `references/scene-production.md`; rounds `MAX_CRITIQUE_ROUNDS`, score threshold `Preferences.quality_threshold`, script rule `script_critique_problems` (`backend/app/workflow/critiques.py`), refactor log `ChangeRecord`, tolerance `SYNC_TOLERANCE_SECONDS`, draft quality `DRAFT_QUALITY` (`backend/app/config.py`) |
| Stage order, checkpoints | `stage_approval_problem` (`backend/app/workflow/checkpoints.py`) / `next_steps` (`status.py`) / `approval_problems` (`approvals.py`) + the `text-2-shorts-produce` stage table |
| Clip-builder / accuracy-reviewer | `runtime-environment/agents/*.md` (frontmatter `model`, `tools`). A different model for some clips: agree with the user how those clips are chosen (a list, or a field added to `ClipPlan`), add a second agent file, say in `text-2-shorts-produce` when to use it, and add that file to `clip_key` (`CLIP_BUILDER_AGENT_PATH` in `backend/app/config.py`) so its edits mark clips stale |
| Workflow, checkpoints | `runtime-environment/skills/text-2-shorts-produce/SKILL.md` (+ the command handlers in `backend/app/commands/`) |
| Hooks, sandbox, permissions | `runtime-environment/hooks/hooks.json`, `runtime-environment/settings.json`; jail mounts: `build_jail_command` in `backend/app/sandbox.py` |
| Contracts of files and payloads | one module per domain in `backend/schemas/` (map in `docs/PROJECT_STRUCTURE.md`); re-export with `uv run python backend/schemas/export_json_schemas.py` |
| Frontend | `frontend/` (black and white only, no motion: `tests/test_web.py` enforces it); data from `backend/app/workflow/run_views.py` → `backend/schemas/api.py`; served by `backend/app/commands/serve_command.py` |
| Manim knowledge | `runtime-environment/skills/manim-ce-0-20-1-reference/topics/` (examples are executed by tests) |

## Rules
- **Contract first**: never instruct a format a schema or validator rejects; after schema edits regenerate
  `backend/schemas/json/`.
- **Keep always-loaded text small**: `runtime-environment/workspace/CLAUDE.md` and SKILL.md bodies load every session; detail goes in
  a reference named at the step that needs it.
- **No hand-written Manim API lists**: use generated cards and tested topic cards.
- **Editing `runtime-environment/agents/clip-builder.md` marks every clip stale** (it is part of each clip's key): say so first on a
  run in progress.
- **Model choice**: frontmatter `model`; ask the user before switching any agent to a more expensive model.

## Validate
`uv run pytest -q` (layout, schemas, jail, hooks, docs) · `tests/test_topic_cards.py` for topic edits · on a short
test run, compare `uv run text-2-shorts report artifacts/runs/<id>` (tokens, cache share) and CP3 rejection notes before vs after.

References: Claude Code [skills](https://code.claude.com/docs/en/skills) ·
[subagents](https://code.claude.com/docs/en/sub-agents) · [hooks](https://code.claude.com/docs/en/hooks) ·
[plugins](https://code.claude.com/docs/en/plugins) · [settings](https://code.claude.com/docs/en/settings) ·
[sandboxing](https://code.claude.com/docs/en/sandboxing) · [CLAUDE.md](https://code.claude.com/docs/en/memory) ·
[agent skills spec](https://agentskills.io/specification).
