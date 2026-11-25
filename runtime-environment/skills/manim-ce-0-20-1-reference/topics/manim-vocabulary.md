# Manim Vocabulary (Full Reference)

**Target: Manim Community Edition 0.20.1** (pinned in this project)
Entries tagged [0.21+] or [0.22+] need that version or later: they are NOT installed here (rule V8).

> Part of a three-file set for ManimCE 0.20.1, the version this project pins (checked against the installed package,
> 2026-11-25):
> [`manim-vocabulary.md`](manim-vocabulary.md) (which names exist), [`manim-construction-patterns.md`](manim-construction-patterns.md) (how to write the code; rule IDs L, A, C, T, S, P), [`manim-common-mistakes.md`](manim-common-mistakes.md) (what still goes wrong).
> Block names used inside the text map to files: MANIM_VOCABULARY = manim-vocabulary.md, MANIM_CONSTRUCTION_PATTERNS = manim-construction-patterns.md, MANIM_COMMON_MISTAKES = manim-common-mistakes.md. TEMPLATE = the TEMPLATE block of the clip's TASK.md. `TPL.<role>` means the hex string TEMPLATE gives for that colour role (text, focus, given, derived, warning, secondary, accent, outline, dim, surface).
> Scene code follows the project conventions in MANIM_CONSTRUCTION_PATTERNS PART 9 before anything here.

## PART 0. HOW TO USE THIS BLOCK

### 0.1 Scope

```text
    This block lists every name in the ManimCE reference manual that
    scene code can use, grouped by job. It says WHICH name to use.
    MANIM_CONSTRUCTION_PATTERNS says HOW to write the code. Its rules
    are cited here by ID (L1, A3, C5, T5, S3, ...).
```

### 0.2 Precedence (highest first)

```text
    1. MANIM_CONSTRUCTION_PATTERNS PART 9 - the project's scene harness
    2. TEMPLATE            - all colors, fonts, sizes; the background is
                             the harness's
    3. The clip's TASK.md  - content, beats, timing
    4. This block and the rest of MANIM_CONSTRUCTION_PATTERNS
```

### 0.3 Reading order

```text
    Step 1. Find the visual intent in PART 2 (quick index).
    Step 2. Look up the chosen name in PARTS 4-12 for its tags and
            arguments.
    Step 3. Run the checklist in PART 15.
```

### 0.4 Notation

```text
    MUST / NEVER / PREFER  - required / forbidden / default
    TPL.<role>             - a value from TEMPLATE
    Name                   - a class: Name(...)
    obj.method()           - a method on an existing object
    Tags:
      [3D]                 only inside ThreeDScene
      [BASE]               parent class; NEVER instantiate or cite
      [INTERNAL]           exists, but NEVER appears in scene code
      [LEGACY: use X]      exists; cite X instead
      [ADD]                self-animating mobject; show with self.add()
      [OPTIONAL-DEP: pkg]  needs an extra install
      [0.21+] / [0.22+]    minimum ManimCE version
      [COLOR: arg=DEFAULT] has a built-in non-template color; MUST
                           pass TPL.<role> through arg
```

### 0.5 Layout

```text
    PART 1   Selection rules              V1-V10
    PART 2   Quick index: intent -> name
    PART 3   Banned names
    PART 4   Scenes and scene methods
    PART 5   Geometry
    PART 6   Graphing and coordinate systems
    PART 7   Text, math, numbers, code
    PART 8   Data display, graphs, vector fields
    PART 9   Media, 3D, groups, annotations
    PART 10  Animations
    PART 11  Composition, timing, rate functions
    PART 12  Camera, updaters, layering
    PART 13  Visual patterns (not classes)
    PART 14  Rendering and configuration
    PART 15  Pre-output checklist
```

## PART 1. SELECTION RULES

```text
V1.  MUST cite only names listed in PARTS 4-12. Any other name is
     treated as nonexistent.
V2.  NEVER cite a name from PART 3. Use its replacement.
V3.  NEVER cite [BASE] or [INTERNAL] entries. NEVER cite a PART 13
     pattern as a class.
V4.  MUST match the scene class to what the scene uses:
         any [3D] entry or 3D camera method -> ThreeDScene
         camera pan or zoom                 -> MovingCameraScene
         zoom inset                         -> ZoomedScene
V5.  Every [COLOR] entry MUST receive TPL.<role> through its named
     argument (rule C1).
V6.  Every other visible object MUST get an explicit template color,
     because the Manim default is WHITE (rule C5).
V7.  NEVER use Manim's color libraries or generators (PART 3, last
     rows). Colors come only from TEMPLATE (rules C1-C4).
V8.  MUST NOT cite a version-tagged entry unless the pipeline's
     ManimCE version meets the tag.
V9.  [OPTIONAL-DEP] entries MUST NOT be cited unless the scene spec
     says the dependency is installed.
V10. Choose by intent (PART 2). When two names fit, PREFER the one
     listed first in PART 2.
```

## PART 2. QUICK INDEX: INTENT -> NAME

