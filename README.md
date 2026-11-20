# Text-2-Shorts

Turns a topic into a narrated **Manim** explainer video: 2560×1440 (16:9), 60–120 fps, with the font you choose.
Claude Code is the execution environment: each video is produced by one Claude Code session that runs inside its own
isolated run folder, guided by a skill, two subagents and hooks. Python only holds deterministic steps (validation,
voice, checks, rendering, state) that the session calls. There are no per-stage API calls or prompts in app code.

## Setup
```bash
sudo apt install ffmpeg texlive-latex-base texlive-latex-extra dvisvgm libpango1.0-dev pkg-config bubblewrap socat
uv sync                       # Python deps (manim==0.20.1 pinned) + the `t2s` command
claude --version              # Claude Code ≥ 2.1.275, logged in
cp .env.example .env          # optional settings
uv run pytest -q              # deterministic suite, no LLM calls
```
Voice credentials (AWS Polly or Google Cloud TTS) and details: `docs/DEPLOYMENT.md`.

## Use it
```bash
uv run t2s new "<topic>" --approach zoom --minutes 2 --audience "…" --tts polly --voice Matthew --font Roboto
uv run t2s open runs/<id>     # interactive Claude Code session for this run, inside its jail
```
From a repo session, `/make-short <topic>` asks the setup questions and runs `t2s new` for you. The run session then
writes the outline, clip plans and clip code, and asks you at four checkpoints (CP1 outline · CP2 clip plan and
math · CP3 each scene's preview · CP4 final video). Re-running `t2s open` resumes from where the run stopped.
`uv run t2s status runs/<id>` shows approvals, every clip's state and the next steps from anywhere.

## Architecture
```
env/                              the execution environment, defined once (declarative, version-controlled)
  .claude-plugin/plugin.json      a Claude Code plugin, loaded with --plugin-dir
  skills/t2s-produce/             the workflow (CP1–CP4) + references loaded only when a step needs them:
    references/                   standards (palette, type, timing, narration, ELI5) · brief · outline per approach ·
                                  outline review · clip planning
  skills/manim-ce-0-20-1-reference/  version-pinned Manim topic cards + scripts
  agents/clip-builder.md          subagent: builds ONE clip in its prepared folder (fresh context per clip)
  agents/math-reviewer.md         subagent: independent math check → math.json
  hooks/hooks.json                SessionStart → status + next steps; PostToolUse → log + validate what was written
  settings.json                   session sandbox (bubblewrap, fails closed) + permissions (secrets unreadable)
  workspace/CLAUDE.md             the per-run instructions copied into every run
runs/<id>/                        one run = one workspace (git-ignored)
```
- **Provisioning** (`t2s new`): preflight (LaTeX, ffmpeg, bwrap, Claude Code version), voice-credential check, then
  `runs/<id>/` with `brief.json`, `CLAUDE.md`, `environment_report.json`.
- **Isolation** (`t2s open`): Claude Code runs in a bubblewrap jail. The system and the repo are read-only; the run
  folder is writable, as are Claude Code's own state (`~/.claude`) and caches. `$HOME` is a private, throwaway tmpfs
  with tool folders and voice credentials mounted back read-only. One run cannot change another run or the shared
  code. Inside, Claude Code's own sandbox (`env/settings.json`) confines every Bash command again (no network except
  `t2s voice`, secrets unreadable). LLM-written clip code is re-checked by `t2s accept` and rendered by `t2s final`
  in a further network-less jail.
- **Context**: `CLAUDE.md` is short; the skill says which reference to read at each step; the clip-builder gets a
  `TASK.md` with only its clip, the paths of the standards and three always-on Manim cards, and the cards specific
  to that clip. The session-start hook prints the run's state, so resuming costs one short block instead of
  re-reading files.
- **Validation loop**: right after the session writes `outline.json`, a `plan.json` or `math.json`, the PostToolUse
  hook validates it (schema, ±20% length, empty scene boundaries, one colour per symbol); errors go straight back to
  Claude. Clips pass `./check` (validator → layout/timing probe → section render → frames) and `t2s accept`.

| `t2s` command | What it does (deterministic) |
|---|---|
| `validate <run> outline\|plan\|math` | schema + rules for what the session wrote |
| `voice <run>` | narration per clip via AWS Polly or Google Cloud TTS: symbols, units, abbreviations and M-vs-m spoken correctly (`app/speech.py`), SSML pauses, word timings → beat start times; only changed clips are re-synthesised |
| `task <run> sNNcMM` | prepares the clip-builder folder: `TASK.md`/`.json`, `API_CARDS.md`, `./check`, earlier clips |
| `accept <run> sNNcMM` | re-runs every gate in a jail; installs the clip only if all pass |
| `final <run>` | 1440p section render per scene, per-clip audio sync (0.3 s lead-in), EBU R128 loudness, media checks (≥ 60 fps) |
| `approve` / `feedback` / `status` / `report` | checkpoints, scoped feedback, state + next steps, token totals from the run's transcripts |

Settings: `T2S_FPS` (60–120, default 60), `T2S_PARALLEL` (scenes rendered at once, default 4), `T2S_TTS`
(`polly` default, or `google`), `POLLY_ENGINE`, `POLLY_VOICE`, `GOOGLE_VOICE`.

## Logs and observability
- `runs/<id>/log.jsonl`: one row per tool call the session makes (`ts`, `tool`, `detail`), written by the hook.
- `runs/<id>/state.json`: approvals, each clip's status, open findings and key, and the session transcripts.
- `uv run t2s report runs/<id>`: tokens used by the run's sessions and subagents (net input, cache read/write,
  output), counted once per model response.

## Repository
```
app/pipeline.py         t2s CLI: new (provision), open (jail), TTS providers
app/clips.py            validate · voice · task · accept · final · approve · feedback · status · report · hook
app/check.py            ./check gates used by the clip-builder and re-run by accept
app/speech.py           narration → speakable text / SSML; word timings → beat times
app/graph/models/       outline schemas (used by validate)
env/                    the Claude Code environment (see Architecture)
schemas/models.py       Pydantic contracts (ScenePlan, ClipPlan, …) + json/ exports
tools/                  validator, layout probe, scene harness, assembly, doc cards, API index, preflight, cost report
.claude/skills/         repo-session skills: make-short (launcher) · t2s-clip-debugging · t2s-prompt-maintenance
Plan.md, docs/          design reference; Plan.md §29 standards/sync/speech, §30 Claude Code-native architecture
tests/                  deterministic suite: validators, task → accept → final, jail isolation, hooks, speech
```
