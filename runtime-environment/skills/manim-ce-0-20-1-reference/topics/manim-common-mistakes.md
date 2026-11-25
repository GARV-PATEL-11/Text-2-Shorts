# Manim Common Mistakes

**Target: Manim Community Edition 0.20.1** (pinned in this project)

> Part of a three-file set for ManimCE 0.20.1, the version this project pins (checked against the installed package,
> 2026-11-25):
> [`manim-vocabulary.md`](manim-vocabulary.md) (which names exist), [`manim-construction-patterns.md`](manim-construction-patterns.md) (how to write the code; rule IDs L, A, C, T, S, P), [`manim-common-mistakes.md`](manim-common-mistakes.md) (what still goes wrong).
> Block names used inside the text map to files: MANIM_VOCABULARY = manim-vocabulary.md, MANIM_CONSTRUCTION_PATTERNS = manim-construction-patterns.md, MANIM_COMMON_MISTAKES = manim-common-mistakes.md. TEMPLATE = the TEMPLATE block of the clip's TASK.md. `TPL.<role>` means the hex string TEMPLATE gives for that colour role.
> The static validator (`./check static`) already rejects every removed name in MANIM_VOCABULARY PART 3 before any render.

## PART 0. HOW TO USE THIS BLOCK

### 0.1 Scope

```text
    This block lists mistakes that pass a name check but still break a
    render or render the wrong picture. It is the third Manim block:
        MANIM_VOCABULARY              - which names exist (banned names)
        MANIM_CONSTRUCTION_PATTERNS   - how to write code (rule IDs L, A,
                                        C, T, S)
        MANIM_COMMON_MISTAKES         - what goes wrong anyway (this block)
    Where a mistake is already a rule elsewhere, the entry gives the rule
    ID and only the shortest reminder.
```

### 0.2 Entry format

```text
    ID      family letter + number
    Wrong   code that fails
    Right   code that works
    Why     one line
    Detect  how a reviewer or linter can spot it
```

### 0.3 Families

```text
    V  version trap         old API that no longer exists
    E  render error         the render aborts
    S  silent wrong output  renders without error, picture is wrong
    T  timing / determinism output depends on frame rate, run, or audio
    P  performance          renders correctly, but slowly
    N  not a mistake        looks wrong, is fine; do not "fix" it
```

### 0.4 Rule of thumb

```text
    An API that feels standard and certain is the one most likely to
    have been renamed: it was used in older tutorials for years. Check
    it against MANIM_VOCABULARY before using it.
```

## PART 1. QUICK INDEX

| ID  | Mistake                                         | Effect                    |
|-----|-------------------------------------------------|---------------------------|
| V1  | get_graph / get_\*_curve / GraphScene            | AttributeError / NameError|
| V2  | Old play syntax: play(mob.method, arg)          | Error                     |
| V3  | "}}" inside MathTex on v0.20.0 only             | Wrong split / TeX error   |
| V4  | Removed kwargs and attributes                   | TypeError / AttributeError|
| V5  | Pre-0.20 MathTex part selection                 | IndexError / TypeError    |
| E1  | Non-animation passed to play()                  | Error                     |
| E2  | .animate.create() / .animate.write()            | Error                     |
| E3  | self.wait(run_time=...)                         | TypeError                 |
| E4  | VGroup holding a non-VMobject                   | TypeError                 |
| E5  | TeX in a non-raw string                         | TeX error or wrong symbol |
| E6  | TeX needed but not expected                     | TeX error                 |
| E7  | Zero or negative duration                       | Render aborts             |
| E8  | Restore / MoveToTarget without setup            | Error                     |
| E9  | Guessed keyword names                           | TypeError                 |
| E10 | camera.frame outside MovingCameraScene          | AttributeError            |
| E11 | 2D coordinates; list addition                   | Shape error / wrong point |
| E12 | File, sound or process access in a clip         | Rejected by ./check       |
| E13 | .animate chained twice                          | Error                     |
| S1  | Transform vs ReplacementTransform references    | Ghost duplicates          |
| S2  | Two animations on one mobject in one play()     | Only one applies          |
| S3  | Second name for the same object                 | Both change               |
| S4  | Anchoring to an object not yet placed           | Wrong position            |
| S5  | TransformMatchingTex fades instead of morphing  | Looks like a cut          |
| S6  | set_fill without opacity                        | Fill invisible            |
| S7  | Angles in degrees                               | Wrong rotation            |
| S8  | Arrow stops short of its endpoints              | Gap at the target         |
| S9  | 2D text in ThreeDScene                          | Text tilts with camera    |
| S10 | Markup or TeX in plain Text                     | Literal characters shown  |
| S11 | MathTex used for sentences                      | Spaces lost, italic       |
| S12 | Long Text expected to wrap                      | Runs off screen           |
| S13 | Updater in a loop uses the loop variable        | All copies identical      |
| S14 | Updater lifecycle mistakes                      | Stuck or drifting objects |
| S15 | Visible object with no explicit color           | Off-template color        |
| T1  | No run_time on narrated beats                   | Out of sync with audio    |
| T2  | Updater without dt                              | Speed depends on fps      |
| T3  | wait() expected to show updater motion          | Frozen frame              |
| T4  | Unseeded randomness                             | Preview != final render   |
| P1  | Text/MathTex built every frame                  | Very slow render          |
| P2  | TracedPath with no dissipating_time             | Slows down over time      |

