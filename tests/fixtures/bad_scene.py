from manim import *
import os
class Scene003(Scene):
    def construct(self):
        self._clip_1()
    def _clip_1(self):
        ax = Axes(x_range=[0, 5], y_range=[0, 5])
        g = ax.get_graph(lambda x: x**2)
        t = TextMobject("hi")
        b = ThoughtBubble()
        self.play(ShowCreation(g), FadeIn(t, shift=UP))
        c = Circle(radius=1, glow=3)
        c.make_it_shiny()
        self.wait(1)
