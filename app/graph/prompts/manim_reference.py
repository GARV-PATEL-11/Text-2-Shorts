"""
Manim Reference
"""

# =============================================================================
#  MANIM CONSTRUCTION PATTERNS — PLUGGABLE PROMPT SUB-COMPONENT
#  Target: Manim Community Edition v0.20.x (docs.manim.community)
#  Verified against the live v0.20.1 Reference Manual, mobject.py source,
#  and constants.py on 2026-07-01.
# =============================================================================
#
# CHANGELOG
# ----------
# v2 (this revision)
#   - Promoted the module's export from a private, single-use string
#     (`_MANIM_CONSTRUCTION_PATTERNS`) to a public constant
#     (`MANIM_CONSTRUCTION_PATTERNS`) so it can be imported and composed
#     into other prompts the same way `MANIM_VOCABULARY` already is.
#     A private alias is kept for backward compatibility with any existing
#     `from ... import _MANIM_CONSTRUCTION_PATTERNS` call sites.
#   - Section 7 (MathTex indexing): added a one-line cross-reference to
#     `get_part_by_tex` being the safer alternative to raw index math when
#     a spec is written by an LLM that may miscount tokens.
#   - No factual corrections were required elsewhere in this file — the
#     canvas geometry, spacing constants, positioning/mutation API, color
#     system, and MathTex-indexing claims were checked against the live
#     v0.20.1 docs and are accurate as written.
#
# Purpose: this block is NOT a class catalog (see the vocabulary module for
# that). It covers the *construction* API — positioning, mutation, color,
# MathTex indexing, and scene structure — which is where generated Manim
# code most often breaks even when the right classes were chosen. This
# module is designed to be imported and concatenated alongside the
# vocabulary block and the common-mistakes block in the same system prompt.
# =============================================================================

from __future__ import annotations


