"""Shared prompt blocks for the outline prompts (Approaches A, B, C).

Each approach file composes these blocks with its own rules. Every rule
lives in exactly one place, so a change here applies to all approaches.

Plain string concatenation is used (no f-strings, no .format) because the
blocks contain literal JSON braces.
"""

# ---------------------------------------------------------------------------
# Inputs, computed targets, global limits
# ---------------------------------------------------------------------------
INPUTS_AND_TARGETS = """
============================================================
INPUTS
============================================================
  raw_content       required  educational text to outline
  topic             optional  topic name for meta.title; default: inferred
                              from raw_content
  duration_minutes  optional  target video length; default: 5
  pace              optional  "slow" | "medium" | "fast"; default: "medium"
If an optional input is missing, use its default and continue.

============================================================
COMPUTED TARGETS (compute these first)
============================================================
  target_wpm          slow = 110, medium = 140, fast = 165
  total_seconds       = duration_minutes x 60
  timing_lower        = floor(total_seconds x 0.90)
  timing_upper        = ceil(total_seconds x 1.10)
  segment_count       = see APPROACH RULES (always between 4 and 10)
  words(segment)      = round(duration_seconds / 60 x target_wpm)
  sentences(segment)  = clamp(round(duration_seconds x 0.7), 20, 60)
                        -> required length of that segment's visual_plan
  Example (5 min, medium): total_seconds = 300, valid sum = 270-330,
  target_wpm = 140, a 60-second segment needs about 140 words of
  talking points and a 42-sentence visual_plan.

============================================================
GLOBAL LIMITS (G-rules, all approaches)
============================================================
G1. timing_lower <= sum of all duration_seconds <= timing_upper.
G2. 10 <= duration_seconds <= 120 for every segment.
G3. 4 <= number of segments <= 10.
G4. 2 to 8 talking_points per segment, one idea per point. Their total
    word count is within 15% of words(segment). Delivery never exceeds
    200 words per minute.
G5. A segment covers at most 2 thematic blocks. If it covers more,
    split it and rebalance timing.
G6. Every thematic block in raw_content maps to at least one segment.
G7. These rules apply to any subject. The machine-learning examples
    below show the standard; replace their content with the topic's own.
""".strip()


