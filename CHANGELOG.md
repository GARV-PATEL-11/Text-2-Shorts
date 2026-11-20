# Changelog

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
