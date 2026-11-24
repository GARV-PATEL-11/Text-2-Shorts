## Topic: emphasis & indication (all exist in 0.20.1)
`Indicate`, `Circumscribe`, `Flash`, `FocusOn`, `Wiggle`, `ApplyWave`, `Blink`, `ShowPassingFlash`,
`ShowPassingFlashWithThinningStrokeWidth`, `GrowFromCenter`, `GrowFromPoint`, `GrowFromEdge`, `GrowArrow`,
`SpinInFromNothing`, `SurroundingRectangle` (mobject), `BackgroundRectangle` (mobject).
- Emphasis is a beat: it should coincide with the narration word it stresses; ≤ 1 s.
- `ShowPassingFlash(mob.copy().set_color(YELLOW), time_width=0.5)` — pass a copy, the original stays.
```python
from manim import *


class CardEmphasis(Scene):
    def construct(self):
        eq = MathTex(r"e^{i\pi} + 1 = 0")
        self.play(GrowFromCenter(eq), run_time=1)
        self.play(Circumscribe(eq), run_time=1)
        self.play(ShowPassingFlash(Underline(eq).set_color(YELLOW), time_width=0.5), run_time=1)
        self.play(Indicate(eq), run_time=0.8)
```
