from manim import *


def clip_03(self):
    # entry: reg["eq"] · exit: nothing
    self.play(FadeOut(self.reg.pop("eq")), run_time=0.5)
