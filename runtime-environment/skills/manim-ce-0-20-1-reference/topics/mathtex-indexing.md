## Topic: MathTex parts & indexing (Manim CE 0.20.x — MathTex was rewritten in 0.20.0, PR #4515)
- `MathTex(r"a^2 + b^2 = c^2")` (one string) → `len(eq) == 1`; `eq[0]` is a `MathTexPart`; `eq[0][k]` is glyph k.
- `MathTex(r"a^2", "+", r"b^2", "=", r"c^2")` (several strings) → one part per string: `eq[4]` is `c^2`.
- `MathTex(r"{{a^2}} + {{b^2}} = {{c^2}}")` → double braces also split into parts (5 here).
- `substrings_to_isolate=[...]` does NOT create top-level parts any more; select with `eq.get_part_by_tex("c^2")`.
- Prefer `get_part_by_tex` / `set_color_by_tex` over glyph arithmetic — glyph counts are an LLM's most common miscount.
- `TransformMatchingTex(src, dst)` morphs parts with equal tex strings; split both expressions the same way.
```python
from manim import *


class CardMathTex(Scene):
    def construct(self):
        eq = MathTex(r"a^2", "+", r"b^2", "=", r"c^2")
        self.play(Write(eq), run_time=1.5)
        self.play(eq[4].animate.set_color(YELLOW), run_time=0.5)
        eq2 = MathTex(r"c^2", "=", r"a^2", "+", r"b^2")
        self.play(TransformMatchingTex(eq, eq2), run_time=1.5)
        self.play(Indicate(eq2.get_part_by_tex("c^2")), run_time=1)
        self.wait(0.5)
```
