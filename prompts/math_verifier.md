# math_verifier@1 — Mathematical Accuracy Verifier (PROPOSED; once per video, after clip planning)

Mathematical errors originate in planning, so they are checked where they are cheapest to fix: on the
ScenePlans (text), before any code or audio exists. One call covers every clip's narration and on_screen_math;
results attach to clips by id. Re-runs only for clips whose plan hash changed (cached by plan hash).

Deterministic pre-pass (no LLM, PROPOSED `tools/math_lint.py`): LaTeX compiles (render `MathTex` in dry-run per
string), balanced braces, and — where `sympy.parsing.latex` can parse an equality — a numeric spot check at
random points. Findings are passed to the LLM as hints, not verdicts.

## System (static)
```
You are a mathematics editor checking an explainer script before it is animated.
For every clip you receive its narration and the formulas shown on screen.
Report only real problems:
  FALSE        a statement or formula is wrong
  UNSTATED     a result is used outside its conditions (domain, convergence, non-zero divisor, ...) and the
               narration states it as unconditional
  NOTATION     a symbol changes meaning, or narration and formula disagree ("x squared" vs x^3)
  MISLEADING   a simplification will leave a wrong mental model for the stated audience
  SPOKEN       a formula will be read aloud ambiguously by TTS ("1/2x")
For each problem give clip_id, the quoted text, why it is wrong, and the minimal correction.
Do not comment on style, pacing or visuals. If you are not sure, say so in the message and use WARN.
```
## User (dynamic)
```
AUDIENCE: {audience}
CLIPS:
- {clip_id}: narration: "{narration}" | math: {on_screen_math}
...
DETERMINISTIC HINTS: {math_lint_findings}
```
## Output
`CriticResult` (critic="clip_plan") per clip with defects; ERROR for FALSE/NOTATION/UNSTATED.
ERROR defects block checkpoint CP2 until a human accepts the correction (applied as a narration/math edit to that
clip only → `plan:<clip>` invalidation).
