from manim import *
class L(Scene):
    def construct(self):
        title = Text("A very long title that will certainly run off the edge of the frame", font_size=48).to_edge(UP)
        eq = MathTex(r"E = mc^2").move_to(ORIGIN)
        lab = Text("energy").move_to(ORIGIN + RIGHT*0.2)
        self.play(Write(title), run_time=1)
        self.play(Write(eq), FadeIn(lab), run_time=1.5)
        self.wait(0.5)
