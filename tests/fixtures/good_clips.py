from manim import *
class Scene001(Scene):
    def construct(self):
        self._clip_1()
        self._clip_2()
    def _clip_1(self):
        self.eq = MathTex(r"a^2", "+", r"b^2", "=", r"c^2")
        self.play(Write(self.eq), run_time=2)
        self.wait(1)
    def _clip_2(self):
        box = SurroundingRectangle(self.eq[4], color=YELLOW)
        self.play(Create(box), run_time=1)
        self.wait(0.5)
