# Task: Scene Execution Plan for __SCENE_ID__

Write the complete Scene Execution Plan for scene **__SCENE_ID__**, lasting **__TARGET_DURATION__ s**.

Write the sections below into the `execution_plan` text of `scenes/__SCENE_ID__/plan.json`, **in this order**, each wrapped in its exact XML tag (for example `<SCENE_OVERVIEW> ... </SCENE_OVERVIEW>`). A missing section fails `text-2-shorts validate . plan`. The text holds only the plan: no preamble, no closing remarks. Then derive the plan.json fields from it (references/scene-visual-planning.md).

How the plan is built:
- The scene is split into **clips** of 4-20 s of narration each (hard maximum 30 s; 2-6 clips, at most 8; rule D0). Each clip becomes one pipeline clip with its own code, audio and checks.
- Each clip is a **time-ordered list of atomic events** (D15). Each event records one change, how it happens, where it happens, what it looks like, and the words being spoken.
- Read in order, the events form a second-by-second log of the whole scene.

---

## <SCENE_OVERVIEW>

```text
Scene ID     : __SCENE_ID__
Title        : [scene title]
Duration     : __TARGET_DURATION__s
Scene Type   : Scene | MovingCameraScene | ZoomedScene | ThreeDScene
               (must match rule V4: camera moves need MovingCameraScene,
               any 3D object needs ThreeDScene)
Clip Count   : [number of clips]
Key Ideas    : [numbered list, one sentence each: what the viewer should
                understand by the end of this scene, in teaching order]
Visual Arc   : [4-6 sentences, in order:
                1. the empty canvas at t=0
                2. the major visual beats, in sequence
                3. the main reveal or animation event
                4. what the final frame shows
                Describe what the viewer sees, not what the math means.]
Screen Start : Empty canvas.
Screen End   : [one sentence: everything visible in the last frame]
Clip Map     : [clip -> key idea -> talking point(s), e.g.
                Clip 1 -> idea 1 -> point 1]
```

## <INPUTS_USED>

```text
Template     : [the TPL roles this scene uses; background: the
               harness draws the template's backdrop (rule C8)]
Narration    : given without timestamps; phrase timings estimated at
               the script's speaking rate
Assets       : [image or SVG files used, or "none"]
Packages     : [non-default LaTeX packages needed (rule T6), or "none"]
```

## <LAYOUT_PLAN>

Which zone holds what, and when. One line per zone the scene uses.

```text
ZONE        | holds                          | from -> to
TOP_STRIP   | scene_title                    | Clip 1 -> end
MAIN_CANVAS | loss_axes, loss_curve, ball    | Clip 2 -> end
SIDE_PANEL  | update_rule (MathTex)          | Clip 4 -> end
BOTTOM_BAR  | (unused)                       | -
```

Two objects may share a zone only if the plan says how they are arranged within it (for example "update_rule sits directly below step_label").

## <CONTINUITY>

`None: this scene recalls nothing earlier.` or one line per recall from PREVIOUS_SCENES (D19):

```text
Recalled: [concept or visual] from [scene id]
Rebuilt as: [VAR_NAME], same look, color role and zone as before
Spoken cue: "[words in the narration that point back to it]"
```

## <MANIM_PRIMITIVE_SELECTION>

List every Manim name this scene uses, grouped by the category of `manim-vocabulary.md` it comes from. For each, state its use **in this scene**. Include only categories the scene uses.

```text
Format:  Name  ->  use in this scene

[SCENE CLASS]          (vocabulary PART 4)
[GEOMETRY]             (PART 5)
[GRAPHING]             (PART 6)
[TEXT AND MATH]        (PART 7)
[DATA AND GRAPHS]      (PART 8)
[MEDIA, 3D, GROUPS]    (PART 9)
[ANIMATIONS]           (PART 10)
[COMPOSITION / RATE]   (PART 11)
[CAMERA / UPDATERS]    (PART 12)
[VISUAL PATTERN]       (PART 13: name the pattern, then its building blocks)
```

## <OBJECT_REGISTRY>

One row per object, persistent or brief. The code agent declares one Python variable per row.

