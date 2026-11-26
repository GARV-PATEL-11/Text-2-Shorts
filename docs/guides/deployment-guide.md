# Deployment, environment and dependencies

v1 is a **local, single-user** tool run from a terminal / Claude Code session. No server.

## 1. System packages (Ubuntu 24.04; verified in the audit environment)
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg texlive-latex-base texlive-latex-extra texlive-fonts-recommended dvisvgm \
                        libcairo2-dev libpango1.0-dev pkg-config bubblewrap socat
```
`libpango1.0-dev` + `pkg-config` are required to build Manim's `manimpango` from source; `dvisvgm` is required by MathTex
(the audit's first LaTeX render failed without it). macOS: `brew install ffmpeg cairo pango pkg-config` + MacTeX;
the Claude Code sandbox uses the macOS system sandbox, final-render bwrap jail is Linux-only (use Docker or skip).

## 2. Python
Python ≥ 3.12 (developed on 3.14).
```bash
uv sync                                              # manim==0.20.1 pinned; installs the `text-2-shorts` command
uv run python -c "import manim; print(manim.__version__)"   # must print 0.20.1
```

## 3. Claude Code CLI
Install per https://code.claude.com/docs (native installer), then `claude --version` ≥ **2.1.275**
(≥ 2.1.259 for `--permission-prompts`, ≥ 2.1.248 for `--restricted`).
Auth: `claude auth login --console` (API billing) or `claude setup-token` (subscription). Check: `claude auth status`.

## 4. Voice provider credentials (one of them, chosen per video with `text-2-shorts new --tts polly|google`)
- **AWS Polly** (default): `aws configure` (or `AWS_PROFILE`); the identity needs `polly:SynthesizeSpeech`.
- **Google Cloud TTS**: enable the Text-to-Speech API in your project, then
  `gcloud auth application-default login` (or `GOOGLE_APPLICATION_CREDENTIALS=/path/key.json`).
`text-2-shorts new` checks the chosen provider's credentials before any Claude call.

## 5. Configuration
```bash
cp .env.example .env                                 # optional: TEXT_2_SHORTS_PARALLEL, TEXT_2_SHORTS_FPS, TTS/voice
uv run python backend/tools/preflight.py                     # exit 0 = ready (text-2-shorts new runs it too)
```
`runtime-environment/settings.json` is the run session's sandbox and permissions (no network except `text-2-shorts voice`, secrets
unreadable, fails closed). The Manim API index is built on the first `text-2-shorts task` into `~/.cache/text-2-shorts/`.

## 6. Verify the installation (no LLM calls, ~2 min)
```bash
uv run pytest -q           # tools, contracts, Manim reference examples, harness, assembly, and a fake-agent build → final run
node backend/tools/check_diagrams.mjs diagrams   # optional: Mermaid syntax (needs `npm i mermaid@11 jsdom@24`)
```

## 7. Operating
`uv run text-2-shorts new "<topic>" …` provisions `artifacts/runs/<id>/` (the website's new-run form does the same), then
`uv run text-2-shorts open artifacts/runs/<id>` starts the run's own Claude Code session inside its bubblewrap jail, with the `runtime-environment/`
plugin (workflow skill, the builder, critic and audio subagents, hooks) and `runtime-environment/settings.json` (sandbox,
permissions). The jail needs bubblewrap with unprivileged user namespaces (the same requirement as Claude Code's
sandbox); `text-2-shorts open RUN -- sh` opens a shell in the same jail for debugging.

## 8. Docker
Not shipped. The agents depend on bubblewrap, which inside Docker needs unprivileged user namespaces; a container
image only makes sense once the container itself is chosen as the isolation boundary.
