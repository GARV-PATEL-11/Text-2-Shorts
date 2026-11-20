## Topic: frame, positioning, safe layout
- Default frame: 14.22 × 8.0 units (16:9), origin at centre. x ∈ [-7.11, 7.11], y ∈ [-4, 4].
  For 9:16 shorts the project sets `config.frame_width/height` in `manim.cfg`; read `config.frame_width` — never hard-code 7.11.
- Safe area = frame minus 0.3 units on every side (the layout probe fails anything outside it).
- Place with relations, not coordinates: `to_edge(UP)`, `next_to(obj, DOWN, buff=MED_SMALL_BUFF)`, `arrange(DOWN, buff=0.4)`,
  `align_to(obj, LEFT)`. Built-in buffs: SMALL_BUFF 0.1 · MED_SMALL_BUFF 0.25 · MED_LARGE_BUFF 0.5 · LARGE_BUFF 1.0.
- Shrink to fit instead of overflowing: `mob.scale_to_fit_width(config.frame_width - 1)` when wider than the safe area.
- At most 2 text blocks + 1 diagram on screen; remove (FadeOut) what the narration has left behind.
```python
from manim import *

class CardLayout(Scene):
    def construct(self):
        title = Text("Pythagoras", font_size=44).to_edge(UP)
        tri = Polygon(LEFT * 2 + DOWN, RIGHT * 2 + DOWN, LEFT * 2 + UP * 1.5, color=BLUE)
        eq = MathTex(r"a^2 + b^2 = c^2").next_to(tri, DOWN, buff=MED_LARGE_BUFF)
        group = VGroup(tri, eq).arrange(DOWN, buff=0.5).next_to(title, DOWN, buff=0.5)
        if group.width > config.frame_width - 1:
            group.scale_to_fit_width(config.frame_width - 1)
        self.play(FadeIn(title), run_time=0.5)
        self.play(Create(tri), Write(eq), run_time=1.5)
        self.wait(0.5)
```
