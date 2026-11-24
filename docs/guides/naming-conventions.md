# Naming conventions

> **Current layout (0.13):** `backend/` (app, schemas, tools), `runtime-environment/`, `artifacts/` (runs, reports, trash), `docs/`, `tests/`, `frontend/` — see `docs/PROJECT_STRUCTURE.md`. The tables below record the names of their time.

The rules every name in this repository follows, the project vocabulary, what was renamed in 0.6.0, and the
deliberate exceptions. Goal: every name says what the thing holds or does, in one reading, without being longer than
that needs.

## Rules

| Kind | Convention | Examples |
|---|---|---|
| Python module, package | `snake_case`, a noun for what it holds | `change_requests.py`, `clip_gates.py`, `outline_models/` |
| Function, method | `snake_case`, starts with a verb | `load_scene_plans`, `build_jail_command`, `check_final_media` |
| CLI subcommand handler | `handle_<subcommand>_command` | `handle_voice_command`, `handle_open_command` |
| Predicate | `is_…` / `has_…` | `is_approval_current`, `is_text_like` |
| Class, Pydantic model | `PascalCase` noun | `ScenePlan`, `MathFinding`, `Validator` |
| Module constant | `UPPER_SNAKE_CASE` with its unit or kind | `VOICE_LEAD_IN_SECONDS`, `API_INDEX_PATH`, `TOOLS_DIRECTORY` |
| Variable, parameter | `snake_case` noun for the value | `scene_directory`, `audio_index`, `clip_states` |
| Paths | suffix `_path` (file) or `_directory` (folder) | `state_path`, `work_directory` |
| Durations | suffix `_seconds` (or `_ms` when milliseconds) | `clip_seconds`, `end_seconds`, `time_ms` |
| Test | `test_<behaviour in words>` | `test_state_updates_are_safe_across_processes` |
| Project prefix | the project name, never an abbreviation | command `text-2-shorts`, skill `text-2-shorts-produce`, `TEXT_2_SHORTS_FPS` |
| Markdown file | `kebab-case.md` | `architecture-plan.md`, `deployment-guide.md` |
| Folder (non-Python) | `kebab-case` | `run-environment/`, `proposed-stages/` |
| JSON key, TOML key | `snake_case` (every reader is Python) | `clip_seconds`, `scene_class_name` |
| Environment variable | `UPPER_SNAKE_CASE`, prefixed by owner | `TEXT_2_SHORTS_FPS`, `POLLY_VOICE`, `GOOGLE_VOICE` |

Short names are allowed only where they are the convention: `i`/`j` loop indices, `x`/`y`/`z` coordinates, `_` for an
ignored value, `cls`/`self`, `np` for numpy, `argv`. No other single letters, and no abbreviations a reader has to
decode (`sd`, `mm`, `st`, `fp`, `idx`, `kw`, `rc`, …).

Formatting: `uv run ruff format` (line length 120, quotes preserved). Lint: `uv run ruff check --select E,F,W`.
Types: `uv run pyrefly check app tools schemas tests`.

## Vocabulary (one term per concept)

| Term | Meaning | Form |
|---|---|---|
| run | one video's workspace folder `runs/<id>/` (a `Path`, named `run` everywhere) | `runs/20261120-…-topic` |
| run environment | the Claude Code plugin + settings every run session loads | `run-environment/` |
| scene id | a scene's identifier | `s01` |
| clip id | a clip's identifier | `s01c02` |
| clip name | a clip's file/method name | `clip_02` |
| brief | stage 1: the user's requirements | `brief.json` |
| script | stage 2: every scene's objective, key concepts, duration, bridge and complete narration | `script.json` |
| bridge | the spoken scene-to-scene transition at the start of a scene | `bridge_in` |
| scene plan / clip plan | stage 3: `ScenePlan` / `ClipPlan` contracts (scene visual plan split into clips) | `scenes/s01/plan.json` |
| accuracy review | independent check of the script (per scene) or plans (per clip) | `script_review.json`, `plan_review.json` |
| index scene | s01: what the video covers | `role: "index"`, `previews` |
| topic list / content | the request modifier's numbered topics / the educational text the outline is built from | `topics.md` / `content.md` |
| outline | stage 2: segments with type, timing, talking points, visual plan (CP0) | `outline.json` |
| change request | one tweak the user asked for, open until applied or declined | `requests.jsonl`, `rNNN` |
| checkpoint decision | how the user decided at a checkpoint | `decisions.jsonl` |
| preferences | standing settings applied at every stage | `preferences.json` |
| critique round | one review by the script-critic (one per change asked at CP1), plan-critic or video-critic (≤ 3 scored rounds per scene) | `script_critique.json`, `plan_critique.json`, `video_critique.json` |
| change record | what one video refactor iteration changed | `scenes/sNN/changes.json` → `changes.txt` |
| template | the video's look and motion: a starter template + the user's tweaks | `template.json`, `template_preview.svg` |
| beat mark | where a clip's animation starts beat n | `self.beat(n)` |
| entry object | an object a clip takes over from the previous clip; re-created from its description when the clip runs alone | `self.entry(name, make)`, `descriptions` |
| batch | the exact next set of actions the driver hands out | `text-2-shorts next` |
| sync report | per beat: spoken vs shown time — the changes-made document | `sync.json` |
| preview | a scene at 720p30 with audio | `preview.mp4` |
| work directory | the clip-builder's prepared folder | `scenes/s01/work/clip_02/` |
| audio index | `scenes/sNN/audio/index.json` (narration hash → seconds, beat times) | |
| state | `state.json`: approvals, clip states, session transcripts | |
| clip key / fingerprint | hash of a clip's inputs / of several clips' keys | |
| finding | one `{severity, code, message, …}` result of a check | |
| gate | one `./check` step: static, probe, render, frames | |
| speech synthesizer | function `text → (mp3 bytes, word marks)` for Polly or Google | |

