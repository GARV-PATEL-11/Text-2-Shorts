from manim import *


def clip_02(self):
    # entry contract: reg["eq"] at top_center · exit: reg["eq"] at top_center
    eq = self.entry("eq", lambda: MathTex(r"a^2 + b^2 = c^2").to_edge(UP))
    self.beat(1)
    box = SurroundingRectangle(eq, buff=0.15)
    self.play(Create(box), run_time=1)
    self.beat(2)  # beat 2 starts once the box is drawn
    self.wait(1)
    self.play(FadeOut(box), run_time=0.5)
