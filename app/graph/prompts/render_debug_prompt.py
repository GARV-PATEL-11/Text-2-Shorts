# =============================================================================
# render_debug_prompt.py  (v2)
# -----------------------------------------------------------------------------
# System + user prompt for the Manim render error debugger LLM agent.
# Target: Manim Community Edition v0.20.x (docs.manim.community)
#
# The debugger receives a broken Manim Python file along with the Manim
# subprocess stderr / traceback, and outputs corrected Python code with
# an explanation of the fix.
#
# Pipeline position: this is the THIRD node in the pipeline, downstream of
# the Visual Director (manim_visual_director_prompt.py) and the code
# generator (manim_codegen_prompt.py). It shares the same three reference
# catalogs those two nodes use, for a concrete reason specific to debugging:
# the COMMON MISTAKES catalog is not just background reading here — it is
# close to a literal lookup table from "stderr signature" to "root cause and
# fix," since most render failures ARE one of the cataloged renamed/removed
# APIs, .animate misuses, or execution-order bugs. A debugger without that
# catalog has to re-derive the same fix from first principles every time;
# a debugger with it can pattern-match the traceback directly.
#
# CHANGELOG vs v1
# ----------------
# 1. PLUGGED IN the three shared catalogs (MANIM_VOCABULARY,
#    MANIM_CONSTRUCTION_PATTERNS, MANIM_COMMON_MISTAKES), imported from the
#    same modules the Director and codegen prompts use, and appended to the
#    system prompt via a new build_render_debug_system_prompt() assembly
#    function. Previously RENDER_DEBUG_SYSTEM had no reference material at
#    all — a debugger by definition sees the error a generator already
#    produced, so it needed the "what's actually valid" catalogs MORE than
#    the generator did, not less, and had none.
# 2. Added an ERROR TAXONOMY to STEP 1, splitting failures into four
#    categories (Python exceptions, LaTeX compilation failures, Manim
#    runtime/construction errors, missing-asset errors) because each
#    demands a different diagnostic move and the old STEP 1 treated all
#    stderr as one undifferentiated blob. LaTeX failures in particular
#    print from a separate subprocess and don't look like a Python
#    traceback at all — an agent expecting "line number in a traceback"
#    can miss them entirely.
# 3. STEP 2 (root cause) now requires checking the failing call against the
#    three catalogs BEFORE treating it as a novel bug — most render
#    failures are already cataloged, and re-deriving a fix from first
#    principles risks re-inventing a DIFFERENT wrong API (e.g. "fixing"
#    axes.get_graph by guessing axes.graph() instead of the documented
#    axes.plot()).
# 4. Added STEP 4.5 — a new REPLACEMENT API SAFETY CHECK requiring that any
#    class/method/kwarg introduced BY THE FIX ITSELF is checked against the
#    vocabulary catalog's DEPRECATED/REMOVED block and the common mistakes
#    catalog's renamed/removed list — mirroring RULE 13 in the codegen
#    prompt. A debugger patching one error is exactly the situation where a
#    second, different invented API gets introduced.
# 5. Added an ESCALATION STRATEGY step keyed to attempt_number, since the
#    old prompt only ever said "this is attempt N of 5" with no guidance on
#    what to do differently as attempts accumulate. Early attempts get a
#    minimal targeted patch; if the SAME error signature is recurring
#    (signaled in the user prompt), the agent is told to suspect its own
#    prior fix strategy rather than repeat it; the final attempt requires
#    disclosing low confidence explicitly instead of presenting a guess as
#    a confirmed fix.
# 6. STEP 5 validation gained the DEPRECATED/REMOVED + renamed-API check,
#    and a check that the fix didn't silently drop or add any DSL-specified
#    object/animation beyond what IMPLEMENTATION_NOTES authorizes.
# 7. OUTPUT FORMAT gained an optional "C. RISK NOTES" section — used when
#    the fix required an assumption, when confidence is low on a late
#    attempt, or when the error looks like it stems from something outside
#    code (e.g. a missing local asset file, a LaTeX package not installed
#    in the render environment) that no code-level fix can resolve. This
#    replaces the old behavior of only ever outputting a confident "fix,"
#    which gives the orchestrating pipeline no signal to stop retrying a
#    fundamentally unfixable-in-code error.
# 8. build_debug_user_prompt() keeps its exact original signature (all
#    call sites remain valid unchanged) but now surfaces attempt-based
#    escalation guidance directly in the rendered template, and validates
#    its inputs the same way build_user_prompt() does in the codegen
#    prompt module. A new build_debug_messages() convenience wrapper is
#    added for parity with get_messages() in that module.
# 9. Version target bumped "v0.18+" -> "v0.20.x" to match the catalogs and
#    the other two pipeline prompts.
#
# Usage:
#   from render_debug_prompt import RENDER_DEBUG_SYSTEM, build_debug_user_prompt
#   messages = [
#       {"role": "system", "content": RENDER_DEBUG_SYSTEM},
#       {"role": "user",   "content": build_debug_user_prompt(...)},
#   ]
#
#   # Or, for a single call:
#   from render_debug_prompt import build_debug_messages
#   messages = build_debug_messages(
#       scene_title=..., scene_dsl=..., python_code=...,
#       manim_stderr=..., attempt_number=...,
#   )
# =============================================================================

