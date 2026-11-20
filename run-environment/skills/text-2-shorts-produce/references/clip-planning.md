# Planning one scene as clips

You plan one scene of an animated math/science explainer (Manim, 2D, 16:9) as a sequence of CLIPS.
A clip is the unit that will be animated, rendered, reviewed and regenerated on its own.

CLIP RULES
1. One teaching purpose per clip. If the objective needs "and", split it.
2. 2–6 clips per scene; 4–20 s of narration per clip (hard max 30 s). The scene's clips together should match the
   scene's duration_seconds.
3. narration: the exact words the voice will say, following "Narration text" in VIDEO STANDARDS (symbols in
   backticks, [pause] markers, no markdown, numbers ≤ 2 decimals). Word budget per clip
   = est_seconds × target_wpm / 60 (±10%). Across the scene, cover the scene's talking_points in order.
4. beats: 1–8 visual events in narration order. Each beat names the narration phrase it starts on, in quotes,
   then what visibly changes. Example: "\"the hypotenuse\" → side c highlights in YELLOW".
   One visual event per phrase; never two unrelated events during one sentence.
5. on_screen_math: every LaTeX string that appears, exactly as it should render (raw LaTeX, no $).
   Keep a formula on screen while the narration discusses it.
6. Continuity contracts. entry = what is on screen when the clip starts; exit = what must remain at its end.
   Name objects with snake_case registry names (eq_main, axes, curve_f). Clip N+1's entry must equal clip N's exit.
   The FIRST clip's entry and the LAST clip's exit are always empty: each scene renders separately.
   Transitions between scenes are visual: the last clip's final beat leads into transition_to_next and fades the
   scene out; when the outline continues an idea, the first clip's first beat re-draws PREVIOUS SCENE FINAL IMAGE
   (same objects, colours and zones) before moving on, so the cut feels like one continuous video.
7. object_positions use semantic zones only: top_center, top_left, top_right, center, left_half, right_half,
   bottom_center, bottom_left, bottom_right.
8. manim_topics: choose from this closed list only: clip-structure, mathtex-indexing, text-and-latex,
   positioning-layout, timing-and-sync, transforms, axes-and-graphs, camera, updaters-and-trackers, emphasis.
9. Do not introduce facts, formulas or numbers that are not in the scene's talking points or derivable from them.
   If a talking point is ambiguous, keep the claim narrower rather than adding content.
10. Screen budget: at most 2 text blocks and 1 diagram visible at once; say in beats when things leave.
11. Ids: scene_id is given; clip_id = scene_id + "c" + two-digit index (s02c01, s02c02, …); index starts at 1.
12. color_roles: map every math symbol and recurring object of this scene to one palette constant. Reuse SYMBOL
   COLORS SO FAR exactly; add only symbols that are new in this scene.
13. Pacing: about one [pause] per clip, after the key result; beats never put motion inside a pause.
14. HUMAN FEEDBACK, when present, overrides everything above for what it mentions.

target_wpm by brief pace: slow 130 · medium 150 · fast 170.
on_screen_math may be empty: for subjects without formulas, put the key terms, dates or labels in beats and
visual_intent instead.
Inputs to gather first: the outline scene, one-line summaries of the other scenes, SYMBOL COLORS SO FAR (the
color_roles of earlier scenes' plan.json files), PREVIOUS SCENE FINAL IMAGE (the last clip's visual_intent and final
beat of the previous scene), and feedback.jsonl rows for this scene or its clips.
Output: write scenes/sNN/plan.json matching schemas/json/ScenePlan.schema.json, then run
`t2s validate <run> plan --scene sNN` and fix every error it reports.
