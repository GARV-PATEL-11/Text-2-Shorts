"""
An agent-style scene: the agent decides layout, motion, emphasis and stroke widths;
the template decides colours, fonts, sizes, background, border, voice and subtitles.

    TEMPLATE=templates/chalkboard.json manim -qm example_scene.py Pythagoras
    TEMPLATE=templates/blueprint.json MANIM_TEMPLATE_MODE=light NARRATION_ENGINE=polly manim example_scene.py Pythagoras
"""
import os

import numpy as np
from manim import (DOWN, LEFT, RIGHT, UP, UL, Circumscribe, Create, FadeIn, FadeOut, Indicate, Polygon,
                   SurroundingRectangle, TransformMatchingTex, VGroup, Write)

from template_kit import TemplateScene, use_template

T = use_template(os.environ.get("TEMPLATE", "templates/standard.json"))


class Pythagoras(TemplateScene):
    def construct(self):
        x0, x1, y0, y1 = T.safe_area
        title = T.text("The Pythagorean theorem", style="title").to_edge(UP, buff=T.inset)
        with self.narrate("Here is one of the oldest results in geometry."):
            self.play(Write(title))

        tri = Polygon([0, 0, 0], [4, 0, 0], [4, 3, 0], color=T.color("given"), stroke_width=4)
        a = T.math("a", role="given").next_to(tri, DOWN)
        b = T.math("b", role="given").next_to(tri, RIGHT)
        hyp = tri.get_vertices()[2] - tri.get_vertices()[0]
        normal = np.array([-hyp[1], hyp[0], 0]) / np.linalg.norm(hyp)
        c = T.math("c", role="focus").move_to(tri.get_center() + 0.45 * normal)
        figure = VGroup(tri, a, b, c).move_to([x0 + (x1 - x0) * 0.3, (y0 + title.get_bottom()[1]) / 2, 0])
        T.fit(figure)

        with self.narrate("Take a right triangle: short sides a and b, long side c.") as n:
            self.play(Create(tri))
            n.wait_until("short")
            self.play(FadeIn(a, shift=UP * 0.2), FadeIn(b, shift=LEFT * 0.2))
            n.wait_until("long")
            self.play(FadeIn(c))
            self.play(Indicate(c, color=T.color("focus")))

        eq = T.math("a^2", "+", "b^2", "=", "c^2").move_to([x0 + (x1 - x0) * 0.75, figure.get_y(), 0])
        with self.narrate("Square the short sides, add them, and you get the long side squared.") as n:
            self.play(Write(eq))
            n.wait_until("long")
            self.play(Circumscribe(eq[4], color=T.color("focus")))

        solved = T.math("c", "=", r"\sqrt{a^2+b^2}", role="derived").move_to(eq)
        box = SurroundingRectangle(solved, color=T.color("derived"), buff=0.2, corner_radius=0.1)
        with self.narrate("So we can always find c from a and b."):
            self.play(TransformMatchingTex(eq, solved))
            self.play(Create(box))

        self.play(*[FadeOut(m) for m in self.content()])
        self.wait(0.5)