# ---------------------------------------------------------------------------
# Visual plan standard
# ---------------------------------------------------------------------------
VISUAL_PLAN_STANDARD = """
============================================================
VISUAL PLAN STANDARD (VP-rules, all approaches)
============================================================
visual_plan describes, in plain English, what the viewer sees in one
segment, from an empty canvas to the final frame. A separate stage turns
it into animation code, so it describes the viewer's experience, not
instructions to a programmer.

Form
VP1.  Write continuous prose: full sentences, one paragraph, no bullets,
      no numbering, no line breaks inside the string.
VP2.  Length: exactly sentences(segment) sentences or more, with one
      visual event per sentence.
VP3.  The first sentence describes the empty canvas before anything
      appears.
VP4.  The last sentence begins "The scene ends with", lists every element
      still visible, and states the idea that frame leaves the viewer
      with.
VP5.  Write all on-screen text in single quotes, e.g. 'best-fit line'.
      Never use double quotes inside visual_plan (they break the JSON).

Self-containment
VP6.  Introduce every element inside this visual_plan. The animator
      starts each segment on an empty canvas and has not seen any other
      segment. NEVER write: "same as before", "as shown earlier",
      "continue from", "reuse", "the existing", "from the opening", or
      any reference to an object from another segment. To show something
      again, rebuild it from scratch in this plan.

Motion and density
VP7.  The scene is always moving. Never write more than 2 consecutive
      sentences in which nothing appears, moves, changes, or leaves.
      A deliberate pause counts as one sentence and is allowed at most
      twice per plan.
VP8.  Build each visual as a chain: it is constructed piece by piece, a
      label or annotation joins it, attention moves to one feature, that
      feature is compared, tested, or transformed, and the chain ends in
      a takeaway.
VP9.  At least two elements are visible and active at any moment (for
      example, a main visual plus a label or highlight). Use the width of
      the frame: describe placement in words (left, right, above, beside,
      in the corner), not as coordinates.
VP10. For anything that transforms, state both its starting and its
      ending appearance.
VP11. For graphs and equations, state how they first appear, what changes,
      and what the final state shows.
VP12. Include at least one reinforcement moment: the segment's core idea
      shown a second way (a side-by-side comparison, a worked instance,
      or a before/after panel).

What can be drawn
VP13. Describe only things that can be drawn with simple shapes, arrows,
      lines, axes, graphs, number lines, equations, tables, labels, cards,
      flowcharts, icons, and timelines. The view may move closer to or
      away from a region. NEVER describe photographs, lighting, blur,
      particles, realistic 3D rendering, or film effects.
VP14. NEVER name a specific color or background. Describe emphasis by
      role instead: highlighted, accent, dimmed, faint, muted, brighter.
      All colors come from the visual template at render time.
VP15. NEVER include coordinates, pixel sizes, object IDs, function or
      class names, or any animation-library term.

------------------------------------------------------------
REFERENCE EXAMPLE (mechanism segment, 40 seconds, target 28 sentences)
------------------------------------------------------------
The scene opens on an empty canvas with nothing on it, held for a moment so the viewer knows the picture will be built from nothing. A horizontal line draws itself outward from the center in both directions, forming the base of a coordinate frame. A vertical line draws itself through the middle of the first, completing a pair of axes that fill most of the frame. Small tick marks appear one after another along the horizontal axis, each a beat after the last. Matching tick marks appear the same way along the vertical axis. A faint grid spreads softly behind the axes, giving the space a sense of measurement without competing for attention. A single data point appears near the lower left of the graph. A second point appears slightly higher and to the right, inviting the viewer to compare their heights. More points appear one at a time until about a dozen form a loose upward trend with clear scatter. A straight line sweeps onto the graph at a clearly wrong angle, passing far below some points and far above others. Thin vertical connectors grow from each point to the line, one at a time, marking the gap between each prediction and the real value. The longest connectors briefly flash highlighted so the viewer sees how poor this first guess is. A small label in the upper right corner fades in reading 'loss' beside a large number. The line tilts by a small step, and every connector stretches or shrinks to match the new angle. The loss number ticks down to a smaller value. The line tilts again by a smaller step, the connectors adjust again, and the number drops again. A faint outline of the line's earlier position lingers for a moment and then fades, showing the path of the adjustment. The line now shifts slightly upward instead of tilting, and the connectors and the loss number update once more. Several more rounds of tilting and shifting follow, each smaller than the last, so the motion visibly slows. The three connectors that were longest at the start are highlighted together, showing how much shorter they have become. A small panel appears in the lower right corner showing a miniature of the first, badly placed line beside a miniature of the current line. The panel holds long enough for the viewer to compare the two and then fades away. The line makes a few last, barely visible adjustments, each lowering the loss number by a smaller amount. The line stops moving, and every connector is now a short stub between its point and the line. The loss number settles on its lowest value and gains a soft highlight to show it has stopped changing. A label reading 'best-fit line' fades in just above the line, tilted to match its angle. The background grid dims slightly, pushing attention onto the line, the points, and the labels. The scene ends with the axes, the scattered points, the settled best-fit line, the short connectors, the final loss value, and the 'best-fit line' label all visible together, showing that the best line is the one that leaves the smallest total gap to the data.

------------------------------------------------------------
COUNTER-EXAMPLE (fails VP1, VP2, VP3, VP4, VP6, VP10)
------------------------------------------------------------
Show previous graph. Move the line slightly. Transform the graph.
Reduce the loss. Highlight it.
Why it fails: it refers to another segment's graph, is written as
commands, has 5 sentences instead of the target, never says what the
viewer sees, and has no final-frame sentence.
""".strip()


