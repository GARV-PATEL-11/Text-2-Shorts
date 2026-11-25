from manim import *


class Scene01(Scene):
    def _build_objects(self):
        self.eq = MathTex(r"a^2 + b^2 = c^2")

    def _clip_1(self):
        self.play(Write(self.eq), run_time=1.5)
        self.play(self.eq.animate.to_edge(UP), run_time=1)

    def _clip_2(self):
        self.beat(1)
        box = SurroundingRectangle(self.eq, buff=0.15)
        self.play(Create(box), run_time=1)
        self.beat(2)  # beat 2 starts once the box is drawn
        self.wait(1)
        self.play(FadeOut(box), run_time=0.5)

    def _clip_3(self):
        self.play(FadeOut(self.eq), run_time=0.5)

    def construct(self):
        self._build_objects()
        self._clip_1()
        self._clip_2()
        self._clip_3()
