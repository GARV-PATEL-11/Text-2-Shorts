from manim import *


def clip_01(self):
    # exit contract: reg["eq"] visible at top_center
    eq = MathTex(r"a^2 + b^2 = c^2")
    self.play(Write(eq), run_time=1.5)
    self.play(eq.animate.to_edge(UP), run_time=1)
    self.reg["eq"] = eq
