from manim import *


def clip_03(self):
    # entry: reg["eq"] · exit: nothing
    eq = self.entry("eq", lambda: MathTex(r"a^2 + b^2 = c^2").to_edge(UP))
    self.play(FadeOut(eq), run_time=0.5)
    self.reg.pop("eq")
