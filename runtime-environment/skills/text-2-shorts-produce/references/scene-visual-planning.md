# Stage 3 — Scene-wise visual and audio planning (read after CP1)

The **scene-planner** subagent (Opus) is the Visual Director: it plans the approved script one scene at a time
(s01, s02, …) and refactors the plans after critique rounds and visual change requests. Per scene it writes ONE file,
`scenes/sNN/plan.json` (schema `ScenePlan`):
- `execution_plan`: the Scene Execution Plan — atomic, time-ordered events, what is on screen and what is said at
  every moment (rules D0-D19: `visual-director-system.md`; format and checks K1-K13:
  `visual-director-output-spec.md`, printed filled for the scene by `text-2-shorts plan-task . --scene sNN`); the code
  generator implements exactly this;
- every other field, derived from it: what the gate, the voice, the critics and the website read.
A scene is a sequence of CLIPS: the units that are animated, voiced, checked and rebuilt on their own (4-20 s of
narration each, rule D0). Complete, validate and critique the plans of every scene before CP2; no voice and no clip
code until CP2 is approved. The code generator turns the whole execution plan into the scene's one Manim file, each
clip one section of it.

From the execution plan to plan.json
| plan.json | from the execution plan |
|---|---|
| `title`, `objective` | SCENE_OVERVIEW title; its key ideas, in one sentence |
| `composition` | LAYOUT_PLAN and the Visual Arc, 2-4 sentences |
| `transition_in` | how CLIP 1 opens (empty for s01; transitions.md) |
| `color_roles` | COLOR_MAP: each math symbol and recurring object → its TPL role name |
| `clips[n].objective` | CLIP n's KEY IDEA |
| `clips[n].narration`, `ssml` | CLIP n's SPEECH phrases, joined word for word; SSML over exactly those words |
| `clips[n].beats` | 1-8 lines in narration order, each `"phrase" → what visibly changes (event ids)`, one per narrated group of events |
| `clips[n].visual_intent` | what the viewer sees in CLIP n, 2-6 sentences, no code |
| `clips[n].on_screen_math` | every Tex/MathTex string of CLIP n, raw LaTeX, no $ |
| `clips[n].entry` / `exit` | OBJECT STATES start / end: registry names, LAYOUT_PLAN zones, and `descriptions` from OBJECT_REGISTRY LOOK |
| `clips[n].est_seconds` | CLIP n's duration |
| `clips[n].sound_effects` | the user's own files only (`assets/…`), `at` in seconds from the clip's start |

Rules for plan.json (the gate checks the starred ones)
1. *Narration: the clips split the scene's spoken text (bridge_in, then narration) into consecutive pieces, word for
   word — the gate compares them with the approved script. To change wording, change the script (CP1 again).
2. *SSML: each clip's `ssml` holds exactly its narration words, with tags for waits and pace (audio-ssml.md).
3. *execution_plan: every section of the output spec, in order, and one CLIP block per plan.json clip.
4. *Continuity: clip N+1's entry = clip N's exit. The first clip's entry and the last clip's exit are empty: each
   scene renders separately (D1). Describe every object carried into the next clip in `descriptions` (type, text
   or LaTeX, colour role, size token), so a clip run alone re-creates it.
5. Positions use the director's zones only: TOP_STRIP, MAIN_CANVAS, SIDE_PANEL, BOTTOM_BAR, CENTER, FULL_SCREEN.
6. *color_roles: one colour role per math symbol and recurring object; reuse earlier scenes' roles exactly.
7. Screen budget: at most 2 text blocks and 1 diagram at once (rule L9); nothing moves during a [pause].
8. Ids: clip_id = scene_id + "c" + two-digit index (s02c01, …); index starts at 1. `manim_topics`: leave empty.
9. The script scene's `on_screen_text` must appear in a clip (visual_intent, beats or on_screen_math); its
   `animations`, `audio_requirements` and `transition_requirements` shape the events, SSML and transition_in.
10. Template: its colour roles, font, text sizes and safe area; layout, motion and density are yours.
11. HUMAN FEEDBACK, when present, overrides the above for what it mentions.

Per scene, after writing plan.json:
1. `text-2-shorts validate . plan --scene sNN` (the hook also runs it) and fix every error.
2. Critic loop — at most 3 rounds; an open basic issue (or a score under a user-set `quality_threshold`) sends it back; tiers, scoring
   and how to refactor from a round: critique-protocol.md:
   **plan-critic** subagent appends a round to `scenes/sNN/plan_critique.json` (clarity · sync · constructability
   in Manim 0.20.1 · design, and the output spec's checks K1-K13 on the execution plan). On "revise", the
   scene-planner refactors the plan and validates it, then the next round. After round 3 below the threshold
   the plan REQUIRES ATTENTION: the open issues go to the user at CP2.
After all scenes: accuracy-reviewer subagent (plan mode) → `plan_review.json`; fix ERRORs. CP2: show the user,
per scene, the composition, transition_in, a clip table (clip, seconds, objective, beats, pauses) and the last
critique round; on approval `text-2-shorts approve . plan`. Editing a plan after CP2 needs CP2 again — except
SSML-only changes by the audio-refactorer, which re-time the audio to the built video.