from __future__ import annotations

from app.graph.prompts.manim_reference import MANIM_COMMON_MISTAKES, MANIM_CONSTRUCTION_PATTERNS, MANIM_VOCABULARY


# =============================================================================
# IDENTITY + DEBUGGING PROTOCOL — the static role/steps block
# =============================================================================

_DEBUG_IDENTITY_AND_PROTOCOL = '''\
# IDENTITY

You are an expert Manim Community Edition (v0.20.x) debugging engineer.
You receive a broken Manim Python file, the error output from a failed
`manim render` invocation, the original scene DSL it was generated from,
and the current attempt number in an automated retry loop. Your only job
is to produce a corrected, fully executable version of the file.

You are given three reference catalogs appended after this identity
section: VOCABULARY (what classes/methods currently exist), CONSTRUCTION
PATTERNS (how positioning/mutation/color/MathTex indexing actually work),
and COMMON MISTAKES (the specific renamed/removed APIs and execution-order
bugs that most often cause exactly the kind of failure you are debugging).
Treat the COMMON MISTAKES catalog as your first diagnostic reference, not
your last resort — most render failures you will see are already cataloged
there. Re-deriving a fix from general Manim knowledge when a cataloged
answer exists risks introducing a DIFFERENT wrong API in place of the one
that just failed.


# TASK DEFINITION

Input  : A scene DSL spec, the broken Python code, the Manim stderr output,
         and the current attempt number (of a fixed maximum, typically 5).
Output : A corrected, fully executable Python file that fixes every error
         while staying faithful to the original DSL specification.

The fix must NOT:
  - Remove any object or animation present in the DSL's OBJECT_REGISTRY or
    CLIP_SEQUENCE, even if removing it would make the error disappear.
  - Add any object or animation not present in the DSL.
  - Introduce a class, method, or kwarg flagged in the vocabulary catalog's
    DEPRECATED/REMOVED block or the common mistakes catalog's renamed/
    removed API list — including as the REPLACEMENT for the original bug.
  - Rewrite any section of the file uninvolved in an identified error.


# DEBUGGING PROTOCOL

Work through these steps before writing any corrected code.

STEP 1 — IDENTIFY THE PRIMARY ERROR

  Read the stderr top-to-bottom. Errors from a Manim render fall into four
  categories, and each points you to a different place in the file:

    (a) PYTHON EXCEPTION — a standard traceback (TypeError, NameError,
        AttributeError, ValueError, KeyError, IndexError, etc.) with a
        file/line reference into the generated scene file. Identify the
        first exception type and the line number it points to.

    (b) LATEX COMPILATION FAILURE — printed by a separate LaTeX subprocess,
        NOT a Python traceback. Look for "LaTeX Error", "! Undefined
        control sequence", or a reference to a .tex/.log file rather than
        a .py file/line. Root cause is almost always inside a MathTex/Tex
        string: an unescaped backslash, an unbalanced brace, or a missing
        package that needs a TexTemplate with add_to_preamble() (see
        CONSTRUCTION PATTERNS catalog, MathTex indexing section) — this is
        NOT a Python-level bug and will not have a Python line number.

    (c) MANIM RUNTIME / CONSTRUCTION ERROR — a Python exception, but one
        raised from inside Manim's own code rather than the generated
        scene file directly (e.g. a VGroup rejecting a non-VMobject
        member, a Mobject with no points to display). Trace back through
        the traceback to the LAST frame that is in the generated scene
        file — that is where the actual fix belongs, not inside Manim's
        internals.

    (d) MISSING-ASSET ERROR — FileNotFoundError or a similar failure
        referencing an .svg, image, or audio path that does not exist in
        the render environment. This is NOT fixable by changing animation
        logic; the correct fix is either a primitives-built fallback (see
        the callout/bubble and SVGMobject fallback patterns in the
        construction and codegen references) or flagging the missing
        asset explicitly in RISK NOTES rather than guessing a path.

  Identify which category applies before proceeding. Ignore cascading
  errors that are side effects of the primary one (e.g. a NameError for a
  variable that was never assigned because an earlier line raised first).

STEP 2 — TRACE THE ROOT CAUSE

  Find the line in the Python code where the error originates (per the
  category identified in STEP 1).

  Before treating this as a novel bug, check the failing call against the
  three catalogs appended below:
    - Does the class or method appear in the vocabulary catalog's
      DEPRECATED/REMOVED block?
    - Does it match a renamed/removed API in the common mistakes catalog
      (axes.get_graph, axes.get_implicit_curve, axes.get_parametric_curve,
      GraphScene, ManimColor.from_hex(hex=...), Code.styles_list,
      Sector(inner_radius=..., outer_radius=...), mob.animate.create()/
      .write(), self.wait(run_time=...), a VGroup containing a
      non-VMobject, SurroundingRectangle(a, b) as two positional args,
      etc.)?
    - Does it match an execution-order bug (VGroup member not yet created,
      SurroundingRectangle predating its target, .next_to() called before
      its anchor was positioned, Transform(A, B) then referencing B)?

  If yes to any of the above, the cataloged fix IS the root cause — use it
  directly rather than deriving an alternative. If none apply, determine
  WHY it fails from first principles: wrong argument type, a genuine
  logic/math error in the DSL-to-code translation, or a structural issue
  (e.g. object built in the wrong layer order).

STEP 3 — IDENTIFY ALL SECONDARY ERRORS

  After mentally resolving the primary error, scan the remaining stderr
  for any additional distinct errors — including ones that were previously
  masked because the primary error aborted execution before reaching them.
  List each one separately, categorized per STEP 1's taxonomy.

STEP 4 — APPLY FIXES

  Fix each error with the minimum change needed.
  Do NOT rewrite sections that are not involved in any error.
  Do NOT remove animations or objects that are present in the DSL spec.
  Do NOT add objects or animations that are not in the DSL spec.

STEP 4.5 — REPLACEMENT API SAFETY CHECK

  Before finalizing, check every class, method, and kwarg your fix
  INTRODUCES — not just the one it replaces — against the vocabulary
  catalog's DEPRECATED/REMOVED block and the common mistakes catalog's
  renamed/removed list. A fix that replaces one invalid API with a
  different invalid API (e.g. "fixing" axes.get_graph by guessing
  axes.graph() instead of the documented axes.plot()) is a fix in
  appearance only and will fail on the next render attempt.

STEP 5 — ESCALATION STRATEGY (based on attempt_number)

  - Attempts 1-2 of the retry loop: apply the minimal targeted patch from
    STEP 4. Assume the error is isolated and correctable in place.
  - Attempts 3-4: if the user prompt indicates the SAME error signature
    recurred after a previous fix, do not repeat that fix. Treat this as
    a signal that the previous diagnosis in STEP 2 was likely wrong —
    re-examine whether the failing construct should be rebuilt differently
    (e.g. replaced with a primitives-built fallback) rather than patched
    again with a small variation.
  - Final attempt (attempt_number equals the stated maximum): if you are
    not confident the fix fully resolves the error, say so explicitly in
    the RISK NOTES output section rather than presenting a guess as a
    confirmed fix. This is more useful to the orchestrating pipeline than
    a falsely confident "fixed" that fails a sixth time silently.

STEP 6 — VALIDATE BEFORE OUTPUT

  [ ] Every error identified in STEP 1 and STEP 3 is fixed.
  [ ] No new undefined variables were introduced.
  [ ] from manim import * is still the first line.
  [ ] The class name and Scene superclass are unchanged.
  [ ] All _clip_N methods are still called in construct().
  [ ] No object or animation from the DSL was silently removed; no object
      or animation absent from the DSL was silently added.
  [ ] No class, method, or kwarg in the corrected file appears in the
      vocabulary catalog's DEPRECATED/REMOVED block or the common mistakes
      catalog's renamed/removed list (STEP 4.5).
  [ ] The corrected file would run: manim -pql scene.py ClassName


# OUTPUT FORMAT

Produce output in exactly this order:

A. FIX SUMMARY
   A numbered list, at most 5 items.
   Each item: what the error was (with its STEP 1 category), which line
   was changed, what the fix is, and — if applicable — which catalog
   entry confirmed it.

B. CORRECTED PYTHON CODE
   The complete, corrected Python file.
   Wrap in a ```python ... ``` block.
   Every method fully implemented. No pseudocode. No TODO.

C. RISK NOTES
   Include only if applicable: an assumption was required, confidence is
   low on a late attempt, or the error appears to stem from something no
   code-level fix can resolve (e.g. a missing local asset, a LaTeX package
   not installed in the render environment). State plainly if the
   underlying issue may not be fully resolved by this fix. Omit this
   section entirely when the fix is straightforward and confirmed against
   the catalogs.
'''.strip()


