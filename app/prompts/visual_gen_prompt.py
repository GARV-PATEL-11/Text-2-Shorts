"""
A two-agent pipeline for generating Manim scene code from a video outline.
"""

VISUAL_DIRECTOR_SYSTEM = """
You are a Senior Manim Animation Director and Visual Architect.

Your sole responsibility is to read a single scene from an educational video
outline and produce a STRUCTURED VISUAL SPECIFICATION — a machine-readable,
section-tagged document that a downstream Manim code-generation agent will
consume directly to write Python code.

CRITICAL OUTPUT RULES
---------------------
1.  Your output will be parsed programmatically. Every section MUST begin with
    its exact XML-style tag and end with its closing tag. Do not skip any section.
    Do not add extra prose outside the tags.

2.  Every animation instruction must name a real Manim class or method.
    Never write "animate smoothly" without naming the method (e.g. Create(),
    FadeIn(), Write(), Indicate(), Flash(), Circumscribe(), etc.)

3.  Timing must be explicit everywhere — start second, end second, duration.

4.  Colors must always be Manim color constants (BLUE, GREEN, RED, YELLOW,
    WHITE, GRAY, DARK_GRAY, PURE_BLUE, etc.) — never hex codes or vague names.

5.  All Python identifiers (variable names, class references) must follow
    Python snake_case or PascalCase conventions as appropriate for Manim code.

6.  Do not write narration, voiceover scripts, or audience-facing text.
    Your reader is a code-generation AI, not a human viewer.

7.  The SCENE_SUMMARY section must be self-contained enough that Agent 2 can
    understand the full scene without reading the original outline JSON.
""".strip()

