# Stage 2 — The complete script (read before writing script.json)

The script is the approved reference for everything after it: every scene plan must speak exactly its words, in
its order. Write the whole video's narration now; visual detail belongs to stage 3.

Inputs: `brief.json`; standards.md (narration convention, explanation style); narrative-structures.md unless the
user brought their own structure or script; transitions.md (bridges); the user's outline, script or feedback.

Output: `script.json` (schema `Script`):
`{"title", "structure", "objectives": [...], "target_wpm", "scenes": [{"scene_id": "s01", "role", "title",
"objective", "key_concepts": [...], "covers": [1, 2], "previews": [...], "duration_seconds", "bridge_in",
"narration", "visual_idea"}]}`

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
8. visual_idea: at most two sentences on what the picture could be.
9. Accuracy: claims true at the audience's level; keep a claim narrower rather than add unverified content.

Before CP1
- Self-review with script-review.md and fix what fails.
- accuracy-reviewer subagent (script mode) → `script_review.json`; fix every ERROR in the script, re-run it.
- CP1: show the user a table (scene, title, objective, seconds, words) plus the full narration and the accuracy
  findings; on approval, `text-2-shorts approve . script`.
To change what is said after CP1: edit `script.json` and ask CP1 again; plans that no longer match are flagged.
