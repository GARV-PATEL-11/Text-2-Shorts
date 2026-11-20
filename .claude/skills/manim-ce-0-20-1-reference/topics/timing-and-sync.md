## Topic: timing & narration sync
- Clip length is set by its narration audio (seconds given in the task). Budget the clip so that
  `sum(run_time) + sum(wait) ≈ narration_seconds` (checker tolerance ±0.5 s; shorter is an error, longer is a warning).
- Map each beat to a narration phrase: start the animation when the phrase starts; hold (`self.wait`) while the
  phrase is still being spoken. A formula that is being explained must stay on screen ≥ 2 s after it finishes writing.
- One visual event per narration phrase. Never run two unrelated animations while one sentence is spoken.
- `run_time` on every `self.play`; `rate_func=smooth` (default) for reveals, `linear` for tracing/plotting, `there_and_back` for pulses.
- `self.wait(d)` takes seconds; `Wait` animations are what `wait()` uses internally.
```python
from manim import *

class CardTiming(Scene):
    # narration (≈4.0 s): "Here is the curve y equals x squared. | Watch the point slide along it."
    def construct(self):
        ax = Axes(x_range=[-2, 2, 1], y_range=[0, 4, 1], x_length=6, y_length=4)
        curve = ax.plot(lambda x: x ** 2, color=BLUE)
        dot = Dot(ax.c2p(-2, 4), color=YELLOW)
        self.play(Create(ax), Create(curve), run_time=1.5)      # phrase 1
        self.wait(0.5)                                            # phrase 1 tail
        self.add(dot)
        self.play(MoveAlongPath(dot, curve), rate_func=linear, run_time=2.0)  # phrase 2
```