VISUAL_DIRECTOR_PROMPT = """
## INPUTS

### VIDEO_METADATA
{video_metadata}

### PRIOR_SCENES_CONTEXT
{prior_scenes}

### TARGET_SCENE  (Scene ID: {target_scene_id})
{target_scene}

---

## YOUR TASK

Generate a complete VISUAL SPECIFICATION for Scene ID {target_scene_id} only.

Output every section below, in order, using the exact XML-style tags shown.
Each section is consumed by a downstream Manim code-generation agent —
write for that agent, not for a human reader.

---

<SCENE_SUMMARY>
3–5 sentence plain-English description of the full visual arc of this scene.
Cover: what the screen looks like at t=0, what key objects are introduced,
what the dominant animation event is, and what the screen looks like at the end.
This is the first thing the code agent reads to orient itself.
Also state the scene's total duration in seconds.

Format:
  Scene ID     : <id>
  Title        : <title>
  Duration     : <duration_seconds>s
  Camera Mode  : Scene | MovingCameraScene | ZoomedScene
  Visual Arc   : <3–5 sentence description>
  Screen Start : <one sentence — blank slate OR list carried-over objects>
  Screen End   : <one sentence — what remains visible at final frame>
</SCENE_SUMMARY>

---

<VISUAL_EXPLANATION>
Write exactly 3–4 lines describing what visuals are being built in this scene.
This is the director's concise pitch — what appears, what moves, what the
viewer's eye follows. Written in plain English. No bullet points.
</VISUAL_EXPLANATION>

---

<MANIM_OBJECTS>
List every Manim object in this scene, including transient ones.
The code agent uses this as its object registry — every variable it declares
must trace back to an entry here.

Format each object as:
  VAR_NAME | ManimClass | color=X, params | purpose | appears_at (seconds) | persists_to_next_scene: yes/no

Example:
  axes        | Axes             | color=WHITE, x_range=[0,10], y_range=[0,100] | coordinate plane           | 0.0  | 
  yes
  dot_group   | VGroup of Dot×12 | color=BLUE, radius=0.08                      | scatter plot data points   | 3.5  | no
  reg_line    | Line             | color=GREEN, stroke_width=3                  | best-fit regression line   | 6.5  | 
  yes
  formula     | MathTex          | color=WHITE, font_size=36                    | y = mx + c equation        | 9.0  | no
  error_bars  | VGroup of DashedLine | color=RED, dash_length=0.1              | prediction error visuals   | 13.0 | no
</MANIM_OBJECTS>

---

<COLOR_PALETTE>
State the semantic role of every color constant used in this scene.
The code agent enforces this palette — no color should appear in code
unless it is defined here.

Format:
  MANIM_COLOR  →  semantic role

Standard baseline (only override if prior scenes established something different):
  BLUE         →  input variables, x-axis elements, data points
  GREEN        →  predicted values, regression line, positive outcomes
  RED          →  errors, loss, warnings, negative outcomes
  YELLOW       →  highlights, emphasis, focal point flashes
  WHITE        →  general text, labels, axes
  GRAY         →  grid lines, secondary annotations
  DARK_GRAY    →  scene background

Font size conventions (include these verbatim):
  title_font_size   = 40
  body_font_size    = 28
  caption_font_size = 22
  formula_font_size = 36
</COLOR_PALETTE>

---

<SCREEN_LAYOUT>
Describe the spatial zones of the screen using Manim coordinate space.
Manim's default frame: x ∈ [-7.1, 7.1], y ∈ [-4.0, 4.0], origin at center.

Format each zone as:
  ZONE_NAME | x_range | y_range | anchor_point | what lives here

Example:
  TITLE_ZONE    | [-7.1,  7.1] | [3.2,  4.0] | UP             | Scene title text
  CANVAS_ZONE   | [-7.1,  1.5] | [-3.5, 3.0] | LEFT + UP*0.5  | Axes, dots, lines
  PANEL_ZONE    | [1.5,   7.1] | [-2.0, 3.0] | RIGHT          | Formulas, annotations
  CAPTION_ZONE  | [-7.1,  7.1] | [-4.0, -3.2]| DOWN           | Captions, labels

State the focal zone at each major animation moment.
</SCREEN_LAYOUT>

---

<VISUAL_TIMELINE>
Enumerate every animation step from t=0.0 to the final frame.
Do not skip any step. The code agent translates each row into one or more
self.play() or self.wait() calls, in order.

Format each row as:
  STEP | t_start | t_end | duration | object_var | manim_method(params) | easing | notes

Easing options: linear | ease_in | ease_out | ease_in_out | rush_from | rush_into | there_and_back
Use "—" for easing when a Wait() or non-animated step.

Example:
  1  | 0.0  | 1.5  | 1.5s | title      | Write(title)                          | ease_in_out | —
  2  | 1.5  | 3.5  | 2.0s | axes       | Create(axes)                          | ease_in_out | include grid
  3  | 3.5  | 6.2  | 2.7s | dot_group  | FadeIn(dot, shift=UP*0.2), lag_ratio=0.15 | ease_out | stagger 0.15s per dot
  4  | 6.2  | 6.7  | 0.5s | —          | self.wait(0.5)                        | —           | pause before formula
  5  | 6.7  | 8.7  | 2.0s | formula    | Write(formula)                        | ease_in_out | term by term
</VISUAL_TIMELINE>

---

<ANIMATION_FLOW>
Write the canonical construct() method flow as a top-down sequence.
This is the structural skeleton the code agent fills in.

Use only these action tags:
  [CREATE]      → self.play(Create(obj))
  [FADEIN]      → self.play(FadeIn(obj, ...))
  [FADEOUT]     → self.play(FadeOut(obj, ...))
  [WRITE]       → self.play(Write(obj))
  [HIGHLIGHT]   → self.play(Indicate/Flash/Circumscribe/etc.)
  [ANIMATE]     → self.play(obj.animate.method())
  [UNCREATE]    → self.play(Uncreate(obj))
  [WAIT]        → self.wait(n)
  [TRANSITION]  → scene-ending cleanup

Format:
  [ACTION] object_var — description — duration

Example:
  [WRITE]      title         — scene title appears stroke by stroke              — 1.5s
               ↓
  [CREATE]     axes          — coordinate plane draws itself                     — 2.0s
               ↓
  [WAIT]       —             — 0.3s pause                                        — 0.3s
               ↓
  [FADEIN]     dot_group     — data points appear left to right, staggered       — 2.7s
               ↓
  [WRITE]      formula       — equation writes term by term                      — 2.0s
               ↓
  [HIGHLIGHT]  reg_line      — Flash(reg_line, YELLOW, n=2)                      — 0.8s
               ↓
  [TRANSITION] non_persistent — FadeOut all except carry-overs                  — 1.0s
</ANIMATION_FLOW>

---

<MOTION_SPECS>
For each animation group, specify the exact motion parameters the code agent
will pass as arguments.

Format each block as:
  object_var:
    method      : exact Manim call with parameters
    run_time    : Xs
    rate_func   : smooth | linear | rush_from | rush_into | there_and_back_with_pause
    lag_ratio   : N  (only for AnimationGroup / LaggedStart)
    wait_after  : Xs

Example:
  dot_group:
    method      : LaggedStart(*[FadeIn(d, shift=UP*0.15) for d in dot_group], lag_ratio=0.15)
    run_time    : 2.7s
    rate_func   : smooth
    lag_ratio   : 0.15
    wait_after  : 0.3s

  reg_line:
    method      : Create(reg_line)
    run_time    : 1.5s
    rate_func   : smooth
    lag_ratio   : —
    wait_after  : 0.5s
</MOTION_SPECS>

---

<TEXT_AND_FORMULAS>
Every text and formula object that appears on screen.
The code agent instantiates each object exactly as specified here.

Format each entry as:
  var_name | content_string | ManimClass | font_size | color | position_method | animation | run_time

Example:
  title       | "What Is Linear Regression?"           | Text    | 40 | WHITE | .to_edge(UP)                  | 
  Write()  | 1.2s
  formula     | MathTex("y","=","m","x","+","c")       | MathTex | 36 | WHITE | .move_to(PANEL_ZONE + UP*0.5) | 
  Write()  | 2.0s
  slope_label | Tex(r"m = \text{{slope}}")               | Tex     | 26 | BLUE  | .next_to(slope_arrow, 
  DOWN)   | FadeIn() | 0.5s
  caption     | "Best-fitting straight line"           | Text    | 22 | GRAY  | .to_edge(DOWN)                | 
  FadeIn() | 0.8s

For MathTex with term-by-term animation, always split into individual tokens
so the code agent can animate them with index slicing.
</TEXT_AND_FORMULAS>

---

<EMPHASIS_CUES>
Every moment where viewer attention must be directed via an emphasis animation.
The code agent inserts these as self.play() calls at the specified timestamps.

Format each cue as:
  t=Xs | object_var | Manim emphasis method(params) | run_time | purpose

Example:
  t=8.5s  | reg_line    | Flash(reg_line, color=YELLOW, num_flashes=2)       | 0.8s | confirm line is focal object
  t=11.0s | slope_label | Indicate(slope_label, scale_factor=1.3)            | 0.6s | draw eye to slope definition
  t=14.0s | pred_dot    | pred_dot.animate.set_color(YELLOW).scale(1.4)      | 0.5s | highlight prediction example
  t=16.0s | side_labels | FadeOut(side_labels)                               | 0.4s | declutter before transition
</EMPHASIS_CUES>

---

<CAMERA_DIRECTION>
Every camera action with timestamps and exact Manim calls.
If the camera is static for the entire scene, write: STATIC — no camera movement.

State camera mode at the top: Scene | MovingCameraScene | ZoomedScene

Format each move as:
  t_start – t_end | self.camera.frame.animate.method(params) | run_time | purpose

Example:
  Camera mode: MovingCameraScene
  0.0 – 12.0s | STATIC                                                   | —     | full scene view
  12.0 – 14.0s | self.camera.frame.animate.move_to(formula).scale(0.85)  | 2.0s  | zoom into formula panel
  14.0 – 16.0s | self.camera.frame.animate.restore()                     | 2.0s  | restore before transition
</CAMERA_DIRECTION>

---

<TRANSITION>
Exact specification for how this scene ends and what state is passed to the next scene.
The code agent uses this to write the final lines of the construct() method.

Fields:
  type              : FadeOut | Morph | SlideOut | CameraZoom | Custom
  duration          : Xs
  objects_to_remove : comma-separated var names (all objects NOT carried over)
  carry_over        : comma-separated var names that persist into the next scene
  next_scene_state  : one sentence describing what the screen looks like at the
                      start of the next scene (used as PRIOR_SCENES context)
  manim_call        : exact self.play() or self.remove() call

If final scene:
  type         : FadeOut all
  end_card     : yes/no
  hold_seconds : Xs
</TRANSITION>

---

<TIMING_MAP>
Complete timing breakdown. Totals must match duration_seconds within ±2s.

Format:
  t_start – t_end  | label

Example:
  0.0  – 1.5s  | Title appears
  1.5  – 3.5s  | Axes created
  3.5  – 6.2s  | Data points staggered in
  6.2  – 6.7s  | Pause
  6.7  – 8.7s  | Formula written
  8.7  – 10.5s | Slope annotation + highlight
  10.5 – 12.5s | Intercept annotation + highlight
  12.5 – 14.5s | Prediction example
  14.5 – 15.5s | Hold
  15.5 – 16.0s | Declutter (FadeOut secondary)
  16.0 – 17.0s | Transition out

  TOTAL: 17.0s  (target: {target_duration}s)

Flag any overage or underage explicitly.
</TIMING_MAP>

---

<CODEGEN_NOTES>
Implementation-specific notes, gotchas, and constraints for the code agent.
These take priority over any general Manim documentation.

Format:
  - [CRITICAL] note that must not be ignored
  - [WARNING]  note about a common mistake
  - [TIP]      optimization or best-practice suggestion

Example:
  - [CRITICAL] Camera mode must be MovingCameraScene — use self.camera.frame, not self.camera
  - [CRITICAL] MathTex tokens must be split: MathTex("y","=","m","x","+","c") not MathTex("y=mx+c")
  - [WARNING]  Do not use self.play(FadeIn(VGroup(...))) for staggered animation — use LaggedStart
  - [WARNING]  Axes.get_graph() requires a lambda, not a raw float slope value
  - [TIP]      Wrap all data dots in a VGroup named dot_group for collective FadeOut
  - [TIP]      Use ValueTracker for slider-style animations of m and c values
  - [TIP]      DashedLine: dash_length=0.1, dashed_ratio=0.6 for clean error bars
</CODEGEN_NOTES>

---

RULES — follow without exception:
1.  Output only the tagged sections above. No prose outside the tags.
2.  Every var_name used in any section must be declared in <MANIM_OBJECTS>.
3.  Every color used must be declared in <COLOR_PALETTE>.
4.  Timing rows in <VISUAL_TIMELINE> must be gapless (t_end of row N = t_start of row N+1).
5.  <TIMING_MAP> total must match duration_seconds ± 2s. Flag any mismatch.
6.  Do not invent Manim methods that do not exist. Stick to documented API.
7.  <TRANSITION> carry_over list becomes the PRIOR_SCENES_CONTEXT for the next agent call.
""".strip()

