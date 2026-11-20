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
Python 3.12 (tested here) or 3.14 (the app's `.pyc` files show 3.14 — run the test suite on it in Phase 1).
```bash
uv sync                                   # root pyproject.toml (manim==0.20.1 pinned; pytest in dev group)
python -c "import manim; print(manim.__version__)"   # must print 0.20.1
```

## 3. Claude Code CLI
Install per https://code.claude.com/docs (native installer), then `claude --version` ≥ **2.1.275** (needed for the
system-prompt cache boundary; ≥ 2.1.259 for `--permission-prompts`, ≥ 2.1.248 for `--restricted`).
Auth: `claude auth login --console` (API billing) or `claude setup-token` (subscription).
Check: `claude auth status` → `authMethod`.

## 4. Configuration
```bash
cp .env.example .env                   # current settings; config/.env.example lists PROPOSED target-CLI vars
# app/sandbox.json is already the hardened version (failIfUnavailable + denyRead for secrets)
cp config/stages.yaml config/stages.local.yaml   # optional overrides
python tools/build_manim_api_index.py --out cache/manim_api/0.20.1/index.json
python tools/preflight.py --out reports/environment_report.json   # exit 0 = ready
```

## 5. Verify the installation (no LLM calls, ~1 min)
```bash
pytest -q tests            # 38 tests: tools, contracts, topic cards, harness, assembly
node tools/check_diagrams.mjs diagrams   # optional: Mermaid syntax (needs `npm i mermaid@11 jsdom@24`)
```

## 6. Operating
Open Claude Code in the repo; install the operator skill (`.claude/skills/make-short/`), then ask
"make a 2-minute video about the Pythagorean theorem". The skill drives `t2s` step by step (Plan.md §12).

## 7. Docker [PROPOSED, untested]
`config/Dockerfile`. Bubblewrap inside Docker needs unprivileged user namespaces; otherwise treat the container as the
isolation boundary and disable the inner bwrap jail via config.

## 8. Environment variables
See `config/.env.example` (all documented inline).
