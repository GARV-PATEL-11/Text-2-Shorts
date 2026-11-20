## Topic: names that do NOT exist in Manim CE 0.20.1 (verified against the installed package)
| Do not write | Write instead |
|---|---|
| `axes.get_graph(f)` | `axes.plot(f)` |
| `axes.get_line_graph(...)` | `axes.plot_line_graph(...)` |
| `axes.get_implicit_curve(...)` / `get_parametric_curve` | `plot_implicit_curve` / `plot_parametric_curve` |
| `ShowCreation(m)` | `Create(m)` |
| `GraphScene` | `Scene` + `Axes(...)` |
| `TextMobject`, `TexMobject` | `Text`/`Tex`, `MathTex` |
| `ShowCreationThenDestruction`, `ShowCreationThenFadeAround` | `ShowPassingFlash(...)` |
| `ThoughtBubble`, `SpeechBubble` | `RoundedRectangle` + `Text` callout |
| `InteractiveScene`, `manimlib` imports | ManimGL only — not available |
| `FadeInFrom`, `FadeOutAndShift` | `FadeIn(m, shift=...)`, `FadeOut(m, shift=...)` |
The static validator (`validate_manim_code.py`) rejects every row above before any render.