| Intent                              | First choice                       | Alternative                    |
|-------------------------------------|------------------------------------|--------------------------------|
| Show a word or label                | Text                               | MarkupText (styled spans)      |
| Show an equation                    | MathTex                            | Tex (prose + math)             |
| Show a heading                      | Title                              | Text                           |
| Show a list revealed step by step   | BulletedList                       | VGroup of Text + arrange       |
| Show code                           | Code                               | -                              |
| Draw a shape onto the screen        | Create                             | DrawBorderThenFill (filled)    |
| Write text onto the screen          | Write                              | AddTextLetterByLetter          |
| Bring in an image or group          | FadeIn                             | GrowFromCenter                 |
| Remove something                    | FadeOut                            | Uncreate / Unwrite             |
| Point at / connect two things       | Arrow                              | Line, CurvedArrow              |
| Mark a span or measurement          | BraceLabel                         | Brace + Text                   |
| Highlight a region                  | SurroundingRectangle               | BackgroundRectangle            |
| Draw attention briefly              | Indicate                           | Circumscribe, Flash            |
| Turn A into B                       | ReplacementTransform               | Transform, FadeTransform       |
| Rearrange an equation               | TransformMatchingTex               | TransformMatchingShapes        |
| Move along a path                   | MoveAlongPath                      | .animate.move_to               |
| Rotate                              | Rotate                             | Rotating (continuous)          |
| Plot y = f(x)                       | Axes + axes.plot                   | NumberPlane + plane.plot       |
| Plot data points as a line          | axes.plot_line_graph               | Dot + Line                     |
| Compare categories                  | BarChart                           | Rectangle bars                 |
| Show a table                        | Table                              | MathTable                      |
| Show a matrix                       | Matrix                             | IntegerMatrix, DecimalMatrix   |
| Show a network or tree              | Graph / DiGraph                    | Circle + Line                  |
| Show a 1D range or timeline         | NumberLine                         | Line + Dot                     |
| Show a vector field / flow          | ArrowVectorField / StreamLines     | -                              |
| Count a number up or down           | DecimalNumber + ValueTracker       | ChangeDecimalToValue           |
| Keep a label attached to a mover    | always_redraw                      | add_updater                    |
| Draw a trail behind a mover         | TracedPath                         | -                              |
| Zoom or pan                         | MovingCameraScene + camera.frame   | ZoomedScene (inset)            |
| Show 3D                             | ThreeDScene + ThreeDAxes           | -                              |
| Sync to narration                   | self.beat(n) + run_time + wait (P6-P8) | - (the pipeline adds audio) |

## PART 3. BANNED NAMES

| Banned                                           | Use instead                                       |
|--------------------------------------------------|---------------------------------------------------|
| ShowCreation                                     | Create                                            |
| TexMobject, TextMobject                          | MathTex, Tex, Text                                |
| OpenGLTexMobject, OpenGLTextMobject              | MathTex, Tex, Text                                |
| FadeInFrom, FadeInFromPoint, FadeInFromLarge     | FadeIn(mob, shift=..., scale=...)                 |
| FadeOutAndShift, FadeOutToPoint                  | FadeOut(mob, shift=..., scale=...)                |
| VFadeIn, VFadeOut, VFadeInThenOut                | FadeIn, FadeOut                                   |
| CircleIndicate                                   | Indicate or Circumscribe                          |
| ShowCreationThenDestruction                      | Succession(Create(m), Wait(1), Uncreate(m))       |
| ShowCreationThenDestructionAround                | Circumscribe                                      |
| ShowCreationThenFadeAround                       | Circumscribe                                      |
| ShowPassingFlashAround                           | ShowPassingFlash(SurroundingRectangle(m))         |
| AnimationOnSurroundingRectangle                  | SurroundingRectangle + Create / FadeIn            |
| WiggleOutThenIn                                  | Wiggle                                            |
| TurnInsideOut                                    | Transform                                         |
| ShowPassingFlashWithThinningStroke               | ShowPassingFlashWithThinningStrokeWidth           |
| VMobjectFromSVGPathstring                        | VMobjectFromSVGPath                               |
| rotate_in_place, scale_in_place,                 | rotate(), scale(), move_to(), shift()             |
|   scale_about_point (methods)                    |                                                   |
| GraphScene                                       | Scene + Axes                                      |
| SampleSpaceScene                                 | Scene + SampleSpace                               |
| ReconfigurableScene                              | Scene                                             |
| InteractiveScene                                 | Scene (InteractiveScene is ManimGL only)          |
| LineGraph (class), get_line_graph (method)       | axes.plot_line_graph(...)                         |
| Bezier (class)                                   | CubicBezier                                       |
| ImplicitCurve                                    | ImplicitFunction or axes.plot_implicit_curve      |
| TypstMath                                        | MathTypst [0.21+, not installed]                  |
| ThoughtBubble, SpeechBubble                      | RoundedRectangle + Text callout                   |
| manimlib imports, ManimGL-only names             | from manim import * (ManimCE)                     |
| eq.get_parts_by_tex (removed in 0.20)            | eq.set_color_by_tex / eq.get_part_by_tex          |
| ease_in, ease_out, ease_in_out (bare)            | shaped variant, e.g. ease_in_out_sine (11.3)      |
| Color libraries: XKCD.\*, X11.\*, SVGNAMES.\*,      | `TPL.<role>`                                        |
|   DVIPSNAMES.\*, AS2700.\*, BS381.\*                |                                                   |
| random_color, random_bright_color,               | `TPL.<role>`                                        |
|   RandomColorGenerator                           |                                                   |
| color_gradient, interpolate_color, invert_color  | `TPL.<role>` (rule C4)                              |

