from manim import *


def clip_02(self):
    # entry contract: reg["eq"] at top_center · exit: reg["eq"] at top_center
    box = SurroundingRectangle(self.reg["eq"], buff=0.15)
    self.play(Create(box), run_time=1)
    self.wait(1)
    self.play(FadeOut(box), run_time=0.5)
