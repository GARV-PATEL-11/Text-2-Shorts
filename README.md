# Text-2-Shorts

Turns a topic into a narrated **Manim** explainer video: 2560×1440 (16:9), 60–120 fps, with the font you choose.
Every LLM step is a sandboxed `claude -p` call. The `/make-short` Claude Code skill operates the `t2s` CLI and asks
you at four checkpoints.

## Setup
```bash
sudo apt install ffmpeg texlive-latex-base texlive-latex-extra dvisvgm libpango1.0-dev pkg-config bubblewrap socat
uv sync                       # Python deps (manim==0.20.1 pinned) + the `t2s` command
claude --version              # Claude Code ≥ 2.1.275, logged in
cp .env.example .env          # optional settings
uv run pytest -q              # deterministic suite, no LLM calls
```
Details: `docs/DEPLOYMENT.md`.

## Use it
In Claude Code: `/make-short <topic>`. Or step by step:
```bash
uv run t2s new "<topic>" --approach zoom --minutes 2 --audience "…" --voice af_heart --font Roboto
uv run t2s outline runs/<id>            # CP1 → uv run t2s approve runs/<id> outline
uv run t2s clips   runs/<id>            # scenes → clips + math check. CP2 → approve runs/<id> plan
uv run t2s voice   runs/<id>            # narration audio per clip (Kokoro local, or AWS Polly)
uv run t2s build   runs/<id>            # one sandboxed agent per clip. CP3 → approve runs/<id> sNN
uv run t2s final   runs/<id>            # 1440p render, audio sync, loudness, media checks. CP4 → approve … final
uv run t2s status  runs/<id>            # approvals, every clip's state, spend
uv run t2s feedback runs/<id> s02c03 --scope visual --text "…"   # or: build --clips s02c03 --feedback "…"
```
A video is scenes (`s01`…), a scene is clips (`s01c01`…): 4–20 s each, one teaching purpose, its own narration file
and its own code file. Re-running any step redoes only what changed: an edited plan, new audio, feedback, or an
earlier clip in the same scene. Everything else is reused through content hashes.

## How it works
| Stage | What runs | Output |
|---|---|---|
| `new` | preflight (LaTeX, ffmpeg, bwrap, Claude Code version), brief refiner | `brief.json` |
| `outline` | approach prompt → critic loop → deterministic length check | `outline.json` |
| `clips` | clip planner per scene (Pydantic-validated contracts: clip N+1 entry = clip N exit) → math verifier | `scenes/sNN/plan.json`, `math.json` |
| `voice` | TTS per clip; reused while the text is unchanged | `scenes/sNN/audio/clip_MM.mp3` |
| `build` | per clip: `TASK.md` + generated API cards → sandboxed agent loops `./check static → probe → render → frames` → the orchestrator re-runs `./check all` in a jail and only then installs the clip | `scenes/sNN/clips/clip_MM.py` |
| `final` | each scene composed from its clips, rendered in a jail with one Manim section per clip → per-clip A/V mux → EBU R128 loudness → media checks | `final.mp4`, `final_report.json` |

- **Gates** (`app/check.py`): `tools/validate_manim_code.py` (names, removed APIs, contracts), `tools/layout_probe.py`
  (overlap, out-of-frame, clip timing vs narration), `tools/scene_harness.py` (clip isolation, section renders).
- **Prompt caching**: every system prompt is byte-identical across calls; per-call data goes in the user message.
  Identical non-agent calls are answered from `.cache/llm/`.
- **Limits**: rate-limit and overload errors back off (10/40/120 s). A usage limit is waited out until its reset time.
- **Sandbox**: agents run in Claude Code's bubblewrap sandbox (`app/sandbox.json`: no network, writes only in the
  clip folder, secrets unreadable, fails closed). Final renders run LLM-written code in a read-only bwrap jail.
- **Settings**: `STAGES` in `app/pipeline.py` (model/effort per stage). Env: `T2S_PARALLEL` (scenes at a time,
  default 4), `T2S_FPS` (60–120, default 60), `T2S_MODEL` (force one model), `TTS_ENGINE`, `KOKORO_VOICE`.

## Logs
`runs/<id>/log.jsonl` has 2 rows per Claude call, paired by `call_id`. The `start` row is written when the call
begins; a `start` row with no `end` row means the call is still running or was killed. The `end` row holds the result:
- identity: `run`, `stage_no`, `stage`, `type` (llm/agent), `scene`, `model`, `model_id`, `effort`, `attempt`
- result: `success`, `cache_hit`, `outcome` (agent READY/FAILED), `stop_reason`, `notes`, `error`
- tokens: `input_tokens` (net, uncached), `output_tokens`, `thinking_tokens`, `cache_read`, `cache_write`,
  `total_input_tokens`
- cost and time: `cost_usd`, `duration_ms` (wall clock), `api_ms`, `ttft_ms`, `turns`
- other: `permission_denials`, `session_id`

Per-stage table: `uv run python tools/cost_report.py runs/<id>/log.jsonl` (`final` prints it too).

## Repository
```
app/pipeline.py         t2s CLI, Claude runner (cache, retries, limit waits, logging), brief/outline/TTS
app/clips.py            clip planner, math verifier, voice, build orchestration, final, approvals/feedback/status
app/check.py            ./check gates used by clip agents and re-run by the orchestrator
app/graph/              outline schemas + brief/outline prompts
schemas/models.py       Pydantic contracts (ScenePlan, ClipPlan, …) + json/ exports
tools/                  validator, layout probe, scene harness, assembly, doc cards, API index, preflight, cost report
.claude/skills/         make-short (operator) · manim-ce-0-20-1-reference · t2s-clip-debugging · t2s-prompt-maintenance
Plan.md, docs/          design reference (architecture, module specs, deployment, skills assessment)
prompts/                specs of the two stages not built (outline_review, clip_reviewer)
tests/                  deterministic suite, including a full build → final run with a fake agent
```
