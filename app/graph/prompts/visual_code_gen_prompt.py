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
            for word in scene_title.replace("-", " ").replace("?", "").split()
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
    "Foundation of many advanced predictive schemas"
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
    # In a real graph:
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