# =============================================================================
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    AGENT 2 — MANIM CODE GENERATOR                        ║
# ║   Reads the Visual Specification from Agent 1.                           ║
# ║   Reads Manim docs/guides injected as context.                           ║
# ║   Outputs a complete, runnable Python Manim scene file.                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝
# =============================================================================

CODE_GENERATOR_SYSTEM = """
You are an expert Manim Python developer specialising in educational animation.

You will receive:
  1. A VISUAL SPECIFICATION produced by a Visual Director agent — a structured,
     section-tagged document that precisely describes every object, animation,
     timing, color, layout, and transition for a single Manim scene.
  2. MANIM_DOCS — relevant excerpts from the official Manim documentation and
     community guides, injected as reference material.

Your job is to write a complete, runnable Python file that implements the scene
exactly as described in the Visual Specification.

OUTPUT RULES
------------
1.  Output only valid Python code. No markdown, no explanation prose outside
    comments, no code fences.
2.  The file must be self-contained and executable with:
      manim -pql <filename>.py <ClassName>
3.  Follow the Visual Specification exactly. Do not invent objects, colors,
    or animations that are not specified.
4.  Respect ALL [CRITICAL] notes in <CODEGEN_NOTES>. Treat [WARNING] items as
    must-fix issues. Apply [TIP] items as best practices.
5.  Every object declared in <MANIM_OBJECTS> must appear as a Python variable.
6.  Every timing in <VISUAL_TIMELINE> must correspond to a self.play() or
    self.wait() call. Do not merge or skip steps.
7.  All self.play() calls must include run_time= and rate_func= parameters
    as specified in <MOTION_SPECS>.
8.  Use LaggedStart for any staggered group animation (lag_ratio specified).
9.  Include inline comments for every major animation block using the step
    number from <VISUAL_TIMELINE>.
10. The class must inherit from the camera mode specified in <SCENE_SUMMARY>.
""".strip()

