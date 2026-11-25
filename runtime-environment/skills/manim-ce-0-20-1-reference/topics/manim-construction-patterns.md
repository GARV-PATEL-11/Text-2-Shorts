# Manim Construction Patterns

**Target: Manim Community Edition 0.20.1** (pinned; entries for later versions are tagged and not installed here)

> Part of a three-file set for ManimCE 0.20.1, the version this project pins (checked against the installed package,
> 2026-11-25):
> [`manim-vocabulary.md`](manim-vocabulary.md) (which names exist), [`manim-construction-patterns.md`](manim-construction-patterns.md) (how to write the code; rule IDs L, A, C, T, S, P), [`manim-common-mistakes.md`](manim-common-mistakes.md) (what still goes wrong).
> Block names used inside the text map to files: MANIM_VOCABULARY = manim-vocabulary.md, MANIM_CONSTRUCTION_PATTERNS = manim-construction-patterns.md, MANIM_COMMON_MISTAKES = manim-common-mistakes.md. TEMPLATE = the TEMPLATE block of the clip's TASK.md (its COLOUR ROLES, TEXT and SAFE AREA lines). `TPL.<role>` means the hex string TEMPLATE gives for that colour role.
> This set replaces the earlier one-topic cards; their project rules are PART 9 here, their checked examples sit beside the rules they show.

## PART 0. HOW TO USE THIS BLOCK

### 0.1 Scope

```text
    This block defines HOW to write Manim code: layout, animation,
    color, MathTex, and scene structure.
    MANIM_VOCABULARY defines WHICH classes to use.
    MANIM_COMMON_MISTAKES lists what still goes wrong.
    Apply all three.
```

### 0.2 Precedence (highest first)

```text
    1. PART 9              - this project's scene harness (overrides any
                             generic Manim rule below)
    2. TEMPLATE            - all colors, fonts, text sizes, safe area;
                             the background is the harness's
    3. The clip's TASK.md  - content, beats, timing, entry and exit
    4. This block          - everything else
```

### 0.3 Notation

```text
    MUST   = required
    NEVER  = forbidden
    PREFER = default unless the scene spec says otherwise
    TPL.<role> = the hex string TEMPLATE gives for a colour role: text,
                 focus, given, derived, warning, secondary, accent,
                 outline, dim, surface. Write the hex string itself,
                 e.g. color="#58C4DD". It is not Manim syntax.
```

### 0.4 Layout of this block

```text
    PART 1  Reference values      (facts, no rules)
    PART 2  Layout rules          L1-L8
    PART 3  Animation rules       A1-A6
    PART 4  Color rules           C1-C8
    PART 5  MathTex rules         T1-T7
    PART 6  Scene structure rules S1-S5
    PART 7  Wrong -> Right lookup
    PART 8  Pre-output checklist
    PART 9  Project conventions   P1-P12 (the scene harness, timing,
                                  camera, layout limits)
```

## PART 1. REFERENCE VALUES (facts only)

### 1.1 Frame (the same at every render quality; it depends on the aspect)

```text
    16:9 (the delivery default):
        config.frame_width    = 14.222   visible x: -7.111 to 7.111
        config.frame_height   = 8.0      visible y: -4.0 to 4.0
    9:16 (portrait, set in manim.cfg): width and height swap (8.0 x 14.222).
    ALWAYS read config.frame_width / frame_height / frame_x_radius /
    frame_y_radius. NEVER type 7.111 or 4.0 into scene code.
    ORIGIN = (0, 0, 0) = center of the frame
    Safe area: TEMPLATE's SAFE AREA inset (0.5 or more) on every side.
    The layout probe fails anything closer than 0.3 to an edge.
```

### 1.2 Directions (unit vectors; multiply for distance: 2 * UP)

```text
    UP    = ( 0,  1, 0)    DOWN  = ( 0, -1, 0)
    RIGHT = ( 1,  0, 0)    LEFT  = (-1,  0, 0)
    OUT   = ( 0,  0, 1)    IN    = ( 0,  0, -1)
    UL = UP+LEFT   UR = UP+RIGHT   DL = DOWN+LEFT   DR = DOWN+RIGHT
```

### 1.3 Buffers

```text
    SMALL_BUFF     = 0.1
    MED_SMALL_BUFF = 0.25    default buff of next_to() and arrange()
    MED_LARGE_BUFF = 0.5     default buff of to_edge() and to_corner()
    LARGE_BUFF     = 1.0
```

