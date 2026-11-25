"""Write the script_prompts package out as the reference files the run session reads by path.

The prompts are maintained once, in runtime-environment/prompts/script_prompts/ (shared blocks in _shared.py). A run
session reads Markdown references, so this script renders each prompt into
runtime-environment/skills/text-2-shorts-produce/references/ with a short note on how to use it inside a run. A test
fails when the references and the package drift apart.

    uv run python runtime-environment/prompts/export_references.py
"""

import sys
from pathlib import Path

PROMPTS_DIRECTORY = Path(__file__).resolve().parent
REFERENCES_DIRECTORY = PROMPTS_DIRECTORY.parent / "skills" / "text-2-shorts-produce" / "references"
sys.path[:0] = [str(PROMPTS_DIRECTORY), str(PROMPTS_DIRECTORY.parents[1] / "backend")]

import script_prompts
from schemas.outline_models.approaches import APPROACHES

GENERATED = (
    "<!-- GENERATED from runtime-environment/prompts/script_prompts/{module}.py by "
    "runtime-environment/prompts/export_references.py: edit the package (or the approach table), then re-run the export. -->\n"
)
OUTLINE_USE = (
    "**Stage 2 — outline.json ({approach} approach).** Apply the prompt below yourself and write only the JSON "
    "object to `outline.json` (the hook validates it against `VideoOutline` and the approach's stages in `backend/schemas/outline_models/`). "
    "Inputs: `raw_content` = `content.md`; `topic`, `duration_minutes` and `pace` from `brief.json`. The prompt "
    "contains literal JSON braces: never treat it as a format string. The scene_id values become the "
    "`outline_segment` numbers the script narrates in order.\n"
)
TOPIC_USE = (
    "**Stage 1 — topics.md and content.md.** Apply the prompt below yourself with `{user_raw_input}` = the user's "
    "request (`brief.json` → `requirement`, plus anything they said). `brief.json`'s length, audience, objectives "
    "and constraints override the defaults written into the prompt. Write the numbered list to `topics.md` and "
    "confirm it with the user. Then write `content.md`: one `## <topic>` section per topic, in the same order, "
    "with the correct educational content the outline is built from (its `raw_content`).\n"
)
PROMPTS = {
    "topic-list.md": ("req_modifier", "Topic list (request modifier)", TOPIC_USE, "REQ_MODIFIER_SYSTEM"),
}


def references() -> dict[str, str]:
    """Reference file name → its full text: the topic list, then one outline reference per approach."""
    texts = {
        name: GENERATED.format(module=module) + f"# {title}\n\n{use}\n---\n\n{getattr(script_prompts, constant)}\n"
        for name, (module, title, use, constant) in PROMPTS.items()
    }
    for key, approach in APPROACHES.items():
        texts[f"outline-{key}.md"] = (
            GENERATED.format(module="approach_outline")
            + f"# Outline — {approach.name}: {approach.tagline}\n\n{OUTLINE_USE.format(approach=key)}\n---\n\n"
            + f"{script_prompts.outline_system(key)}\n"
        )
    return texts


if __name__ == "__main__":
    for name, text in references().items():
        (REFERENCES_DIRECTORY / name).write_text(text)
        print(f"wrote {REFERENCES_DIRECTORY / name}")
