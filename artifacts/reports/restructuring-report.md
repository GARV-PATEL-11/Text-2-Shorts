# Restructuring report (2026-11-24, versions 0.12 and 0.13)

Goal: a responsibility-driven layout with no change in behaviour, every file and payload behind a Pydantic contract,
and a frontend. The test suite grew from 111 to 118 tests (topic-card guard, web) and passes. Nothing was deleted;
candidates for removal are in `unused-files-inventory.md`.

## Before → after

```
BEFORE (0.11)                                   AFTER (0.13)
app/cli.py            333 lines                 frontend/                  index.html · styles.css · app.js
app/run_steps.py      2,532 lines               backend/app/               cli.py · config.py · utilities.py · sandbox.py ·
app/clip_gates.py                                                          narration.py · commands/ (5) · workflow/ (16)
app/narration.py                                backend/schemas/           base · requirements · script · plans · reviews ·
app/outline_models/   5 files                                              interaction · run_state · media · session · api ·
schemas/models.py     640 lines + json/                                    unused_contracts · outline_models/ · json/
tools/                                          backend/tools/             (+ clip_gates.py)
run-environment/                                runtime-environment/
runs/                                           artifacts/runs/ · artifacts/reports/ · artifacts/trash/
diagrams/ · reference/ · docs/ (flat)           docs/ PROJECT_STRUCTURE.md · guides/ · changes/ · diagrams/ · history/
```

## What changed

| Change | Detail |
|---|---|
| split (0.12) | `run_steps.py` + `cli.py` → entry point, settings, helpers, sandbox, command handlers, workflow modules; statements moved unchanged by a script; no import cycles |
| moved (0.12) | `clip_gates.py` → tools (a standalone script run in the render jail); outline models → schemas; docs into guides/changes/diagrams/history |
| moved (0.13) | `app/`, `schemas/`, `tools/` → `backend/`; `run-environment/` → `runtime-environment/`; `runs/` → `artifacts/runs/`; reports → `artifacts/reports/`; `app.zip`, `media/` → `artifacts/trash/`; `PROJECT_STRUCTURE.md` → `docs/` |
| contracts (0.13) | `models.py` split by domain; new contracts for `state.json`, `log.jsonl`, the audio index, `TASK.json`, gate results, scene renders, `sync.json`, `assembly.json`, `final_report.json`, media findings, requests and decisions as events, the `next` batch, the hook's input and output, the environment report, token totals, the web API |
| code (0.13) | every module reads and writes those files through their contracts (typed loaders in `workflow/artifacts.py`); the tools validate their inputs and outputs (`ClipTask`, `GateResult`, `SceneRender`, `AssemblyManifest`, `EnvironmentReport`) |
| frontend (0.13) | `frontend/` and `text-2-shorts serve` (read-only, 127.0.0.1) with `workflow/run_views.py` and `schemas/api.py` |
| fixed | `test_topic_cards.py` found no cards after the move (10 tests silently skipped); a guard test now fails instead |

## Validation

| Check | Result |
|---|---|
| Every module imports; no import cycles | yes |
| Entry point and every command's `--help` | all start |
| Template discovery, prompt export, schema export | 3 templates; references match the prompts; 56 JSON Schemas |
| Frontend | served; black, white and greys only; no motion; no `innerHTML`; checked in headless Chrome at 1440 px and 390 px |
| Test suite | 118 passed |
| Ruff (format, lint) · Pyrefly | clean · 31 errors, all in the pre-existing baseline |

## Remaining
1. Decide the removals in `unused-files-inventory.md`.
2. Prompts as Markdown only, and one Manim vocabulary file: both change what a run reads; they wait for your go-ahead.
3. `.claude/settings.json` still allows the removed `app.pipeline` module.
4. `serve` sends whole files (no HTTP Range), so seeking in long videos is limited.