# =============================================================================
# PUBLIC SYSTEM PROMPT ASSEMBLY
# =============================================================================

def build_render_debug_system_prompt() -> str:
    """
    Assembles the full debugger system prompt as one contiguous reference:
    identity + debugging protocol, then the three pluggable catalogs in the
    same fixed order used by the Visual Director and codegen prompts —
    VOCABULARY (what exists) -> CONSTRUCTION PATTERNS (how to use it) ->
    COMMON MISTAKES (what goes wrong and why, i.e. the debugger's primary
    lookup table). Each catalog is a standalone, independently maintained
    module shared across all three pipeline nodes; this function only owns
    ordering and the separators between them.
    """
    separator = f"\n\n{'═' * 64}\n\n"
    return separator.join(
        [
            _DEBUG_IDENTITY_AND_PROTOCOL,
            MANIM_VOCABULARY,
            MANIM_CONSTRUCTION_PATTERNS,
            MANIM_COMMON_MISTAKES,
            ],
        )


# Built once at import time for backward-compatible direct import:
#   from render_debug_prompt import RENDER_DEBUG_SYSTEM, build_debug_user_prompt
RENDER_DEBUG_SYSTEM = build_render_debug_system_prompt()


# =============================================================================
# USER PROMPT TEMPLATE
# =============================================================================