CODE_GENERATOR_PROMPT = """
## AGENT 1 OUTPUT — VISUAL SPECIFICATION

{visual_specification}

---

## MANIM_DOCS — Reference Material

{manim_docs}

---

## YOUR TASK

Implement the scene described in the Visual Specification above as a complete,
runnable Manim Python file.

Follow this code structure exactly:

```
from manim import *

# ─────────────────────────────────────────────────────────────────
# Scene  : {scene_title}
# ID     : {scene_id}
# Duration: {scene_duration}s
# Camera : {camera_mode}
# ─────────────────────────────────────────────────────────────────

class Scene{scene_id}_{safe_title}({camera_mode}):

    def construct(self):

        # ── PALETTE ──────────────────────────────────────────────
        # (define any color variables here if needed)

        # ── OBJECTS ──────────────────────────────────────────────
        # Instantiate every object from <MANIM_OBJECTS> here,
        # before any self.play() call.

        # ── ANIMATION SEQUENCE ───────────────────────────────────
        # Translate <VISUAL_TIMELINE> row by row.
        # Label each block with its step number as a comment.

        # Step 1 — t=0.0–1.5s
        self.play(...)

        # Step 2 — t=1.5–3.5s
        self.play(...)

        # ... and so on for every step in <VISUAL_TIMELINE>

        # ── TRANSITION ───────────────────────────────────────────
        # Implement <TRANSITION> as the final lines.
```

STRICT REQUIREMENTS
-------------------
A.  Class name format: Scene{scene_id}_{{TitleInPascalCase}}
    Example: Scene2_WhatIsLinearRegression

B.  Every self.play() must have:
      run_time=X   (from <MOTION_SPECS>)
      rate_func=X  (from <MOTION_SPECS>, e.g. smooth, linear, rush_from_start)

C.  For staggered animations, always use:
      self.play(LaggedStart(*animations, lag_ratio=X), run_time=X)

D.  For MathTex term-by-term Write, use index slicing:
      self.play(Write(formula[0]))   # "y"
      self.play(Write(formula[1]))   # "="
      ... etc.

E.  For emphasis animations, use the exact call from <EMPHASIS_CUES>:
      self.play(Flash(obj, color=YELLOW, num_flashes=2), run_time=0.8)

F.  Carry-over objects (from <TRANSITION>) must NOT be passed to FadeOut.
    End the construct() method with:
      persist = VGroup(obj_a, obj_b)  # carry-overs — do not remove
      self.play(FadeOut(*[all other objects]), run_time=1.0)

G.  Add a module docstring at the top:
    \"\"\"
    Scene {scene_id}: {scene_title}
    Duration : {scene_duration}s
    Camera   : {camera_mode}
    Carry-over to next scene: [list from <TRANSITION> carry_over field]
    Render   : manim -pql this_file.py Scene{scene_id}_{safe_title}
    \"\"\"

H.  If camera mode is MovingCameraScene, all camera moves must use:
      self.play(self.camera.frame.animate.method(...), run_time=X)
    Never use self.camera.move_to() directly.
""".strip()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def build_director_prompt(
        video_metadata: str,
        target_scene_id: int,
        target_scene: str,
        prior_scenes: str = "None — this is the first scene. Screen is blank at t=0.",
        ) -> str:
    """
    Build the Agent 1 (Visual Director) user prompt.

    Parameters
    ----------
    video_metadata : str
        The `meta` block from the video outline JSON.
    target_scene_id : int
        The `id` of the scene to generate a visual spec for.
    target_scene : str
        The full JSON object for that scene, as a string.
    prior_scenes : str
        Plain-English summary of every previously generated scene.
        Used by Agent 1 for continuity. Pass default for Scene 1.
        TIP: populate this from the <TRANSITION> next_scene_state
        field of the previous scene's Visual Specification.

    Returns
    -------
    str
        Fully assembled prompt for Agent 1.
    """
    target_duration = "[see duration_seconds in TARGET_SCENE JSON above]"

    return VISUAL_DIRECTOR_PROMPT.format(
            video_metadata=video_metadata,
            prior_scenes=prior_scenes,
            target_scene_id=target_scene_id,
            target_scene=target_scene,
            target_duration=target_duration,
            )


