## Topic: Text vs Tex vs MathTex
- `Text("...")` — Pango, no LaTeX needed, any Unicode; use for titles/labels.
- `MathTex(r"...")` — math mode (`align*`); use for formulas. Needs `latex` + `dvisvgm` installed (preflight checks both).
- `Tex(r"... $x$ ...")` — text mode with inline math.
- Raw strings for LaTeX always (`r"\frac{a}{b}"`). Font sizes via `font_size=` (default 48).
- `VGroup(Text(...), MathTex(...))` is valid in 0.20.1 (verified) — mixing is fine.
- Prefer ≤ 40 characters per Text line; split long sentences with `Paragraph` or two `Text` objects `arrange(DOWN)`.
```python
from manim import *


class CardText(Scene):
    def construct(self):
        title = Text("Euler's identity", font_size=40).to_edge(UP)
        eq = MathTex(r"e^{i\pi} + 1 = 0", font_size=60)
        note = Tex(r"where $i^2 = -1$", font_size=32).next_to(eq, DOWN)
        self.play(FadeIn(title), Write(eq), run_time=1.5)
        self.play(FadeIn(VGroup(note)), run_time=0.5)
        self.wait(0.5)
```