MANIM_CONSTRUCTION_PATTERNS = """
════════════════════════════════════════════════════════════════
MANIM CONSTRUCTION PATTERNS — PROMPT SUB-COMPONENT
Target: Manim Community Edition v0.20.x (docs.manim.community)
Verified against the live v0.20.1 Reference Manual, mobject.py source,
and constants.py on 2026-07-01.

Purpose: this block is NOT a class catalog (see MANIM_PRIMITIVE_SELECTION
vocabulary for that). It covers the *construction* API — positioning,
mutation, color, MathTex indexing, and scene structure — which is where
generated Manim code most often breaks even when the right classes were
chosen. Compose this alongside the vocabulary block in the same prompt.
════════════════════════════════════════════════════════════════

──────────────────────────────────────────
1. CANVAS GEOMETRY — the actual visible bounds
──────────────────────────────────────────
config.frame_width   = 14.222...  (= frame_height * 16/9)
config.frame_height  = 8.0
config.frame_x_radius = 7.111...   (half-width; usable x ∈ [-7.11, 7.11])
config.frame_y_radius = 4.0        (half-height; usable y ∈ [-4.0, 4.0])
These are LOGICAL units, independent of render resolution (480p/1080p/4k
all use the same 14.222 × 8.0 coordinate frame unless frame_width/height
is explicitly overridden). ORIGIN (0,0,0) is the exact center of frame.
Any layout-agnostic placement math (semantic zones, safe margins, etc.)
should be expressed as fractions of frame_x_radius / frame_y_radius,
never as hardcoded pixel or absolute-unit guesses.

──────────────────────────────────────────
2. DIRECTION CONSTANTS
──────────────────────────────────────────
ORIGIN = (0,0,0)         UP = (0,1,0)      DOWN = (0,-1,0)
RIGHT = (1,0,0)          LEFT = (-1,0,0)
IN = (0,0,-1)            OUT = (0,0,1)      — into / out of the screen (3D)
UL = UP+LEFT   UR = UP+RIGHT   DL = DOWN+LEFT   DR = DOWN+RIGHT
These are unit vectors — multiply for distance: `mob.shift(2*UP)`,
or combine for diagonals: `mob.to_corner(UP + RIGHT)`.

──────────────────────────────────────────
3. DEFAULT SPACING CONSTANTS — cite exact values, don't guess
──────────────────────────────────────────
SMALL_BUFF      = 0.1
MED_SMALL_BUFF  = 0.25   → this is DEFAULT_MOBJECT_TO_MOBJECT_BUFFER
                            (the default buff for `.next_to()`)
MED_LARGE_BUFF  = 0.5    → this is DEFAULT_MOBJECT_TO_EDGE_BUFFER
                            (the default buff for `.to_edge()` / `.to_corner()`)
LARGE_BUFF      = 1.0
DEFAULT_FONT_SIZE = 48
Use these named constants (or their literal values) rather than inventing
arbitrary buff numbers — arbitrary buffs are how generated layouts end up
with inconsistent, visually noisy spacing.

──────────────────────────────────────────
4. POSITIONING API — relative and absolute placement
──────────────────────────────────────────
mob.next_to(other, direction=RIGHT, buff=0.25, aligned_edge=ORIGIN)
                    → places `mob` adjacent to `other`/a point, offset by
                      `direction`; THE primary relative-positioning call
mob.to_edge(edge, buff=0.5)      → snaps to a frame edge (UP/DOWN/LEFT/RIGHT)
mob.to_corner(corner, buff=0.5)  → snaps to a frame corner (UL/UR/DL/DR)
mob.align_to(other, direction)   → aligns ONE edge of `mob` to match `other`'s
                      corresponding edge/point along `direction`, without
                      moving `mob` along the perpendicular axis
mob.shift(vector)                → relative move by a vector (does not
                      recompute layout relationships — a one-shot nudge)
mob.move_to(point_or_mobject)    → absolute move: centers `mob` on a point,
                      or on another mobject's center
mob.get_center() / get_top() / get_bottom() / get_left() / get_right() /
get_corner(direction)            → read the current position of a critical
                      point on `mob`; use for computing derived positions
mob.shift_onto_screen()          → nudges `mob` back within frame bounds if
                      it has drifted off-screen

VGroup / group arrangement (use these instead of manually positioning each
child — manual per-child coordinates are the #1 cause of overlapping or
misaligned generated layouts):
  VGroup(*mobs).arrange(direction=RIGHT, buff=0.25, center=True,
                         aligned_edge=ORIGIN)
                    → lays out children in a row/column with even spacing
  VGroup(*mobs).arrange_in_grid(rows=None, cols=None, buff=0.25,
                         flow_order="rd")
                    → lays out children in a grid; buff can be (row, col)
                      tuple for different horizontal/vertical gaps

Semantic zone pattern: define named regions (TOP_STRIP, MAIN_CANVAS, etc.)
as fractions of frame_x_radius/frame_y_radius, then use `.move_to(zone_point)`
or `.next_to(zone_anchor, ...)` to place content — never hardcode absolute
coordinates that assume a specific frame size.

──────────────────────────────────────────
5. MUTATION API — the verbs used inside .animate and directly
──────────────────────────────────────────
Color / style:
  set_color(color)                → fill AND stroke color in one call
  set_fill(color=None, opacity=None)
  set_stroke(color=None, width=None, opacity=None)
  set_opacity(opacity)            → fill + stroke opacity together
  fade_to(color, alpha)           → partial blend toward a color

Size / shape:
  scale(factor, about_point=None) → uniform scale
  stretch(factor, dim)            → non-uniform scale along one axis (0=x,1=y,2=z)
  stretch_to_fit_width(width) / stretch_to_fit_height(height) / stretch_to_fit_depth(depth)
  flip(axis=UP)                   → mirror across an axis through its center
  rotate(angle, axis=OUT, about_point=None)

Copying / matching:
  copy()                          → deep-ish copy; ALWAYS copy before mutating
                      an object you still need in its original form
  become(other_mobject)           → morphs self's points/style to match
                      another mobject in-place (no new object created)
  match_color(other) / match_style(other) / match_width(other) /
  match_height(other) / match_x(other) / match_y(other)
                      → copy one specific property from another mobject

  [CRITICAL] `.animate` vs explicit Animation classes:
  `.animate` (e.g. `self.play(mob.animate.shift(UP).set_color(RED))`) only
  works for CONTINUOUS PROPERTY interpolation — position, color, scale,
  opacity, rotation. It does NOT work for animations that construct or
  destroy the object's path/appearance from nothing, e.g. Create, Write,
  FadeIn, DrawBorderThenFill, GrowFromCenter — those MUST be called as
  explicit Animation classes: `self.play(Create(mob))`, never
  `self.play(mob.animate.create())` (no such method exists to chain).
  Rule of thumb: if the class name describes HOW something appears/
  disappears, use the explicit class; if it describes a property change
  on an object already on screen, `.animate` is fine.

──────────────────────────────────────────
6. COLOR SYSTEM
──────────────────────────────────────────
Base hues with 5 shade levels each, A (lightest) → E (darkest):
  RED_A..RED_E, BLUE_A..BLUE_E, GREEN_A..GREEN_E, YELLOW_A..YELLOW_E,
  PURPLE_A..PURPLE_E, TEAL_A..TEAL_E, MAROON_A..MAROON_E, GOLD_A..GOLD_E,
  GREY_A..GREY_E (GRAY is an alias for GREY)
Each hue's unsuffixed name (e.g. `RED`, `BLUE`) aliases its `_C` (middle)
shade. Pure/saturated variants also exist: PURE_RED, PURE_GREEN, PURE_BLUE.
Neutrals: WHITE, BLACK, GREY_BROWN.
Hex strings work directly wherever a color is accepted: `color="#FE298D"`.
ManimColor is the underlying color type; color_gradient([c1, c2, ...], n)
returns n interpolated colors; interpolate_color(c1, c2, alpha) blends two.
Use the letter-graded palette for anything that needs a light/dark pairing
(e.g. a filled region in a light shade with a darker-shade stroke) rather
than inventing arbitrary opacity values to fake a tint.

──────────────────────────────────────────
7. MathTex INDEXING — the most common LLM failure mode in Manim code
──────────────────────────────────────────
MathTex(*strings) treats EACH STRING ARGUMENT as one indexable token/
submobject group — NOT each character.
  CORRECT:   MathTex("y", "=", "m", "x", "+", "c")
             — eq[0] is "y", eq[2] is "m", eq[4] is "+", etc.
  WRONG:     MathTex("y=mx+c")
             — this compiles as far fewer submobjects than you'd expect
             from character-counting, because LaTeX groups symbols; indexing
             by assumed character position (e.g. eq[2] expecting "m") will
             grab the wrong glyph or a partial glyph group.
Rule: split MathTex into one string per semantic unit (variable, operator,
number) if that unit will EVER be individually referenced, transformed,
recolored, or targeted by TransformMatchingTex. Do not split what will
never be targeted — over-splitting just adds noise.

get_part_by_tex(tex_string) → returns the submobject matching an exact
                      token string you originally passed in; safer than
                      raw index math when the token count might shift —
                      prefer this over eq[N] whenever a spec is generated
                      by an LLM that may miscount the split.
.submobjects              → iterate over an object's top-level tokens/parts.

TransformMatchingTex(old_eq, new_eq) auto-pairs identical tex substrings
between the two equations and moves them; substrings present in only one
side fade in/out. If you need `x` in the old equation to visually morph
into `x^2` in the new one, they must share matching tex substrings for
TransformMatchingTex to treat them as one continuous piece — otherwise it
will fade one out and fade the other in as unrelated objects, which reads
as a jump-cut rather than a morph.

Custom LaTeX packages/symbols (e.g. \\mathbb, \\therefore, non-default
fonts) require a TexTemplate with the package added to its preamble,
e.g. `template = TexTemplate(); template.add_to_preamble(r"\\usepackage{amssymb}")`
then `config.tex_template = template` — citing a symbol without ensuring
the required package is loaded will fail LaTeX compilation at render time,
not at code-review time, so any prompt describing an equation with
non-standard symbols should also state the required package.

──────────────────────────────────────────
8. SCENE BOILERPLATE CONVENTIONS
──────────────────────────────────────────
class SceneName(Scene):
    def construct(self):
        ...                      # all scene logic lives here

self.add(mob)                    → puts `mob` on screen with NO animation
                      (zero-duration; use for static setup, not narrative beats)
self.play(*animations, run_time=..., rate_func=...)
                      → the primary narrative unit; can take multiple
                      Animation instances for simultaneous playback (or
                      wrap in AnimationGroup/LaggedStart for finer control
                      over timing/stagger)
self.wait(seconds)               → mandatory pause for the viewer to process
                      a beat; ALSO required at the very end of `construct()`
                      if the last action is a `self.play(...)` whose held
                      final frame needs to persist before cutting — without
                      a trailing wait, some pipelines cut the instant the
                      last animation completes.
A single .py file may define multiple Scene subclasses; the render target
is selected by class name at render time (`manim -pql file.py SceneName`),
so each conceptual "shot" in a beat-based pipeline typically maps to one
Scene class rather than one giant multi-beat construct().
""".strip()

