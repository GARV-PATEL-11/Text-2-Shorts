# Claude Skills assessment

> **Repo status (merged):** the custom skills live in `.claude/skills/` (`make-short` now operates the clip-level `text-2-shorts` CLI). The vendored `external/` skills were removed: use the built-in `claude-api` and `skill-creator` skills; `webapp-testing`, `manimce-best-practices` and the template are listed with their sources in `reference/sources.md` (and in git history, commit ee787a2).

## Skills audit — 2026-11-20 (current)
Scope: the project's own skills (3 repo-session skills in `.claude/skills/`, 2 environment skills in `run-environment/skills/`)
and the 2 environment subagents (`run-environment/agents/`). Third-party plugins are out of scope.
Method (writing-skills TDD): one or two realistic scenarios per skill run by fresh agents **before** the rewrite
(baseline), the same scenarios after (green), then targeted re-tests of every refinement.
Standard for every skill/agent (enforced by `tests/test_run_environment.py`): description starts "Use when…" and only says when
to use it (≤ 500 chars); body ≤ 650 words; mandatory rules separated from the adaptable approach; done criteria;
related skills; verified links.

| Skill / agent | Baseline failure (before) | Change | Validation |
|---|---|---|---|
| make-short | closed lists (1/2/3/5 min) — silently turned a 7-minute request into 5; no rule for unsupported requests | capability table (any length, any Polly/Google voice, fonts, fixed output); unsupported → say so, offer nearest, ask; `--help` is the source of truth; hands off to text-2-shorts-produce inside a run | green: 7 min kept, ElevenLabs and 9:16 flagged with alternatives, asked before substituting |
| text-2-shorts-produce | one fixed pipeline: no path for a user's own outline, no revision flow for an approved run, unclear for non-math topics | mandatory rules (checkpoints, gates, user objective wins, status = truth) + artifact/gate table + adaptation cases (own outline, revisions, colours, parallelism, repeated failures) | green + re-test: converts the user's outline, flags a 180 s vs 120 s mismatch and asks, minimal revision path, accuracy check kept |
| manim-ce-0-20-1-reference | paths relative to the skill, stale index path, `api:all` fiction; scripts were drifted copies of tools/; `doc_cards` reported `Axes.plot` as missing | repo-root commands, real index path, version-bump steps; scripts/ are symlinks to tools/ (one source); `doc_cards` resolves `Class.method` | green: every command worked; correct answer (`plot`, `get_graph_label`) |
| text-2-shorts-clip-debugging | did not explain CLIP_SECONDS (lead-in + narration + hold) or the tolerance | finding-code table with formulas and where to read the numbers; classify → fix where it lives | green: exact diagnosis (5.0 + 0.5 < 5.6) |
| text-2-shorts-prompt-maintenance | missed the approach plumbing, model choice per clip, where tone lives | change → files table (all of them), rules, validation, Claude Code doc links | green: complete file list for a new approach, tone and per-clip model |
| clip-builder (agent) | timing conflict with the topic card; EXIT naming and highlight end-state unclear | CLIP_SECONDS wins; EXIT objects may be created/grouped; highlights are temporary unless stated; report missing things instead of inventing | green + re-test: 5.3 s plan, highlight reverts, lbl_abc grouped |
| math-reviewer (agent) | math-only wording; NOTATION severity unclear | accuracy for any topic (math, science, history, facts); explicit severities; empty findings valid | green: 2 ERROR + 1 WARN, correct |

Cross-skill fixes: one timing vocabulary (`CLIP_SECONDS`) in topic cards, builder, debugging and standards;
make-short defers to text-2-shorts-produce inside a run; tool scripts have one source; descriptions trigger-only.
Links verified reachable: Claude Code docs (skills, sub-agents, hooks, plugins, settings, sandboxing, memory), AWS
Polly voices, Google Cloud TTS voices, agentskills.io spec, Manim GitHub releases. Not verifiable from this machine:
docs.manim.community (no response) — the generated API cards still link there.
Remaining limitations: scenario tests are dry runs (no live Claude Code session or video, per the current
no-video rule); per-clip model routing is documented but not built; repo skills also load inside run sessions.

---

## Original assessment (v0.2 package, historical)

**Question answered:** which Claude Skills are needed to *develop, operate and maintain* this system, which exist,
which need customization, and which must be built.

**Historical constraint (v0.2–0.4):** the app's per-stage subprocess calls ran in `--safe-mode`, which disables
skills, CLAUDE.md, hooks and plugins — so skills could only serve the operator session and developers. Since v0.5
(docs/architecture-plan.md §30) the run session itself uses the `run-environment/` plugin's skills, subagents and hooks.
Before v0.5, the runtime agent receives its knowledge as an appended
prompt + generated API/topic cards instead. This is deliberate: runtime context must be minimal and version-exact.

