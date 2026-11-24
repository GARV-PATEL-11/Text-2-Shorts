# clip_reviewer@1 — Clip Reviewer (PROPOSED; conditional, multimodal, one call per clip)

One reviewer instead of separate Animation-Quality, Visual-Layout and Math critics. Geometry (overlap, off-frame,
tiny text) and timing are already decided deterministically, so the remaining judgement is semantic, and all three
semantic questions need the same evidence (frames + narration + plan). Splitting them would send the same images
three times. Runs only when: the clip passed all gates AND (first build of the clip OR its code changed since the
last review) — never on cache hits.

Evidence sent: a contact sheet = 1 frame per beat boundary (from the probe timeline) + the final frame, max 8 frames,
downscaled to 640 px wide (≈ 0.5k tokens/frame estimate — measure); the clip plan; narration with phrase times.

## System (static)
```
You review one rendered clip of a math explainer against its plan. You see frames taken at each beat boundary.
Report only defects visible in the frames or contradicted by the plan:
  MISMATCH    a beat does not show what its narration phrase says (wrong object highlighted, wrong formula)
  MATH_VISUAL the picture misrepresents the math (wrong curve shape, wrong label, sign error on screen)
  CLARITY     the viewer cannot tell what to look at (no emphasis on the discussed object, competing motion)
  STYLE       inconsistent with style tokens (colour roles swapped, wrong font role)
  EXIT        the last frame does not match the exit contract
Each defect: code, severity (ERROR for MISMATCH/MATH_VISUAL/EXIT, else WARN), the frame index, and a one-line fix.
Do not report overlaps, off-screen text or timing — those are measured elsewhere.
```
## User (dynamic)
`clip plan JSON` + `phrase timeline` + images labelled `frame k @ t=… s (beat k)`.

## Output
`CriticResult` (critic="clip_render"). ERROR → one targeted Clip Builder session with the defects as LAST FINDINGS.
WARN → shown at the scene checkpoint only.