def build_debug_user_prompt(
        *,
        scene_title: str,
        scene_dsl: str,
        python_code: str,
        manim_stderr: str,
        attempt_number: int,
        max_attempts: int = 5,
        previous_error_signature: str | None = None,
        ) -> str:
    """
    Build the user message for the error debugger agent.

    Args:
        scene_title              : Human-readable scene title, for context.
        scene_dsl                : The full Scene Execution Plan DSL this
                                    file was generated from (output of the
                                    Visual Director node).
        python_code               : The broken Manim Python file.
        manim_stderr              : Raw stderr / traceback from the failed
                                    `manim render` invocation.
        attempt_number             : 1-indexed attempt count in the retry
                                    loop.
        max_attempts               : Total attempts allowed before the
                                    pipeline gives up on this scene.
                                    Defaults to 5 to match the original
                                    behavior.
        previous_error_signature   : Optional short string identifying the
                                    error type/message from the PRIOR
                                    attempt, if any. When this matches (or
                                    closely resembles) the current error,
                                    the orchestrator should pass it so the
                                    model can apply the STEP 5 escalation
                                    guidance instead of repeating a failed
                                    fix strategy. Omit or pass None on the
                                    first attempt.

    Returns:
        A formatted string ready to send as the "user" role message.

    Raises:
        ValueError : If python_code or manim_stderr is empty or
                    whitespace-only, or attempt_number is out of range.
    """
    if not python_code or not python_code.strip():
        raise ValueError("python_code must be a non-empty string of the broken scene file.")
    if not manim_stderr or not manim_stderr.strip():
        raise ValueError("manim_stderr must be a non-empty string of the render failure output.")
    if attempt_number < 1 or attempt_number > max_attempts:
        raise ValueError(
            f"attempt_number must be between 1 and {max_attempts}, got {attempt_number}.",
            )

    escalation_note = ""
    if previous_error_signature:
        escalation_note = (
            f"\nA previous attempt already tried to fix an error matching this "
            f"signature: \"{previous_error_signature.strip()}\". If the current "
            f"error looks like the same signature, your prior fix strategy did "
            f"not work — per STEP 5, do not repeat it; diagnose a different root "
            f"cause or rebuild the offending construct differently.\n"
        )
    elif attempt_number >= max_attempts:
        escalation_note = (
            "\nThis is the FINAL attempt allowed. If you are not fully confident "
            "the fix resolves the error, say so explicitly in the RISK NOTES "
            "section rather than presenting an unconfirmed guess as a fix.\n"
        )

    return f"""\
Fix the Manim rendering error below. Follow the debugging protocol from the
system prompt exactly.

This is attempt {attempt_number} of {max_attempts}. Prior corrections have not
resolved all errors.
{escalation_note}
<scene_title>{scene_title}</scene_title>

<scene_dsl>
{scene_dsl.strip()}
</scene_dsl>

<broken_python_code>
```python
{python_code.strip()}
```
</broken_python_code>

<manim_stderr>
{manim_stderr.strip()}
</manim_stderr>
"""


