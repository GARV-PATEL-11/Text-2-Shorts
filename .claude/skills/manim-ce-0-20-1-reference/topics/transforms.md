## Topic: transforms (which one to use)
- `Transform(a, b)`: `a` stays in the scene and takes b's shape — keep using the name `a` afterwards.
- `ReplacementTransform(a, b)`: `a` is removed, `b` is added — use the name `b` afterwards. Default choice for clip code,
  because the registry name then matches what is on screen.
- `TransformMatchingTex(a, b)` / `TransformMatchingShapes(a, b)`: matching parts move, others fade.
- `FadeTransform(a, b)`: cross-fade when shapes are unrelated.
- `mob.animate.<method>(...)` animates a method call; chain methods inside one `.animate`, never chain `.animate` twice.
```python
from manim import *

class CardTransforms(Scene):
    def construct(self):
        sq = Square(color=BLUE)
        circ = Circle(color=GREEN)
        self.play(Create(sq), run_time=1)
        self.play(ReplacementTransform(sq, circ), run_time=1)
        self.play(circ.animate.shift(LEFT * 2).scale(0.5), run_time=1)
        self.play(FadeTransform(circ, Text("done").shift(LEFT * 2)), run_time=1)
```
