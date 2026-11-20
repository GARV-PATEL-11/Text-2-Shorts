## Topic: camera (MovingCameraScene)
- Only use when a clip spec asks for zoom/pan. The class becomes `class SceneNN(MovingCameraScene)`.
- Animate the frame: `self.play(self.camera.frame.animate.scale(0.5).move_to(obj))`; restore at clip end unless
  the EXIT contract states the camera state (camera is part of continuity).
- Save/restore: `self.camera.frame.save_state()` … `self.play(Restore(self.camera.frame))`.
- The layout probe measures against the default frame; zoomed clips must declare `camera` in the exit contract.
```python
from manim import *

class CardCamera(MovingCameraScene):
    def construct(self):
        dots = VGroup(*[Dot(RIGHT * i) for i in range(-3, 4)])
        self.play(FadeIn(dots), run_time=0.5)
        self.camera.frame.save_state()
        self.play(self.camera.frame.animate.scale(0.5).move_to(dots[5]), run_time=1)
        self.play(Indicate(dots[5]), run_time=1)
        self.play(Restore(self.camera.frame), run_time=1)
```