## PART 4. SCENES AND SCENE METHODS

### 4.1 Scene classes

```text
Scene                      fixed camera; default for 2D
MovingCameraScene          camera can pan, zoom, follow (PART 12.1)
ZoomedScene                magnified inset of one region
                           [COLOR: call .set_color(TPL.<role>) on
                           self.zoomed_camera.frame and
                           self.zoomed_display.display_frame]
ThreeDScene                3D depth and camera orientation
SpecialThreeDScene         ThreeDScene with preset 3D helpers
VectorScene                2D scene with vector helpers:
                           add_plane(), add_vector(), add_axes()
LinearTransformationScene  grid and basis vectors under a matrix;
                           self.apply_matrix(m) animates it
                           [COLOR: grid and basis vectors have built-in
                           colors; override with template colors]
```

### 4.2 Scene methods (inside construct)

```text
self.add(*mobs)                  show instantly, no animation
self.remove(*mobs)               remove instantly
self.clear()                     remove everything
self.play(*anims, run_time=, rate_func=)
                                 play animations (PART 10, 11)
self.wait(seconds)               hold the frame; the clip ends on a hold (S3)
self.wait_until(condition)       wait until condition() is True
self.pause(seconds)              hold the frame with updaters frozen
self.bring_to_front(*mobs)       draw on top
self.bring_to_back(*mobs)        draw underneath
self.add_sound(path, time_offset=0, gain=None)
                                 add an audio file at the current time
                                 [NOT IN CLIPS: no file access (P2);
                                 the pipeline adds the narration]
self.add_subcaption(text, duration=1, offset=0)
                                 add a subtitle cue (written to .srt)
                                 [NOT IN CLIPS: subtitles come from the
                                 narration]
self.next_section(name)          start a named section; each section
                                 can be saved as its own video file
self.mobjects                    list of objects currently on screen

Background: set only per rule C8.

4.3 [INTERNAL] - never in scene code
Manager [0.22+], SceneFileWriter, RerunSceneHandler,
SceneInteractContinue, SceneInteractRerun, Section,
DefaultSectionType, Camera, MovingCamera, ThreeDCamera,
MultiCamera, MappingCamera, OldMultiCamera, SplitScreenCamera,
BackgroundColoredVMobjectDisplayer, ManimConfig, ManimFrame
```

## PART 5. GEOMETRY

### 5.1 Points and lines

```text
Dot                  data point, node, marker
AnnotationDot        larger Dot meant to carry a label
LabeledDot           Dot with a label inside
Point                invisible anchor (point cloud)
VectorizedPoint      invisible anchor that can sit in a VGroup
Line                 connector, segment
DashedLine           guide, projection, boundary hint
Elbow                right-angle connector
TangentLine          tangent to a curve at a proportion along it
Arrow                direction, causality, pointer
DoubleArrow          two-way link
Vector               arrow starting at ORIGIN
CurvedArrow          curved one-way link
CurvedDoubleArrow    curved two-way link
LabeledLine          Line with a label along it
LabeledArrow         Arrow with a label along it
Angle                angle marker between two lines
RightAngle           square-corner marker
TipableVMobject      parent of lines that can carry tips [BASE]
```

### 5.2 Arrow tips (pass as tip_shape=)

```text
ArrowTriangleFilledTip   default filled triangle
ArrowTriangleTip         outlined triangle
StealthTip               swept "stealth" head
ArrowCircleFilledTip     filled circle end
ArrowCircleTip           outlined circle end
ArrowSquareFilledTip     filled square end
ArrowSquareTip           outlined square end
ArrowTip                 parent [BASE]
Example: Arrow(a, b, tip_shape=StealthTip)
```

### 5.3 Arcs and curves

```text
Circle               boundary, ring, node
Ellipse              stretched region, orbit
Arc                  partial circle
ArcBetweenPoints     arc from two endpoints
TangentialArc        arc tangent to two lines; rounded corner
Sector               pie slice (radius, angle)
AnnularSector        ring wedge (inner_radius, outer_radius)
Annulus              full ring
ArcPolygon           closed shape whose sides are arcs
ArcPolygonFromArcs   ArcPolygon built from existing Arc objects
CubicBezier          smooth S-curve between two points
```

### 5.4 Polygons

```text
Square, Rectangle, RoundedRectangle, Triangle
RegularPolygon       symmetric n-sided shape
Polygon              shape from a vertex list
Polygram             several vertex loops in one mobject
RegularPolygram      star polygon (e.g. pentagram)
Star                 star shape
Cutout               shape with holes cut out
ConvexHull           boundary around a 2D point set
```

