# Project structure

Text-2-Shorts turns a topic into a narrated Manim explainer video. A Claude Code session does the reasoning inside an
isolated run workspace; the `text-2-shorts` command does every deterministic step: validation, ordering, voice,
rendering, assembly, and the web view. No Python code calls a language model. Every file and payload that
crosses a boundary has a Pydantic contract in `backend/schemas/`.

## Top level

| Folder | Holds |
|---|---|
| `frontend/` | The web UI (black, after armakuni.com's dark sections; Geist type): sign-in with Claude, runs, where a run stands, what happens next, approvals, change requests, previews, the final video |
| `backend/` | `app/` (the `text-2-shorts` command), `schemas/` (Pydantic contracts), `tools/` (standalone scripts) |
| `runtime-environment/` | The Claude Code execution environment of a run: agents, skills, references, templates, hooks, settings |
| `artifacts/` | Generated output: `runs/` (one folder per video, git-ignored), `reports/` (repository reports), `trash/` (files awaiting deletion, git-ignored) |
| `docs/` | This file, `guides/`, dated `changes/`, `diagrams/`, and `history/` (superseded designs) |
| `tests/` | The deterministic test suite and its fixtures |

At the root: `README.md`, `CHANGELOG.md`, `pyproject.toml` + `uv.lock` (dependencies, entry point, tool settings),
`.env.example` (the environment variables; never commit `.env`), `.github/workflows/ci.yml` (`uv run pytest -q`).

## `frontend/`

| File | Responsibility |
|---|---|
| `index.html` | The page shell: bar, main area, footer; loads Geist and Geist Mono (the fonts of armakuni.com) |
| `styles.css` | Fraunces for headings, Geist to read, Fira Code (Retina, 450) for the terminal-style interaction layer (console, forms, panels). A black page with night-2 cards, white type and white pill buttons, greys only (armakuni.com's dark tokens); no transitions or animations (tests enforce both) |
| `app.js` | Hash routes `#/signin`, `#/` (runs and the `faraday new` form) and `#/runs/<run>` (header, console, approvals, scenes, final, changes); DOM nodes only (never HTML strings) |

Served by `text-2-shorts serve` at `http://127.0.0.1:8765`. The user can approve checkpoints (with notes, or anyway
with open problems, recorded as forced), record change requests and mark them applied or declined. These go through the
same workflow functions as the CLI, so a decision made on the page is the same as one made in the run's session.

## `backend/app/` — the command

Execution and implementation are separate: `cli.py` parses, `commands/` executes one command each, `workflow/` holds
the logic they share.

| Module | Responsibility |
|---|---|
| `cli.py` | **Entry point** (`text-2-shorts = app.cli:main`): the argument parser and dispatch |
| `config.py` | Every setting: paths, environment variables, models and effort, standard style, timing, quality, limits |
| `utilities.py` | Shared helpers: JSON, hashing, timestamps, JSONL, ffprobe duration, thread pool, error formatting |
| `sandbox.py` | Isolation: the run-session jail, the render jail prefix, the Claude Code session command |
| `narration.py` | Speech: speakable text and SSML, word timings → beat times, AWS Polly and Google synthesizers |
| `commands/run_commands.py` | `new` (preflight, credentials, provision a run) · `open` (start the jailed session) |
| `commands/workflow_commands.py` | `next` · `status` · `report` · `validate` · `hash` · `doc` · `approve` · `feedback` · `resolve` |
| `commands/production_commands.py` | `voice` · `accept` · `preview` · `final` |
| `commands/hook_command.py` | The Claude Code hook: SessionStart and PostToolUse |
| `commands/serve_command.py` | `serve`: runs the FastAPI app with uvicorn on 127.0.0.1 |
| `web/app.py` | The FastAPI app: frontend files, `/api/session`, runs, approvals, change requests, media (Range); host, origin and JSON checks; Pydantic request/response models |
| `web/console.py` | The console: one turn of the run's Claude Code session per message (Claude Code in print mode with `--resume`, in the run jail), streamed as `ConsoleEntry` lines and kept in `console.jsonl`; one turn at a time per run |
| `web/auth.py` | Sign-in with the Claude account Claude Code is signed in to (`claude auth status --json`); in-memory sessions in an HttpOnly, SameSite=Strict cookie |
| `workflow/ledger.py` | `state.json` (`RunState`) under a lock, JSONL files, checkpoint decisions |
| `workflow/change_requests.py` | Change requests: `record_change_request()`, resolve, route to the stage that applies them, block checkpoints |
| `workflow/preferences.py` | Standing preferences and the speech settings they control |
| `workflow/templates.py` | Template library, `template.json` + overrides, preview, video style and font |
| `workflow/artifacts.py` | Typed loaders: brief, topics, outline, script, plans, audio index, gate results, sync report, final report |
| `workflow/fingerprints.py` | What approvals and clip builds depend on |
| `workflow/checkpoints.py` | Checkpoint gates; scenes in series |
| `workflow/validation.py` | Validators for brief, topics, content, outline, script, plans, accuracy reviews |
| `workflow/critiques.py` | Critique rounds, scores, the script rule, the refactor log |
| `workflow/clips.py` | The clip-builder task folder (`TASK.json` = `ClipTask`) and jailed acceptance (`ClipBuild`) |
| `workflow/production.py` | Stale audio, scene renders, preview sync report, assembly manifest, delivery checks |
| `workflow/approvals.py` | What blocks an approval; `approve_checkpoint()` (CLI and web) |
| `workflow/driver.py` | The next batch of work (`ActionBatch`) |
| `workflow/status.py` | Remaining steps, every stage/scene/clip status, token totals |
| `workflow/run_workspace.py` | Creating a run workspace; finding a run from a path |
| `workflow/run_views.py` | Views for the frontend (`RunSummary`, `RunDetail`, the checkpoints waiting for the user) |

**Dependency layers** (a module imports only from layers above it; no import cycles):

```
config → utilities → sandbox
       → workflow: ledger → change_requests → preferences → artifacts → templates → fingerprints → checkpoints
                   → validation → critiques → production → clips → approvals → driver · status · run_workspace
                   → run_views
       → web (auth · app)
       → commands (run · workflow · production · hook · serve) → cli
```

## `backend/schemas/` — the contracts

| Module | Contracts | Files |
|---|---|---|
| `base.py` | `Strict` base (extra fields rejected), id types, severity | — |
| `requirements.py` | `Brief`, `Preferences`, `VideoTemplate`, `EnvironmentReport` | `brief.json`, `preferences.json`, `template.json`, `environment_report.json` |
| `outline_models/` | one outline model per approach | `outline.json` |
| `script.py` | `Script`, `ScriptScene` | `script.json` |
| `plans.py` | `ScenePlan`, `ClipPlan`, `ContinuityState`, `SoundEffect` | `scenes/sNN/plan.json` |
| `reviews.py` | `ReviewReport`, `Critique`, `ChangeRecord`, `ChangeLog` | reviews, critiques, `changes.json` |
| `interaction.py` | `ChangeRequest`, `RequestEvent`, `ResolutionEvent`, `TrackedRequest`, `CheckpointDecision` | `requests.jsonl`, `decisions.jsonl` |
| `run_state.py` | `RunState`, `Approval`, `ClipBuild`, `LogEntry`, `TokenUsage`, `Status` | `state.json`, `log.jsonl` |
| `media.py` | `ClipAudio`/`AudioIndex`, `ClipTask`, `GateResult`, `SceneRender`, `SyncReport`, `AssemblyManifest`, `FinalReport`, `MediaFinding` | audio index, `TASK.json`, `checks/*.json`, `sync.json`, `assembly.json`, `final_report.json` |
| `session.py` | `Action`, `ActionBatch`, `HookEvent`, `HookOutput` | `next --json`, hook stdin/stdout |
| `api.py` | `ClaudeAuthStatus`, `ClaudeAccount`, `SessionView`, `RunSummary`, `RunDetail`, `SceneView`, `ClipView`, `CheckpointView`, `ApproveInput`, `ChangeRequestInput`, `ResolveInput`, `ApiError` | the frontend API |
| `unused_contracts.py` | contracts of a design never built, kept until their removal is approved | — |
| `export_json_schemas.py` → `json/` | JSON Schema of every live contract | `json/<Model>.schema.json` |

Raw JSON is read in only three places, on purpose: fingerprints hash file content, and ffprobe output and Claude
Code transcripts are formats this project does not own.

## `backend/tools/` — standalone scripts

| Script | Run by |
|---|---|
| `clip_gates.py` | `./check` in a clip folder; `accept` re-runs it in the render jail (reads `ClipTask`, writes `GateResult`) |
| `validate_manim_code.py`, `layout_probe.py`, `scene_harness.py` | `clip_gates.py`, `preview`, `final` |
| `doc_cards.py`, `build_manim_api_index.py` | `task`, `doc`, `./check doc` (symlinked from the Manim skill) |
| `assemble_clips.py` | `final`, `preview` (validates the `AssemblyManifest`) |
| `preflight.py` | `new` (writes an `EnvironmentReport`) |
| `cost_report.py`, `audit_prompt_catalog.py`, `check_diagrams.mjs` | nothing in the workflow (see `artifacts/reports/unused-files-inventory.md`) |

## `runtime-environment/` — what a run session reads

| Path | Responsibility |
|---|---|
| `.claude-plugin/plugin.json` | The plugin manifest (`--plugin-dir`) |
| `settings.json` | Session sandbox and permissions (`--settings`) |
| `hooks/hooks.json` | SessionStart and PostToolUse → `text-2-shorts hook` |
| `workspace/CLAUDE.md` | The instructions copied into every run |
| `agents/*.md` | One file per subagent: script-writer, scene-planner and clip-builder (Opus: builders and refactors); critics, accuracy-reviewer, audio-refactorer (Sonnet). The session itself runs on Haiku |
| `skills/text-2-shorts-produce/` | The workflow skill; `references/` = one guide per stage, read by path |
| `skills/manim-ce-0-20-1-reference/` | Manim topic cards; `scripts/` link to `backend/tools/` |
| `templates/*.json` | Starter video templates (logic: `backend/app/workflow/templates.py`) |
| `prompts/` | The topic-list and outline prompts as Python, exported to `references/` by `export_references.py` |

## A run workspace (`artifacts/runs/<id>/`)

| Path | Written by |
|---|---|
| `brief.json`, `topics.md`, `content.md`, `preferences.json`, `template.json` | Stage 1 (session; `new`, `template`) |
| `outline.json` → `script.json`, `script_review.json`, `script_critique.json` | Stages 2–3 |
| `scenes/sNN/plan.json`, `plan_critique.json`, `plan_review.json` | Stage 4 (scene-planner, critics) |
| `scenes/sNN/audio/` | `voice` |
| `scenes/sNN/work/clip_MM/` → `scenes/sNN/clips/` | `task`, clip-builder, `accept` |
| `scenes/sNN/preview.mp4`, `sync.json`, `video_critique.json`, `changes.json` | `preview`, critics, refactors |
| `final.mp4`, `final_report.json`, `assembly.json` | `final` |
| `state.json`, `requests.jsonl`, `decisions.jsonl`, `log.jsonl`, `changes.txt` | ledger, `feedback`, `approve`, the hook |

## Where a change belongs

A setting: `backend/app/config.py`. A new file or payload: a contract in `backend/schemas/` first. A
new command: a handler in `backend/app/commands/`, logic in `backend/app/workflow/`, the parser entry in
`backend/app/cli.py`. A new screen: `frontend/app.js`, fed by a view model in `backend/schemas/api.py`.