# =============================================================================
#  MANIM COMMON GENERATION MISTAKES — PLUGGABLE PROMPT SUB-COMPONENT
#  Target: Manim Community Edition v0.20.x (docs.manim.community)
#  Verified against the live v0.20.1 reference, mobject.py source, the
#  get_graph→plot rename, and the v0.19.0 changelog (PR #3884, #3922,
#  #4115) on 2026-07-01.
# =============================================================================
#
# CHANGELOG
# ----------
# v2 (this revision)
#   - Promoted the module's export from a private, single-use string
#     (`_MANIM_COMMON_MISTAKES`) to a public constant
#     (`MANIM_COMMON_MISTAKES`) so it can be imported and composed into
#     other prompts the same way `MANIM_VOCABULARY` already is. A private
#     alias is kept for backward compatibility.
#   - Re-verified every specific version/rename claim against the live
#     v0.20.1 docs and v0.19.0 changelog:
#       axes.get_graph -> axes.plot                          confirmed
#       axes.get_implicit_curve -> axes.plot_implicit_curve   confirmed
#       axes.get_parametric_curve -> axes.plot_parametric_curve  confirmed
#       ManimColor.from_hex(hex=...) -> hex_str=...   (PR #3884) confirmed
#       Code.styles_list -> Code.get_styles_list()    (v0.19.0)  confirmed
#       Sector(inner_radius=, outer_radius=) removed  (PR #3922) confirmed
#         — AnnularSector still accepts both; Sector now takes radius+angle
#       SurroundingRectangle(a, b) -> SurroundingRectangle([a, b])
#         (PR #3964, sequence-of-mobjects signature change)      confirmed
#     No corrections were needed — all were accurate as written.
#   - Item 1: added that `axes.plot_implicit_curve(...)` returns an
#     `ImplicitFunction` mobject, and that `ImplicitFunction` can also be
#     instantiated directly (without an `Axes` instance) when the curve
#     doesn't need to live inside a coordinate system — this was missing
#     and is a common point of confusion when a spec calls for a bare
#     implicit curve with no visible axes.
#
# Purpose: these are execution-order and state-management bugs, distinct
# from "wrong class name" (covered by the DEPRECATED section of the
# vocabulary module) and "wrong construction call" (covered by the
# construction-patterns module). Most of these come from an LLM's training
# data containing a mix of old 3b1b/manim, early ManimCE, and current
# ManimCE code with no version signal to distinguish them — so the model
# reproduces whichever pattern was statistically more common, which is
# often the OLDER, now-broken one. This module is designed to be imported
# and concatenated alongside the vocabulary and construction-patterns
# blocks in the same system prompt.
# =============================================================================

MANIM_COMMON_MISTAKES = """
════════════════════════════════════════════════════════════════
MANIM COMMON GENERATION MISTAKES — PROMPT SUB-COMPONENT
Target: Manim Community Edition v0.20.x (docs.manim.community)
Verified against the live v0.20.1 reference, mobject.py source, and
the get_graph→plot rename PR (#2187) on 2026-07-01.

Purpose: these are execution-order and state-management bugs, distinct
from "wrong class name" (covered by the DEPRECATED section of the
vocabulary block) and "wrong construction call" (covered by the
CONSTRUCTION PATTERNS block). Most of these come from an LLM's training
data containing a mix of old 3b1b/manim, early ManimCE, and current
ManimCE code with no version signal to distinguish them — so the model
reproduces whichever pattern was statistically more common, which is
often the OLDER, now-broken one.
════════════════════════════════════════════════════════════════

──────────────────────────────────────────
1. TRAINING-DATA CONTAMINATION — old API surface bleeding into new code
──────────────────────────────────────────
The single largest source of broken generated Manim code is citing an
API that existed in an older library version (3b1b/manim or early
ManimCE) which was renamed or removed. Beyond the DEPRECATED CLASSES
list in the vocabulary block, watch for renamed METHODS specifically:

  axes.get_graph(func, ...)        → RENAMED to axes.plot(func, ...)
                                      (PR #2187; get_graph doesn't exist
                                      in v0.20.x). This is extremely
                                      common because it appears in almost
                                      every pre-2022 Manim tutorial.
  axes.get_implicit_curve(...)     → RENAMED to axes.plot_implicit_curve(...)
                                      Returns an ImplicitFunction mobject.
                                      If the scene needs an implicit curve
                                      with NO visible coordinate axes,
                                      instantiate ImplicitFunction(func,
                                      x_range=..., y_range=...) directly
                                      instead of routing through Axes.
  axes.get_parametric_curve(...)   → RENAMED to axes.plot_parametric_curve(...)
  GraphScene / self.setup_axes() / self.coords_to_point()
                                    → GraphScene is a removed legacy scene
                                      class entirely; use a plain Scene
                                      with an explicit Axes() instance and
                                      axes.coords_to_point() instead.
  ManimColor.from_hex(hex=...)     → kwarg RENAMED to hex_str= (v0.19.0)
  Code.styles_list                 → RENAMED to Code.get_styles_list() (v0.19.0)

Rule: if a method or class "feels very standard/canonical" for a task
(gets suggested with high confidence from memory), that's actually a
signal to double check it against the current reference rather than
trust it more — canonical-feeling APIs are exactly the ones most likely
to have been long-lived and therefore renamed at least once.

──────────────────────────────────────────
2. .animate MISUSE — trying to chain a creation animation
──────────────────────────────────────────
  WRONG:  self.play(mob.animate.create())       # no .create() method exists
  WRONG:  self.play(mob.animate.write())        # no .write() method exists
  RIGHT:  self.play(Create(mob))
  RIGHT:  self.play(Write(mob))
.animate wraps property mutations (shift, scale, set_color, rotate,
set_opacity) that Manim can interpolate as continuous state changes.
Creation/removal-style animations construct or dismantle the object's
visible path from nothing and have no continuous "half-created" state
to interpolate toward via .animate — they are Animation subclasses only.

──────────────────────────────────────────
3. self.wait() vs Wait() — parameter name mismatch
──────────────────────────────────────────
  WRONG:  self.wait(run_time=2)      # Scene.wait() takes `duration`, not run_time
  RIGHT:  self.wait(2)               # or self.wait(duration=2)
  RIGHT:  Wait(run_time=2)           # the Animation CLASS does use run_time,
                                      # but only when constructed directly
                                      # (e.g. inside an AnimationGroup)
These are two different call surfaces for conceptually the same pause,
with different parameter names — an LLM that has seen both in training
data commonly cross-wires them.

──────────────────────────────────────────
4. VGroup ONLY accepts VMobjects — mixed-type groups raise TypeError
──────────────────────────────────────────
  WRONG:  VGroup(Circle(), ImageMobject("photo.png"))
                    # ImageMobject is NOT a VMobject → TypeError at runtime
  RIGHT:  Group(Circle(), ImageMobject("photo.png"))
                    # Group accepts any Mobject subtype
Rule: if the group mixes vector shapes/text with ImageMobject, SVGMobject-
as-raster, Surface, or other non-VMobject types, use Group. If every
member is a VMobject (shapes, Text, Tex, MathTex, Line, etc.), VGroup is
correct and gives access to VMobject-only styling methods (set_stroke,
etc.) on the group as a whole.

──────────────────────────────────────────
5. Mutating a reused mobject instance instead of copying it
──────────────────────────────────────────
  WRONG:
    label = Text("Before")
    self.play(FadeIn(label))
    other = label            # SAME object, not a new one
    other.set_text("After")  # mutates `label` too — both names now
                              # point at identical, already-mutated state
  RIGHT:
    label = Text("Before")
    self.play(FadeIn(label))
    other = label.copy()
    self.play(Transform(label, Text("After")))
Any time a "before" and "after" version of the same visual concept are
needed as two independent, animatable states, the second one must be a
`.copy()` (or a fresh instantiation) — reusing the same Python reference
silently corrupts the first state as soon as the second is mutated,
which is invisible until playback because Python won't raise an error.

──────────────────────────────────────────
6. TransformMatchingTex silently fades instead of morphing
──────────────────────────────────────────
TransformMatchingTex(old_eq, new_eq) only treats a piece as "the same
piece moving/morphing" if the exact tex substring appears in BOTH
equations' token lists. If a symbol changes form entirely (e.g. `x`
becoming `x^2`), it will NOT be recognized as related unless a shared
substring exists — Manim will just fade the old token out and fade the
new one in, which looks like a cut, not a morph, even though the code
runs without error. Verify shared substrings deliberately when a smooth
per-symbol morph is the intended visual, rather than assuming
TransformMatchingTex "figures it out" for any semantically-related pair.

──────────────────────────────────────────
7. Wrong kwarg names — plausible-but-incorrect parameter guesses
──────────────────────────────────────────
  WRONG:  Text("Hello", size=48)          → RIGHT: Text("Hello", font_size=48)
  WRONG:  Sector(inner_radius=1, outer_radius=2)
                    → REMOVED in v0.19; Sector now takes radius + angle only.
                      Use AnnularSector(inner_radius=..., outer_radius=...)
                      for a ring-shaped wedge instead.
  WRONG:  SurroundingRectangle(mob_a, mob_b)   # two positional args
  RIGHT:  SurroundingRectangle([mob_a, mob_b]) # one sequence argument
When uncertain of an exact kwarg name for a less-common class, prefer a
construction pattern already verified elsewhere in this prompt (e.g. the
CONSTRUCTION PATTERNS or VOCABULARY blocks) over inventing a
plausible-sounding kwarg — parameter names are not guessable from the
concept the class represents.

──────────────────────────────────────────
8. Missing or default run_time on self.play() for narration-timed scenes
──────────────────────────────────────────
self.play() defaults to run_time=1.0 second if not specified. In a
narration-synced pipeline (TTS-driven beats), every self.play() call
whose visual needs to occupy a specific narrated duration MUST pass an
explicit run_time — otherwise every animation defaults to the same 1s
regardless of how much narrated time the beat actually spans, producing
visuals that finish far before or drag on after the matching audio.

──────────────────────────────────────────
9. Referencing a mobject's position before it has a final position
──────────────────────────────────────────
`.next_to()`, `.align_to()`, and `.get_center()` all read an object's
CURRENT position at call time — not some eventual laid-out position. If
mobject B is positioned `.next_to(A)` before A itself has been placed
via `.to_edge()`/`.arrange()`/`.move_to()`, B will be positioned relative
to A's default (usually ORIGIN-centered) location, not its intended
final one. Establish each mobject's own position fully before using it
as an anchor for the next one — positioning must be sequenced, not
assumed to resolve automatically at render time.
""".strip()

