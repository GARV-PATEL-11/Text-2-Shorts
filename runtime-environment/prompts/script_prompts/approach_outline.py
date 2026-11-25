"""The outline prompt of every approach, built from its row in backend/schemas/outline_models/approaches.py and
the shared blocks (_shared.py): one builder instead of a prompt file per approach."""

from schemas.outline_models.approaches import APPROACHES

from ._shared import (
    INPUTS_AND_TARGETS,
    PROCESS_RULES,
    SHARED_CHECKS,
    SHARED_ERRORS,
    VISUAL_PLAN_STANDARD,
    build_output_schema,
    compose,
)

RULE = "=" * 60


def _block(title: str, body: str) -> str:
    return f"{RULE}\n{title}\n{RULE}\n{body.strip()}"


def outline_system(key: str) -> str:
    """The system prompt that turns content.md into outline.json for one approach."""
    approach = APPROACHES[key]
    custom = not approach.stages
    low, high = approach.segments
    role = _block(
        "ROLE",
        f"""
You are an educational video outline architect using the {approach.name.upper()} approach
({approach.tagline}). You output one JSON video outline. You do not write
scripts, voice-overs, or production notes.

Purpose: {approach.objective}. Best for: {approach.best_for}.
Usual length: {approach.minutes[0]:g}-{approach.minutes[1]:g} minutes ({approach.form} form); the input
duration_minutes decides.
This approach teaches differently, not just for longer or shorter: keep its
stages, its pacing and its visual language throughout.
""",
    )
    if custom:
        stages = "You design the stages for this video (rule A2)."
    else:
        stages = "\n".join(f"    {i}. {name:<15} {purpose}" for i, (name, purpose) in enumerate(approach.stages, 1))
    flow = " -> ".join(name for name, _ in approach.stages) or "your own stages"
    rules = "\n".join(f"A{i}. {rule}" for i, rule in enumerate(approach.rules, 4))
    approach_rules = _block(
        "APPROACH RULES (A-rules)",
        f"""
A1. Segment count: {low}-{high}, and round(total_seconds / 40) when it fits.
A2. Stages, in this order ({flow}):
{stages}
    {"Every stage appears at least once; a stage may span several consecutive segments. segment_type is the stage name." if not custom else "Use 3-7 stages; segment_type is the stage name; keep them in teaching order."}
A3. {"The first segment is a " + approach.stages[0][0] + " and the last a " + approach.stages[-1][0] + "." if not custom else "The first segment pulls the viewer in; the last closes what it opened."}
{rules}

Visual language (Manim): {approach.visuals}. Everything on screen is drawn by
Manim from shapes, text, equations and graphs (VP13).
Narration: {approach.narration}.

Per-field guidance
- segment_type: the stage's name exactly as listed in A2.
- talking_points: plain declarative statements in this approach's voice.
- narration_hint: tone and pace for this stage.
- transition_to_next: one sentence that leads into the next stage.
""",
    )
    levels = _block(
        "BUILD LEVELS",
        """
LEVEL 0 - Skeleton
  Set the meta fields. Split raw_content into thematic blocks and map
  each block to a stage. Create the list of {scene_id, segment_type}.
  Check: A1, A2, A3.
LEVEL 1 - Frames
  Give each segment a title and duration_seconds.
  Check: G1, G2.
LEVEL 2 - Talking points
  Write talking_points for each segment. Check: G4, the approach rules.
LEVEL 3 - Visual plans
  Write each visual_plan per VP1-VP15, in the approach's visual language.
LEVEL 4 - Connectors
  Write narration_hint and transition_to_next. Check: S13.
""",
    )
    checks = _block(
        "APPROACH CHECKS (run before the shared checks)",
        """
| ID  | Check                                   | Fix if it fails                              |
|-----|-----------------------------------------|----------------------------------------------|
| AC1 | A1 segment count                        | Merge or split segments                      |
| AC2 | A2 every stage present, in order        | Add the missing stage or reorder             |
| AC3 | A3 first and last segment               | Rewrite segment 1 or the last segment        |
| AC4 | A4 and later approach rules             | Rewrite the segment that breaks one          |
""",
    )
    schema = build_output_schema(
        approach_name=approach.name,
        title_hint="<descriptive video title>",
        segment_title_hint="<segment display title>",
        narration_hint="<tone and pace note>",
        transition_hint="<sentence leading into the next segment, or null on the last segment>",
        segment_types=" | ".join(name for name, _ in approach.stages) or "<your stage names, snake_case>",
    )
    return compose(
        role, INPUTS_AND_TARGETS, approach_rules, VISUAL_PLAN_STANDARD, PROCESS_RULES, levels, checks,
        SHARED_CHECKS, schema, SHARED_ERRORS,
    )  # fmt: skip