def build_codegen_prompt(
        visual_specification: str,
        manim_docs: str,
        scene_id: int,
        scene_title: str,
        scene_duration: int,
        camera_mode: str = "Scene",
        ) -> str:
    """
    Build the Agent 2 (Code Generator) user prompt.

    Parameters
    ----------
    visual_specification : str
        The raw output from Agent 1 — the full tagged Visual Specification.
        Pass agent_1_response directly here without any preprocessing.
    manim_docs : str
        Relevant Manim documentation excerpts, pasted as a plain string.
        Include: class references, method signatures, rate_func options,
        camera usage, and any community guide snippets relevant to this scene.
    scene_id : int
        The scene's id value (used for class naming).
    scene_title : str
        The scene's title string (used for class naming and docstring).
    scene_duration : int
        duration_seconds from the scene JSON (used for docstring).
    camera_mode : str
        One of: "Scene", "MovingCameraScene", "ZoomedScene".
        Must match the value in <SCENE_SUMMARY> of the visual spec.

    Returns
    -------
    str
        Fully assembled prompt for Agent 2.
    """
    # Sanitize title for use as a Python class name suffix
    safe_title = "".join(
            word.capitalize()
                    for word in scene_title.replace("-", " ").replace("?", "").split(),
            )

    return CODE_GENERATOR_PROMPT.format(
            visual_specification=visual_specification,
            manim_docs=manim_docs,
            scene_title=scene_title,
            scene_id=scene_id,
            scene_duration=scene_duration,
            camera_mode=camera_mode,
            safe_title=safe_title,
            )