# ---------------------------------------------------------------------------
# Shared checks
# ---------------------------------------------------------------------------
SHARED_CHECKS = """
============================================================
SHARED CHECKS (run after the approach checks)
============================================================
| ID  | Check                                               | Fix if it fails                                            |
|-----|-----------------------------------------------------|------------------------------------------------------------|
| S1  | G1 total time in range                              | Move seconds between adjacent segments; the densest        |
|     |                                                     | segment keeps the largest share                            |
| S2  | G2 every segment 10-120 s                           | Merge a short segment into a neighbor or split a long one  |
| S3  | G3 segment count 4-10                               | Merge the two most similar segments, or split the densest  |
| S4  | G4 talking-point count and word budget              | Add, cut, or tighten points                                |
| S5  | G6 every thematic block is covered                  | Add a segment or extend the closest compatible one         |
| S6  | VP1 prose, VP5 single quotes                        | Rewrite as one prose paragraph; convert quotes             |
| S7  | VP2 sentence count >= sentences(segment)            | Add chained visual events (VP8) until the count is met     |
| S8  | VP3 opening and VP4 closing sentences               | Add the missing sentence                                   |
| S9  | VP6 no references to other segments                 | Rebuild the referenced element from scratch                |
| S10 | VP7 no idle stretch longer than 2 sentences         | Insert a change, highlight, or comparison                  |
| S11 | VP12 reinforcement moment present                   | Add a comparison, worked instance, or before/after panel   |
| S12 | VP13-VP15 renderable, no colors, no implementation  | Replace with drawable elements and role words              |
| S13 | transition_to_next is null only on the last segment | Write the missing transition or set the last one to null   |
| S14 | Output is one valid JSON object matching the schema | Fix field names, types, escaping                           |
""".strip()


# ---------------------------------------------------------------------------
# Process and output rules
# ---------------------------------------------------------------------------
PROCESS_RULES = """
============================================================
HOW TO WORK
============================================================
1. Do all planning, checking, and fixing internally.
2. Build the outline level by level (LEVEL 0 to LEVEL 4 below). Finish and
   check each level before starting the next.
3. Run the approach checks, then the shared checks. Fix every failure
   with the smallest change, then run all checks again. Repeat until every
   check passes.
4. Output only the final JSON object: no reasoning, no check results, no
   correction notes, no markdown fences, no text before or after it.
""".strip()


_OUTPUT_SCHEMA_TEMPLATE = """
============================================================
OUTPUT SCHEMA (strict)
============================================================
Field name for the segment ID is "scene_id" (never "id").

{
  "meta": {
    "title": "__TITLE_HINT__",
    "topic": "<topic name>",
    "total_duration_seconds": <integer>,
    "pace": "slow" | "medium" | "fast",
    "target_wpm": <integer>,
    "approach_name": "__APPROACH_NAME__",
    "approach_style": "<one line describing this outline's style>"
  },
  "outline": [
    {
      "scene_id": <integer, starting at 1>,
      "segment_type": "<allowed value>",
      "title": "__SEGMENT_TITLE_HINT__",
      "duration_seconds": <integer>,
      "talking_points": ["<point>", "<point>"],
      "visual_plan": "<one prose paragraph following VP1-VP15>",
      "narration_hint": "__NARRATION_HINT__",
      "transition_to_next": "__TRANSITION_HINT__"
    }
  ]
}

Allowed segment_type values:
  hook | problem | intro | concept | math | visualization | mechanism |
  application | tradeoffs | recap | cta
""".strip()


def build_output_schema(approach_name, title_hint, segment_title_hint, narration_hint, transition_hint):
    """Return the shared schema block with approach-specific field hints."""
    return (
        _OUTPUT_SCHEMA_TEMPLATE.replace("__APPROACH_NAME__", approach_name)
        .replace("__TITLE_HINT__", title_hint)
        .replace("__SEGMENT_TITLE_HINT__", segment_title_hint)
        .replace("__NARRATION_HINT__", narration_hint)
        .replace("__TRANSITION_HINT__", transition_hint)
    )


# ---------------------------------------------------------------------------
# Shared error handling
# ---------------------------------------------------------------------------
SHARED_ERRORS = """
============================================================
ERROR HANDLING
============================================================
E1. raw_content is missing or empty -> output exactly:
    {"error": "raw_content is required. Provide the educational text to outline.", "code": "MISSING_INPUT"}
E2. Total word budget (duration_minutes x target_wpm) is under 200 words,
    or duration_minutes is under 3 -> use 4 segments; VP2 still applies.
E3. raw_content cannot fill the duration -> add an "application" segment
    whose visual_plan works one concrete example from start to finish.
E4. Content produces more than 10 segments -> merge the two most similar
    thematic blocks into one segment and write one combined visual_plan.
E5. Unsure whether the first segment is "hook" or "intro" -> use "hook"
    if it is under 30 seconds and poses a question; otherwise "intro".
""".strip()


def compose(*blocks):
    """Join prompt blocks with blank lines."""
    return "\n\n".join(block.strip() for block in blocks)
