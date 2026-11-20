# Text-2-Shorts

Turns a topic into a narrated **Manim** explainer video. Every LLM step runs as a sandboxed `claude -p`
call driven by `app/pipeline.py`; the `/make-short` Claude Code skill operates it and asks you at each checkpoint.

## Use it (current pipeline)
In Claude Code, run `/make-short <topic>`. Or step by step:
```bash
uv run python -m app.pipeline new "<topic>" --approach zoom --minutes 3 --audience "…" --voice af_heart
uv run python -m app.pipeline outline  runs/<id>          # outline + narration (critic loop)
uv run python -m app.pipeline tts      runs/<id>          # Kokoro (local) or AWS Polly
uv run python -m app.pipeline plan     runs/<id> [--refine --rounds 4] [--scenes 2,4 --feedback "…"]
uv run python -m app.pipeline render   runs/<id> [--scenes N --feedback "…"]
uv run python -m app.pipeline assemble runs/<id>          # → runs/<id>/final.mp4
```
- Model/effort per stage: `STAGES` in `app/pipeline.py`. Env vars: `.env.example`
  (`T2S_PARALLEL`, default 4 scenes at a time; `T2S_MODEL`; `T2S_QUALITY`).
- Each run's `log.jsonl` has a `started` line and a result line (cost, duration, error) per Claude call.
- Plan revisions: `scenes/NNN/plan.vN.md`. Critic history: `plan_review.json`.

## Development package (merged in)
This is a blueprint and tested building blocks for moving from scene-level to clip-level generation, with
human-in-the-loop review and cost control. It was built by auditing this app against **Manim 0.20.1** and the
Claude Code CLI. Its labels: **[EXISTS]** in the app · **[EXISTS-DEFECT]** verified defect ·
**[BUILT-HERE]** implemented and tested · **[PROPOSED]** designed, not implemented · **[PROVISIONAL]** number not
yet measured.

| You are… | Read |
|---|---|
| Deciding whether to proceed | `Plan.md` §1 (summary), §3.3 (verified findings), §26 (risks/open questions) |
| Implementing | `Plan.md` §25 (roadmap) → `docs/MODULE_SPECS.md` → `prompts/` → `schemas/models.py` → `tools/` |
| An AI coding agent | `Plan.md` §20 (target layout), §25 (phase order + acceptance); run `uv run pytest -q` after every change |
| Setting up a machine | `docs/DEPLOYMENT.md` |
| Working on prompts/skills | `prompts/README.md`, `skills/SKILLS_ASSESSMENT.md` |

```
Plan.md                 full reference (28 sections, 14 Mermaid diagrams)
docs/                   MODULE_SPECS.md (M1–M14), DEPLOYMENT.md, make-short.target-cli.md (skill for the PROPOSED t2s CLI)
diagrams/               the 14 diagrams as .mmd
schemas/                models.py (Pydantic v2 contracts) + export_json_schemas.py → json/ (21 schemas)
prompts/                [PROPOSED] outline_review, clip_planner, math_verifier, clip_builder_agent, clip_reviewer, …
tools/                  [BUILT-HERE] API index, validator, layout probe, scene harness, assembly, invalidation,
                        doc cards, preflight, prompt-catalog audit, cost report (see tools/README.md)
tests/                  pipeline tests + 38 package tests + fixtures
config/                 stages.yaml, manim.landscape/portrait.cfg, .env.example (target vars), Dockerfile, ci/ [PROPOSED]
.claude/skills/         make-short (current, working) · manim-ce-0-20-1-reference · t2s-clip-debugging · t2s-prompt-maintenance
skills/                 SKILLS_ASSESSMENT.md + external/ vendored skills (skill-creator, claude-api, webapp-testing,
                        manimce-best-practices); kept for developers, not activated
reference/              SOURCES.md, existing-app inventory, audit evidence
```
`app/sandbox.json` uses the package's hardened settings (`failIfUnavailable`, `denyRead` for secrets).

### Verify (no LLM calls)
```bash
uv run pytest -q                                    # all tests
uv run python tools/preflight.py --planning-only    # environment check → JSON, "problems": []
```
System packages: ffmpeg, texlive-latex-base, texlive-latex-extra, dvisvgm, libpango1.0-dev, pkg-config,
bubblewrap, socat.

### Implemented vs proposed
- **Implemented and tested:** API index, static validator (including clip contracts), layout/timing probe, scene
  harness (clip isolation, section renders, 9:16), clip A/V assembly, invalidation planner, doc cards, preflight,
  catalog auditor, cost report, data contracts with JSON Schemas, and 11 topic cards (10 with executed examples
  plus a removed-API table).
- **Proposed (not implemented):** the `t2s` CLI, ledger, runner refactor, artifact cache, new LLM stages and
  prompts, checkpoints, math lint, media checks, Docker, CI wiring.

**Key decisions (Plan.md §5.2):**
- Each clip is an isolated file, rendered through Manim sections.
- Audio is produced first.
- The scene-level Director DSL is dropped.
- Version-pinned generated API cards replace hand-written catalogs.
- Deterministic checks run before any LLM review, and there is one conditional multimodal reviewer.
- There are four human checkpoints, with feedback scoped to clips.
- A plain-Python ledger replaces LangGraph, and LLM calls run one at a time.
