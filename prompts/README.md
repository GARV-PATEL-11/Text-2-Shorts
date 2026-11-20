# Prompt templates (PROPOSED — not yet in `app/`)

Every template here is a **specification-grade draft**: complete enough to implement, written against the
data contracts in `schemas/models.py`. None is wired into the existing app yet. Status per file is in its header.

## Conventions (apply to every LLM stage)
1. **Static first, dynamic last.** System prompt = role + rules + reference (identical across calls → cacheable).
   Task-specific data goes in the user message, at the END. For `claude -p --system-prompt-file` stages, put the
   line `__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__` between static and any per-run system text (Claude Code ≥ 2.1.275).
   The existing visual-plan prompt violates this: ~5.8k tokens of static output spec sit after the dynamic inputs.
2. **Structured output via `--json-schema`** generated from the Pydantic model (as today). Never ask for JSON in prose
   *and* send a schema that disagrees (today's refactor prompts ask for JSON while the plan is tagged text).
3. **Prompt id + version** (`clip_planner@1`) is recorded in `GenerationMetadata.prompt_id` and is part of the cache key.
   Editing a prompt = bump the version = invalidates exactly the artifacts that prompt produced.
4. **Evidence-bearing critique.** Critics return `defects[]` with `code`, `severity`, and evidence (field path, frame
   time, line). A defect without evidence is discarded by the router. Scores alone never trigger a refactor.
5. **No version-unaware Manim lists in prompts.** Manim API knowledge comes from `doc_cards.py` (generated from the
   installed package) and executable-tested topic cards — not hand-maintained catalogs.
6. **Human feedback is data, not a header.** It arrives as `HumanFeedback` records scoped to one clip/field.

| File | Stage | Model / effort (default, configurable) | Replaces |
|---|---|---|---|
| `outline_review.md` | outline QA (1 pass) | sonnet / medium | `OUTLINE_CRITIC_SYSTEM` + refactor loop (fixed) |
| `clip_planner.md` | scene → clips + narration + contracts | sonnet / high | `NARRATION_SYSTEM` + scene-level Director DSL |
| `math_verifier.md` | math & claims check, whole video, once | sonnet / high (opus for advanced math) | — (new) |
| `clip_builder_agent.md` | sandboxed Claude Code agent writes + renders ONE clip | sonnet / high → retry xhigh | `SCENE_AGENT_PROTOCOL` + codegen + debug prompts |
| `clip_reviewer.md` | multimodal clip QA (conditional) | sonnet / medium | plan critic + agent self-review (partially) |
| `existing_prompt_fixes.md` | patches to keep existing outline prompts | — | — |
