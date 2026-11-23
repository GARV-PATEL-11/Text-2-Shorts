# Stage 3 — Scene-wise visual and audio planning (read after CP1)

Plan the approved script one scene at a time (s01, s02, …) as `scenes/sNN/plan.json` (schema `ScenePlan`): what is
shown and how it is spoken, together. A scene is a sequence of CLIPS: the units that are animated, voiced, checked
and rebuilt on their own. Complete, validate and critique the plans of every scene before CP2; no voice and no
clip code until CP2 is approved.

Inputs per scene (no more — keep context small): this scene from `script.json`; the other scenes' titles and
objectives; SYMBOL COLORS SO FAR (`color_roles` of the earlier plans); PREVIOUS SCENE FINAL IMAGE (last clip's
visual intent and final beat of the previous plan); `feedback.jsonl` rows for this scene; standards.md;
transitions.md; audio-ssml.md. Look up Manim names with `text-2-shorts doc Name1,Name2`.

What the plan must decide, and where it goes
| Aspect | Field |
|---|---|
| visual elements and composition | `composition` (zones, main objects, 2–4 sentences) + `color_roles` |
| opening transition from the previous scene | `transition_in` (empty for s01; transitions.md) |
| animation types and movement | `beats` and `visual_intent` of each clip |
| positioning, scaling, transformations | `beats`, `entry`/`exit` `object_positions` (zones) |
| fades, highlights, timing | `beats` (each starts on a quoted narration phrase), `est_seconds` |
| sync with narration | each beat quotes the phrase it starts on (the clip marks it with `self.beat(n)`) |
| lags, waits, pauses, pace, emphasis | `ssml` of each clip (audio-ssml.md) |
| entry and exit states | `entry` / `exit` continuity contracts |

Clip rules
0. *SSML: each clip's `ssml` holds exactly its narration words, with tags for waits and pace (audio-ssml.md).
1. *Narration: split the scene's spoken text (bridge_in, then narration) into consecutive pieces, word for word —
   the gate compares them with the approved script. To change wording, change the script (CP1 again).
2. One teaching purpose per clip ("and" → split). 2–6 clips per scene; 4–20 s of narration each (hard max 30 s).
3. beats: 1–8 visual events in narration order, each naming the phrase it starts on, then what visibly changes:
   `"\"the hypotenuse\" → side c highlights in YELLOW"`. One visual event per phrase.
4. on_screen_math: every LaTeX string that appears, exactly as it renders (raw LaTeX, no $). Keep a formula on
   screen while the narration discusses it. Subjects without formulas: key terms and labels go in beats.
5. *Continuity: entry = what is on screen when the clip starts, exit = what must remain at its end, as snake_case
   registry names (eq_main, axes). Clip N+1's entry = clip N's exit. *The first clip's entry and the last clip's exit
   are empty: each scene renders separately. Transitions between clips stay simple (transitions.md).
   *Describe every object you carry into the next clip in `descriptions` (type, text or LaTeX, colour, size):
   clips are built in parallel, and a clip run alone re-creates what it takes over from that description.
6. object_positions use zones only: top_center, top_left, top_right, center, left_half, right_half,
   bottom_center, bottom_left, bottom_right.
7. manim_topics: from the topic cards only: clip-structure, mathtex-indexing, text-and-latex, positioning-layout,
   timing-and-sync, transforms, axes-and-graphs, camera, updaters-and-trackers, emphasis.
8. *color_roles: one palette constant per math symbol and recurring object; reuse SYMBOL COLORS SO FAR exactly.
9. Screen budget: at most 2 text blocks and 1 diagram at once; say in beats when things leave. Nothing moves
   during a [pause].
10. Ids: clip_id = scene_id + "c" + two-digit index (s02c01, …); index starts at 1.
11. HUMAN FEEDBACK, when present, overrides the above for what it mentions.

Per scene, after writing the plan:
1. `text-2-shorts validate . plan --scene sNN` (the hook also runs it) and fix every error.
2. Critic loop — at most 3 rounds: **plan-critic** subagent appends a round to `scenes/sNN/plan_critique.json`
   (clarity · sync · constructability in Manim 0.20.1 · design). On "revise", refactor the plan, validate, and run
   the next round. After round 3, whatever is still open goes to the user at CP2.
After all scenes: accuracy-reviewer subagent (plan mode) → `plan_review.json`; fix ERRORs. CP2: show the user,
per scene, the composition, transition_in, a clip table (clip, seconds, objective, beats, pauses) and the last
critique round; on approval `text-2-shorts approve . plan`. Editing a plan after CP2 needs CP2 again — except
SSML-only changes by the audio-refactorer, which re-time the audio to the built video.