```text
VAR_NAME | CLASS | LOOK | ROLE | ENTERS | EXITS

VAR_NAME  snake_case Python name
CLASS     Manim class; VGroup[ClassName x N] for collections
LOOK      full appearance (D18): shape, stroke (role, token), fill (role,
          opacity), size tokens, label text and style. Never positions.
ROLE      one sentence: what it is for
ENTERS    event id and time, e.g. [2.03] t=7.0s
EXITS     event id and time, or "end"
```

Rules for rows:
- Collections of 12 or fewer instances: one row per instance (D12).
- Larger collections: one VGroup row plus a note listing each wave.
- MathTex rows show the planned split, only for terms targeted later (rule T3: separate strings or {{ }}, never substrings_to_isolate for indexing).
- Every object a clip takes over from the clip before needs a LOOK complete enough to rebuild it alone (D1, rule P4).

```text
Correct:
loss_curve | ParametricFunction via axes.plot | U-shaped curve; THICK
           stroke TPL.accent; no fill | the loss for each weight |
           [2.03] t=7.0s | end
Wrong:     color=BLUE        (Manim constant; use a TPL role)
Wrong:     font_size=40      (use TITLE / BODY / CAPTION / FORMULA)
Wrong:     move_to(CENTER)   (positions belong in events)
```

## <COLOR_MAP>

Map each TPL role this scene uses to its meaning here (D5, D7). The same concept keeps the same role across scenes (D19).

```text
TPL.<role>  ->  meaning in this scene
Background  ->  template, drawn by the harness (rule C8)
```

## <CLIP_SEQUENCE>

Rules for the whole sequence:
- Clips and events run in order with no gaps. Every moment from t=0.0 to __TARGET_DURATION__ belongs to exactly one clip, and within it to an event or a HOLD (D13).
- Event IDs are `[clip.number]`, e.g. `[3.07]`, numbered in time order.
- Every object named is in OBJECT_REGISTRY (D6). No forbidden phrases (D10).

Repeat this block for every clip:

```text
==============================================================================
CLIP [N]  |  t=[start]s -> t=[end]s  |  Duration: [D]s  |  "[Clip title]"
==============================================================================
```

Each clip has these **9 fields**, in this order.

**1. KEY IDEA**
One sentence: what the viewer understands by the end of this clip (D17).

**2. SPEECH**
The words spoken in this clip, split into timed phrases (D16):
```text
t=[a]-[b]s  "[phrase]"          (verbatim from NARRATION, or "(estimated)")
```

**3. EVENT TIMELINE**
Every change in this clip, as atomic events in time order (D15). Format:
```text
[N.nn] t=[a]-[b]s ([D]s) | TYPE | VAR_NAME     (PARALLEL WITH [N.mm])
  what   : the one change, in plain words
  how    : Manim call, run_time, rate_func
  motion : which part shows or moves first and last; stroke before fill;
           path, pivot and direction; speed profile; overshoot or
           settle; what stays still meanwhile; what is in front
  where  : zone or anchor (start -> end, if it moves)
  look   : appearance during and after the change
  speech : "words spoken during this span" | (silence)
  why    : what this event shows, linked to the KEY IDEA
  Q1-Q4  : only if run_time >= 1.5 s (D11): one clause per quarter
  before/after : only for EMPHASIS: the state just before and just after
```
TYPE is one of ENTER, MOVE, TRANSFORM, UPDATE, EMPHASIS, EXIT, HOLD, CAMERA. A HOLD event lists everything visible and still, and why the viewer needs this pause; never "for pacing".

**4. OBJECT STATES**
For every object this clip touches: its state at the start of the clip and at the end (exists or not, opacity, scale, relative position, what it is in front of).

**5. INSTANCE BREAKDOWN**
For collections (D12): each instance or wave, with its order, offset, position relative to neighbors, and whether it supports the scene's pattern. Otherwise `N/A, no collections in this clip.`

**6. STYLE NOTES**
The clip's motion feel: snappy (`rush_into`), natural (`smooth`) or mechanical (`linear`), with the reason; any stagger and its lag_ratio; any ValueTracker or updater and what it drives (dt-based, D14). Shaped easings are written `rate_functions.ease_out_bounce` (vocabulary 11.3).

