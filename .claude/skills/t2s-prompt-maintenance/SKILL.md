---
name: t2s-prompt-maintenance
description: Safely change any LLM prompt, topic card, schema or model/effort setting in the Text-to-Shorts project. Use when editing files under app/prompts (or app/graph/prompts), prompts/, .claude/skills/manim-ce-0-20-1-reference/topics, schemas/models.py or config/stages.yaml, or when someone asks to reduce cost or improve output quality of a stage.
---

# Prompt / contract maintenance

Status: PROPOSED.

A prompt edit is a code change with a blast radius: it invalidates cached artifacts and can silently shift cost.
1. **Find the contract first.** Every stage's output is a Pydantic model (`schemas/models.py`); the prompt must
   agree with the schema sent via `--json-schema`. Never ask for a format the schema does not describe.
2. **Static before dynamic.** Keep role/rules/reference text byte-identical across calls and put per-call data last
   (prompt caching). Check `cache_read` vs `cache_write` in `log.jsonl` before and after.
3. **No hand-written Manim API lists.** API facts come from generated cards; patterns from topic cards with tested
   examples. Run `python tools/audit_prompt_catalog.py <prompt files> --index <index>` — it must report no
   "banned_in_prompt_but_exists_in_api" and no unexplained "not_in_api" names.
4. **Bump the prompt version** (`clip_planner@2`). This changes cache keys of exactly the artifacts it produces.
5. **Run the evals**: `pytest tests/` (contracts, tools) and the golden-topic regression set (Plan.md §22.4) for any
   stage whose prompt changed; compare first-pass gate success, tokens per clip and cost per clip against the
   baseline in `reports/baseline.json`. Do not merge a change that raises cost >10% without a quality gain.
6. For cost work, the vendored `claude-api` skill (`skills/external/claude-api`, workflow `cost-optimize` and
   `shared/prompt-caching.md`) is the reference for caching rules and pricing — check live pricing before quoting.