### 5.5 Shape matchers (built around another object)

```text
SurroundingRectangle highlight box; accepts one mobject or a list
                     [COLOR: color=YELLOW]
BackgroundRectangle  opaque fill behind text
                     [COLOR: defaults to background; pass
                     color=TPL.background]
Cross                X over an object; wrong / deleted
Underline            line under text
```

### 5.6 Boolean operations

```text
Union, Intersection, Difference, Exclusion
                     Venn-style region algebra on two VMobjects
```

### 5.7 Frame helpers

```text
ScreenRectangle      16:9 rectangle; "screen" or video placeholder
FullScreenRectangle  rectangle the size of the frame
                     NEVER use as a background (rule C8)
```

### 5.8 Custom paths

```text
VMobject             build a custom path:
                       VMobject().set_points_as_corners([p1, p2, p3])
                       VMobject().set_points_smoothly([p1, p2, p3])
DashedVMobject       dashed copy of any VMobject
CurvesAsSubmobjects  split a path into per-segment parts
```

## PART 6. GRAPHING AND COORDINATE SYSTEMS

### 6.1 Classes

```text
NumberLine           1D axis
UnitInterval         NumberLine from 0 to 1
Axes                 2D Cartesian frame
                     [COLOR: axis_config={"color": ...}]
NumberPlane          2D grid
                     [COLOR: background_line_style=
                     {"stroke_color": ...}, axis_config]
PolarPlane           r-theta grid
ComplexPlane         Argand diagram
ThreeDAxes           x-y-z frame [3D]
CoordinateSystem     shared parent [BASE]
LinearBase, LogBase  axis scaling:
                     x_axis_config={"scaling": LogBase()}
FunctionGraph        y = f(x) in scene units (no axes)
ParametricFunction   x(t), y(t) in scene units
ImplicitFunction     F(x, y) = 0 in scene units
On any axes, PREFER the methods in 6.2 so curves use the axes' scale.
```

### 6.2 Axes / NumberPlane methods

```text
Plotting
  axes.plot(f, x_range=)                  y = f(x)
  axes.plot_parametric_curve(f, t_range=) x(t), y(t)
  axes.plot_implicit_curve(F)             F(x, y) = 0
  axes.plot_polar_graph(r_func, theta_range=)
  axes.plot_derivative_graph(graph)       f'(x)
  axes.plot_antiderivative_graph(graph)   integral of f
  axes.plot_line_graph(x_values, y_values, add_vertex_dots=True)
                                          VDict with "line_graph" and
                                          "vertex_dots"
                                          [COLOR: line_color=YELLOW,
                                          vertex_dot_style={...}]
  axes.plot_surface(f, u_range=, v_range=)  [3D, ThreeDAxes]
Areas and slopes
  axes.get_area(graph, x_range=, opacity=) shaded area
  axes.get_riemann_rectangles(graph, x_range=, dx=)
  axes.get_secant_slope_group(x, graph, dx=)
Lines and labels
  axes.get_axis_labels(x_label="x", y_label="y")
  axes.get_graph_label(graph, label=r"x^2", x_val=1.5, direction=UL)
  axes.get_vertical_line(point), axes.get_horizontal_line(point)
  axes.get_lines_to_point(point)
  axes.get_T_label(x_val, graph)
  axes.add_coordinates()                  tick numbers
Coordinate conversion
  axes.c2p(x, y)      axes coordinates -> scene point
                      (long name: axes.coords_to_point)
  axes.p2c(point)     scene point -> axes coordinates
  axes.i2gp(x, graph) x value -> point on graph
```

### 6.3 NumberLine methods

```text
  line.n2p(x)         number -> scene point
  line.p2n(point)     scene point -> number
  line.add_numbers()  tick numbers
  line.add_labels({value: label})
```