## Renamed in 0.6.0

**Files and folders**

| Before | After | Why |
|---|---|---|
| `app/pipeline.py` | `app/cli.py` | it is the `text-2-shorts` CLI (provision + jail); no pipeline left |
| `app/clips.py` | `app/run_steps.py` | holds every run-level step, not only clips |
| `app/check.py` | `app/clip_gates.py` | the `./check` gates of one clip |
| `app/speech.py` | `app/narration.py` | narration text, SSML, timings, and now the Polly/Google synthesizers |
| `app/graph/models/base_models.py` (+ 3) | `app/outline_models/base_outline.py` (+ 3); removed in 0.7.0, restored in 0.10.0 for the outline stage | outline schemas; LangGraph is gone |
| `env/` | `run-environment/` | `env/` read as a virtualenv and was git-ignored by that rule |
| `prompts/*.md` | `docs/proposed-stages/*.md` (kebab-case) | specs for stages not built, not prompts |
| `Plan.md` | `docs/architecture-plan.md` | kebab-case, with the other docs |
| `docs/MODULE_SPECS.md`, `DEPLOYMENT.md`, `SKILLS_ASSESSMENT.md` | `module-specifications.md`, `deployment-guide.md`, `skills-assessment.md` | kebab-case |
| `reference/SOURCES.md`, `audit-evidence/prompt_sizes.md`, `prompt_catalog_audit.json` | `sources.md`, `prompt-sizes.md`, `prompt-catalog-audit.json` | kebab-case |
| `tests/test_env.py` | `tests/test_run_environment.py` | matches the folder it tests |
| plugin `t2s-env` | `text-2-shorts-run-environment` | matches the folder |
| command `t2s` | `text-2-shorts` | the project name instead of an abbreviation |
| skills `t2s-produce`, `t2s-clip-debugging`, `t2s-prompt-maintenance` | `text-2-shorts-produce`, `text-2-shorts-clip-debugging`, `text-2-shorts-prompt-maintenance` | same |
| `T2S_FPS`, `T2S_PARALLEL`, `T2S_TTS`, `T2S_BACKGROUND`, `T2S_TARGET_CLIP`, `T2S_STOP_AFTER` | `TEXT_2_SHORTS_…` | same |
| `~/.cache/t2s/` | `~/.cache/text-2-shorts/` | same |

**Module-level names** (functions and constants other modules use)

