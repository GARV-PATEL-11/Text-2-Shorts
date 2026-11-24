# Prompt specifications

The implemented instructions live in the Claude Code environment: `run-environment/skills/text-2-shorts-produce/` (workflow +
references) and `run-environment/agents/` (clip-builder, accuracy-reviewer).
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
4. **Human feedback is data**: `requests.jsonl` change requests targeting outline / script / sNN / sNNcMM.