MANIM_VOCABULARY = """
════════════════════════════════════════════════════════════════
MANIM PRIMITIVE VOCABULARY — REFERENCE CATALOG
Target: Manim Community Edition v0.20.x (docs.manim.community)
Verified against the live v0.20.1 Reference Manual and Changelog
(reference.html module index + rate_functions.html + 0.19.0 changelog)
on 2026-07-01. Corrections from the prior draft are marked [FIXED].
════════════════════════════════════════════════════════════════

Every primitive below can be cited in <MANIM_PRIMITIVE_SELECTION>.
For each entry: what it is and the visual use case it best serves.

════════════════════════════════════════════════════════════════
DEPRECATED / REMOVED — NEVER USE
These classes do not exist in current ManimCE. Some appear plausible because
they existed in very old Manim versions or in 3b1b/manim; citing any of them
is a pipeline-breaking error. Use the listed replacement instead.
════════════════════════════════════════════════════════════════
  FadeInFrom, FadeInFromPoint, FadeInFromLarge   → use FadeIn(mobject, shift=...)
  FadeOutAndShift, FadeOutToPoint                → use FadeOut(mobject, shift=...)
  VFadeIn, VFadeOut, VFadeInThenOut              → use FadeIn / FadeOut
  CircleIndicate                                  → use Indicate or Circumscribe
  ShowCreationThenDestruction                     → use Succession(
                                                       Create(obj, run_time=...),
                                                       Wait(...),
                                                       Uncreate(obj, run_time=...))
  ShowCreationThenDestructionAround               → use Circumscribe(obj)
  ShowCreationThenFadeAround                      → use Circumscribe(obj) or
                                                       ShowPassingFlash(SurroundingRectangle(obj))
  ShowPassingFlashAround                          → use ShowPassingFlash(SurroundingRectangle(obj))
  AnimationOnSurroundingRectangle                 → use SurroundingRectangle(obj) directly
                                                       with Create / FadeIn / ShowPassingFlash
  WiggleOutThenIn                                 → use Wiggle(obj)
  TurnInsideOut                                   → no direct replacement; use Transform
  OpenGLTexMobject, OpenGLTextMobject             → use MathTex / Tex (renderer-agnostic)
  VMobjectFromSVGPathstring                       → use SVGPathMobject
  ShowPassingFlashWithThinningStroke               → misnamed; correct class is
                                                       ShowPassingFlashWithThinningStrokeWidth
  Mobject.rotate_in_place / .scale_in_place /
  .scale_about_point                              → deprecated since v0.11; use .rotate(),
                                                       .scale(), or .move_to()/.shift() directly
  ShowCreation                                    → renamed long ago; use Create
  TexMobject, TextMobject                         → removed since v0.6; use Tex / MathTex or Text
  GraphScene, SampleSpaceScene, ReconfigurableScene → legacy scenes; use Axes-based
                                                       Scene construction, or SampleSpace directly

  [FIXED — this was WRONG in the prior draft]
  "No bounce/overshoot rate_func exists" — FALSE. ManimCE ships
  ease_in_bounce / ease_out_bounce / ease_in_out_bounce natively.
  Do not compose a custom bounce curve; just cite the built-in one
  (see RATE FUNCTIONS section below).

  [FIXED] "LineGraph" is NOT a Mobject class. There is no standalone
  LineGraph type. A connected line plot is produced via the method
  CoordinateSystem.get_line_graph() on an Axes/NumberPlane instance
  (added in v0.19.0), not by instantiating a class named LineGraph.

──────────────────────────────────────────
SCENE CONTAINERS
──────────────────────────────────────────
Scene               → base scene; fixed camera; use for most educational scenes
MovingCameraScene   → use whenever the camera pans, zooms, or tracks an object
ZoomedScene         → built-in zoom window + inset; for focusing on a sub-region
                      while keeping the full scene visible
ThreeDScene         → 3D-capable scene with depth; supports set_camera_orientation,
                      move_camera, begin_ambient_camera_rotation
SpecialThreeDScene  → ThreeDScene subclass with pre-configured axes helpers
InteractiveScene    → interactive/browser-rendered elements; live demos
VectorScene         → 2D scene with vector-plane helper methods (add_plane, add_vector)
LinearTransformationScene → VectorScene subclass specialized for showing linear
                      transformations applied to a grid/basis vectors

──────────────────────────────────────────
GEOMETRY — shapes that form the visual substrate
──────────────────────────────────────────
Dot                 → single data point, graph node, position marker, scatter element
AnnotationDot       → larger, styled Dot meant to be paired with a text label
LabeledDot           → Dot with an embedded text/number label inside it; numbered markers
Point               → invisible zero-radius anchor; reference position only
Line                → connect two concepts, axis segment, regression line, connector
DashedLine          → error bar, uncertainty range, guide line, projection, boundary hint
Elbow               → right-angle connector line (two perpendicular segments); wiring diagrams
Arrow               → direction of causality, annotation pointer, gradient direction
DoubleArrow         → two-way relationship, bijection, bidirectional mapping
CurvedArrow         → curved one-way relationship; cyclic causality, feedback loop
CurvedDoubleArrow   → curved two-way relationship; mutual feedback
LabeledArrow         → Arrow with a text label anchored along its length
LabeledLine          → Line with a text label anchored along its length
Vector              → physics force arrow, eigenvector, vector field element
Circle              → set boundary, focus ring, probability node, cycle marker
Ellipse             → stretched set boundary, orbital path, covariance region
Arc                 → curved path between two points, partial circle, angle sweep
ArcBetweenPoints    → arc constructed directly from two endpoint coordinates
TangentialArc       → arc tangent to a given line/curve at a point; smooth connectors
Sector              → pie chart slice, angular probability region, wedge highlight
                      [FIXED, v0.19.0] Constructor now takes radius + angle only;
                      inner_radius/outer_radius kwargs were REMOVED from Sector.
                      Use AnnularSector (below) if you need a ring-shaped wedge —
                      it still accepts inner_radius and outer_radius.
AnnularSector       → ring-shaped wedge (donut slice); layered pie/radial charts
Annulus             → ring shape; concentric layers, donut chart, focus zone
Square              → bounding box, FSM state node, matrix cell highlight, grid element
Rectangle           → panel background, table cell, bar in a bar chart, code block frame
RoundedRectangle    → soft panel, card UI, callout box, tooltip
Polygon             → arbitrary convex shape, crystal cell, custom territory
Polygram            → multi-part polygon (several disjoint point-loops in one mobject)
RegularPolygram     → star-polygon / regular polygram (e.g. pentagram); decorative motifs
Cutout               → polygon with holes cut out of it; stencil shapes, cutaway diagrams
ConvexHull           → 2D convex hull computed from a set of points; cluster boundary
Triangle             → delta symbol, derivative indicator, 3-way relationship, direction arrow
RegularPolygon      → symmetric n-sided shape (hexagon for honeycomb, octagon for stop, etc.)
Star                → emphasis decoration, rating icon, landmark marker
Cross               → error symbol, deletion mark, XOR gate, cancellation
Angle               → angle marker between two lines; proof geometry, rotation amount
RightAngle           → dedicated right-angle (square-corner) marker; proof geometry

──────────────────────────────────────────
CURVES — mathematical and freeform paths
──────────────────────────────────────────
Bezier              → smooth freeform curve between control points; custom connectors
CubicBezier         → smooth S-curve; elegant connector between non-adjacent elements
ParametricFunction  → any curve defined by x(t), y(t); Lissajous, spirals, cycloids
FunctionGraph       → plot a single-variable function y=f(x) on an Axes object
ImplicitFunction    → curve defined by F(x,y)=0; level sets, contours, conics
                      (current ManimCE name is ImplicitFunction, not ImplicitCurve)

──────────────────────────────────────────
COORDINATE SYSTEMS — reference frames for data and math
──────────────────────────────────────────
NumberLine          → single-axis number line; distributions, ranges, 1D comparisons
UnitInterval        → NumberLine preconfigured to the [0, 1] range; probability bars
Axes                → 2D Cartesian frame; function plots, data visualizations
CoordinateSystem    → abstract base shared by Axes/NumberPlane/PolarPlane/ComplexPlane;
                      cite when describing shared behavior (coords_to_point, plot, etc.)
ThreeDAxes          → 3D x-y-z frame; 3D surfaces, vector fields, transformations
NumberPlane         → full 2D grid with tick labels; linear algebra, complex number plane
PolarPlane          → r-θ frame; polar functions, circular/angular data
ComplexPlane        → Argand diagram; complex arithmetic, Fourier analysis
LinearBase / LogBase → scale objects passed to Axes(x_axis_config={"scaling": ...});
                      linear vs. logarithmic axis scaling for skewed data ranges

──────────────────────────────────────────
TEXT AND FORMULAS — all on-screen language
──────────────────────────────────────────
Text                → plain English labels, annotations, captions, titles
MarkupText          → styled text with inline bold/italic/color spans (HTML-like)
Paragraph           → multi-line body text block; longer explanations
BulletedList        → step list that can reveal one line at a time
Title               → large heading; scene title or major section header
Tex                 → LaTeX with prose and inline math; mixed text+formula
MathTex             → pure LaTeX math; ALWAYS split into tokens for submobject animation
                      e.g., MathTex("y","=","m","x","+","c") — NOT MathTex("y=mx+c")
DecimalNumber       → live decimal value that updates in sync with a ValueTracker
Integer             → live integer value that updates in sync with a ValueTracker
Variable            → named value pair "x = 3.5" that updates live; slider labels
Label                → small pill/badge-style text marker, typically attached to a
                      geometric mobject (paired with LabeledLine/LabeledArrow/LabeledPolygram)
LabeledPolygram      → Polygram with an attached Label; annotated custom shape/territory

──────────────────────────────────────────
DATA DISPLAY — structured information
──────────────────────────────────────────
Table               → grid of text cells; comparison tables, data grids, lookup tables
MathTable           → grid of LaTeX math cells; truth tables, operation tables
DecimalTable        → grid of live decimal-number cells
IntegerTable        → grid of live integer cells
MobjectTable        → grid whose cells are arbitrary Manim objects (icons, mini-plots)
Matrix              → mathematical matrix with brackets; linear algebra operations
DecimalMatrix       → matrix with live decimal values that update
IntegerMatrix       → matrix with live integer values
MobjectMatrix       → matrix whose cells are arbitrary Manim objects
BarChart            → vertical or horizontal bar chart; categorical comparisons
SampleSpace          → rectangle subdivided into weighted regions; probability tree
                      / conditional-probability diagrams
  [FIXED] get_line_graph() — NOT a class. This is a *method* on
  CoordinateSystem/Axes: axes.get_line_graph(x_values, y_values, ...).
  Use it for a connected line plot / trend-over-time visualization;
  do not cite a bare "LineGraph" class, it does not exist.

──────────────────────────────────────────
MEDIA — imported external assets
──────────────────────────────────────────
ImageMobject        → raster image (PNG, JPG) overlaid on scene; photos, diagrams
ImageMobjectFromCamera → live feed of a secondary camera's rendered output as an image
SVGMobject          → vector graphic; complex logos, icons, imported diagrams
VMobjectFromSVGPath  → a single path parsed out of SVG path-data into a VMobject
Code                → syntax-highlighted code block; algorithm + code side-by-side
                      (v0.19.0: use Code.get_styles_list() for available highlight styles,
                      not the old .styles_list attribute)

──────────────────────────────────────────
GRAPH STRUCTURES — network topology
──────────────────────────────────────────
Graph               → undirected network (nodes + edges); social graphs, trees, BFS/DFS
DiGraph             → directed network (nodes + arrows); DAGs, state machines, pipelines
GenericGraph         → shared base class of Graph/DiGraph; cite for generic graph behavior
LayoutFunction        → pluggable node-positioning strategy (spring, circular, tree, etc.)
                      passed to Graph(..., layout=...)

──────────────────────────────────────────
3D OBJECTS — require ThreeDScene
──────────────────────────────────────────
Cube                → 3D box; convolution filter, tensor block, voxel
Sphere              → 3D ball; data point in 3D space, neuron body, globe
Dot3D                → 3D point marker; scatter point in a 3D plot
Cylinder            → 3D tube; column chart bar, pipe, rotation axis
Cone                → 3D cone; gradient descent funnel, focus beam
Prism               → 3D generalized prism; crystal structures, extruded shapes
Line3D               → 3D line segment; edges of a 3D graph, axis segment
Arrow3D              → 3D arrow; force/vector in 3D space, 3D annotation pointer
Surface             → parametric 3D surface; loss landscape, probability surface
Torus               → donut shape; topology examples, loop structures
ThreeDVMobject        → base VMobject variant with 3D-aware normals/shading
Polyhedron, Tetrahedron, Octahedron,
Icosahedron, Dodecahedron          → platonic-solid primitives; crystallography,
                      molecular geometry, polyhedral graph illustrations
ConvexHull3D          → 3D convex hull computed from a point cloud; enclosing volume

──────────────────────────────────────────
GROUPS — collection wrappers
──────────────────────────────────────────
VGroup              → ordered group of VMobjects; style, animate, or remove as a unit
VDict                 → dict-like group of VMobjects, addressable by key; named UI panels
Group               → general group for mixed Mobject types
PGroup                → group specifically for point-cloud (PMobject) elements
PMobject / Mobject1D / Mobject2D → low-level point-cloud primitives (raw point sets);
                      rarely cited directly, used under PointCloudDot
PointCloudDot          → scatter of many small points as a single Mobject; particle
                      systems, dense scatter plots (cheaper than many individual Dots)
CurvesAsSubmobjects    → decomposes a VMobject's path into per-segment submobjects;
                      needed before applying ShowPassingFlash-style per-segment effects
DashedVMobject         → converts any VMobject's path into a dashed version of itself

──────────────────────────────────────────
UTILITY AND DECORATORS — annotation helpers
──────────────────────────────────────────
Brace               → curly brace spanning an object or range; label a measurement
ArcBrace              → curved brace variant, following an arc-shaped span
BraceBetweenPoints     → brace constructed directly from two endpoint coordinates
BraceLabel              → brace with inline text label; annotate a span or group
BraceText               → shorthand BraceLabel variant that takes a plain string
SurroundingRectangle → highlight box around any object; draw attention to a region
                      [FIXED, v0.19.0] Now accepts a *sequence* of Mobjects (not
                      just one) — SurroundingRectangle([obj_a, obj_b]) draws a
                      single box enclosing all of them.
BackgroundRectangle → opaque fill behind text; ensure legibility over complex visuals
Underline           → line beneath text; stress a term or definition

──────────────────────────────────────────
BOOLEAN OPS — shape algebra
──────────────────────────────────────────
Union               → merge two shapes into one; Venn diagram union, merged region
Intersection        → keep only the overlapping part; Venn intersection, common area
Difference          → cut one shape out of another; cutaway diagram, excluded zone
Exclusion           → symmetric difference (XOR); non-overlapping combined region

════════════════════════════════════════════════════════════════
ANIMATION METHODS
════════════════════════════════════════════════════════════════

──────────────────────────────────────────
BASE / SEQUENCING PRIMITIVES
──────────────────────────────────────────
Add                 → adds a mobject to the scene with zero-duration "animation";
                      use when you need it in an AnimationGroup/Succession slot
                      but want no visible transition
Wait(n)             → pause execution for n seconds; mandatory for breath and sync;
                      every Wait must be justified per RULE 9 (state what the
                      viewer is meant to process during it, not just its length)

──────────────────────────────────────────
CREATION — how objects first appear on screen
──────────────────────────────────────────
Create              → draws the border/path of any VMobject; best for axes, arrows,
                      geometric shapes — the path itself is the visual reveal
Uncreate            → reverse-draws a geometric path (mirror of Create); "undo" a
                      shape drawn with Create()
DrawBorderThenFill  → draws outline first, then floods fill inside; filled shapes
                      where the boundary reveal is meaningful
ShowPartial         → base class for revealing a fractional portion of a path;
                      use its subclasses (Create/Uncreate) directly in most cases
ShowIncreasingSubsets → reveals a VGroup's submobjects one at a time, additively,
                      with no easing between them; discrete step-by-step reveal
                      for lists, sequences, or table rows
ShowSubmobjectsOneByOne → shows exactly one submobject at a time, replacing the
                      previous one; use for cycling through alternatives at a
                      fixed screen position
SpiralIn            → sub-Mobjects fly inward on spiral trajectories with a
                      fade-in during the initial fraction of the motion (default
                      fade_in_fraction=0.3); playful, orbital, multi-object entry —
                      use for a VGroup of several small shapes, not a single object
Write               → stroke-by-stroke text rendering; matches the cadence of spoken
                      narration; use for ALL Text, Tex, and MathTex objects
Unwrite             → reverse-strokes text off screen (mirror of Write)
AddTextLetterByLetter → types text in one character at a time with a fixed
                      per-character interval; terminal/typewriter reveal
AddTextWordByWord   → reveals text one whole word at a time; slower narrative pacing
                      than AddTextLetterByLetter
TypeWithCursor      → AddTextLetterByLetter with a visible blinking cursor glyph
                      trailing the reveal; code-typing or terminal simulation
RemoveTextLetterByLetter → mirror of AddTextLetterByLetter; deletes text one
                      character at a time from the end
UntypeWithCursor    → mirror of TypeWithCursor; deletes with a trailing cursor
GrowFromCenter      → scales object up from its center; "pop in" for new key concepts
GrowArrow           → arrow extends from tail tip to arrowhead; directional reveal,
                      shows directionality as it builds
GrowFromPoint       → scales up from a specified anchor point; origin-relative growth
GrowFromEdge        → grows from one specified edge; directional panel reveal
SpinInFromNothing   → object spins and scales up simultaneously from zero size;
                      energetic, attention-grabbing entrance

──────────────────────────────────────────
FADE — opacity-based appear/disappear
──────────────────────────────────────────
FadeIn              → object materializes from transparent; supports a `shift=`
                      kwarg for a directional fade-in (replaces the old
                      FadeInFrom family); use when there is no natural path or
                      stroke to animate (images, groups, panels)
FadeOut             → object dematerializes to transparent; supports `shift=` for
                      directional fade-out (replaces FadeOutAndShift); the
                      universal removal method; use for cleanup and transitions
FadeTransform       → cross-fade morph from one object to another; soft conceptual swap
FadeTransformPieces → cross-fade morph piece by piece; segmented or complex objects
FadeToColor         → shift the fill color through a fade; state or status transition

──────────────────────────────────────────
TRANSFORMS — shape morphing between states
──────────────────────────────────────────
Transform                 → morph one object into another; general-purpose shape change
ReplacementTransform      → morph and replace (source disappears); clean swap of objects
TransformFromCopy         → morph a copy while original stays; show a derived form
TransformAnimations        → cross-fade/morph between two *animations'* end states,
                      not just two static mobjects; rarely needed, legacy-style use
MoveToTarget                → animates a mobject to a previously-set `.target` state
                      (set via mobject.generate_target() then mutate .target)
Restore                     → animates a mobject back to a previously saved state
                      (set via mobject.save_state()); "undo" to a checkpoint
ScaleInPlace                → scales a mobject about its own center as an animation
ShrinkToCenter               → scales a mobject down to zero size at its center; removal
Swap                        → swaps the positions of exactly two mobjects
ClockwiseTransform         → morph with a clockwise rotational path
CounterclockwiseTransform  → morph with a counter-clockwise rotational path
TransformMatchingShapes    → auto-matches similar sub-parts between two objects;
                            complex shape morphs with natural piece-to-piece motion
TransformMatchingTex       → auto-matches LaTeX tokens between two equations;
                            equation rearrangement, algebraic manipulation
CyclicReplace              → cyclically swaps the positions of a list of mobjects;
                            round-robin reassignment, rotating a set of labels
ApplyMethod                → call any Manim method on an object as an animation step
ApplyFunction               → apply an arbitrary Python function to transform all points
ApplyPointwiseFunction       → apply a function to every point of the mobject
                            independently; localized, non-uniform warping
ApplyPointwiseFunctionToCenter → apply a function to the mobject's center point only,
                            then move the whole mobject there; simpler repositioning
                            via a function rather than a fixed target
ApplyMatrix                → apply a 2D or 3D matrix transformation to object's points;
                            linear algebra demos (shear, rotation, scaling matrices)
ApplyComplexFunction        → warp the entire plane by a complex function; complex analysis

──────────────────────────────────────────
MOTION — path and function-based movement
──────────────────────────────────────────
MoveAlongPath       → object travels along any VMobject path; trace a curve,
                      orbit an object, follow a data trajectory
Homotopy            → continuously deform a shape via a point-mapping function;
                      abstract topological transformations
ComplexHomotopy     → homotopy applied in the complex plane
SmoothedVectorizedHomotopy → homotopy variant with smoothed intermediate curvature;
                      gentler deformation than raw Homotopy for VMobjects
PhaseFlow           → simulate a vector field flow over time;
                      differential equations, particle systems

──────────────────────────────────────────
ROTATION
──────────────────────────────────────────
Rotate              → one-shot rotation by a fixed angle; gear turn, dial, compass
                      Use for: a single deliberate rotation event
Rotating            → continuous rotation animation played over a fixed run_time
                      (NOT an updater — it is a standard Animation subclass);
                      use for a spinning object whose spin is itself the timed event

──────────────────────────────────────────
INDICATION — attention and emphasis
──────────────────────────────────────────
Indicate                                → subtle pulse-scale + color flash on an
                                          object; gentle "look here" without
                                          disrupting the scene's flow
Circumscribe                            → draws a temporary circle or rectangle
                                          around a concept then removes it; use
                                          when defining or bounding a named element
                                          (replaces the removed ShowCreationThenFadeAround)
Flash                                   → radiating burst of lines from a point or
                                          object; use for "aha" moments, confirmed
                                          answers, revelations
FocusOn                                 → camera-style spotlight ring contracting
                                          onto a point; pinpoint viewer attention on
                                          a specific coordinate or small object
Wiggle                                  → lateral wobble animation; "watch out,"
                                          error flag, uncertainty, or playful callback
ApplyWave                               → ripple wave along an object's path;
                                          signal propagation, sequence flow, data streams
Blink                                   → rapid opacity toggle on/off a fixed number
                                          of times; alert, cursor blink, warning light
ShowPassingFlash                        → glowing highlight sweeps along a path;
                                          trace a route, highlight a data flow or pipeline
ShowPassingFlashWithThinningStrokeWidth → sweep along a path whose stroke width
                                          thins progressively across n_segments
                                          copies; elegant trace, signal that visibly
                                          dissipates as it travels (this is the
                                          correct current class name)

──────────────────────────────────────────
SPECIALIZED
──────────────────────────────────────────
Broadcast           → concentric shapes (default: circles) expand outward from a
                      point and fade, like a radar ping or sonar pulse;
                      signal broadcast, notification, ripple-outward emphasis
ChangeSpeed         → wraps an already-defined animation and speeds it up or
                      slows it down over its own duration (a "speed ramp");
                      use for time-lapse or slow-motion emphasis mid-clip

──────────────────────────────────────────
CHANGING / TRACKING (persist across the scene)
──────────────────────────────────────────
AnimatedBoundary     → animated shimmering outline attached to a mobject, updated
                      every frame; "actively selected" or "processing" indicator
TracedPath           → draws a growing trail behind a moving mobject; comet tail,
                      trajectory history, path-drawing visualizations

════════════════════════════════════════════════════════════════
COMPOSITION AND TIMING
════════════════════════════════════════════════════════════════

AnimationGroup      → run multiple animations simultaneously (true parallel playback)
Succession          → run animations strictly one after another (zero overlap)
LaggedStart         → staggered start: each animation begins lag_ratio × run_time
                      after the previous one started; creates cascade / wave effects
LaggedStartMap      → apply one animation type to a list of objects with stagger;
                      shorthand for LaggedStart over a collection

run_time            → total duration of a self.play() call in seconds
lag_ratio           → stagger fraction (0.0 = fully parallel, 1.0 = fully sequential)
rate_func           → easing curve controlling acceleration over the animation

──────────────────────────────────────────
RATE FUNCTIONS — easing and motion feel
[FIXED] This is the FULL verified function list from manim.utils.rate_functions
(v0.20.1). Cite the exact function name — "ease_in" / "ease_out" / "ease_in_out"
alone are NOT valid names; you must pick a shape suffix (sine/cubic/quad/etc).
──────────────────────────────────────────
linear              → constant speed; mechanical, robotic, clock-like feel
smooth(t, inflection=10.0)  → ease in + ease out sigmoid; default for most
                      animations; feels natural
smoothstep          → 1st-order polynomial smoothstep (speed is zero at endpoints)
smootherstep        → 2nd-order smoothstep (speed & acceleration zero at endpoints)
smoothererstep      → 3rd-order smoothstep (speed, accel & jerk zero at endpoints)
double_smooth       → two smooth eases in sequence at half duration each; two-stage settle
rush_into(t, inflection=10.0) → starts fast, slows at end; object "arrives" and settles
rush_from(t, inflection=10.0) → starts slow, speeds up; object "launches" and accelerates away
slow_into           → decelerating variant biased toward a slow arrival
there_and_back(t, inflection=10.0) → goes to a state and returns to start; ping-pong, hover, preview
there_and_back_with_pause(t, pause_ratio=1/3) → there-and-back with a held pause
                      at the peak; emphasize-then-return with a beat of dwell time
wiggle(t, wiggles=2) → oscillates around the target before settling; nervousness, uncertainty
lingering           → holds near the end value longer than smooth before finishing;
                      emphasizes a final resting state
exponential_decay(t, half_life=0.1) → rapid initial change that decays quickly to
                      near-zero; snap-settle
running_start(t, pull_factor=-0.5) → dips backward slightly before launching forward;
                      anticipation before a big move (wind-up effect)
not_quite_there(func=smooth, proportion=0.7) → wraps another rate_func so the
                      animation stops short of full completion; "almost but not quite"
squish_rate_func(func, a=0.4, b=0.6) → compresses another rate_func into a sub-window
                      [a, b] of the total duration, holding still outside it;
                      use to delay or shorten *when* a nested effect plays
unit_interval / zero → utility wrappers used internally when composing custom rate funcs

  Standard shaped families — each exists as _in, _out, and _in_out variants,
  e.g. ease_in_sine, ease_out_sine, ease_in_out_sine:
    sine    → ease_in_sine / ease_out_sine / ease_in_out_sine
    quad    → ease_in_quad / ease_out_quad / ease_in_out_quad
    cubic   → ease_in_cubic / ease_out_cubic / ease_in_out_cubic
    quart   → ease_in_quart / ease_out_quart / ease_in_out_quart
    quint   → ease_in_quint / ease_out_quint / ease_in_out_quint
    expo    → ease_in_expo / ease_out_expo / ease_in_out_expo
    circ    → ease_in_circ / ease_out_circ / ease_in_out_circ
    back    → ease_in_back / ease_out_back / ease_in_out_back
              (slight overshoot-then-settle past the target before easing in/out)
    elastic → ease_in_elastic / ease_out_elastic / ease_in_out_elastic
              (springy oscillating overshoot; "boing" feel)
    bounce  → ease_in_bounce / ease_out_bounce / ease_in_out_bounce
              [FIXED] THIS is the correct "bounce" curve — it exists natively.
              Use ease_out_bounce for an object that drops and bounces to rest;
              do NOT compose a custom rate_func for this, and do not claim
              ManimCE lacks a bounce easing.

  Note: the standard shaped families above (sine/quad/.../bounce) are accessed
  via `rate_functions.ease_in_sine` etc. — they are not top-level exports of
  `manim`, unlike `smooth`, `linear`, `there_and_back`, `wiggle`, and the other
  non-standard functions listed above, which ARE exported directly.

════════════════════════════════════════════════════════════════
CAMERA
════════════════════════════════════════════════════════════════
Pan (MovingCameraScene)   → self.camera.frame.animate.move_to(...); translate
                            camera frame horizontally or vertically; follow
                            action across the scene
Zoom (MovingCameraScene)  → self.camera.frame.animate.scale(...); scale camera
                            frame in (magnify) or out (reveal context)
move_camera (ThreeDScene) → move camera to a new 3D position / orientation
begin_ambient_camera_rotation (ThreeDScene) → continuous slow orbit around a
                            3D object; gives a sense of 3D depth passively
stop_ambient_camera_rotation (ThreeDScene) → halts an active ambient rotation
set_camera_orientation (ThreeDScene) → jump camera to a specific phi/theta/
                            gamma/zoom; setup shot or dramatic perspective shift
activate_zooming (ZoomedScene) → activates the picture-in-picture zoom inset
                            defined by self.zoomed_camera

════════════════════════════════════════════════════════════════
REACTIVE ELEMENTS — live-updating objects
════════════════════════════════════════════════════════════════
ValueTracker            → holds a scalar that can be animated; use to drive
                          DecimalNumber, live positions, or graph parameters
ComplexValueTracker     → holds a complex number; drives complex plane animations
ChangingDecimal          → animation that continuously updates a DecimalNumber
                          mobject via a number-generating function over the
                          animation's run_time
ChangeDecimalToValue     → animation that interpolates a DecimalNumber's
                          displayed value from its current value to a target
                          value over run_time
add_updater              → attach a function that re-evaluates every rendered frame;
                          use for objects that must track another object's state
remove_updater            → detach a previously added updater function
always_redraw            → shorthand updater that reconstructs the object every frame;
                          use for labels or lines that must follow a moving object
UpdateFromFunc            → animation-flavored updater; calls func(mobject) every
                          frame for the duration of a self.play() call
UpdateFromAlphaFunc       → like UpdateFromFunc but also receives the animation's
                          progress alpha (0→1); drive a custom eased effect
MaintainPositionRelativeTo → animation that keeps a mobject's offset fixed relative
                          to another mobject while the other one moves

════════════════════════════════════════════════════════════════
LAYERS AND DEPTH
════════════════════════════════════════════════════════════════
z_index         → integer stacking order; higher value renders in front
set_z_index()   → explicit call to assign the stacking order on a mobject

════════════════════════════════════════════════════════════════
HIGH-LEVEL VISUAL PATTERNS
(Conceptual templates — not Manim classes. Cite in MANIM_PRIMITIVE_SELECTION
to declare the structural intent of the scene.)
════════════════════════════════════════════════════════════════
Flowchart                   → boxes + arrows showing a process or decision flow
Timeline                    → horizontal or vertical sequence of dated/ordered events
NeuralNetwork                → layered nodes + weighted edges; forward pass, backprop
DecisionTree                 → branching tree of conditions and outcomes
FiniteStateMachine            → states + transition arrows; use DiGraph + labeled Arrows
SortingVisualization          → array bar elements moving into sorted order; comparisons
GraphTraversal                 → BFS/DFS animation with node coloring + edge highlighting
AlgorithmVisualization         → step-by-step code panel + evolving visual state panel
PhysicsSimulation               → particles, forces, trajectories, energy diagrams
MathematicalProof                → equation chain with step justification labels
CalculusVisualization             → integrals as shaded regions, derivatives as tangent lines
DataStructureVisualization        → linked list, stack, queue, heap, tree as visual objects
CircuitDiagram                     → logic gates, wires, voltage/current labels
Infographic                         → mixed text + icons + mini-charts in one composition

════════════════════════════════════════════════════════════════
SELECTED v0.19.0+ API NOTES (not vocabulary, but affects citations above)
════════════════════════════════════════════════════════════════
- ManimColor.from_hex(hex=...) is now ManimColor.from_hex(hex_str=...)
- Scene.next_section(type=...) is now Scene.next_section(section_type=...)
- Sector no longer accepts inner_radius/outer_radius (see GEOMETRY note above)
- SurroundingRectangle accepts a list of Mobjects, not just a single one
- Code.styles_list attribute replaced by Code.get_styles_list() classmethod
- ffmpeg is no longer a required external dependency (pyav is used internally);
  irrelevant to scene-vocabulary citation but worth knowing for the rendering
  pipeline / environment setup side of the project
""".strip()
