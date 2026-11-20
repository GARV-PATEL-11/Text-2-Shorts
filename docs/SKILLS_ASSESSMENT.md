# Claude Skills assessment

> **Repo status (merged):** the custom skills live in `.claude/skills/` (`make-short` is the working one for today's `app.pipeline`; the package's target-CLI version is `docs/make-short.target-cli.md`). The vendored `external/` skills were removed: use the built-in `claude-api` and `skill-creator` skills; `webapp-testing`, `manimce-best-practices` and the template are listed with their sources in `reference/SOURCES.md` (and in git history, commit ee787a2).

**Question answered:** which Claude Skills are needed to *develop, operate and maintain* this system, which exist,
which need customization, and which must be built.

**Important constraint discovered:** every `claude -p` call the app makes — including the render agent — passes
`--safe-mode` (it is in the base command of `pipeline.claude()`), and `--safe-mode` disables skills, CLAUDE.md, hooks
and plugins (CLI reference).
So skills serve the **operator session** and **developers**; the runtime agent receives its knowledge as an appended
prompt + generated API/topic cards instead. This is deliberate: runtime context must be minimal and version-exact.

## Summary
| Skill | Category | Who uses it | Location in package | Status |
|---|---|---|---|---|
| make-short | **New** (reconstructs the missing operator skill) | Operator in Claude Code | `custom/make-short/` | PROPOSED (target CLI) + current-CLI section usable now |
| manim-ce-0-20-1-reference | **New** | Developers; topic cards also feed the runtime agent via doc_cards | `custom/manim-ce-0-20-1-reference/` | IMPLEMENTED (scripts + 11 tested topic cards) |
| t2s-clip-debugging | **New** | Developers | `custom/t2s-clip-debugging/` | PROPOSED (tools it calls are implemented) |
| t2s-prompt-maintenance | **New** | Developers | `custom/t2s-prompt-maintenance/` | PROPOSED (audit tool implemented) |
| skill-creator (Anthropic) | **Reuse as-is** | Developers authoring/evaluating the 4 custom skills | `external/skill-creator/` | vendored, Apache-2.0, commit e4bb5d9 |
| claude-api (Anthropic) | **Reuse as-is** | Developers: prompt caching, cost-optimize, models/pricing, token counting, prompt-audit workflows (Phases 4, 11, 13) | `external/claude-api/` | vendored, Apache-2.0, commit e4bb5d9 |
| manimce-best-practices (community, MIT) | **Reuse with customization** | Developers writing topic cards / reviewing Manim patterns | `external/manimce-best-practices/` | vendored unmodified; required customizations listed in its SOURCE.md |
| webapp-testing (Anthropic) | **Reuse later** | Future review web UI tests (Plan.md §28) | `external/webapp-testing/` | vendored, Apache-2.0 |
| Anthropic template + spec | Reference | Skeleton for new skills | `external/_anthropic-template/` | vendored |
| mcp-builder, docx/pptx/xlsx/pdf, frontend-design | Not required for v1 | — | — | see `external/_reference-only/README.md` |
| Community Manim skills (Yusuke710, vumichien, awesome-skills, manim-composer) | Reviewed, not adopted | — | `external/_reference-only/README.md` | reasons recorded |

## Per-skill detail

### 1. make-short — NEW
- **Purpose:** let a human operate the generator conversationally and safely: one command at a time, show checkpoint
  tables, collect clip-scoped feedback, never generate content in the chat.
- **Capabilities:** maps user intents to `t2s new/plan/build/final/feedback/approve/status/explain`; recovery rules
  (FAILED clips); current-CLI fallback section for today's `python -m app.pipeline`.
- **Dependencies:** the `t2s` CLI (Phase 2+), Claude Code ≥ 2.1.275.
- **Implementation approach:** SKILL.md only (no scripts) — the CLI owns all logic, so the skill cannot drift from it.
  Evaluate with skill-creator's eval loop on 5 scripted conversations (new run, outline revise, clip visual revise,
  failed clip, resume after interrupt).
- **Integration points:** installed at `.claude/skills/make-short/`; reads CLI `--json` outputs; Plan.md §12, §15.

### 2. manim-ce-0-20-1-reference — NEW
- **Purpose:** single source of version-exact Manim knowledge for humans and (via doc_cards) the runtime agent.
- **Capabilities:** build API index from the installed package; API cards for exact names; 11 topic cards (10 with code
  examples that are statically validated and dry-run rendered in tests, plus a removed-API table); static validator; layout/timing probe; harness.
- **Dependencies:** Manim 0.20.1, LaTeX + dvisvgm, ffmpeg.
- **Implementation approach:** generated knowledge (index/cards) + curated-but-tested knowledge (topics). No
  hand-written API lists. Upgrade procedure in SKILL.md and Plan.md §14.4.
- **Integration points:** `app/manim_docs`, `app/render`, runtime TASK/API_CARDS generation, CI.

### 3. t2s-clip-debugging — NEW
- **Purpose:** fast, evidence-first diagnosis of clip failures from a run directory without spending LLM tokens.
- **Capabilities:** ordered evidence path (ledger → checks → local reproduction → logs/prompts); classification into
  tool false positive / plan defect / code defect, each with a fix route.
- **Dependencies:** run layout (Plan.md §20), tools.  **Integration:** developer workflow; feeds validator/card backlog.

### 4. t2s-prompt-maintenance — NEW
- **Purpose:** make prompt/schema/model edits safe (cache invalidation, cost regressions, API drift).
- **Capabilities:** contract-first checklist, static/dynamic split rule, catalog audit, prompt versioning, eval gate,
  pointer to claude-api cost workflows.
- **Dependencies:** `tools/audit_prompt_catalog.py`, golden set, `cost_report.py`.

### 5. skill-creator — REUSE AS-IS
Use to draft/iterate the four custom skills and to run description-trigger evals. No changes needed.

### 6. claude-api — REUSE AS-IS
Directly relevant references: `shared/prompt-caching.md` (minimum cacheable prefix 512 tokens on current models,
TTL economics), `shared/cost-optimization.md` (workflow `cost-optimize`), `shared/models.md` (ids, pricing),
`shared/token-counting.md`, `shared/prompt-audit.md` (workflow `prompt-audit` — run it on `app/graph/prompts` in
Phase 4). Note the skill itself instructs to verify live pricing/models before quoting.

### 7. manimce-best-practices — REUSE WITH CUSTOMIZATION
Validated against 0.20.1 with our validator (results in its SOURCE.md). Customizations: version pin in description,
remove/fix the malformed cli.md block, exclude 3D from default load set, never load in the runtime agent, CI re-check
on pin changes. Predates the 0.20 MathTex rewrite → our mathtex-indexing card supersedes its MathTex indexing advice.

### 8. webapp-testing — REUSE LATER
For Playwright tests of the optional review UI (Plan.md §28). Not used in v1.

## Gap analysis
| Need | Covered by | Gap |
|---|---|---|
| Version-exact Manim API knowledge | generated index/cards | none |
| Manim patterns (layout, timing, MathTex 0.20) | topic cards (11) | add cards from findings histogram (Plan.md §23) |
| Operating the pipeline | make-short | CLI must exist (Phases 2–10) |
| Prompt caching/cost know-how | claude-api | none |
| Video/audio engineering (ffmpeg, loudness) | tools/assemble_clips.py + Plan.md §16.6/§17 | a dedicated skill not warranted yet |
| Math verification tooling | math_verifier prompt; math_lint proposed | sympy LaTeX parsing needs antlr pin (pyproject `[math]`) |