Checked example (6.1-6.2; colors are the Standard template's roles):

```python
from manim import *

TEXT, GIVEN, DERIVED = "#FFFFFF", "#58C4DD", "#83C167"


class CardAxes(Scene):
    def construct(self):
        ax = Axes(x_range=[0, 3, 1], y_range=[0, 9, 3], x_length=6, y_length=4, axis_config={"color": TEXT}).to_edge(
            DOWN
        )
        labels = ax.get_axis_labels(x_label="x", y_label="y").set_color(TEXT)
        g = ax.plot(lambda x: x**2, x_range=[0, 3], color=GIVEN)
        lab = ax.get_graph_label(g, label=r"x^2", x_val=2.2, direction=UL, color=GIVEN)
        area = ax.get_area(g, x_range=[0, 2], color=GIVEN, opacity=0.4)
        pts = ax.plot_line_graph(
            [0, 1, 2, 3], [0, 1, 4, 9], add_vertex_dots=True, line_color=DERIVED, vertex_dot_style={"color": DERIVED}
        )
        self.play(Create(ax), FadeIn(labels), run_time=1)
        self.play(Create(g), Write(lab), run_time=1.5)
        self.play(FadeIn(area), FadeIn(pts), run_time=1)
        self.wait(0.5)
```

## PART 7. TEXT, MATH, NUMBERS, CODE

### 7.1 Plain text (Pango, no LaTeX)

```text
Text                 labels, captions; t2c={"word": TPL.<role>}
                     font= TEMPLATE's font; under ~40 characters a
                     line (rule L10); no LaTeX needed, any Unicode
MarkupText           inline styling with Pango markup
                     [COLOR: every <span foreground="..."> MUST be a
                     template hex]
Paragraph            multi-line text block
```

### 7.2 LaTeX

```text
MathTex              math; split rules T1-T5; raw strings (T8);
                     needs latex + dvisvgm (the run's preflight checks)
Tex                  prose with inline $math$
Title                large heading; underline on by default
BulletedList         list whose items can be revealed one by one
SingleStringMathTex  one-string parent of MathTex [BASE]
MathTexPart          type of the parts inside MathTex [INTERNAL]
TexTemplate          custom preamble (rule T6)
TexTemplateLibrary   ready templates: .default, .simple, .ctex,
                     .threeb1b
TexFontTemplates     ready font templates, e.g.
                     TexFontTemplates.french_cursive
                     Pass via tex_template=...
```

Checked example (Text vs Tex vs MathTex):

```python
from manim import *

TEXT, SECONDARY = "#FFFFFF", "#BBBBBB"


class CardText(Scene):
    def construct(self):
        title = Text("Euler's identity", font_size=40, color=TEXT).to_edge(UP)
        eq = MathTex(r"e^{i\pi} + 1 = 0", font_size=60, color=TEXT)
        note = Tex(r"where $i^2 = -1$", font_size=32, color=SECONDARY).next_to(eq, DOWN)
        self.play(FadeIn(title), Write(eq), run_time=1.5)
        self.play(FadeIn(VGroup(note)), run_time=0.5)
        self.wait(0.5)
```

### 7.3 Typst [0.21+] [OPTIONAL-DEP: manim[typst]]

```text
Typst                text and markup compiled by Typst; no LaTeX
                     install needed
MathTypst            math compiled by Typst; supports {{ ... }}
                     grouping like MathTex
```

### 7.4 Live numbers

```text
DecimalNumber        decimal value; num.set_value(x)
Integer              integer value
Variable             "label = value" pair; var.tracker is its
                     ValueTracker
```

### 7.5 Code

```text
Code(code_string=..., language="python", formatter_style=...,
     add_line_numbers=True, background_config={...})
     Syntax-highlighted code block.
     Code.get_styles_list() lists built-in style names.
     [COLOR, v0.20: background_config={"fill_color": TPL.<role>};
     use the formatter_style TEMPLATE names]
     [COLOR, 0.21+: syntax and line-number colors come ONLY from
     formatter_style. To use template colors, pass a Pygments Style
     subclass built from TPL hex values:
         from pygments.style import Style
         from pygments.token import Token, Keyword, String, Comment, Number
         class TplStyle(Style):
             background_color  = TPL.code_background
             line_number_color = TPL.muted
             styles = {Token: TPL.text, Keyword: TPL.accent,
                       String: TPL.highlight, Comment: TPL.muted,
                       Number: TPL.accent}
         Code(code_string=src, language="python",
              formatter_style=TplStyle)
     paragraph_config={"color": ...} no longer has any effect.]
```

## PART 8. DATA DISPLAY, GRAPHS, VECTOR FIELDS

### 8.1 Tables

```text
Table, MathTable, DecimalTable, IntegerTable, MobjectTable
     Cells hold Text / MathTex / decimals / integers / mobjects.
     [COLOR: line_config={"color": ...}; element colors via
     table.get_entries().set_color(...)]
     Methods: get_cell((r, c)), get_entries(), get_rows(),
     get_columns(), add_highlighted_cell((r, c), color=TPL.<role>)
```

### 8.2 Matrices

```text
Matrix, DecimalMatrix, IntegerMatrix, MobjectMatrix
     Bracketed grids for linear algebra.
     Methods: get_entries(), get_rows(), get_columns(),
     get_brackets(), set_row_colors(...), set_column_colors(...)
     (pass template colors)
```

### 8.3 Charts and probability

```text
BarChart             categorical bars (an Axes subclass)
                     [COLOR: bar_colors=[...]]
                     Methods: change_bar_values(values),
                     get_bar_labels()
SampleSpace          rectangle split into weighted regions
                     Methods: divide_horizontally(p),
                     divide_vertically(p)
```

### 8.4 Networks

```text
Graph                undirected network
DiGraph              directed network
GenericGraph         parent [BASE]
LayoutFunction       protocol for custom layouts [BASE]
Arguments:
    layout="spring" | "circular" | "kamada_kawai" | "partite" |
           "planar" | "random" | "shell" | "spectral" | "spiral" |
           "tree"   ("tree" needs layout_config={"root_vertex": v})
    [COLOR: vertex_config={"fill_color": ...},
            edge_config={"stroke_color": ...}]
Access:  graph[v] -> vertex mobject; graph.edges[(u, v)] -> edge
Change:  graph.add_vertices(...), graph.remove_vertices(...),
         graph.add_edges(...), graph.change_layout("circular")
```

### 8.5 Vector fields

```text
ArrowVectorField     grid of arrows showing f(point)
StreamLines          flowing lines along f(point); animate with
                     self.add(field); field.start_animation(
                     warm_up=True, flow_speed=1.5); self.wait(n)
StreamLine           a single stream line [INTERNAL]
VectorField          parent [BASE]
[COLOR: color=TPL.<role> for one color, or colors=[TPL...] for a
scheme; the default is a built-in multi-color list]
```

## PART 9. MEDIA, 3D, GROUPS, ANNOTATIONS

### 9.1 Media

```text
ImageMobject         raster image (PNG, JPG)
ImageMobjectFromCamera  image of another camera's output
AbstractImageMobject parent [BASE]
SVGMobject           vector file
                     [COLOR: keeps the file's colors; call
                     .set_color(TPL.<role>) unless the asset comes
                     from the template]
VMobjectFromSVGPath  one SVG path as a VMobject
ManimBanner          the Manim logo; NEVER use in lesson content

9.2 3D objects (all [3D])
Sphere, Cube, Prism, Cylinder, Cone, Torus, Dot3D, Line3D, Arrow3D
Surface              parametric surface
                     [COLOR: checkerboard_colors=[...] or fill_color]
Tetrahedron, Octahedron, Icosahedron, Dodecahedron
Polyhedron           custom solid from vertices and faces
ConvexHull3D         solid enclosing a point cloud
ThreeDVMobject       3D-shaded parent [BASE]
```

### 9.3 Groups

```text
VGroup               group of VMobjects; arrange per rule L4
VDict                VMobject group addressed by key
Group                group of mixed types (needed with images)
PGroup               group of point clouds
PointCloudDot        many points as one mobject; dense scatter
PMobject, Mobject1D, Mobject2D   point-cloud parents [BASE]
Mobject              root parent [BASE]
```

### 9.4 Annotations

```text
Brace                curly brace along a side of an object
BraceLabel           brace + label (mobject or tex)
BraceText            brace + plain text
BraceBetweenPoints   brace between two points
ArcBrace             brace that follows an Arc
Label                small badge attached to a shape
LabeledPolygram      Polygram with an attached Label
```

## PART 10. ANIMATIONS

### 10.1 Utility

```text
Add(mob)             zero-length add; fills a Succession slot
Wait(run_time)       pause inside Succession / AnimationGroup
Animation            parent of all animations [BASE]
```

### 10.2 Appear (MUST be classes, rule A2)

```text
Create               draw a path
DrawBorderThenFill   outline, then fill
Write                stroke-by-stroke; default for Text/Tex/MathTex
AddTextLetterByLetter  typewriter, one character at a time
AddTextWordByWord    one word at a time
TypeWithCursor       typewriter with a cursor
FadeIn               fade in; shift= for direction, scale= for size
GrowFromCenter       grow from center
GrowFromPoint        grow from a point
GrowFromEdge         grow out of one edge
GrowArrow            arrow extends start -> tip
SpinInFromNothing    spin and grow from zero
SpiralIn             VGroup parts spiral inward
ShowIncreasingSubsets   reveal parts cumulatively
ShowSubmobjectsOneByOne show one part at a time
ShowPartial          parent of Create/Uncreate [BASE]
```

### 10.3 Disappear (MUST be classes)

```text
FadeOut              default removal; shift= / scale= supported
Uncreate             reverse Create
Unwrite              reverse Write
RemoveTextLetterByLetter  delete one character at a time
UntypeWithCursor     delete with a cursor
ShrinkToCenter       shrink to nothing
```

### 10.4 Transform

```text
ReplacementTransform       A becomes B; B replaces A
Transform                  A takes B's form; A stays
TransformFromCopy          copy of A becomes B; A stays
FadeTransform              cross-fade A -> B
FadeTransformPieces        cross-fade part by part
TransformMatchingTex       equation rearrangement (rule T5)
TransformMatchingShapes    match similar sub-shapes
TransformMatchingAbstractBase  parent [BASE]
ClockwiseTransform         morph along a clockwise arc
CounterclockwiseTransform  morph along a counter-clockwise arc
MoveToTarget               animate to mob.target
                           (mob.generate_target() first)
Restore                    animate back to mob.save_state()
ScaleInPlace               scale about own center
Swap                       swap two mobjects' positions
CyclicReplace              rotate positions through a list
FadeToColor                fade to a color
                           [COLOR: color MUST be TPL.<role>]
ApplyMatrix                matrix transform of all points
ApplyComplexFunction       warp by a complex function
ApplyFunction              function applied to the whole mobject
ApplyPointwiseFunction     function applied to each point
ApplyPointwiseFunctionToCenter  move by mapping the center
ApplyMethod                [LEGACY: use .animate]
TransformAnimations        [LEGACY: use Transform]
```

### 10.5 Motion and rotation

```text
MoveAlongPath        travel along a path
Rotate               one rotation by an angle (rule A3)
Rotating             continuous spin over run_time
Homotopy             deform by a point function
SmoothedVectorizedHomotopy  smoother Homotopy for VMobjects
ComplexHomotopy      Homotopy in the complex plane
PhaseFlow            move points along a vector field
```

### 10.6 Emphasis

```text
Indicate             scale-and-color pulse  [COLOR: color=YELLOW]
Circumscribe         temporary outline      [COLOR: color=YELLOW]
Flash                burst of lines         [COLOR: color=YELLOW]
FocusOn              shrinking spotlight    [COLOR: color=GREY]
Wiggle               wobble
ApplyWave            ripple
Blink                visibility toggle
ShowPassingFlash     highlight travels along a path (path's color);
                     pass a copy so the original stays (A9)
ShowPassingFlashWithThinningStrokeWidth  thinning passing flash
Broadcast            copies of a shape expand and fade
                     (shape's own color)
```

Checked example (emphasis on template colors; each lasts 1 s or less, rule A9):

```python
from manim import *

TEXT, FOCUS = "#FFFFFF", "#FFFF00"


class CardEmphasis(Scene):
    def construct(self):
        eq = MathTex(r"e^{i\pi} + 1 = 0", color=TEXT)
        self.play(GrowFromCenter(eq), run_time=1)
        self.play(Circumscribe(eq, color=FOCUS), run_time=1)
        self.play(ShowPassingFlash(Underline(eq).set_color(FOCUS), time_width=0.5), run_time=1)
        self.play(Indicate(eq, color=FOCUS), run_time=0.8)
```

### 10.7 Numbers

```text
ChangeDecimalToValue(number, target)   animate to a value
ChangingDecimal(number, func)          value from func(alpha)
```

### 10.8 Persistent [ADD]

```text
AnimatedBoundary     shimmering outline  [COLOR: colors=[...]]
TracedPath           trail behind a point [COLOR: stroke_color=WHITE]
```

## PART 11. COMPOSITION, TIMING, RATE FUNCTIONS

### 11.1 Composition

```text
AnimationGroup       together; lag_ratio staggers
Succession           one after another
LaggedStart          staggered starts
LaggedStartMap(AnimClass, group)  one class over many mobjects
ChangeSpeed          speed up / slow down within an animation
```

### 11.2 Timing arguments

```text
run_time   seconds
lag_ratio  0.0 = together; 1.0 = fully sequential
rate_func  easing (11.3)
```

### 11.3 Rate functions

```text
Direct names (rate_func=smooth):
    linear, smooth, smoothstep, smootherstep, smoothererstep,
    double_smooth, rush_into, rush_from, slow_into,
    there_and_back, there_and_back_with_pause, wiggle, lingering,
    exponential_decay, running_start,
    not_quite_there(func, proportion), squish_rate_func(func, a, b)
Through the module (rate_func=rate_functions.ease_out_bounce):
    ease_in_<f>, ease_out_<f>, ease_in_out_<f>
    where <f> is sine, quad, cubic, quart, quint, expo, circ,
    back (overshoot), elastic (spring), bounce (drop and bounce)
```

## PART 12. CAMERA, UPDATERS, LAYERING

### 12.1 Camera

| Action                    | Code                                          | Scene             |
|---------------------------|-----------------------------------------------|-------------------|
| Pan                       | self.camera.frame.animate.move_to(target)     | MovingCameraScene |
| Zoom                      | self.camera.frame.animate.scale(f)            | MovingCameraScene |
| Fit an object             | self.camera.frame.animate.set(width=w)        | MovingCameraScene |
| Save / return             | self.camera.frame.save_state(); Restore(...)  | MovingCameraScene |
| Jump to orientation       | self.set_camera_orientation(phi=, theta=)     | ThreeDScene       |
| Animate orientation       | self.move_camera(phi=, theta=)                | ThreeDScene       |
| Start / stop orbit        | self.begin_ambient_camera_rotation(rate=)     | ThreeDScene       |
|                           | self.stop_ambient_camera_rotation()           |                   |
| Keep 2D text flat in 3D   | self.add_fixed_in_frame_mobjects(\*mobs)       | ThreeDScene       |
| Show zoom inset           | self.activate_zooming()                       | ZoomedScene       |

### 12.2 Live values and updaters

```text
ValueTracker               animatable number (not drawn);
                           t.get_value(), t.animate.set_value(x)
ComplexValueTracker        animatable complex number
mob.add_updater(func)      run func(mob) or func(mob, dt) every frame
mob.remove_updater(func)
mob.clear_updaters()
always_redraw(func)        rebuild a mobject every frame
mob.always.next_to(other, UP)  0.20 builder: keep a relation every
                           frame without a lambda
always(method, *args)      call a method every frame
f_always(method, *arg_funcs)  same, with arguments from functions
always_shift(mob, direction, rate)   constant drift
always_rotate(mob, rate)   constant spin
turn_animation_into_updater(anim)    loop an animation as an updater
cycle_animation(anim)      repeat an animation as an updater
UpdateFromFunc             call func(mob) during one play()
UpdateFromAlphaFunc        same, with progress alpha 0 -> 1
MaintainPositionRelativeTo keep an offset from another mobject
Objects built inside always_redraw MUST set template colors there
(rule C5).
```

Checked example (a tracker drives a redrawn dot and a number; updaters cleared after, P11):

```python
from manim import *

TEXT, GIVEN, FOCUS = "#FFFFFF", "#58C4DD", "#FFFF00"


class CardTracker(Scene):
    def construct(self):
        ax = Axes(x_range=[0, 3, 1], y_range=[0, 9, 3], x_length=6, y_length=4, axis_config={"color": TEXT})
        g = ax.plot(lambda x: x**2, color=GIVEN)
        t = ValueTracker(0.5)
        dot = always_redraw(lambda: Dot(ax.c2p(t.get_value(), t.get_value() ** 2), color=FOCUS))
        val = DecimalNumber(0, num_decimal_places=2, color=TEXT).to_corner(UR)
        val.add_updater(lambda m: m.set_value(t.get_value() ** 2))
        self.add(ax, g, dot, val)
        self.play(t.animate.set_value(2.5), run_time=2)
        val.clear_updaters()
        self.wait(0.5)
```

### 12.3 Layering

```text
mob.set_z_index(n)   higher n draws in front
self.bring_to_front(mob), self.bring_to_back(mob)
```

## PART 13. VISUAL PATTERNS (not classes, rule V3)

| Pattern                    | Built from                                                    |
|----------------------------|---------------------------------------------------------------|
| Flowchart                  | RoundedRectangle, Text, Arrow, VGroup.arrange                 |
| Timeline                   | NumberLine, Dot, Text                                         |
| NeuralNetwork              | Circle, Line, VGroup.arrange; or Graph(layout="partite")      |
| DecisionTree               | DiGraph(layout="tree"), Text                                  |
| FiniteStateMachine         | Circle + CurvedArrow + Text, or DiGraph                       |
| SortingVisualization       | Rectangle bars in VGroup, Swap, .animate                      |
| GraphTraversal             | Graph, vertex/edge .animate.set_color(TPL...)                 |
| AlgorithmVisualization     | Code, SurroundingRectangle on the active line, a state panel  |
| PhysicsSimulation          | Dot, Vector, TracedPath, ValueTracker, add_updater            |
| FlowField                  | ArrowVectorField or StreamLines                               |
| MathematicalProof          | MathTex chain, TransformMatchingTex, Text justifications      |
| CalculusVisualization      | Axes, plot, get_area, get_riemann_rectangles, TangentLine     |
| DataStructureVisualization | Square or Rectangle, Text, Arrow, VGroup.arrange              |
| CircuitDiagram             | Line, Elbow, Rectangle or SVGMobject, Text                    |
| Infographic                | SVGMobject, Text, BarChart, VGroup.arrange_in_grid            |

## PART 14. RENDERING AND CONFIGURATION

### 14.1 Command line (reference only: clips are checked with ./check, never rendered with manim; rule S5)

| Goal                          | v0.20.x                        | v0.22+                              |
|-------------------------------|--------------------------------|-------------------------------------|
| Render one scene              | manim -ql file.py Scene        | same                                |
| Quality                       | -ql / -qm / -qh / -qp / -qk    | same                                |
| Open the result               | -p                             | -p (opens the file)                 |
| Render all scenes             | -a                             | -a                                  |
| Last frame only               | -s                             | -s or --format png                  |
| GIF                           | -i / --save_as_gif             | --format gif                        |
| Every frame as PNG            | -g / --save_pngs               | --format png-sequence               |
| Transparent background        | -t                             | -t with --format auto, mov or webm  |
| Save sections separately      | --save_sections                | --save_sections                     |
| Clear cache                   | --flush_cache                  | manim cache clear file.py Scene     |
| Live preview window           | --force_window (OpenGL)        | -l / --live-preview                 |

```text
14.2 config values code may read
config.frame_width, config.frame_height,
config.frame_x_radius, config.frame_y_radius   (MANIM_CONSTRUCTION_PATTERNS 1.1)
config.pixel_width, config.pixel_height, config.frame_rate
Code MUST NOT write config.background_color except per rule C8.
NEVER change frame_width / frame_height in scene code. Layout rules
read these values: 16:9 is 14.222 x 8.0, portrait swaps them
(MANIM_CONSTRUCTION_PATTERNS 1.1).
```

## PART 15. PRE-OUTPUT CHECKLIST

```text
[ ] V1   Every name appears in PARTS 4-12
[ ] V2   No name from PART 3
[ ] V3   No [BASE] or [INTERNAL] entry; patterns built from parts
[ ] V4   Scene class matches 3D entries and camera actions
[ ] V5   Every [COLOR] entry overridden with TPL.<role>
[ ] V6   Every other visible object has an explicit template color
[ ] V7   No Manim color libraries, generators, or blends
[ ] V8   No version-tagged entry above the pipeline's version
[ ] V9   No [OPTIONAL-DEP] entry unless the spec allows it
[ ] 11.3 Shaped easing written as rate_functions.ease_*_<family>
[ ] 14   Render command matches the installed version
```