## PART 2. VERSION TRAPS (V)

```text
V1. Renamed graphing API
    Wrong:  axes.get_graph(f)
            axes.get_implicit_curve(F)
            axes.get_parametric_curve(f)
            class S(GraphScene): self.setup_axes(); self.coords_to_point(x, y)
    Right:  axes.plot(f)
            axes.plot_implicit_curve(F)
            axes.plot_parametric_curve(f)
            class S(Scene): axes = Axes(...); axes.c2p(x, y)
    Why:    The get_* names and GraphScene were removed years ago but
            fill pre-2022 tutorials.
    Detect: grep "get_graph(", "get_implicit_curve(",
            "get_parametric_curve(", "GraphScene", "setup_axes(".
    Note:   For an implicit curve with no visible axes, use
            ImplicitFunction(F, x_range=..., y_range=...) directly.

V2. Old play syntax
    Wrong:  self.play(mob.shift, UP)
            self.play(ApplyMethod(mob.shift, UP))   (legacy)
    Right:  self.play(mob.animate.shift(UP))
    Why:    Passing a bound method to play() is no longer supported.
    Detect: play( followed by an attribute with no call parentheses.

V3. "}}" inside MathTex (v0.20.0 only)
    Wrong:  MathTex(r"e^{\frac{a}{b}}")      (ends in two closing braces)
    Right:  MathTex(r"e^{\frac{a}{b} }")     (space between the braces)
    Why:    In v0.20.0, MathTex treated "{{ }}" as its part-splitting
            syntax and could misread ordinary nested braces. 0.20.1,
            pinned here, parses them correctly (checked: one part,
            e^{\frac{a}{b}}). The space stays harmless if a file is
            ever run on 0.20.0.
    Detect: grep "}}" inside MathTex strings that do not intend a split.

V4. Removed or renamed keywords and attributes
    Wrong:  Sector(inner_radius=1, outer_radius=2)
            Code.styles_list
    Right:  AnnularSector(inner_radius=1, outer_radius=2)
            Code.get_styles_list()
    Detect: check the class entry in MANIM_VOCABULARY.

V5. Pre-0.20 MathTex part selection (rewrite in 0.20.0, PR #4515)
    Wrong:  eq = MathTex("y = m x + c", substrings_to_isolate=["m"])
            eq[1]                          only one top-level part
            eq.get_parts_by_tex("x")       removed in the rewrite
    Right:  eq = MathTex("y", "=", "m", "x", "+", "c");  eq[2]
            eq.get_part_by_tex("m");  eq.set_color_by_tex("x", TPL.focus)
    Why:    substrings_to_isolate still colours and finds a term, but
            it no longer splits the top level (len(eq) == 1).
    Detect: numeric indexing on a MathTex built with
            substrings_to_isolate; any get_parts_by_tex.
```

## PART 3. RENDER ERRORS (E)

