# Prompt specifications

The implemented prompts are code: `app/clips.py` (`CLIP_PLANNER_SYSTEM`, `MATH_VERIFIER_SYSTEM`,
`CLIP_BUILDER_SYSTEM`) and `app/graph/prompts/` (brief refiner, the three outline approaches, outline critic).
This folder keeps the two specified stages that are NOT built:

| File | Stage | Why not built |
|---|---|---|
| `outline_review.md` | single-pass outline QA | the existing outline critic + deterministic length check cover it |
| `clip_reviewer.md` | multimodal clip QA | the human reviews every scene at CP3; add when CP3 rejections show a pattern a model could catch |

## Conventions (apply to every LLM stage)
1. **Static first, dynamic last.** System prompt = role + rules + reference, byte-identical across calls (prompt
   cache); task data goes in the user message.
2. **Structured output via `--json-schema`** generated from the Pydantic model. Never ask for a format in prose that
   the schema does not describe.
3. **No hand-written Manim API lists.** API facts come from `tools/doc_cards.py` (generated from the installed
   package) and the tested topic cards.
4. **Human feedback is data**: `feedback.jsonl` rows scoped to outline / sNN / sNNcMM.
