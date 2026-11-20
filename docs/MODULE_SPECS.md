# Module-wise development specifications

> **Implementation status (v0.2.0).** Built, smallest form that meets each spec:
> M2 runner → `pipeline.claude()` (LLM result cache, rate/usage-limit waits, start/end log rows) ·
> M3 ledger → `state.json` + `feedback.jsonl` + versioned `plan.json` (`app/clips.py`) ·
> M4 invalidation → content-hash keys (a clip's key includes the previous clip's code, so changes cascade in order) ·
> M5 steps + checkpoints → `t2s clips | voice | build | final | approve | feedback | status` ·
> M6 prompts → constants in `app/clips.py` · M7 → `tools/doc_cards.py` + API index in `.cache/` ·
> M8 → `app/check.py` (`./check`) + jailed re-check · M9 → `t2s voice` · M10 → `tools/assemble_clips.py` + `media_checks` ·
> M11 → `.cache/llm/` · M12 → `log_row` + `tools/cost_report.py` · M13 → `t2s` · M14 → preflight in `t2s new`.
> v0.3–0.4 added M15 speech (Polly/Google, SSML, word timings) and M16 video standards — see Plan.md §29.
> **v0.5 inverted control** (Plan.md §30): no runner/orchestrator any more — M2's `claude()`, M5's LLM steps and
> M6's prompt constants are gone; one Claude Code session per run does the reasoning, env/ holds its skill,
> subagents and hooks, and `app/` keeps only deterministic commands (validate, voice, task, accept, final, …).
> Not built: M1 config file (`STAGES` + env vars instead), `outline_review` (existing critic + length check),
> `clip_reviewer` (human CP3), Docker. Sections below are the original design.

Target layout: Plan.md §20. Each module: responsibility · public interface · behaviour · errors · tests · acceptance.
Status tags as in Plan.md. Signatures are Python 3.12, Pydantic v2 types from `app/contracts/models.py`.

---
## M1 `app/config.py` [PROPOSED]
**Responsibility:** load `.env` and `config/stages.yaml` once; expose typed settings.
```python
class StageCfg(BaseModel): model: str | None; effort: str | None; kind: Literal["llm","agent","deterministic"]
    timeout_s: int = 1800; max_attempts: int = 2
    retry: dict | None = None; final_retry: dict | None = None
def load_settings(root: Path) -> Settings      # Settings: stages: dict[str, StageCfg], manim_pin, api_index, aspect, tts...
```
Env overrides: `T2S_MODEL` (all LLM stages), `T2S_FPS`. **Tests:** yaml parse; override precedence.

## M2 `app/llm/runner.py` [PROPOSED — extracted from `pipeline.claude()` EXISTS]
**Responsibility:** the only place that launches `claude -p`; classification, retries, logging, artifact cache.
```python
class LLMError(Exception): error_class: Literal["AUTH","CLI","RATE_LIMIT","OVERLOADED","TIMEOUT","SCHEMA_INVALID",
                                               "AGENT_LIMIT","UNKNOWN"]
@dataclass class CallSpec: stage: str; prompt_id: str; system_static: str; system_dynamic: str = ""; user: str = ""
    schema: type[BaseModel] | None = None; scene_id: str | None = None; clip_id: str | None = None
    agent: bool = False; cwd: Path | None = None; input_hashes: dict[str, str] = {}
def run(spec: CallSpec, *, ledger: Ledger, cache: Store, settings: Settings) -> tuple[BaseModel | str, GenerationMetadata]
```
Behaviour: (1–2) cache lookup by `GenerationMetadata.cache_key()`
→ return on hit (log `artifact_cache_hit`); (3) write system file = `system_static` + `\n__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__\n`
+ `system_dynamic` (non-agent) or append file = `system_static` (agent, plus `--exclude-dynamic-system-prompt-sections`);
(4) flags exactly as today (`--safe-mode --no-session-persistence --tools ""` / agent set with `--restricted`, sandbox
settings, `--permission-prompts none`); (5) parse envelope; classify errors from `is_error`,
`subtype`, stderr text; (6) policy per Plan.md §21 (backoff 10/40/120 s for RATE_LIMIT/OVERLOADED; 1 retry TIMEOUT;
1 retry SCHEMA_INVALID with the validation error appended to `user`); (7) log row (Plan.md §23); (8) save prompts to
`.prompts/<stage>/<clip or scene or run>.<attempt>.md`; (9) store result in cache. Concurrency: process-wide lock
(`max_concurrent_llm_calls: 1`).
**Tests:** fake `claude` executable on PATH emitting scripted envelopes (success, `is_error`, invalid JSON, timeout,
rate-limit text) → assert classification, retries, backoff calls (patched sleep), log rows, cache hit path.
**Acceptance:** legacy pipeline switched to `runner.run` with identical outputs on one golden run.