```text
E1. Non-animation passed to play()
    Wrong:  self.play(square.shift(RIGHT))
            self.play(square)
    Right:  self.play(square.animate.shift(RIGHT))
            self.play(Create(square))
    Why:    square.shift(...) moves the square immediately and returns
            the square, not an animation.
    Detect: inside play(), a mobject or a direct method call with no
            .animate and no Animation class.

E2. Appearing with .animate  (rule A2)
    Wrong:  self.play(mob.animate.create())
    Right:  self.play(Create(mob))      self.play(Write(text))

E3. wait() keyword
    Wrong:  self.wait(run_time=2)
    Right:  self.wait(2)  or  self.wait(duration=2)
            Wait(run_time=2)   only as a step inside Succession or
                               AnimationGroup
    Why:    Scene.wait takes duration; the Wait class takes run_time.

E4. Mixed types in VGroup
    Wrong:  VGroup(Circle(), ImageMobject("photo.png"))
    Right:  Group(Circle(), ImageMobject("photo.png"))
    Why:    VGroup accepts only VMobjects. ImageMobject and point-cloud
            mobjects are not VMobjects. Text, MathTex, shapes, lines and
            SVGMobject are, so VGroup is fine for them.

E5. TeX in a non-raw string
    Wrong:  MathTex("\frac{a}{b}")    \f becomes a form-feed character
            MathTex("\theta")         \t becomes a tab
            MathTex("\nabla f")       \n becomes a newline
            MathTex("\beta")          \b becomes a backspace
    Right:  MathTex(r"\frac{a}{b}")   and r"..." for every Tex/MathTex
            string
    Why:    Python processes backslash escapes before LaTeX sees the
            string. The result is a LaTeX error or a silently wrong
            symbol.
    Detect: a Tex/MathTex string literal containing a backslash and no
            r prefix.

E6. LaTeX needed where none is expected
    These compile LaTeX internally, so they fail if LaTeX is missing or
    a package is not loaded: DecimalNumber, Integer, Variable, Matrix,
    and axis numbers (add_coordinates, NumberLine numbers).
    For non-default packages, see rule T6.
    Debug:  open the .log file in media/Tex/ and read the first line
            that starts with "!".

E7. Zero or negative duration
    Wrong:  self.play(Write(t), run_time=0)    self.wait(0)
    Right:  any duration > 0; to show something instantly, use
            self.add(t)

E8. Missing setup step
    Wrong:  self.play(Restore(mob))           with no mob.save_state()
            self.play(MoveToTarget(mob))      with no mob.generate_target()
    Right:  call mob.save_state() / mob.generate_target() first, on every
            code path that reaches the animation.

E9. Guessed keyword names
    Wrong:  Text("Hi", size=48)          Square(size=2)
            SurroundingRectangle(a, b)
    Right:  Text("Hi", font_size=48)     Square(side_length=2)
            SurroundingRectangle([a, b])
    Why:    Keyword names cannot be guessed from what a class does. Use
            the names in MANIM_VOCABULARY and MANIM_CONSTRUCTION_PATTERNS
            only.

E10. Camera frame in the wrong scene class
    Wrong:  class S(Scene): ... self.camera.frame.animate.scale(0.5)
    Right:  class S(MovingCameraScene): ...
    Why:    Only MovingCameraScene's camera has .frame (vocabulary V4).

E11. Coordinates
    Wrong:  dot.move_to([1, 2])                 two components
            p = [1, 2, 0] + [0, 1, 0]           list addition
    Right:  dot.move_to([1, 2, 0])
            p = np.array([1, 2, 0]) + UP
    Why:    Manim points have three components. Adding Python lists
            joins them into a 6-element list instead of adding the
            values.

E12. File, sound or process access in a clip  (rule P2)
    Wrong:  self.add_sound("voice.wav")   ImageMobject("photo.png")
            import os; open(...)
    Right:  nothing: the pipeline adds the narration; draw with shapes
    Why:    Clips run sandboxed; ./check static reports FORBIDDEN_IMPORT
            or FORBIDDEN_CALL.

E13. .animate chained twice  (rule A7)
    Wrong:  self.play(mob.animate.shift(UP).animate.scale(2))
    Right:  self.play(mob.animate.shift(UP).scale(2))
    Detect: ".animate" twice in one expression.
```

## PART 4. SILENT WRONG OUTPUT (S)