| Module | Before → after |
|---|---|
| `app/cli.py` | `ROOT` → `REPOSITORY_ROOT` · `ENV` → `RUN_ENVIRONMENT` · `PYTHON` → `PYTHON_EXECUTABLE` · `FPS` → `FINAL_FRAME_RATE` · `MAX_PARALLEL` → `MAX_PARALLEL_RENDERS` · `CACHE` → `USER_CACHE_DIRECTORY` · `BWRAP` → `RENDER_JAIL_PREFIX` · `parallel` → `run_in_parallel` · `probe_seconds` → `probe_duration_seconds` · `cmd_new`/`cmd_open` → `handle_new_command`/`handle_open_command` · `jail_cmd` → `build_jail_command` · `provision` → `provision_run_workspace` |
| `app/narration.py` | `tts_for` → `create_speech_synthesizer` · `polly_tts` → `create_polly_synthesizer` · `google_tts` → `create_google_synthesizer` (moved here from `pipeline.py`) |
| `app/clip_gates.py` | `TOOLS` → `TOOLS_DIRECTORY` · `PY` → `PYTHON_EXECUTABLE` · `save` → `save_gate_result` · `run` → `run_tool` · `compose` → `compose_scene` |
| `app/run_steps.py` | `MANIM` → `MANIM_VERSION` · `TOOLS` → `TOOLS_DIRECTORY` · `TOPICS_DIR` → `TOPICS_DIRECTORY` · `API_INDEX` → `API_INDEX_PATH` · `ALWAYS_TOPICS` → `ALWAYS_LOADED_TOPICS` · `STYLE` → `VIDEO_STYLE` · `LEAD_IN` → `VOICE_LEAD_IN_SECONDS` · `HOLD` → `END_HOLD_SECONDS` · `AGENT_FILE` → `CLIP_BUILDER_AGENT_PATH` · `STANDARDS` → `STANDARDS_PATH` · `sha` → `content_hash` · `_errors` → `format_validation_errors` · `scene_plans` → `load_scene_plans` · `approved_current` → `is_approval_current` · `find_clip` → `load_clip_plan` · `media_checks` → `check_final_media` · `session_tokens` → `sum_session_tokens` · `find_run` → `find_run_directory` · `register` → `register_subcommands` · `_abs` → `resolve_run_path` · `cmd_<x>` → `handle_<x>_command` · removed unused `sid_of` |
| `tools/layout_probe.py` | `TEXTY` → `TEXT_CLASS_NAMES` · `bbox` → `bounding_box` · `is_texty` → `is_text_like` · `visible` → `max_opacity` · `inter` → `intersection_area` |
| `tools/validate_manim_code.py` | `REMOVED` → `REMOVED_APIS` · `PY_COMMON_METHODS` → `PYTHON_BUILTIN_METHODS` · `reg_access` → `registry_access` · `Validator.add`/`collect` → `add_finding`/`collect_definitions` |
| `tools/scene_harness.py` | `compose` → `compose_scene` · `render` → `render_scene` · `PORTRAIT_RES` → `PORTRAIT_RESOLUTIONS` |
| `tools/assemble_clips.py` | `probe` → `probe_duration_seconds` · `concat` → `concatenate_videos` |
| `tools/doc_cards.py` | `COMMON` → `COMMON_METHODS` · `card` → `api_card` · `method_sig` → `method_signature` |
| `tools/build_manim_api_index.py`, `tools/preflight.py` | `_sig` → `_signature` · `ver` → `detect_version` |
| `tests/conftest.py` | `ROOT`/`TOOLS`/`FIX` → `REPOSITORY_ROOT`/`TOOLS_DIRECTORY`/`FIXTURES_DIRECTORY` · `run` → `run_tool` |

Local variables and parameters (about 400) follow the vocabulary above: `a` → `arguments`, `ap`/`sub`/`p` →
`parser`/`subparsers`/`command_parser`, `sd` → `scene_directory`, `mm` → `clip_name`, `w` → `work_directory`,
`st` → `state` or `clip_states`, `idx` → `audio_index`, `sid` → `scene_id`, `c`/`p` → `clip`/`plan`,
`f` → `finding`/`path`, `rc`/`out` → `exit_code`/`output`, and so on.

**Data keys**

| Where | Before → after |
|---|---|
| `TASK.json` (written by `text-2-shorts task`, read by `./check`) | `clip` → `clip_name` · `class` → `scene_class_name` · `seconds` → `clip_seconds` |
| argparse namespace | `cmd` → `subcommand` · `fn` → `handler` |

## Exceptions (kept on purpose)

| Name | Why it stays |
|---|---|
| `text-2-shorts` subcommands and flags, `./check` gate names | the public CLI; scripts and the run sessions' skills use them |
| `POLLY_*`, `GOOGLE_*`, `GOOGLE_APPLICATION_CREDENTIALS` | names the providers' own tools use |
| `T2S_MODEL`, `T2S_QUALITY`, `t2s_helpers` in the architecture plan | settings of the retired app, kept as history |
| `ScenePlan`/`ClipPlan` field names (`est_seconds`, `color_roles`, …) and `schemas/json/` | contracts shared with the run environment's references and with plans already written |
| keys in files that runs already hold: `state.json` (`at`), `log.jsonl` (`ts`), audio `index.json` (`seconds`), tool JSON outputs (`t`, `duration_s`, `final_s`, `stderr_tail`) | renaming would split existing runs into two formats; every key is documented where it is written |
| `run` for the run folder | the project's core noun; always typed `Path` |
| `README.md`, `CHANGELOG.md`, `CLAUDE.md`, `SKILL.md` | names required by tooling or universal convention |
| historical records (the architecture plan's audit of the original app, everything under `docs/history/`, older `CHANGELOG.md` entries, the dated lists in `docs/changes/`) | records of how the code looked at that time |
| `Agentic_Mathematical_Video_Generation_Implementation_Plan.md` | the source document's own name |
| `tests/fixtures/bad_scene.py` | intentionally broken input for the validator |