## M3 `app/orchestrator/ledger.py` [PROPOSED]
**Responsibility:** durable run state (`state.json`), artifact versions, feedback log, step status, resume.
```python
class Ledger:
    @classmethod def create(cls, runs_dir: Path, brief: Brief, env: EnvironmentReport) -> "Ledger"
    @classmethod def open(cls, run_dir: Path) -> "Ledger"
    def put_artifact(self, kind: str, id: str, src: Path | bytes | BaseModel, meta: GenerationMetadata) -> ArtifactRef  # versions/<kind>/<id>.v<N>
    def current(self, kind: str, id: str) -> ArtifactRef | None
    def clip(self, clip_id: str) -> ClipState;  def set_clip(self, s: ClipState) -> None
    def step_started(self, step: str) -> None; def step_finished(self, step: str) -> None; def step_failed(self, step, err) -> None
    def add_feedback(self, fb: HumanFeedback) -> None; def open_feedback(self, target_id: str | None = None) -> list[HumanFeedback]
    def spend(self) -> float
```
Writes are atomic (temp file + `os.replace`); `state.json` holds `schema_version`. Resume: a step in `running` state
with no live PID (pidfile) is re-run. **Tests:** crash-in-the-middle simulation; version numbering; rollback.

## M4 `app/orchestrator/graph.py` [BUILT-HERE as `tools/invalidation.py`]
`build_graph(scenes: dict[str, list[str]]) -> Graph`, `rebuild_plan(g, changed, unchanged_outputs) -> list[str]`,
`summarize(order)`. Integration: on every artifact write, compare new content hash with the previous version; if equal,
add the node to `unchanged_outputs`; mark dependents stale in the ledger. **Tests:** `tests/test_invalidation.py` (5).

## M5 `app/orchestrator/steps.py` + `checkpoints.py` [PROPOSED]
One function per CLI command (Plan.md §12), each idempotent: compute stale set → run only stale units in order →
write via ledger. Checkpoints: `open_checkpoint(kind, target)` renders the review markdown/table and sets
`pending_review`; `approve(target)`, `feedback(target, scope, text)` → maps scope to graph start nodes (Plan.md §15.3).
**Tests:** scripted HITL sequences with fake runner (`tests/test_checkpoints.py`).

## M6 `app/llm/prompts/*.py` [PROPOSED — specs in `prompts/*.md`]
Each module: `PROMPT_ID`, `STATIC` (str), `build_dynamic(...) -> str`, `OUTPUT_MODEL`. Static text must not contain
run-specific values (test: render twice with different inputs → identical STATIC bytes).

## M7 `app/manim_docs/` [BUILT-HERE tools]
`api_index.build_index() -> dict`, `doc_cards.cards(index, names, topics, topics_dir) -> str`. Cache under
`.cache/manim_api/<ver>/index.json`, `.cache/cards/<hash>.md`.

