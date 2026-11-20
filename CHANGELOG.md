# Changelog

## 0.6.0 — 2026-11-20
Naming standardisation; no behaviour change. Rules, vocabulary, full mapping and exceptions:
`docs/naming-conventions.md`.
- **Modules**: `app/pipeline.py` → `app/cli.py`, `app/clips.py` → `app/run_steps.py`, `app/check.py` →
  `app/clip_gates.py`, `app/speech.py` → `app/narration.py` (the Polly/Google synthesizers moved there too),
  `app/graph/models/` → `app/outline_models/`.
- **Folders and docs**: `env/` → `run-environment/` (plugin `t2s-env` → `text-2-shorts-run-environment`), `prompts/` →
  `docs/proposed-stages/`, `Plan.md` → `docs/architecture-plan.md`, every Markdown file in kebab-case.
- **Identifiers**: descriptive names for module constants, functions and ~400 locals across `app/`, `tools/`,
  `schemas/` and `tests/` (e.g. `LEAD_IN` → `VOICE_LEAD_IN_SECONDS`, `jail_cmd` → `build_jail_command`).
- **`TASK.json`**: `clip`/`class`/`seconds` → `clip_name`/`scene_class_name`/`clip_seconds`.
- **Tooling**: Ruff (format + lint, line length 120) as a dev dependency; Pyrefly search paths configured.
- **The command is `text-2-shorts`** (was `t2s`), and the `t2s` prefix is gone everywhere: skills
  `text-2-shorts-produce`, `text-2-shorts-clip-debugging`, `text-2-shorts-prompt-maintenance`; environment variables
  `TEXT_2_SHORTS_FPS`, `_PARALLEL`, `_TTS` (and the internal `_BACKGROUND`, `_TARGET_CLIP`, `_STOP_AFTER`); API index
  cache `~/.cache/text-2-shorts/`.
- **Migration**: `uv sync` installs the `text-2-shorts` entry point and removes `t2s` (`uv run` does it
  automatically). Rename `T2S_FPS`, `T2S_PARALLEL`, `T2S_TTS` in your `.env` to `TEXT_2_SHORTS_…` (old names are
  ignored). Anything calling `python -m app.pipeline` uses `python -m app.cli`. A clip folder prepared by 0.5 needs
  `text-2-shorts task <run> <clip>` again before `text-2-shorts accept`. Runs, state, feedback and logs are unchanged;
  a run session started before the update must be reopened (`text-2-shorts open`) to load the renamed skills.

## 0.5.0 — 2026-11-20
Claude Code-native execution (Plan.md §30).
- **Inverted control**: no Python orchestrator and no `claude -p` per stage. One interactive Claude Code session per
  run writes the outline and clip plans and dispatches two subagents (clip-builder per clip, math-reviewer).
- **Environment as code** (`env/`): a Claude Code plugin (workflow skill + references, subagents, hooks), session
  settings (sandbox + permissions) and the per-run CLAUDE.md. All prompts moved there verbatim from Python.
- **Per-run isolation**: `t2s new` provisions `runs/<id>/`; `t2s open` runs Claude Code in a bubblewrap jail where only
  the run folder (plus Claude Code's own state/caches) is writable and `$HOME` is private.
- **Deterministic commands** for the session: `t2s validate`, `task`, `accept`, `hook`, `report`; `status` lists the
  next steps. Hooks: session start → status; every tool call → log; written outline/plan/math → validated.
- **Removed**: `pipeline.claude()`, the LLM result cache, limit waits, `STAGES`, `t2s outline/clips/build`,
  `app/graph/prompts/`, `app/sandbox.json` (→ `env/settings.json`).

## 0.4.0 — 2026-11-20
- **Voice providers: AWS Polly or Google Cloud TTS**, chosen per video (`t2s new --tts polly|google`, `--voice`,
  `--engine` for Polly). Google uses SSML `<mark>` timepoints for word timings (beat sync) and falls back to plain text
  for voices without SSML (e.g. Chirp 3 HD). `new` checks the chosen provider's credentials.
- **Removed Kokoro** (engine, model download/SHA pin, `kokoro-onnx` dependency).

## 0.3.0 — 2026-11-20
- **Shared rules sent once**: `VIDEO_STANDARDS` + ELI5/Feynman `EXPLANATION_STYLE` in every stage's static (cached)
  system prompt; always-on Manim topic cards moved into the clip agent's system prompt, so `API_CARDS.md` holds only
  clip-specific cards.
- **Consistency**: palette roles, type scale, zones and timing standards; each symbol keeps one colour across the
  video (`color_roles` carried scene to scene).
- **Explanation style**: ELI5/Feynman rules in the outline and clip-planner prompts.
- **Audio–visual sync**: 0.3 s visual lead-in and ≥ 0.8 s hold per clip; `[pause]` markers; with Polly, beat start
  times from word speech marks in `TASK.md`.
- **Scene transitions**: scenes start and end on an empty frame (enforced; a violating plan is sent back once); the
  last clip transitions out, the next scene re-draws the previous final image. Fixes a latent crash when a plan
  carried objects across scenes.
- **Speech** (`app/speech.py`): symbols in backticks spoken by name, Greek letters, math symbols, units after
  numbers, abbreviations, M-vs-m disambiguation; Polly SSML with plain-text fallback and word marks; Polly neural is
  the default engine; `new` checks AWS credentials.
- **Fixes**: final assembly no longer re-encodes to 30 fps (media checks now verify ≥ 60 fps); `.env.example` no
  longer overrides real AWS credentials with placeholders.

## 0.2.0 — 2026-11-20
Clip-level pipeline (Plan.md roadmap P2–P14, smallest forms; see the status note in `docs/MODULE_SPECS.md`).

- **Clip-level generation**: scenes are planned as 4–20 s clips (`t2s clips`) with Pydantic-validated continuity
  contracts and a math verifier; narration audio per clip (`t2s voice`); one sandboxed agent per clip writes one
  file, gated by `./check` (validator → layout/timing probe → section render → frames) and re-checked in a jail
  before it is accepted (`t2s build`); final per-scene render with one Manim section per clip, per-clip A/V sync,
  EBU R128 loudness and media checks (`t2s final`).
- **Human checkpoints**: `t2s approve outline | plan | sNN | final`; scoped `t2s feedback`; `t2s status`. Only what
  changed is rebuilt (content-hash keys cascade through each scene's clips).
- **Runner**: identical non-agent calls answered from `.cache/llm/`; rate/overload backoff; usage limits waited out
  to their reset time; structured start/end log rows with full token breakdown.
- **Output**: always 2560×1440, `T2S_FPS` 60–120, chosen font, one background for every clip.
- **Prompt caching**: byte-identical system prompts; per-call data only in the user message.
- **`t2s` command**, GitHub Actions CI, deterministic outline length check, preflight before `new`, Kokoro SHA-256
  pin, hardened agent sandbox.
- **Removed**: the scene-level Director DSL path (`tts`, `plan`, `render`, `assemble`), its prompts and the
  hand-written Manim catalogues; spend budgets; unused dependencies, configs and vendored skills.