### 1.4 Text

```text
    DEFAULT_FONT_SIZE = 48
```

### 1.5 Positioning methods

```text
    mob.next_to(target, direction, buff, aligned_edge)  beside target
    mob.to_edge(UP, buff)                               against a frame edge
    mob.to_corner(UL, buff)                             in a frame corner
    mob.move_to(point_or_mobject)                       center on it
    mob.shift(vector)                                   move by a vector
    mob.align_to(other, LEFT)                           match one edge only
    mob.get_center() / get_top() / get_bottom() /
        get_left() / get_right() / get_corner(UR)       read positions
    mob.shift_onto_screen()                             pull back into frame
    VGroup(...).arrange(direction, buff, aligned_edge)  row or column
    VGroup(...).arrange_in_grid(rows, cols, buff)       grid; buff may be
                                                        (horizontal, vertical)
```

### 1.6 Mutation methods

```text
    Style:  set_color(c), set_fill(color, opacity),
            set_stroke(color, width, opacity), set_opacity(o)
    Size:   scale(f), scale_to_fit_width(w), scale_to_fit_height(h)
                      (keep proportions)
            stretch(f, dim), stretch_to_fit_width(w),
            stretch_to_fit_height(h)          (distort; dim 0=x 1=y 2=z)
    Shape:  flip(axis), rotate(angle, axis, about_point)
    Match:  match_color, match_style, match_width, match_height,
            match_x, match_y
    Copy:   copy()          independent duplicate
            become(other)   take other's shape and style, in place
```

## PART 2. LAYOUT RULES

```text
L1. NEVER hardcode coordinates such as (5.3, 2.1, 0). Define zones as
    fractions of the frame radii:
        TITLE_ZONE = UP * config.frame_y_radius * 0.75
        MAIN_ZONE  = ORIGIN
        LEFT_ZONE  = LEFT * config.frame_x_radius * 0.5
L2. MUST pass a named buffer from 1.3 for every buff argument.
    NEVER write values such as buff=0.37.
L3. PREFER next_to() for placing one object relative to another.
L4. MUST place sibling objects with arrange() or arrange_in_grid().
    NEVER position each child of a group by hand.
L5. MUST follow this order: build -> arrange children -> place group.
    Arranging after placing moves the group off its intended spot.
L6. MUST keep every object inside the safe area (1.1), not just the
    frame. If an object is too wide, shrink it:
        mob.scale_to_fit_width(config.frame_width - 2 * MED_LARGE_BUFF)
L7. PREFER scale_to_fit_* over stretch_to_fit_* for text and equations.
    Stretching distorts glyphs.
L8. MUST copy() an object before changing it when its original form is
    still needed later.
L9. At most 2 text blocks and 1 diagram on screen at once. FadeOut what
    the narration has left behind.
L10. Keep a Text line under about 40 characters; split longer ones with
    Paragraph or two Text objects arranged DOWN (Text never wraps).
```

