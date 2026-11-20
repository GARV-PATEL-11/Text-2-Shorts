## Topic: axes & graphs
- `Axes(x_range=[min,max,step], y_range=[...], x_length=..., y_length=...)`; `NumberPlane(...)` for a grid.
- Plot with `ax.plot(f, x_range=[a, b], color=...)` (`get_graph` was removed). Points: `ax.c2p(x, y)` / `ax.coords_to_point`.
- Labels: `ax.get_axis_labels(x_label="x", y_label="y")`, `ax.get_graph_label(graph, label=r"x^2", x_val=1.5)`.
- Data series: `ax.plot_line_graph(x_values, y_values)` (there is no `get_line_graph`).
- Area / Riemann: `ax.get_area(graph, x_range=[a, b])`, `ax.get_riemann_rectangles(graph, x_range=[a, b], dx=0.25)`.
- Implicit / parametric: `ax.plot_implicit_curve(f)`, `ax.plot_parametric_curve(f, t_range=[...])`.
```python
from manim import *

class CardAxes(Scene):
    def construct(self):
        ax = Axes(x_range=[0, 3, 1], y_range=[0, 9, 3], x_length=6, y_length=4).to_edge(DOWN)
        labels = ax.get_axis_labels(x_label="x", y_label="y")
        g = ax.plot(lambda x: x ** 2, x_range=[0, 3], color=BLUE)
        lab = ax.get_graph_label(g, label=r"x^2", x_val=2.2, direction=UL)
        area = ax.get_area(g, x_range=[0, 2], opacity=0.4)
        pts = ax.plot_line_graph([0, 1, 2, 3], [0, 1, 4, 9], add_vertex_dots=True)
        self.play(Create(ax), FadeIn(labels), run_time=1)
        self.play(Create(g), Write(lab), run_time=1.5)
        self.play(FadeIn(area), FadeIn(pts), run_time=1)
        self.wait(0.5)
```