## Summary
| Skill | Category | Who uses it | Location in package | Status |
|---|---|---|---|---|
| make-short | **New** (reconstructs the missing operator skill) | Operator in Claude Code | `custom/make-short/` | PROPOSED (target CLI) + current-CLI section usable now |
| manim-ce-0-20-1-reference | **New** | Developers; topic cards also feed the runtime agent via doc_cards | `custom/manim-ce-0-20-1-reference/` | IMPLEMENTED (scripts + 11 tested topic cards) |
| text-2-shorts-clip-debugging | **New** | Developers | `custom/text-2-shorts-clip-debugging/` | PROPOSED (tools it calls are implemented) |
| text-2-shorts-prompt-maintenance | **New** | Developers | `custom/text-2-shorts-prompt-maintenance/` | PROPOSED (audit tool implemented) |
| skill-creator (Anthropic) | **Reuse as-is** | Developers authoring/evaluating the 4 custom skills | `external/skill-creator/` | vendored, Apache-2.0, commit e4bb5d9 |
| claude-api (Anthropic) | **Reuse as-is** | Developers: prompt caching, cost-optimize, models/pricing, token counting, prompt-audit workflows (Phases 4, 11, 13) | `external/claude-api/` | vendored, Apache-2.0, commit e4bb5d9 |
| manimce-best-practices (community, MIT) | **Reuse with customization** | Developers writing topic cards / reviewing Manim patterns | `external/manimce-best-practices/` | vendored unmodified; required customizations listed in its SOURCE.md |
| webapp-testing (Anthropic) | **Reuse later** | Future review web UI tests (docs/architecture-plan.md §28) | `external/webapp-testing/` | vendored, Apache-2.0 |
| Anthropic template + spec | Reference | Skeleton for new skills | `external/_anthropic-template/` | vendored |
| mcp-builder, docx/pptx/xlsx/pdf, frontend-design | Not required for v1 | — | — | see `external/_reference-only/README.md` |
| Community Manim skills (Yusuke710, vumichien, awesome-skills, manim-composer) | Reviewed, not adopted | — | `external/_reference-only/README.md` | reasons recorded |

## Per-skill detail

### 1. make-short — NEW
- **Purpose:** let a human operate the generator conversationally and safely: one command at a time, show checkpoint
  tables, collect clip-scoped feedback, never generate content in the chat.
- **Capabilities:** maps user intents to `text-2-shorts new/plan/build/final/feedback/approve/status/explain`; recovery rules
  (FAILED clips); current-CLI fallback section for today's `python -m app.cli`.
- **Dependencies:** the `text-2-shorts` CLI (Phase 2+), Claude Code ≥ 2.1.275.
- **Implementation approach:** SKILL.md only (no scripts) — the CLI owns all logic, so the skill cannot drift from it.
  Evaluate with skill-creator's eval loop on 5 scripted conversations (new run, outline revise, clip visual revise,
  failed clip, resume after interrupt).
- **Integration points:** installed at `.claude/skills/make-short/`; reads CLI `--json` outputs; docs/architecture-plan.md §12, §15.

### 2. manim-ce-0-20-1-reference — NEW
- **Purpose:** single source of version-exact Manim knowledge for humans and (via doc_cards) the runtime agent.
- **Capabilities:** build API index from the installed package; API cards for exact names; 11 topic cards (10 with code
  examples that are statically validated and dry-run rendered in tests, plus a removed-API table); static validator; layout/timing probe; harness.
- **Dependencies:** Manim 0.20.1, LaTeX + dvisvgm, ffmpeg.
- **Implementation approach:** generated knowledge (index/cards) + curated-but-tested knowledge (topics). No
  hand-written API lists. Upgrade procedure in SKILL.md and docs/architecture-plan.md §14.4.
- **Integration points:** `app/manim_docs`, `app/render`, runtime TASK/API_CARDS generation, CI.

### 3. text-2-shorts-clip-debugging — NEW
- **Purpose:** fast, evidence-first diagnosis of clip failures from a run directory without spending LLM tokens.
- **Capabilities:** ordered evidence path (ledger → checks → local reproduction → logs/prompts); classification into
  tool false positive / plan defect / code defect, each with a fix route.
- **Dependencies:** run layout (docs/architecture-plan.md §20), tools.  **Integration:** developer workflow; feeds validator/card backlog.

### 4. text-2-shorts-prompt-maintenance — NEW
- **Purpose:** make prompt/schema/model edits safe (cache invalidation, cost regressions, API drift).
- **Capabilities:** contract-first checklist, static/dynamic split rule, catalog audit, prompt versioning, eval gate,
  pointer to claude-api cost workflows.
- **Dependencies:** `tools/audit_prompt_catalog.py`, golden set, `cost_report.py`.

### 5. skill-creator — REUSE AS-IS
Use to draft/iterate the four custom skills and to run description-trigger evals. No changes needed.

### 6. claude-api — REUSE AS-IS
Directly relevant references: `shared/prompt-caching.md` (minimum cacheable prefix 512 tokens on current models,
TTL economics), `shared/cost-optimization.md` (workflow `cost-optimize`), `shared/models.md` (ids, pricing),
`shared/token-counting.md`, `shared/prompt-audit.md` (workflow `prompt-audit` — run it on `run-environment/skills/text-2-shorts-produce/references` and
`run-environment/agents`). Note the skill itself instructs to verify live pricing/models before quoting.

### 7. manimce-best-practices — REUSE WITH CUSTOMIZATION
Validated against 0.20.1 with our validator (results in its SOURCE.md). Customizations: version pin in description,
remove/fix the malformed cli.md block, exclude 3D from default load set, never load in the runtime agent, CI re-check
on pin changes. Predates the 0.20 MathTex rewrite → our mathtex-indexing card supersedes its MathTex indexing advice.

### 8. webapp-testing — REUSE LATER
For Playwright tests of the optional review UI (docs/architecture-plan.md §28). Not used in v1.

## Gap analysis
| Need | Covered by | Gap |
|---|---|---|
| Version-exact Manim API knowledge | generated index/cards | none |
| Manim patterns (layout, timing, MathTex 0.20) | topic cards (11) | add cards from findings histogram (docs/architecture-plan.md §23) |
| Operating the pipeline | make-short | CLI must exist (Phases 2–10) |
| Prompt caching/cost know-how | claude-api | none |
| Video/audio engineering (ffmpeg, loudness) | tools/assemble_clips.py + docs/architecture-plan.md §16.6/§17 | a dedicated skill not warranted yet |
| Math verification tooling | math_verifier prompt; math_lint proposed | sympy LaTeX parsing needs antlr pin (pyproject `[math]`) |
