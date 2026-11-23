# Changelog

## 0.9.0 — 2026-11-23
Option B: a deterministic driver for the Claude Code session; scenes produced in series, a scene's clips in parallel.
- **`text-2-shorts next <run> [--json]`** returns the exact next batch — who does what (write, subagent, command,
  ask the user), for which target, reading which files — and whether it runs in parallel. The session start hook
  prints it; the produce skill is now a loop around it.
- **Clips of a scene in parallel**: the harness's `self.entry(name, make)` returns the previous clip's object in the
  composed scene and builds it from `make()` when a clip runs alone, so every clip is built and checked on its own
  (`text-2-shorts task` no longer waits for or copies earlier clips). Plans describe every carried object
  (`ContinuityState.descriptions`, required for entry objects); `./check static` reports `ENTRY_NOT_STANDALONE`.
- **Scenes in series**: `task` and `preview` for a scene refuse to start until every earlier scene passed CP3;
  status and `next` stop at the first open scene.
- **Clip keys** no longer include the previous clip's code: clips are independent, the entry contract is their
  interface; mismatches show in the scene preview and the video critique.
- `clip-structure` topic card, clip-builder, scene-production and scene-visual-planning references updated.

## 0.8.0 — 2026-11-23
Visual and audio planned together, critic-refactor loops, audio re-timed to the built video, 720p30 drafts.
- **Approaches**: three fixed (`zoom`, `arc`, `linear`) and one `creative` (a structure designed for the topic, or the
  user's own); `custom` is gone.
- **Index scene**: `script.json` must open with s01 (`role: "index"`) saying what the video covers; its `previews`
  list every later scene.
- **Audio planned with the visuals**: every clip has `ssml` — exactly its narration words with `<break>`,
  `<prosody rate>`, `<emphasis>`, … (checked: well-formed, allowed tags, same words). `voice` synthesises from it
  (symbols spoken by name, engine-unsupported tags dropped for Polly, one mark per word for Google).
- **Plan critic loop**: `plan-critic` subagent, one combined critic, at most 3 rounds per scene
  (`scenes/sNN/plan_critique.json`); CP2 needs a passing round on each scene's current plan, or the user accepts the
  open issues after round 3.
- **Beat marks**: clips call `self.beat(n)` where beat n starts (harness method; probe gate `BEAT_MARKS_MISSING`);
  the clip-builder writes `CHANGES.md`.
- **Scene preview + sync report**: `text-2-shorts preview <run> sNN` renders the whole scene at 720p30 with audio
  and writes `sync.json` (spoken vs shown time per beat, audio fit, CHANGES.md) — the changes-made document for the
  new `audio-refactorer` subagent, which re-times the SSML (tags only) to the video.
- **Video critic loop**: `video-critic` subagent, at most 3 rounds per scene (`video_critique.json`); CP3 needs a
  current preview, speech in sync with the animation (±0.35 s) and the critique done.
- **Keys**: a clip's code key no longer includes its SSML or audio (re-timing audio does not rebuild clips); CP3 and
  the final render fingerprint include the audio; CP2 ignores SSML-only edits.
- **Resolution**: drafts (`./check render`) and previews at 1280×720, 30 fps; final delivery 2560×1440 at 120 fps by
  default (`TEXT_2_SHORTS_FPS`, 60–120); the media check expects the configured rate.
- **Commands**: `preview`, `hash <run> sNN plan|video`, `doc <Names>`; `validate … plan-critique|video-critique --scene sNN`.
- **References**: `audio-ssml.md`, `scene-production.md`; the workflow skill lists every reference by path and reads
  each once per session.

## 0.7.0 — 2026-11-23
Staged workflow: requirements → complete script → scene-wise visual plans → clip-wise code, enforced in order.
- **Stage 1, requirements**: `brief.json` gains `objectives` (`--objective`, repeatable) and `style` (`--style`);
  `--approach custom` for the user's own structure; the brief is validated (`Brief`).
- **Stage 2, complete script** replaces the outline: `script.json` (`Script`) holds every scene's objective, key
  concepts, duration, spoken `bridge_in` and complete narration. Gate: every objective covered, bridges present,
  words per scene within ±25% of duration × wpm, total length ±20%. CP1 approves the script.
- **Stage 3, scene visual plans**: `ScenePlan` gains `composition` and `transition_in` (`segment_type`,
  `transition_to_next` removed). A plan's clip narration must equal the approved script's text for that scene, word
  for word. CP2 approves the plans.
- **Order enforced**: plans are rejected before CP1; `voice` and `task` refuse to run before CP2; checkpoints store
  fingerprints, so editing an approved script or plan makes its checkpoint stale. `text-2-shorts status` stops at
  the first open stage.
- **Accuracy reviews at both stages**: subagent `accuracy-reviewer` (was `math-reviewer`) writes
  `script_review.json` (per scene) and `plan_review.json` (per clip, on-screen maths and labels; replaces
  `math.json`). ERROR findings block the checkpoint.
- **Transitions on two levels**: simple continuity between clips; a spoken bridge plus a visual recap between scenes
  (`references/transitions.md`).
- **Prompts**: one reference per stage — `requirements.md`, `script-writing.md`, `narrative-structures.md`,
  `script-review.md`, `scene-visual-planning.md`, `transitions.md` (+ `standards.md`). The legacy outline prompts
  (`outline-zoom/arc/linear.md`, ~93 KB, which also forced 50–70-line visual plans into the outline),
  `outline-review.md`, `brief.md` and `clip-planning.md` are removed; `app/outline_models/` is replaced by `Script`.
- **Commands**: `approve <run> script|plan|sNN|final`; `validate <run> brief|script|script-review|plan|plan-review`.
- **Migration**: runs started before 0.7 have `outline.json`/`math.json` and must be restarted with
  `text-2-shorts new`.

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
