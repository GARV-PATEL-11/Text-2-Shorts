# Unused and unreferenced files — inventory (2026-11-24, paths as of 0.13)

How it was checked: every top-level function, class and constant in `backend/app/`, `backend/tools/` and `backend/schemas/` was searched for
outside its own definition (Python, Markdown references, the run environment, README); files were checked against
imports, subprocess calls (`clip_gates.py`, `doc_cards.py`, `preflight.py`, `assemble_clips.py`), the CLI entry point,
hooks (`hooks.json`), symlinks (`skills/manim-ce-0-20-1-reference/scripts/` → `backend/tools/`), CI (`ci.yml`), template
discovery (`runtime-environment/templates/*.json`) and the paths the session reads (references, agents, skills).

**Nothing was deleted.** Each row needs your decision before removal.

| # | File or component | Location | Responsibility | References found | Status | Recommended action |
|---|---|---|---|---|---|---|
| 1 | `cost_report.py` + `test_cost_report.py` | `backend/tools/`, `tests/` | Cost summary from the log format of the old pipeline (`pipeline.claude()` rows) | only its own test; `text-2-shorts report` (`sum_session_tokens`, `backend/app/workflow/status.py`) replaced it | confirmed unused by the workflow | remove |
| 2 | `audit_prompt_catalog.py` | `backend/tools/` | Checks Manim names in prompt files | none; its usage line targets `backend/app/graph/prompts/`, which no longer exists | confirmed dead | remove (its output is in `docs/history/reference/audit-evidence/`) |
| 3 | `check_diagrams.mjs` | `backend/tools/` | Parses the Mermaid diagrams (needs Node + Mermaid) | not run by CI or tests | potentially unused (manual dev check) | remove, or add to CI if diagrams must stay valid |
| 4 | `save_versioned()` | `backend/app/workflow/artifacts.py` | Writes a file keeping `name.vN.ext` copies | no caller | confirmed dead | remove |
| 5 | 16 schema classes: `ApprovalState`, `ValidationStatus`, `ArtifactRef`, `VideoProject`, `VideoPlan`, `NarrationSegment`, `AudioArtifact`, `DocumentationReference`, `Finding`, `ValidationResult`, `CriticResult`, `ManimCodeArtifact`, `RenderArtifact`, `HumanFeedback`, `CacheEntry`, `ClipState` (139 lines) | `backend/schemas/unused_contracts.py` (moved there in 0.13; no longer exported to JSON) | Contracts of the planned module design that was never built | `GenerationMetadata` in `test_models.py` only; no code, agent or reference uses them | potentially unused | remove the module and its test |
| 6 | Prompts package `script_prompts/` (6 files) + `export_references.py` | `runtime-environment/prompts/` | Source of the 4 topic/outline references | only `export_references.py`, the drift test and Pyrefly's `search-path`; a run reads the generated `.md` files | used only to generate Markdown | consolidate: make the `.md` references the source, then remove the package, the exporter and the drift test (your choice pending: one `outline.md` or three files) |
| 7 | `doc_cards.py --from-spec` and `names_from_spec()` | `backend/tools/doc_cards.py` | Cards from a `VisualSpecification` JSON | no caller passes `--from-spec` | potentially unused option | remove the option (and `VisualSpecification` if nothing else needs it) |
| 8 | `.claude/settings.json` permissions | repo root `.claude/` | Allow-list for developer sessions | allows `uv run python -m app.pipeline` and `xdg-open artifacts/runs/` — the module no longer exists; videos open in Chrome | outdated configuration | update to `uv run text-2-shorts:*` (permission file: left for you to change) |
| 9 | `app.zip` (232 KB) | `artifacts/trash/` (moved from the repo root) | An archive of an old `app/` | none; git-ignored | confirmed unused local file | remove |
| 10 | `media/` (260 KB) | `artifacts/trash/` (moved from the repo root) | Manim's default output folder (LaTeX cache) from a render run at the repo root | none; git-ignored | generated artifact | remove (recreated if Manim runs there again) |
| 11 | Diagrams 01, 05, 06, 08–15 | `docs/diagrams/` | Mermaid diagrams | none from code; 04 is also embedded in the README | not checked against 0.11 | review: keep those still accurate, move the rest to `docs/history/diagrams/` |
| 12 | Architecture plan, module specifications, skills assessment, proposed stages, reference/audit evidence, diagrams 02, 03, 07 | `docs/history/` | Superseded designs (they describe the removed LangGraph pipeline in places) | only from each other and `CHANGELOG.md` | archived (moved, not deleted) | retain as history, or remove |
| 13 | Manim topic cards (11 files) | `runtime-environment/skills/manim-ce-0-20-1-reference/topics/` | Manim patterns for the clip-builder | used: `doc_cards.py`, `ALWAYS_LOADED_TOPICS`, `ClipPlan.manim_topics`, `test_topic_cards.py` | in use | consolidate into one `manim-vocab.md` (your pending decision on the two downloaded vocabulary files) |

## Duplication found

| What | Where | Recommendation |
|---|---|---|
| The pipeline diagram | `README.md` and `docs/diagrams/04-generation-pipeline.mmd` (kept equal by hand) | keep one; the README copy is what people read |
| Standard style values | `backend/app/config.py` `VIDEO_STYLE` and `references/standards.md` | intentional: a test keeps them equal |
| Shared outline rules | repeated in `outline-linear.md`, `outline-arc.md`, `outline-zoom.md` (generated from `_shared.py`) | decide with row 6 |

## Checked and in use (not dead)
`backend/tools/preflight.py` (`new`), `backend/tools/clip_gates.py` (`./check`, `accept`), `validate_manim_code.py`, `layout_probe.py`,
`scene_harness.py`, `doc_cards.py`, `build_manim_api_index.py` (`task`, `doc`, symlinked from the Manim skill),
`assemble_clips.py` (`final`), all `tests/fixtures/` (used by validator, probe, harness and assembly tests), every
`runtime-environment/` file (plugin, hooks, settings, agents, skills, references, templates, workspace), `.env.example`,
`.github/workflows/ci.yml`. Dependencies `manim`, `pydantic`, `python-dotenv` (`backend/app/config.py`), `boto3` and
`google-cloud-texttospeech` (`backend/app/narration.py`, `new`) and the dev group (`pytest`, `ruff`, `pyrefly`) are all used.