**7. MANIM COMPONENTS**
```text
Objects  : [class names]
Anims    : [animation names]
Wrappers : AnimationGroup | Succession | LaggedStart | none
Updaters : [always_redraw / add_updater / always_rotate] | none
```

**8. FRAME SNAPSHOT**
The screen at the clip's last moment, zone by zone, listing every visible object and its look in a few words (D18). Unused zones: `empty`.

**9. TRANSITION OUT**
One sentence: which objects stay for the next clip, which were removed, and by which event.

### Example clip (gradient descent; shows the format, not your content)

```text
==============================================================================
CLIP 2  |  t=6.0s -> t=14.0s  |  Duration: 8.0s  |  "The loss curve and a first step"
==============================================================================

1. KEY IDEA
The ball's height on the curve is the loss, and stepping downhill lowers it.

2. SPEECH
t=6.0-8.2   "Here is the loss for every possible weight."
t=8.2-11.0  "We start with a guess, high on the left side."
t=11.0-14.0 "Then we take a step downhill, along the slope."

3. EVENT TIMELINE
[2.01] t=6.0-7.0s (1.0s) | ENTER | loss_axes
  what   : the two axes are drawn
  how    : Create(loss_axes), run_time=1.0s, rate_func=smooth
  motion : the horizontal axis draws from its left end to its right end,
           then the vertical axis draws upward from the origin; tick
           marks appear as each axis passes them
  where  : MAIN_CANVAS, lower two thirds, origin toward the lower left
  look   : THIN stroke, TPL.dim; ticks, no numbers
  speech : "Here is the loss"
  why    : sets up the space where every weight has a loss

[2.02] t=6.6-7.2s (0.6s) | ENTER | w_label   (PARALLEL WITH [2.01])
  what   : the label 'w' writes in
  how    : Write(w_label), run_time=0.6s, rate_func=smooth
  motion : strokes draw left to right
  where  : just right of the horizontal axis's right end
  look   : CAPTION, TPL.text
  speech : "for every"
  why    : names the horizontal axis as the weight

[2.03] t=6.8-7.4s (0.6s) | ENTER | loss_label   (PARALLEL WITH [2.01])
  what   : the label 'loss' writes in
  how    : Write(loss_label), run_time=0.6s, rate_func=smooth
  motion : strokes draw left to right
  where  : just above the vertical axis's top end
  look   : CAPTION, TPL.text
  speech : "for every"
  why    : names the vertical axis as the loss

[2.04] t=7.4-8.2s (0.8s) | ENTER | loss_curve
  what   : the U-shaped loss curve is drawn
  how    : Create(loss_curve), run_time=0.8s, rate_func=smooth
  motion : draws from its upper-left end, down through its lowest point,
           up to its upper-right end; the axes stay still behind it
  where  : over loss_axes, lowest point above the horizontal axis's middle
  look   : THICK stroke, TPL.accent, no fill
  speech : "possible weight."
  why    : shows that the loss depends on the weight and has one lowest point

[2.05] t=8.2-8.8s (0.6s) | ENTER | ball
  what   : the ball pops onto the curve's left arm
  how    : GrowFromCenter(ball), run_time=0.6s,
           rate_func=rate_functions.ease_out_back
  motion : grows from a point, slightly overshoots its size, settles
  where  : on loss_curve, high on the left arm
  look   : Dot, MEDIUM, fill TPL.focus at full opacity; in front of
           loss_curve
  speech : "We start with a guess,"
  why    : the starting guess has a high loss

[2.06] t=8.8-9.6s (0.8s) | ENTER | w_marker
  what   : a dashed line drops from the ball to the horizontal axis
  how    : Create(w_marker), run_time=0.8s, rate_func=linear
  motion : draws downward from the ball; later redrawn every frame with
           always_redraw so it follows the ball
  where  : vertical, from ball to the horizontal axis
  look   : DashedLine, HAIRLINE, TPL.dim
  speech : "high on the"
  why    : connects the ball to its weight value

[2.07] t=9.6-11.0s (1.4s) | HOLD | (scene)
  what   : nothing moves
  look   : loss_axes, both labels, loss_curve, ball and w_marker visible
           and still
  speech : "left side."
  why    : gives the viewer time to see how high the start is

[2.08] t=11.0-11.6s (0.6s) | ENTER | slope_arrow
  what   : an arrow grows from the ball, pointing down the left arm
  how    : GrowArrow(slope_arrow), run_time=0.6s, rate_func=smooth
  motion : extends from its tail at the ball to its tip further down the curve
  where  : along the curve's tangent at the ball, pointing toward the bottom
  look   : Arrow, THIN, TPL.text, buff=0
  speech : "Then we take a step"
  why    : shows the downhill direction at the current point

[2.09] t=11.6-13.4s (1.8s) | MOVE | ball
  what   : the ball slides down the left arm to a lower point
  how    : MoveAlongPath(ball, step_path), run_time=1.8s, rate_func=smooth
           (step_path: the stretch of loss_curve between the two
           positions; declared in OBJECT_REGISTRY)
  motion : follows the curve itself, not a straight line; w_marker
           follows through its always_redraw; slope_arrow stays fixed
           where it was drawn
  where  : from high on the left arm to about halfway down it
  look   : unchanged
  speech : "downhill, along the slope."
  why    : stepping in the slope's direction lowers the loss
  Q1     : the ball starts slowly, still near its start
  Q2     : it speeds up and passes the tip of slope_arrow
  Q3     : it slows down, clearly lower than it started
  Q4     : it settles about halfway down the left arm

[2.10] t=13.4-13.8s (0.4s) | EXIT | slope_arrow
  what   : the arrow fades out
  how    : FadeOut(slope_arrow), run_time=0.4s
  motion : fades evenly; nothing else moves
  where  : in place
  look   : fades to fully transparent
  speech : (silence)
  why    : clears the old direction before the next step

[2.11] t=13.8-14.0s (0.2s) | HOLD | (scene)
  what   : nothing moves
  look   : loss_axes, labels, loss_curve, ball (lower), w_marker visible
  speech : (silence)
  why    : lets the new, lower position register

4. OBJECT STATES
loss_axes   : start none          | end visible, still
loss_curve  : start none          | end visible, still
ball        : start none          | end halfway down the left arm
w_marker    : start none          | end visible, following ball
slope_arrow : start none          | end removed at [2.10]

5. INSTANCE BREAKDOWN
N/A, no collections in this clip.

6. STYLE NOTES
Natural feel: smooth on all draws and the slide; ease_out_back gives the
ball a small pop on arrival. w_marker uses always_redraw (no per-frame
steps).

7. MANIM COMPONENTS
Objects  : Axes, Text, ParametricFunction, Dot, DashedLine, Arrow
Anims    : Create, Write, GrowFromCenter, GrowArrow, MoveAlongPath, FadeOut
Wrappers : AnimationGroup ([2.01] with [2.02], [2.03])
Updaters : always_redraw (w_marker)

8. FRAME SNAPSHOT
TOP_STRIP   : empty
MAIN_CANVAS : axes (TPL.dim) with labels; U-curve (TPL.accent); ball
              (TPL.focus) halfway down the left arm; dashed marker
              from ball to axis
SIDE_PANEL  : empty
BOTTOM_BAR  : empty

9. TRANSITION OUT
Everything visible stays for Clip 3; only slope_arrow was removed, at [2.10].
```

