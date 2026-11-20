---
name: t2s-prompt-maintenance
description: Safely change the instructions the Text-2-Shorts run session follows — the env/ skill and its references, the clip-builder / math-reviewer subagents, the topic cards, the hooks, the session settings — or the schemas and validators that check its output. Use when editing anything under env/, schemas/models.py or the validate_* functions in app/clips.py, or when someone asks to improve output quality or token use.
---

# Instruction / contract maintenance

Where things live:
- Workflow + checkpoints: `env/skills/t2s-produce/SKILL.md`; step guidance in `env/skills/t2s-produce/references/`
  (standards, brief, outline per approach, outline review, clip planning).
- Subagents: `env/agents/clip-builder.md`, `env/agents/math-reviewer.md` (frontmatter sets tools and model).
- Manim knowledge: `env/skills/manim-ce-0-20-1-reference/topics/` (tested cards) + `tools/doc_cards.py`.
- Run instructions: `env/workspace/CLAUDE.md`; session sandbox/permissions: `env/settings.json`; hooks: `env/hooks/`.
- Contracts: `schemas/models.py` (+ `schemas/export_json_schemas.py`), `app/graph/models/` (outline);
  rules: `validate_outline`, `validate_plan`, `validate_math` in `app/clips.py`.

An instruction edit is a code change with a blast radius:
1. **Contract first.** The session's files are validated by the hook; an instruction must never ask for a format the
   schema or validator rejects. Change both together, regenerate `schemas/json/`, run `uv run pytest -q`.
2. **Keep the always-loaded part small.** `CLAUDE.md` and SKILL.md bodies load every session; put detail in a
   reference that the skill names for the step that needs it.
3. **No hand-written Manim API lists.** API facts come from generated cards; patterns from topic cards with tested
   examples (`tests/test_topic_cards.py` executes them).
4. **Code numbers have one home.** `STYLE`, `LEAD_IN`, `HOLD` in `app/clips.py` drive behaviour;
   `references/standards.md` must state the same values (`tests/test_env.py` checks it).
5. **Clip-builder edits invalidate clips**: its file is part of every clip's key, so `t2s status` will list all
   clips as stale afterwards — intended, but say so before editing it on a run in progress.
6. **Measure**: compare `uv run t2s report runs/<id>` (tokens, cache share) and the CP3 rejection notes before and
   after on a short test run.