Checked example (L1-L6; colors are the Standard template's roles):

```python
from manim import *

TEXT, GIVEN, DERIVED = "#FFFFFF", "#58C4DD", "#83C167"


class CardLayout(Scene):
    def construct(self):
        title = Text("Pythagoras", font_size=44, color=TEXT).to_edge(UP)
        tri = Polygon(LEFT * 2 + DOWN, RIGHT * 2 + DOWN, LEFT * 2 + UP * 1.5, color=GIVEN)
        eq = MathTex(r"a^2 + b^2 = c^2", color=DERIVED)
        group = VGroup(tri, eq).arrange(DOWN, buff=MED_LARGE_BUFF).next_to(title, DOWN, buff=MED_LARGE_BUFF)
        if group.width > config.frame_width - 1:
            group.scale_to_fit_width(config.frame_width - 1)
        self.play(FadeIn(title), run_time=0.5)
        self.play(Create(tri), Write(eq), run_time=1.5)
        self.wait(0.5)
```

## PART 3. ANIMATION RULES

```text
A1. Use .animate only to change a property of an object already on
    screen: position, color, scale, opacity.
        self.play(mob.animate.shift(UP).set_color(TPL.highlight))
A2. MUST use an Animation class to make an object appear or disappear:
        Create, Write, FadeIn, FadeOut, DrawBorderThenFill,
        GrowFromCenter, Uncreate
        self.play(Create(mob))
A3. MUST use Rotate for visible rotation:
        self.play(Rotate(mob, PI))
    Reason: .animate.rotate() moves each point in a straight line, so a
    half-turn collapses through the center instead of turning.
A4. Decision test: if the verb is "appear", "disappear", or "turn", use
    a class (A2, A3). Otherwise .animate is allowed (A1).
A5. To play animations together, pass them to one self.play() call.
    To stagger them, use LaggedStart(...) or
    AnimationGroup(..., lag_ratio=...).
A6. self.add(mob) shows mob instantly, with no animation. Use it only
    for setup that the viewer should not see being built.
A7. Chain methods inside ONE .animate: mob.animate.shift(UP).scale(0.5).
    NEVER chain .animate twice (mob.animate.shift(UP).animate.scale(2)).
A8. Which transform:
        Transform(a, b)             a stays and takes b's shape; keep
                                    using the name a afterwards
        ReplacementTransform(a, b)  a is removed, b is added; use b
                                    afterwards (the default in clips:
                                    the registry name then matches the
                                    screen, P5)
        TransformMatchingTex / TransformMatchingShapes
                                    matching parts move, others fade
        FadeTransform(a, b)         cross-fade unrelated shapes
A9. Emphasis is a beat: it lands on the narration word it stresses and
    lasts 1 s or less. Give ShowPassingFlash a copy, so the original
    stays: ShowPassingFlash(mob.copy().set_color(TPL.focus),
    time_width=0.5).
```

Checked example (A2, A7, A8, A9):

```python
from manim import *

GIVEN, DERIVED, FOCUS, TEXT = "#58C4DD", "#83C167", "#FFFF00", "#FFFFFF"


class CardTransforms(Scene):
    def construct(self):
        sq = Square(color=GIVEN)
        circ = Circle(color=DERIVED)
        self.play(Create(sq), run_time=1)
        self.play(ReplacementTransform(sq, circ), run_time=1)
        self.play(circ.animate.shift(LEFT * 2).scale(0.5), run_time=1)
        self.play(Circumscribe(circ, color=FOCUS), run_time=0.8)
        self.play(FadeTransform(circ, Text("done", color=TEXT).shift(LEFT * 2)), run_time=1)
```

## PART 4. COLOR RULES (TEMPLATE ONLY)

```text
C1. Every color MUST come from TEMPLATE, written exactly as
    the template gives it.
C2. NEVER use Manim color constants (WHITE, RED, BLUE_C, YELLOW_E,
    PURE_GREEN, ...) unless TEMPLATE lists that constant.
C3. NEVER write a hex string that is not in TEMPLATE.
C4. NEVER make new colors with color_gradient, interpolate_color,
    fade_to, or opacity changes meant to imitate a new shade. Use only
    the opacities and color pairings the template defines.
C5. MUST set a template color explicitly on every visible object,
    including Text, MathTex, Arrow, Line, and shapes.
    Reason: an object with no color set uses Manim's default (usually
    WHITE), which is not a template color.
C6. MUST pass template colors into composite objects through their
    style arguments, because their sub-parts have their own defaults:
        Axes(..., axis_config={"color": TPL.stroke})
        NumberPlane(..., background_line_style={"stroke_color": TPL.grid})
C7. Assign colors by role (text, accent, highlight, fill, stroke, ...)
    using the template's role names. Use one role per meaning across the
    whole scene. If the scene needs a role the template lacks, reuse the
    closest existing role. NEVER invent one.
C8. Background: NEVER set it in scene code. The harness draws TEMPLATE's
    backdrop and border before construct runs (P3). NEVER draw a
    full-frame shape to act as a background, and never read or clear
    self.mobjects (use self.content(), P3).
```

## PART 5. MathTex RULES

```text
T1. Each string argument to MathTex becomes one top-level part:
        eq = MathTex("y", "=", "m", "x", "+", "c")
        eq[0] -> y    eq[2] -> m    eq[4] -> +
T2. A single string gives exactly one top-level part:
        eq = MathTex("y=mx+c")
        eq[0] -> whole equation      eq[2] -> IndexError
    NEVER index glyphs inside eq[0] by counting characters. LaTeX glyph
    counts do not match character counts.
T3. MUST give a term its own part if it will later be recolored, moved,
    transformed, or matched. Keep all other terms together.
    Two ways to create top-level parts (0.20 rewrite, PR #4515):
        MathTex("y", "=", "m", "x", "+", "c")
        MathTex("{{ y }} = {{ m }} x + c")
    substrings_to_isolate=[...] no longer creates top-level parts:
    MathTex("y = m x + c", substrings_to_isolate=["m"]) has len 1, so
    eq[1] fails. Select such a term with get_part_by_tex.
    Inside a part, eq[0][k] is glyph k; NEVER count glyphs to find a term.
T4. PREFER lookup by tex over numeric indexes:
        eq.get_part_by_tex("m")          first matching part
        eq.set_color_by_tex("x", c)      colour every matching part
        eq.index_of_part(part)           its index
    eq.get_parts_by_tex does NOT exist in 0.20.1 (removed in the
    rewrite).
T5. TransformMatchingTex(old, new) moves parts whose tex strings are
    identical and fades out/in all other parts. Different strings never
    pair by default ("x" and "x^2" are different). To morph them, map
    them:
        TransformMatchingTex(old, new, key_map={"x": "x^2"})
T6. The default TexTemplate already loads amsmath, amssymb, mathrsfs,
    physics, and xcolor. For any other package, build a template and
    pass it to the object:
        tpl = TexTemplate()
        tpl.add_to_preamble(r"\usepackage{cancel}")
        MathTex(r"\cancel{x}", tex_template=tpl)
    If a scene spec uses a symbol from a non-default package, the spec
    MUST name the package. A missing package fails at render time.
T7. Color MathTex only with template colors (C1), using set_color() or
    tex_to_color_map={"x": TPL.accent}.
T8. Every Tex/MathTex string is a raw string: r"\frac{a}{b}" (E5).
    Text needs no LaTeX; Tex and MathTex need latex and dvisvgm (the
    run's preflight checks both). VGroup(Text(...), MathTex(...)) is
    valid. Font sizes come from TEMPLATE's TEXT line.
```

Checked example (T1, T4, T5):

```python
from manim import *

TEXT, FOCUS = "#FFFFFF", "#FFFF00"


class CardMathTex(Scene):
    def construct(self):
        eq = MathTex(r"a^2", "+", r"b^2", "=", r"c^2", color=TEXT)
        self.play(Write(eq), run_time=1.5)
        self.play(eq[4].animate.set_color(FOCUS), run_time=0.5)
        eq2 = MathTex(r"c^2", "=", r"a^2", "+", r"b^2", color=TEXT)
        self.play(TransformMatchingTex(eq, eq2), run_time=1.5)
        self.play(Indicate(eq2.get_part_by_tex("c^2"), color=FOCUS), run_time=1)
        self.wait(0.5)
```

## PART 6. SCENE STRUCTURE RULES

```text
S1. In this project you write one scene CLASS in scene_code.py (P1):
        # 1. _build_objects: build and place what the scene reuses
        #    (colors: PART 4, places: PART 2)
        # 2. _clip_N per clip: animate its events in time order,
        #    each clip exactly its CLIP_TIMINGS length (P7)
        # 3. construct: _build_objects, then every _clip_N in order
    The harness wraps the class: backdrop, fonts, one section per clip.
S2. Use self.wait(seconds) after each narrative beat so the viewer can
    absorb it (holds are part of the clip's timing, P7).
S3. End every clip on a hold: its last self.wait() completes the
    clip's length (P7). Without it, the video cuts on the last frame.
S4. One file per scene; every clip is a _clip_N method of its class.
    NEVER edit the generated scene.py.
S5. NEVER render with the manim command. Check with ./check in the
    scene's work folder (static, probe, render, frames).
```

## PART 7. WRONG -> RIGHT LOOKUP

| Wrong                                  | Right                                      | Rule |
|----------------------------------------|--------------------------------------------|------|
| mob.move_to([5.3, 2.1, 0])             | mob.move_to(TITLE_ZONE)                    | L1   |
| a.next_to(b, RIGHT, buff=0.37)         | a.next_to(b, RIGHT, buff=MED_SMALL_BUFF)   | L2   |
| a.move_to(p1); b.move_to(p2)  (row)    | VGroup(a, b).arrange(RIGHT)                | L4   |
| mob.stretch_to_fit_width(10)  (text)   | mob.scale_to_fit_width(10)                 | L7   |
| self.play(mob.animate.create())        | self.play(Create(mob))                     | A2   |
| self.play(mob.animate.rotate(PI))      | self.play(Rotate(mob, PI))                 | A3   |
| Text("Hi", color=YELLOW)               | Text("Hi", color=TPL.accent)               | C2   |
| Text("Hi")   (no color set)           | Text("Hi", color=TPL.text)                 | C5   |
| Axes()       (default colors)          | Axes(axis_config={"color": TPL.stroke})    | C6   |
| Rectangle(width=14.3, height=8)  (bg)  | nothing: the harness draws the background  | C8   |
| self.camera.background_color = ...     | nothing: the harness draws the background  | C8   |
| MathTex("y=mx+c", substrings_to_isolate=["m"])[1] | eq.get_part_by_tex("m")        | T3   |
| eq.get_parts_by_tex("x")               | eq.set_color_by_tex("x", TPL.focus)        | T4   |
| mob.animate.shift(UP).animate.scale(2) | mob.animate.shift(UP).scale(2)             | A7   |
| MathTex("y=mx+c")[2]                   | MathTex("y","=","m","x","+","c")[2]        | T2   |
| TransformMatchingTex(a, b)  (x->x^2)   | TransformMatchingTex(a, b, key_map={"x": "x^2"}) | T5 |
| last line is self.play(...)            | a hold that completes the clip's length   | S3   |
| every animation inline in construct    | _build_objects + one _clip_N per clip      | S1   |

## PART 8. PRE-OUTPUT CHECKLIST

```text
Before returning code, confirm each item. Fix any failure first.
[ ] L1  No hardcoded coordinates
[ ] L2  Every buff is a named buffer
[ ] L4  Siblings placed with arrange / arrange_in_grid
[ ] L5  Children arranged before the group is placed
[ ] L6  Every object inside the visible frame
[ ] L8  Objects copied before mutation when the original is reused
[ ] A2  Appear/disappear uses Animation classes
[ ] A3  Rotation uses Rotate
[ ] C1  Every color is from TEMPLATE
[ ] C5  Every visible object has an explicit template color
[ ] C6  Composite objects (Axes, NumberPlane, ...) styled with template colors
[ ] C8  Background never set (the harness draws it)
[ ] T3  Every later-targeted MathTex term is its own part
[ ] T5  key_map given wherever different tex strings must morph
[ ] T6  Non-default LaTeX packages loaded via tex_template
[ ] S3  Every clip ends on a hold that completes its length
[ ] P1-P12  Project conventions (PART 9)
```

## PART 9. PROJECT CONVENTIONS (the scene harness; overrides PARTS 1-8)

```text
P1.  FILE. Write ONE file per scene, scene_code.py (built in
     scenes/sNN/work, installed to scenes/sNN/), holding one class
     SceneNN(Scene) with _build_objects(self), one method _clip_N(self)
     per CLIP of the plan, and construct(self) calling
     self._build_objects() then self._clip_1(), self._clip_2(), ... in
     order. Nothing else at top level except imports and constants.
     scene.py is generated by scene_harness.py compose: NEVER edit it.
P2.  IMPORTS. Only from manim import * (+ math, numpy, random,
     itertools, functools, typing). No file, network or process
     access: no add_sound, no files to load. The pipeline adds the
     narration audio.
P3.  SCREEN. The harness draws TEMPLATE's backdrop and border and
     loads its font before construct runs. Clear with self.content(),
     never self.mobjects; never set the background (C8).
P4.  SECTIONS. The harness opens Manim section clip_NN before each
     _clip_N: NEVER call next_section yourself. Each clip renders to
     its own video, muxed with its own narration.
P5.  CONTINUITY. Objects live on self (self.eq, self.axes), built in
     _build_objects or in the clip that first shows them. What a clip
     leaves on screen is the next clip's start: FadeOut temporary
     helpers before the clip ends. PREFER ReplacementTransform so the
     attribute matches what is on screen (A8). Return a highlighted
     object to its role's colour unless the plan says it stays.
P6.  BEATS (optional). self.beat(n) where beat n's animation starts
     lets the sync report compare it with the voice.
P7.  LENGTH. Clip N lasts exactly its CLIP_TIMINGS length = 0.3 s
     visual lead-in + narration audio + at least 0.8 s hold; the voice
     starts at 0.3 s. Keep a CLIP_N_SECONDS constant per clip and a
     timing cursor. The probe fails a clip shorter than its length -
     0.5 s (CLIP_TOO_SHORT) and warns above it + 1.5 s
     (CLIP_TOO_LONG). run_time on every self.play.
P8.  SYNC. One visual event per narration phrase: start it when the
     phrase starts (CLIP_TIMINGS gives the times), hold (self.wait)
     while it is still spoken. Never run two unrelated animations
     under one sentence. A formula being explained stays on screen 2 s
     or more after it finishes writing. rate_func: smooth (default)
     for reveals, linear for tracing and plotting, there_and_back for
     pulses.
P9.  LOOK. Colours, font and sizes only from TEMPLATE: COLOUR ROLES
     give the hex strings, SYMBOL COLORS map each symbol to a role,
     TEXT gives the font for every Text/MarkupText and the font sizes.
P10. CAMERA. Only when the plan's CAMERA_SCRIPT asks for a zoom or
     pan; the class then derives from MovingCameraScene. Restore the
     frame by the scene's end. The layout probe measures against the
     current camera frame.
P11. UPDATERS. clear_updaters() before the clip ends unless the next
     clip still needs the object live. PREFER one always_redraw over
     many; for simple following, the 0.20 builder
     label.always.next_to(dot, UP).
P12. NOTHING AFTER THE LAST CLIP: construct ends with the last _clip_N
     (its hold is the scene's end). The scene's first clip performs
     transition_in. Use only names confirmed with ./check doc
     Name1,Name2.
```

Checked scene file (P1, P4-P8; colors are the Standard template's roles):

```python
from manim import *

TEXT, GIVEN, FOCUS = "#FFFFFF", "#58C4DD", "#FFFF00"
CLIP_1_SECONDS = 3.6  # 0.3 lead-in + 2.5 narration + 0.8 hold
CLIP_2_SECONDS = 3.1  # 0.3 lead-in + 2.0 narration + 0.8 hold


class Scene01(Scene):
    def _build_objects(self):
        self.eq = MathTex(r"a^2 + b^2 = c^2", color=TEXT).to_edge(UP)
        self.box = SurroundingRectangle(self.eq, buff=0.15, color=FOCUS)

    def _clip_1(self):
        # "Here is the theorem."  (phrase at 0.3 s)
        self.wait(0.3)
        self.play(Write(self.eq), run_time=1.5)
        self.wait(CLIP_1_SECONDS - 1.8)

    def _clip_2(self):
        # "Look at the whole equation."  (phrase at 0.3 s)
        self.wait(0.3)
        self.play(Create(self.box), run_time=1.0)
        self.play(self.box.animate.set_color(GIVEN), run_time=0.5)
        self.play(FadeOut(self.box), run_time=0.5)
        self.wait(CLIP_2_SECONDS - 2.3)

    def construct(self):
        self._build_objects()
        self._clip_1()
        self._clip_2()
```

Checked example (P7-P8: one event per phrase, holds while it is spoken):

```python
from manim import *

TEXT, GIVEN, FOCUS = "#FFFFFF", "#58C4DD", "#FFFF00"


class CardTiming(Scene):
    # narration (about 4.0 s): "Here is the curve y equals x squared. | Watch the point slide along it."
    def construct(self):
        ax = Axes(x_range=[-2, 2, 1], y_range=[0, 4, 1], x_length=6, y_length=4, axis_config={"color": TEXT})
        curve = ax.plot(lambda x: x**2, color=GIVEN)
        dot = Dot(ax.c2p(-2, 4), color=FOCUS)
        self.play(Create(ax), Create(curve), run_time=1.5)  # phrase 1
        self.wait(0.5)  # phrase 1 tail
        self.add(dot)
        self.play(MoveAlongPath(dot, curve), rate_func=linear, run_time=2.0)  # phrase 2
```

Checked example (P10: zoom in, then restore the frame):

```python
from manim import *

TEXT, FOCUS = "#FFFFFF", "#FFFF00"


class CardCamera(MovingCameraScene):
    def construct(self):
        dots = VGroup(*[Dot(RIGHT * i, color=TEXT) for i in range(-3, 4)])
        self.play(FadeIn(dots), run_time=0.5)
        self.camera.frame.save_state()
        self.play(self.camera.frame.animate.scale(0.5).move_to(dots[5]), run_time=1)
        self.play(Indicate(dots[5], color=FOCUS), run_time=1)
        self.play(Restore(self.camera.frame), run_time=1)
```