## <CAMERA_SCRIPT>

All CAMERA events in one log. If none: `STATIC. No camera operations in this scene.`

```text
[N.nn] | t=[a]-[b]s | framing before -> framing after | focus target |
         exact call | run_time | speed profile | purpose

Scene-class reason: [one sentence on why this scene class was chosen]
```

## <SCENE_END>

The scene's last seconds. Nothing carries into the next scene (D1).

```text
End Type     : HoldFinal | FadeOut
Starts at    : t=[N]s (event [N.nn])
Duration     : [N]s (at least the 0.8 s hold of rule P7)
Objects Kept : [VAR_NAMEs visible in the last frame; plan.json's last
                clip exits empty, so FadeOut everything when the next
                scene must open on an empty canvas]
Manim Calls  : [exact final self.play(...) / self.wait(...) lines; the
                last clip ends on the hold that completes its
                its length (rules S3, P7)]
```

## <TIMING_SUMMARY>

One row per clip. Clip N's end time equals clip N+1's start time.

```text
t_start - t_end | Clip [N]: [title] | events [N.01]-[N.nn] | speech covered: yes/no

TOTAL  : [N]s
TARGET : __TARGET_DURATION__s
STATUS : OK (TOTAL equals TARGET within 0.2s)
         | OVER by [X]s: shorten a HOLD event in Clip [N]
         | UNDER by [X]s: lengthen a justified HOLD event in Clip [N]
```