```text
S1. Transform keeps the source; ReplacementTransform swaps it
    After Transform(A, B):            A is on screen and looks like B.
                                      B is NOT on screen.
    After ReplacementTransform(A, B): A is removed. B is on screen.
    Wrong:  self.play(Transform(a, b))
            self.play(Transform(b, c))    b was never on screen: Manim
                                          adds it, leaving a ghost copy
    Right:  self.play(Transform(a, b))
            self.play(Transform(a, c))    keep animating the source
      or:   self.play(ReplacementTransform(a, b))
            self.play(ReplacementTransform(b, c))
    Also:   NEVER write Transform(mob, mob); it does nothing.
    Detect: after Transform(X, Y), a later animation that uses Y.

S2. Two animations on one mobject in one play()
    Wrong:  self.play(sq.animate.shift(RIGHT), sq.animate.rotate(PI))
    Right:  self.play(sq.animate.shift(RIGHT).rotate(PI))
    Why:    Animations on the same mobject in one play() conflict, and
            usually only one takes effect.
    Detect: one mobject named in two arguments of the same play().
    Note:   Per-animation settings go after .animate:
            self.play(a.animate(run_time=2).shift(UP),
                      b.animate(rate_func=linear).shift(DOWN))

S3. A second name for the same object  (rule L8)
    Wrong:  before = label
            label.shift(UP)               before moved too
    Right:  before = label.copy()
            label.shift(UP)
    Why:    Assignment does not copy a mobject. Both names point at one
            object, and no error is raised.

S4. Anchoring to an object not yet placed  (rule L5)
    Wrong:  b.next_to(a, RIGHT)
            a.to_edge(LEFT)               b stays next to a's old spot
    Right:  a.to_edge(LEFT)
            b.next_to(a, RIGHT)
    Why:    next_to, align_to and get_center read positions when called,
            not at render time.

S5. TransformMatchingTex fades instead of morphing  (rule T5)
    Parts pair only on identical tex strings. Map different strings with
    key_map={"x": "x^2"}.

S6. Fill that does not show
    Wrong:  Circle().set_fill(TPL.accent)
    Right:  Circle().set_fill(TPL.accent, opacity=1)
            Circle(fill_color=TPL.accent, fill_opacity=1)
    Why:    Shapes start with fill opacity 0. set_fill(color) without an
            opacity keeps it at 0.

S7. Angles in degrees
    Wrong:  mob.rotate(90)              Rotate(mob, 45)
    Right:  mob.rotate(90 * DEGREES)    Rotate(mob, PI / 4)
    Why:    Every angle argument is in radians; 90 means 90 radians.

S8. Arrow does not reach its points
    Wrong:  Arrow(a.get_center(), b.get_center())   expecting contact
    Right:  Arrow(start, end, buff=0)               to touch the points
    Why:    Arrow's default buff is 0.25, which pulls both ends inward.
            Short arrows also get smaller tips and thinner strokes
            automatically, so tiny arrows can look faint.

S9. 2D text in ThreeDScene
    Wrong:  self.add(Text("Title"))     the text tilts with the camera
    Right:  t = Text("Title").to_corner(UL)
            self.add_fixed_in_frame_mobjects(t)
    Also:   Transforming between fixed-in-frame text objects can glitch.
            Fix the target too before the transform, or swap the texts
            with FadeOut and FadeIn.

S10. Wrong text class for the content
    Wrong:  Text("<b>bold</b>")          shows the tags literally
            Text("x^2")                  shows the caret literally
    Right:  MarkupText("<b>bold</b>")
            MathTex(r"x^2")

S11. Sentences in MathTex
    Wrong:  MathTex(r"the slope is m")   spaces vanish, letters italic
    Right:  Tex(r"the slope is $m$")  or  Text("the slope is m")

S12. Long text expected to wrap
    Text never wraps. Break lines yourself (Paragraph or "\n"), and keep
    the block inside the frame (rule L6).

S13. Updater in a loop uses the loop variable
    Wrong:  for i, d in enumerate(dots):
                d.add_updater(lambda m: m.move_to(points[i]))
    Right:  for i, d in enumerate(dots):
                d.add_updater(lambda m, i=i: m.move_to(points[i]))
    Why:    The lambda looks up i when it runs, after the loop has
            ended, so every updater sees the last value. A default
            argument captures the value at creation time.
    Detect: a lambda inside a loop body that uses the loop variable and
            has no default argument for it.

S14. Updater lifecycle
    - An object made with always_redraw is only drawn after self.add().
    - A mobject's own updaters pause while it is the target of an
      animation. To move things that are driven by updaters, animate the
      ValueTracker (tracker.animate.set_value(x)), not the dependent
      mobject.
    - Remove updaters when their job ends (mob.clear_updaters() or
      mob.remove_updater(f)). Otherwise they keep acting in later beats.

S15. Visible object with no explicit color  (rules C5, C6)
    Manim's default WHITE and built-in highlight colors are not template
    colors. Set TPL.<role> on every visible object.
```