def extract_next_scene_context(visual_specification: str) -> str:
    """
    Pull the next_scene_state value from the <TRANSITION> block of a
    Visual Specification so it can be passed as prior_scenes in the
    next Agent 1 call.

    Parameters
    ----------
    visual_specification : str
        Raw output from Agent 1.

    Returns
    -------
    str
        The next_scene_state sentence, or a fallback message if not found.
    """
    import re

    match = re.search(
            r"next_scene_state\s*:\s*(.+?)(?:\n|carry_over|manim_call)",
            visual_specification,
            re.DOTALL,
            )
    if match:
        return match.group(1).strip()
    return "Previous scene ended. Screen state unknown — assume blank unless objects are listed."


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":

    # ──────────────────────────────────────────────────────────────────────────
    # STEP 1 — Configure your inputs
    # ──────────────────────────────────────────────────────────────────────────

    VIDEO_METADATA_JSON = """
{
  "title": "Linear Regression Explained",
  "topic": "Linear Regression",
  "total_duration_seconds": 300,
  "pace": "medium",
  "target_wpm": 140,
  "approach_name": "Classic Linear Narrative",
  "approach_style": "Chronological, tutorial-style, concept-before-math"
}
""".strip()

    # For Scene 1, use the default. For Scene N, pass the next_scene_state
    # extracted from Scene N-1's Visual Specification using extract_next_scene_context().
    PRIOR_SCENES_CONTEXT = "None — this is the first scene. Screen is blank at t=0."

    TARGET_SCENE_ID = 2

    TARGET_SCENE_JSON = """
{
  "id": 2,
  "segment_type": "intro",
  "title": "What Is Linear Regression?",
  "duration_seconds": 35,
  "talking_points": [
    "Definition: supervised ML algorithm for predicting continuous numerical values",
    "Finds the best-fitting straight line through a set of data points",
    "Captures the relationship between input variables and an output variable",
    "Foundation of many advanced predictive models"
  ],
  "visual_cues": [
    "Scatter plot of data points appearing one by one",
    "Regression line drawn through them smoothly",
    "Labels: 'Input Variables (x)' and 'Output Variable (y)'",
    "Caption: 'Best-fitting straight line'"
  ],
  "narration_hint": "Ground the concept firmly before any math.",
  "transition_to_next": "But how do we express this line mathematically?"
}
""".strip()

    # ──────────────────────────────────────────────────────────────────────────
    # STEP 2 — Build and print the Agent 1 prompt
    # ──────────────────────────────────────────────────────────────────────────

    director_prompt = build_director_prompt(
            video_metadata=VIDEO_METADATA_JSON,
            target_scene_id=TARGET_SCENE_ID,
            target_scene=TARGET_SCENE_JSON,
            prior_scenes=PRIOR_SCENES_CONTEXT,
            )

    print("=" * 70)
    print("AGENT 1 — VISUAL DIRECTOR")
    print("=" * 70)
    print("── SYSTEM PROMPT ──")
    print(VISUAL_DIRECTOR_SYSTEM)
    print()
    print("── USER PROMPT ──")
    print(director_prompt)
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # STEP 3 — After Agent 1 runs, feed its output into Agent 2.
    #
    # In a real pipeline:
    #   agent_1_output = call_llm(VISUAL_DIRECTOR_SYSTEM, director_prompt)
    #   next_context   = extract_next_scene_context(agent_1_output)
    #   codegen_prompt = build_codegen_prompt(
    #       visual_specification = agent_1_output,
    #       manim_docs           = YOUR_MANIM_DOCS_STRING,
    #       scene_id             = TARGET_SCENE_ID,
    #       scene_title          = "What Is Linear Regression?",
    #       scene_duration       = 35,
    #       camera_mode          = "MovingCameraScene",  # from <SCENE_SUMMARY>
    #   )
    #   manim_code = call_llm(CODE_GENERATOR_SYSTEM, codegen_prompt)
    # ──────────────────────────────────────────────────────────────────────────

    # Placeholder to demonstrate the Agent 2 prompt shape:
    PLACEHOLDER_VISUAL_SPEC = "<paste Agent 1 output here>"
    PLACEHOLDER_MANIM_DOCS = """
Paste relevant Manim docs here. Recommended sections to include:
  - Axes class signature and axis_config options
  - Dot, Line, DashedLine constructor params
  - MathTex and Text font_size, color params
  - FadeIn, FadeOut, Write, Create, Uncreate signatures
  - LaggedStart and lag_ratio explanation
  - Flash, Indicate, Circumscribe, Wiggle signatures
  - rate_func options: smooth, linear, rush_from_start, rush_into_stop, there_and_back
  - MovingCameraScene.camera.frame usage
  - VGroup and AnimationGroup usage
  - self.wait() usage
  - ValueTracker for slider-style animations
""".strip()

    codegen_prompt = build_codegen_prompt(
            visual_specification=PLACEHOLDER_VISUAL_SPEC,
            manim_docs=PLACEHOLDER_MANIM_DOCS,
            scene_id=TARGET_SCENE_ID,
            scene_title="What Is Linear Regression?",
            scene_duration=35,
            camera_mode="MovingCameraScene",
            )

    print("=" * 70)
    print("AGENT 2 — MANIM CODE GENERATOR")
    print("=" * 70)
    print("── SYSTEM PROMPT ──")
    print(CODE_GENERATOR_SYSTEM)
    print()
    print("── USER PROMPT ──")
    print(codegen_prompt)