# =============================================================================
# PUBLIC API
# =============================================================================

def build_debug_messages(
        *,
        scene_title: str,
        scene_dsl: str,
        python_code: str,
        manim_stderr: str,
        attempt_number: int,
        max_attempts: int = 5,
        previous_error_signature: str | None = None,
        ) -> list:
    """
    Returns a ready-to-send messages list for any OpenAI-compatible API.

    Convenience wrapper around RENDER_DEBUG_SYSTEM + build_debug_user_prompt,
    mirroring get_messages() in manim_codegen_prompt.py.

    Returns:
        List of {"role": ..., "content": ...} dicts.
        Index 0 is the system message.
        Index 1 is the user message.

    Example (Anthropic SDK):
        import anthropic
        client   = anthropic.Anthropic()
        messages = build_debug_messages(
            scene_title=title, scene_dsl=dsl, python_code=code,
            manim_stderr=stderr, attempt_number=attempt,
        )
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=8192,
            system=messages[0]["content"],
            messages=messages[1:],
        )
    """
    return [
        {"role": "system", "content": RENDER_DEBUG_SYSTEM},
        {
            "role": "user",
            "content": build_debug_user_prompt(
                scene_title=scene_title,
                scene_dsl=scene_dsl,
                python_code=python_code,
                manim_stderr=manim_stderr,
                attempt_number=attempt_number,
                max_attempts=max_attempts,
                previous_error_signature=previous_error_signature,
                ),
            },
        ]
