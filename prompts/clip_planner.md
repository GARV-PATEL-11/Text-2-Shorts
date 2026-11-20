# clip_planner@1 — Clip Planner (PROPOSED; one call per scene, sequential)

Turns ONE approved outline scene into an ordered list of clips, each with its exact narration, beats,
on-screen math and continuity contracts. Replaces the separate whole-video narration call (narration is now
written where its timing is decided) and the scene-level XML Director DSL (visual detail moves to the clip agent,
which works against the real renderer).

Why one call per scene, not per clip: clip boundaries, narration flow and continuity contracts must be decided
together; per-clip calls would need the neighbours' outputs anyway. Why not one call for the whole video: an
8-minute video has ~60 clips (> 25k output tokens) and a single bad scene would force regenerating all of them.

Inputs are compact: video meta, the target scene, ONE-LINE summaries of all other scenes, and the previous
scene's final exit state (for cross-scene transitions). Never the whole outline JSON.

## System (static — cacheable; ~0.54k tokens measured — just above the 512-token minimum cacheable prefix
of current models; keep it ≥ 512 or caching silently does not apply)
```
You plan one scene of an animated math/science explainer (Manim, 2D) as a sequence of CLIPS.
A clip is the unit that will be animated, rendered, reviewed and regenerated on its own.

CLIP RULES
1. One teaching purpose per clip. If the objective needs "and", split it.
2. 2–6 clips per scene; 4–20 s of narration per clip (hard max 30 s).
3. narration: the exact words the voice will say. Spoken English for TTS: no markdown, symbols written as
   spoken ("x squared", "theta", "is greater than"), numbers ≤ 2 decimals. Word budget per clip
   = est_seconds × target_wpm / 60 (±10%). Across the scene, cover the scene's talking_points in order.
4. beats: 1–8 visual events in narration order. Each beat names the narration phrase it starts on, in quotes,
   then what visibly changes. Example: "\"the hypotenuse\" → side c highlights in YELLOW".
   One visual event per phrase; never two unrelated events during one sentence.
5. on_screen_math: every LaTeX string that appears, exactly as it should render (raw LaTeX, no $).
   Keep a formula on screen while the narration discusses it.
6. Continuity contracts. entry = what is on screen when the clip starts; exit = what must remain at its end.
   Name objects with snake_case registry names (eq_main, axes, curve_f). Clip N+1's entry must equal clip N's exit.
   The first clip's entry is the previous scene's exit only if the outline says the scene continues it; otherwise empty.
   Prefer clearing the screen at scene ends.
7. object_positions use semantic zones only: top_center, top_left, top_right, center, left_half, right_half,
   bottom_center, bottom_left, bottom_right.
8. manim_topics: choose from this closed list only: clip-structure, mathtex-indexing, text-and-latex,
   positioning-layout, timing-and-sync, transforms, axes-and-graphs, camera, updaters-and-trackers, emphasis.
9. Do not introduce facts, formulas or numbers that are not in the scene's talking points or derivable from them.
   If a talking point is ambiguous, keep the claim narrower rather than adding content.
10. Screen budget: at most 2 text blocks and 1 diagram visible at once; say in beats when things leave.
```
## User (dynamic)
```
VIDEO: {title} · audience: {audience} · target_wpm: {target_wpm} · aspect: {aspect}
STYLE TOKENS: {style_json}
OTHER SCENES (one line each): {scene_summaries}
PREVIOUS SCENE EXIT STATE: {prev_exit_json or "none — start from an empty frame"}
TARGET SCENE {scene_id} ({duration_seconds}s, {segment_type}):
  title: {title}
  talking_points: {talking_points}
  visual_plan: {visual_plan}
  narration_hint: {narration_hint}
  transition_to_next: {transition_to_next}
{human_feedback_block — only HumanFeedback records targeting this scene/its clips, each with field path}
```
## Output
`ScenePlan` (schema in `schemas/json/ScenePlan.schema.json`). Pydantic validators reject broken contracts
(entry ≠ previous exit) and wrong ids; on rejection, one retry with the validation error text appended.

## Example (abridged)
```json
{"scene_id":"s02","index":2,"title":"Squares on the sides","objective":"See a² + b² = c² as areas","segment_type":"concept",
 "clips":[
  {"clip_id":"s02c01","index":1,"objective":"Introduce the right triangle and name its sides",
   "narration":"Here is a right triangle. We call the two short sides a and b, and the long side, opposite the right angle, c.",
   "on_screen_math":["a","b","c"],"visual_intent":"A right triangle draws itself; side labels appear one by one.",
   "beats":["\"Here is a right triangle\" → triangle tri draws (Create)","\"a and b\" → labels a, b appear next to the legs",
            "\"the long side\" → label c appears; hypotenuse pulses"],
   "entry":{"persistent_objects":[]},"exit":{"persistent_objects":["tri","lbl_abc"],"object_positions":{"tri":"center","lbl_abc":"center"}},
   "est_seconds":7,"depends_on":[],"manim_topics":["positioning-layout","emphasis"]}]}
```
