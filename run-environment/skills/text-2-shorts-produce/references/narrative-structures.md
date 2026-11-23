# Narrative structures (read when the user did not bring their own structure)

`brief.json` → `approach` names one of four structures: three fixed (zoom, arc, linear) and one creative. The
fixed ones are guidance, not templates: skip a part the topic does not need. Whatever the structure, the video
opens with the index scene (script-writing.md), every teaching scene has one objective, and every later scene is
bridged (transitions.md).

## zoom — big picture → detail → big picture
For systems and "how does it work" topics; viewers who want to understand, not just use.
- Start at the system boundary in everyday words (what it is, what it does), then zoom in level by level:
  components → internals → mechanism → trade-offs.
- Vocabulary grows with depth: no deep jargon in the first scenes; full precision at the deepest level.
- Give the mechanism the most time (about a quarter of the video).
- Bridges use zoom language ("zooming in on…", "stepping back…").
- The last scene zooms out: connect every level back to the opening picture.

## arc — problem → solution
For mixed audiences who need a reason to care.
- Open with a concrete, relatable problem (not a definition); the topic arrives as the answer to it.
- Then how it works, where it fits in real life, its limits (each paired with what addresses it), and a concrete
  next step for the viewer.
- Every technical scene connects back to the opening problem.
- Tone follows the arc: tension → relief → curiosity → step-by-step clarity → practical confidence → honest realism.

## linear — lesson
For beginners to intermediate learners; clarity over story.
- Motivation (a question the video answers) → concept → math → visual intuition → mechanism → evaluation/use → recap.
- No math before the concept it formalises; no evaluation before the mechanism; when both math and mechanism
  appear, put a visual intuition scene between them.
- Difficulty rises steadily, then drops for the recap; the recap answers the opening question.

## creative — a structure designed for this topic
When none of the three fits (a story, a historical journey, a myth-busting list, a build-it-step-by-step, …) or
the user brings their own outline. Design the arc from the objectives and the audience: what question pulls the
viewer in, in what order understanding grows, how it closes. Name it in `script.json` → `structure` with a
one-line rationale ("creative: historical journey — each scene is one astronomer's step"). A user's own outline
keeps their order, scene boundaries and wording; fill only required fields and list what you added.