Checked example (the Right forms of S1, S6, S7, S13, T2 and T4; colors are the Standard template's roles):

```python
import random

from manim import *

TEXT, GIVEN, DERIVED, FOCUS = "#FFFFFF", "#58C4DD", "#83C167", "#FFFF00"


class CardRightForms(Scene):
    def construct(self):
        random.seed(0)  # T4
        a = Square(color=GIVEN).set_fill(GIVEN, opacity=0.5)  # S6: fill needs an opacity
        b = Circle(color=DERIVED)
        c = Triangle(color=FOCUS)
        self.play(Create(a), run_time=0.8)
        self.play(ReplacementTransform(a, b), run_time=0.8)  # S1: keep animating the new name
        self.play(ReplacementTransform(b, c), run_time=0.8)
        self.play(Rotate(c, 90 * DEGREES), run_time=0.8)  # S7: radians via DEGREES
        anchors = [LEFT * 3 + DOWN * 2, DOWN * 2, RIGHT * 3 + DOWN * 2]
        dots = VGroup(*[Dot(color=TEXT) for _ in anchors])
        for i, dot in enumerate(dots):
            dot.add_updater(lambda m, i=i: m.move_to(anchors[i]))  # S13: bind the loop variable
        spinner = Square(side_length=0.6, color=GIVEN).to_corner(UR)
        spinner.add_updater(lambda m, dt: m.rotate(0.8 * dt))  # T2: per second, not per frame
        self.add(dots, spinner)
        self.wait(1)
        dots.clear_updaters()
        spinner.clear_updaters()
        self.wait(0.5)
```

## PART 5. TIMING AND DETERMINISM (T)

```text
T1. Narrated beats without run_time
    self.play() defaults to 1 second. For every narrated beat, MUST set
    run_time so that the beat's run_times plus waits equal the narration
    segment's duration, and the clip totals its CLIP_TIMINGS length (rule P7: 0.3 s
    lead-in + narration + at least 0.8 s hold).

T2. Updater without dt
    Wrong:  mob.add_updater(lambda m: m.rotate(0.05))      per frame
    Right:  mob.add_updater(lambda m, dt: m.rotate(0.6 * dt))  per second
    Why:    A fixed per-frame step runs 4x faster at 60 fps than at
            15 fps, so a low-quality preview and the final high-quality
            render move at different speeds.

T3. wait() expected to show updater motion
    self.wait() renders one frozen frame unless something in the scene
    changes over time. Updaters without dt do not count as changing.
    If a pause must show motion, use dt updaters (T2) or pass
    frozen_frame=False.

T4. Unseeded randomness
    Wrong:  random.random() or np.random.rand() in scene code with no seed
    Right:  random.seed(0); np.random.seed(0) at the start of construct()
    Why:    Without a seed, the preview render and the final render draw
            different random values and produce different pictures.

T5. Every clip must end on a hold that completes its length  (rule S3)
```

## PART 6. PERFORMANCE (P)

```text
P1. Text or MathTex built every frame
    Wrong:  always_redraw(lambda: MathTex(f"x={t.get_value():.2f}"))
    Right:  num = DecimalNumber(0)
            num.add_updater(lambda m: m.set_value(t.get_value()))
    Why:    Each frame builds a new text object, and a changing TeX
            string compiles LaTeX again for every new value.

P2. TracedPath with no dissipating_time
    The trail grows every frame for the rest of the scene. Set
    dissipating_time, or remove the path when its beat ends.
```

## PART 7. NOT MISTAKES (N) - do not "fix" these

```text
N1. FadeOut(mob) on a mobject that was never added is fine: play() adds
    it automatically and removes it afterwards.
N2. Create, Write and FadeIn do not need a prior self.add().
N3. self.wait() with no argument waits 1 second.
```

## PART 8. PRE-OUTPUT CHECKLIST

```text
[ ] V1-V5  No removed or renamed API; MathTex parts per the 0.20 rules
[ ] E1     Every play() argument is an animation or .animate
[ ] E5     Every Tex/MathTex string literal has the r prefix
[ ] E7     Every run_time and wait duration > 0
[ ] E11    Every point has 3 components; no list addition
[ ] E12    No file, sound or process access in the clip
[ ] E13    One .animate per expression
[ ] S1     Nothing animates the target of an earlier Transform
[ ] S2     No mobject appears twice in one play()
[ ] S6     Every set_fill that should show has an opacity
[ ] S7     Every angle in radians (DEGREES or PI)
[ ] S13    Loop-built updaters bind the loop variable
[ ] T1     Narrated beats sum to their narration duration
[ ] T2     Every updater that moves over time uses dt
[ ] T4     Randomness seeded
[ ] P1     No Text/MathTex built inside an updater or always_redraw
```