## M8 `app/render/` [BUILT-HERE tools; `check.py` PROPOSED]
- `validate.py` = `tools/validate_manim_code.py` (functions `validate`, `validate_clip_file`).
- `probe.py` = `tools/layout_probe.py` (refactor `main` into `probe(scene_py, cls, budget, tolerance) -> dict`).
- `harness.py` = `tools/scene_harness.py` (`compose`, `render(..., aspect)`).
- `sandbox.py`: `bwrap_cmd(scene_dir) -> list[str]` (moved from `pipeline.BWRAP`), used for final renders.
- `check.py` (the `./check` used by the agent): sub-commands `static|probe|render|frames|all`; reads
  `TASK.json` (machine twin of TASK.md: clip id, entry/exit names, seconds, scene id, aspect); writes
  `checks/<gate>.json`; exit 0/1. `frames` extracts one PNG per beat boundary using the probe timeline + last frame.
**Acceptance:** TC-01…TC-05 (Plan.md §22.3) in CI.

## M9 `app/audio/` [PROPOSED — engines EXIST]
```python
def synth_clip(clip: ClipPlan, voice: str, engine: str, cache: Store) -> AudioArtifact     # mp3 + seconds (+ word_marks)
def phrase_times(clip: ClipPlan, audio: AudioArtifact) -> list[tuple[str, float]]          # beats' quoted phrases → start s
```
Providers: AWS Polly (SSML + word speech marks) and Google Cloud TTS (SSML `<mark>` timepoints); `app/speech.py`
normalises pronunciation for both. **Tests:** cache hit on identical text; seconds measured via ffprobe; phrase_times monotonic.

## M10 `app/assembly/` [BUILT-HERE `assemble_clips.py`; media checks PROPOSED]
`assemble(manifest, out, workdir, loudnorm=True) -> report`; `media_checks(path, expected) -> list[Finding]`
(ffprobe streams; `ebur128`, `blackdetect`, `silencedetect`). **Acceptance:** TC-10; Plan.md §16.6.

## M11 `app/cache/store.py` [PROPOSED]
```python
class Store:
    def get(self, key: str, kind: str) -> Path | None     # verifies content hash; drops broken entries
    def put(self, key: str, kind: str, src: Path | bytes, meta: GenerationMetadata) -> Path
```
JSON index per kind; LRU size cap for renders [PROVISIONAL 20 GB]. **Tests:** every input class changes the key.

## M12 `app/observability/` [BUILT-HERE `cost_report.py`; log helpers PROPOSED]
`log_row(**fields)` appends one JSON line with the schema in Plan.md §23; `report(run_dir) -> dict`.

## M13 `app/cli.py` [PROPOSED]
`t2s new|feedback|approve|plan|build|explain|final|status|resume|report|rollback` (Plan.md §12). Output: short
markdown tables for the operator skill; `--json` on every command for scripting.

## M14 Preflight [BUILT-HERE `tools/preflight.py`]
Runs in `t2s new`; writes `environment_report.json`; blocks on missing hard requirements.

## M15 `app/speech.py` [BUILT · v0.3]
`speakable(text, both_cases) -> str` · `case_pairs(texts) -> set[str]` · `to_ssml(text)` (Polly) ·
`to_ssml_marked(text) -> (ssml, words)` (Google timepoints) · `to_plain(text)` · `phrase_times(marks, beats) -> [s | None]`.
Providers in `app/pipeline.py`: `polly_tts(voice, engine)`, `google_tts(voice)`, `tts_for(brief)`; each `synth(text)`
returns `(mp3_bytes, word_marks | None)`. **Tests:** `tests/test_speech.py` (normalisation, SSML, fallbacks, timings).

## M16 Video standards [BUILT · v0.3]
`VIDEO_STANDARDS`, `EXPLANATION_STYLE`, `STYLE`, `LEAD_IN`, `HOLD` in `app/clips.py`; included in the static system
prompts (Plan.md §29.1); `plan_scene()` enforces empty scene boundaries; `color_roles` carried across scenes;
`media_checks()` enforces 2560×1440 and ≥ 60 fps. **Tests:** `tests/test_clips.py` (timing via CLIP_SECONDS).

