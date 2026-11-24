# Stage 3 — The complete script (read before writing script.json)

The script is the approved reference for everything after it: every scene plan must speak exactly its words, in
its order. Write the whole video's narration now; visual detail belongs to stage 3.

Inputs: the approved `outline.json` (CP0) — one script scene per outline segment, in order: its talking points
become narration, its `narration_hint` sets the tone, its `transition_to_next` becomes the next scene's bridge;
`brief.json` and `preferences.json` (tone); standards.md; transitions.md; open change requests for the script.

Output: `script.json` (schema `Script`):
`{"title", "structure", "objectives": [...], "target_wpm", "scenes": [{"scene_id": "s01", "role", "title",
"objective", "key_concepts": [...], "covers": [1, 2], "previews": [...], "duration_seconds", "bridge_in",
"outline_segment", "narration", "visual_idea"}]}`
*`outline_segment` = the outline segment a scene narrates; the scenes after the index narrate segments 1, 2, 3, …
once each, in order (a one-scene video: the index scene narrates segment 1).

Rules (the gate checks the starred ones)
1. *Objectives: start from the brief's objectives (all of them) and add only what the user agreed to; every
   objective is covered by at least one teaching scene (`covers` = 1-based objective numbers).
2. *Index scene first: s01 has `role: "index"` and tells the viewer what the video covers and why it matters —
   a short hook plus the route ahead; `previews` lists every later scene id in order. Typical length 10–25 s.
   (A one-scene video: s01 is the index and teaches, so it also `covers` objectives.)
3. Scenes after the index: one objective each (`role: "content"`, or `"recap"` for a closing summary),
   prerequisites first, each building on the last. The content decides the scene count. Typical: 20–90 s.
4. *Narration is the exact spoken text, written for a voice per standards.md (symbols in backticks, [pause]
   markers, numbers ≤ 2 decimals, no markdown). Words per scene ≈ duration_seconds × target_wpm / 60 (±25%).
5. *bridge_in: empty for s01; for every later scene, the spoken inter-scene transition (transitions.md).
6. *Pacing: scene durations total the brief's minutes ±20%; harder ideas get more time; one [pause] after each
   key result; vary sentence length.
7. key_concepts: the terms and results the scene introduces; later scenes may rely only on concepts already
   introduced.
8. visual_idea: at most two sentences on what the picture could be. Name what the plan must honour:
   `on_screen_text` (text or formulas that must appear), `animations`, `audio_requirements`,
   `transition_requirements`, and `depends_on` (earlier scenes this one builds on).
9. Accuracy: claims true at the audience's level; keep a claim narrower rather than add unverified content.

Before CP1
- Self-review with script-review.md and fix what fails.
- accuracy-reviewer subagent (script mode) → `script_review.json`; fix every ERROR in the script, re-run it.
- CP1: show the user a table (scene, title, objective, seconds, words) plus the full narration, the last critique
  round and the accuracy findings; on approval, `text-2-shorts approve . script`.
When the user asks for modifications at CP1 (`text-2-shorts feedback . <target> --kind … --checkpoint script`):
one iteration — the **script-critic** writes one round to `script_critique.json` (outline-fit · clarity · flow ·
pacing · speakability · tone) with the request first, you refactor the script to apply the request and the
critique, validate, resolve the request, and show the user the script again. No loop: the user decides.
To change what is said after CP1: edit `script.json` and ask CP1 again; plans that no longer match are flagged.
