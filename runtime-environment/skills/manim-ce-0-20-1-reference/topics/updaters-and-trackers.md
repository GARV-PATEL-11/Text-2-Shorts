## Topic: updaters & ValueTracker
- `t = ValueTracker(0)`; animate with `self.play(t.animate.set_value(3))`; read with `t.get_value()`.
- Rebuilt-every-frame objects: `always_redraw(lambda: ...)`. Cheaper relative placement: `label.add_updater(lambda m: m.next_to(dot, UP))`
  or the 0.20 builder `label.always.next_to(dot, UP)` (PR #4594).
- Remove updaters (`clear_updaters()`) before the clip ends unless the exit contract says the object is still live.
- Updaters are the main source of slow renders; prefer one `always_redraw` over many.
```python
from manim import *

class CardTracker(Scene):
    def construct(self):
        ax = Axes(x_range=[0, 3, 1], y_range=[0, 9, 3], x_length=6, y_length=4)
        g = ax.plot(lambda x: x ** 2, color=BLUE)
        t = ValueTracker(0.5)
        dot = always_redraw(lambda: Dot(ax.c2p(t.get_value(), t.get_value() ** 2), color=YELLOW))
        val = DecimalNumber(0, num_decimal_places=2).to_corner(UR)
        val.add_updater(lambda m: m.set_value(t.get_value() ** 2))
        self.add(ax, g, dot, val)
        self.play(t.animate.set_value(2.5), run_time=2)
        val.clear_updaters()
        self.wait(0.5)
```
