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
| `index.html`, `vite.config.ts`, `tsconfig.json`, `package.json` | React 19 + Vite + TypeScript. `npm ci && npm run build` → `dist/` (served by FastAPI); `npm run dev` → live reload on :5173, API proxied to :8765 |
| `src/main.tsx` | Mount; imports the five stylesheets in order |
| `src/app/` | `App.tsx` (session, frame, route table), `routes.ts` (hash routes, `navigate`, `useHashRoute`: focus and scroll on page change), `session.tsx` (account, sign-in/out, `fail`) |
| `src/config/` | `stages.tsx` (stages, steps, names), `status.tsx` (one status vocabulary: word, icon, fill), `quotes.ts` (verified Faraday quotations), `media.ts` (aspect-ratio presets, waveform limits) — decisions in `docs/DESIGN_REFERENCE.md` |
| `src/services/` | `http.ts` (one request core: `load`, `loadText`, `send`, `streamTurn`; `ApiError`, `SignedOut`), `runs.ts` (paths: `runPath`, `mediaUrl`, `runHash`, `starterPreview`), `log.ts` (the frontend's logging → `POST /api/logs`) |
| `src/types/api.ts` | The API's Pydantic contracts as TypeScript types |
| `src/hooks/` | `useApi` (cancellable, kept while reloading), `useAction` (busy + one message per write), `useRuns`, `useRunFile` |
| `src/components/ui/` | `Button` + `LinkButton`, `fields` (Field, SelectField, Checkbox, Toggle, RadioCards), `Tabs`, `pickers` (colour, gradient), `icons` (Untitled UI), `text` (`titleCase`), `Markdown` (+ `plainText`, `runTitle`), `MarkdownField` in `fields` |
| `src/components/layout/`, `navigation/` | `Shell` (one-tier header, footer, skip link), `Page`/`PageHeader`/`Section`/`SectionHeader`; `Breadcrumbs`, `ProgressSteps` (horizontal, vertical) |
| `src/components/feedback/` | `SystemMessage` (every non-content state: 11 kinds, told apart by label, icon and border), `Notice` (persistent live regions), `ProgressBar`, `StatusPill`, `Overlay` (Modal, Drawer) |
| `src/components/media/` | `ImagePreview` (`MediaImage`, `ExpandImage`), `VideoPreview`, `AudioPreview` (waveform): one box model with loading, empty and unavailable states |
| `src/pages/` | `Home`, `NewRun`, `RunList`, `SignIn`; `run/` — `RunPage` (rail + stage), `ClaudePanel` (what Claude says and asks, with a reply), `context.tsx`, `Console`, `ChangeModal`, `CheckpointPanel`, `review.tsx`, `stages/` (`StageTabs`, `look/` (Template: `useTemplateEditor`, shared with Start a Run), `Requirements`, `Writing`, `Production`, `Reshuffle`) |
| `src/styles/` | `tokens.css` (every colour, space, radius, type role, height, icon, width, layer and duration), `base.css`, `layout.css`, `components.css`, `motion.css` (the motion contract). Black, white and greys only; tests scan them |

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
| `workflow/templates.py` | Choosing and saving `template.json` (starter + element choices + custom values), the Look & sound catalogue; look and sound come from `video_settings` / `audio_settings` |
| `workflow/reshuffle.py` | The optional last stage: a seeded reshuffle of the look applied without Claude (clips recoloured and re-keyed, old final kept in `versions/`) |
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
| `template_kit/` | The template kit as given: `elements.json` (22 look-and-sound elements and their options), `templates/*.json` (7 starters), `gallery/*.png` (every option rendered, dark and light), its Python (`template_kit.py`, `gallery.py`, `narration.py`, `install_fonts.py`, `example_scene.py`; not run by the pipeline yet) |
| `faraday_logging.py` | Logging for backend, frontend and runtime in one format: `configure(component, run)`, `channel("frontend")` |
| `video_settings.py` | The look from `template.json`: background, colour roles, font, text sizes, safe area; checks (contrast); the TEMPLATE block of every TASK.md |
| `audio_settings.py` | The sound from `template.json`: voice per provider, speaking rate, pauses, narration tone |
| `look_renderer.py` | Our Manim drawing of a look (backdrop, grids, borders, text, maths, a subtitle line): previews and the backdrop behind every clip |
| `generate_preview.py` | Fonts; the starter stills; every option drawn in the user's look (`option_in_look`, lossless, cached; `warm` pre-renders each starter's in both modes); the whole look; a voice sample |
| `previews/starters/<name>.webp` | Each starter template as one 2560×1440 frame (the Template gallery). Option previews are drawn in the user's own look and cached in `~/.cache/text-2-shorts/previews` (`generate_preview.py warm` pre-renders every starter's) |
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
`backend/app/cli.py`. A new screen: a component in `frontend/src/`, fed by a view model in `backend/schemas/api.py` (typed in `src/api.ts`).