## <IMPLEMENTATION_NOTES>

Notes for the code agent. Cite rule IDs from the reference files instead of restating them, so the plan and the references cannot disagree.

```text
[CRITICAL]  the scene fails or renders wrong if ignored
[WARNING]   a common mistake; the scene renders but looks wrong
[TIP]       quality or maintainability

Always include:
[CRITICAL] E5  Every Tex/MathTex string literal uses r"...".
[CRITICAL] T3  Split MathTex into parts only for terms targeted later.
[CRITICAL] S1  After Transform(A, B), keep animating A; B is not on screen.
[CRITICAL] D5  Every color is TPL.<role>; every [COLOR] entry overridden.
[WARNING]  D12 To stagger a group, use
               LaggedStart(*[FadeIn(d, shift=0.15 * UP) for d in group],
                           lag_ratio=0.15);
               FadeIn(group) reveals every member at once.
[WARNING]  T2  A spin lasting across clips uses always_rotate(mob, rate)
               and mob.clear_updaters() when it should stop. Rotating is
               one timed animation.
[WARNING]  -   SurroundingRectangle does not follow a moving target. Use
               always_redraw(lambda: SurroundingRectangle(target,
               color=TPL.<role>)) and self.remove(...) when done.
[TIP]      -   Each clip becomes one block of self.play() / self.wait()
               calls; event IDs go in code comments, e.g. # [2.09].

[Add scene-specific notes with their rule IDs here]
```

---

## Checks before you output

The code agent rejects the plan if any check fails. Run each check, fix failures, and check again.

| # | Check | Fix if it fails |
|---|---|---|
| K1 | Every VAR_NAME used anywhere is in OBJECT_REGISTRY (D6) | Add the row or rename the use |
| K2 | Every TPL role used is in COLOR_MAP and TEMPLATE_REFERENCE; no Manim color constants or hex (D5, D7) | Replace with a template role |
| K3 | Events cover every moment with no gap; TOTAL equals TARGET within 0.2 s (D13) | Add or adjust HOLD events |
| K4 | Every clip has all 9 fields | Add the missing field |
| K5 | Every event has what, how, motion, where, look, speech and why (D15) | Fill the missing line |
| K6 | Every event changes one object, or one listed wave (D15) | Split the event |
| K7 | All spoken words appear in SPEECH and in the events' speech lines, in order (D16) | Realign speech to events |
| K8 | Every name is in vocabulary PARTS 4-12; none is banned (D3) | Replace with the listed alternative |
| K9 | No coordinates or numeric positions; only D8 tokens for sizes (D2, D8) | Rewrite with zones, anchors and tokens |
| K10 | No forbidden phrase (D10); Q1-Q4 on every event >= 1.5 s (D11); collections broken down (D12) | Expand the event |
| K11 | No object from another scene is reused; every recall is rebuilt and listed in CONTINUITY (D1, D19) | Rebuild it or drop the reference |
| K12 | Scene class matches camera and 3D use (V4); every zone used is in LAYOUT_PLAN | Change the scene class or update the layout |
| K13 | Every clip is 4-20 s of narration (D0); plan.json has the same clips, in order, speaking the same words; each clip's ENTRY objects are its OBJECT STATES "start" | Merge or split clips; re-derive plan.json |
