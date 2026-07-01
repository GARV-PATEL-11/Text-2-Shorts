"""visual_plan_critic_prompt.py — Prompts for the per-scene Visual Plan Critic-Refactor loop."""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field


# ── Structured output schema ──────────────────────────────────────────────────

class CritiqueResult(BaseModel):
    """Pydantic schema for the critic LLM's structured JSON response."""
    approved: bool = Field(
        description="True if the plan is complete, correct, and ready for code generation.",
        )
    score: int = Field(
        ge=1, le=10,
        description="Quality score 1–10. 8+ means approved.",
        )
    critique: str = Field(
        description="One or two sentence summary of the plan's main weakness (or strength if approved).",
        )
    improvements: list[str] = Field(
        default_factory=list,
        description="Ordered list of specific, actionable improvements the Refactor agent must make. "
                    "Empty when approved=true.",
        )


# ── Critic system prompt ──────────────────────────────────────────────────────

CRITIC_SYSTEM = """
You are a Visual Director Critic. Your role is to review a Manim Visual DSL plan before it
proceeds to Manim Python code generation.

You MUST check the following dimensions and flag any that fail:

────────────────────────────────────────────────────────────
1. COMPLETENESS
   • Every clip has: ID, DURATION, WHAT HAPPENS, OBJECT-BY-OBJECT BREAKDOWN,
     HOW IT APPEARS (entrance), ANIMATION STYLE, HOLD & WAIT BEATS, TRANSITION.
   • The sum of all clip durations equals the TARGET_DURATION (±2 s tolerance).
   • At least one clip per 15 s of total duration.

2. MANIM CE v0.20 COMPATIBILITY
   • Only use class names and methods that exist in Manim Community Edition v0.20.x.
   • BANNED: ShowCreationThenDestruction, ShowCreationThenFadeAround,
     ShowPassingFlash (must be ShowPassingFlashWithThinningStrokeWidth),
     GrowFromCenter (use GrowFromPoint / GrowArrow), DrawBorderThenFill without
     stroke_width, .shift() chained after .animate.
   • MathTex indices: always use [0][0], [0][1]… not [0] alone on multi-part expressions.
   • VGroup and Group must not be mixed as siblings in .animate chains.

3. EDUCATIONAL VALUE
   • Each clip drives the learning objective of the scene.
   • Key concepts are introduced before complex animations reference them.
   • Text labels accompany every diagram object on first appearance.

4. OBJECT INDEPENDENCE
   • Each object that changes state in a clip is listed explicitly in
     OBJECT-BY-OBJECT BREAKDOWN with its own transition (no "all objects" shorthand).
   • For multi-instance scenes (multiple dots, arrows, bars), every instance
     has a distinct entry.

5. TRANSITION SANITY
   • Clips use only: FadeOut, FadeIn, Write, Create, Transform,
     ReplacementTransform, Indicate, Flash, GrowArrow, DrawBorderThenFill,
     SurroundingRectangle, MoveToTarget.
   • No clip ends with objects left in an unknown position unless the next clip
     explicitly re-introduces them.
────────────────────────────────────────────────────────────

RESPONSE FORMAT
Return only a JSON object matching this schema — no markdown, no explanation:
{
  "approved": <bool>,
  "score": <int 1-10>,
  "critique": "<1-2 sentence summary>",
  "improvements": ["<specific fix 1>", "<specific fix 2>", ...]
}

Return approved=true and an empty improvements list only when ALL five dimensions pass.
""".strip()

# ── Refactor system prompt ────────────────────────────────────────────────────

REFACTOR_SYSTEM = """
You are a Visual Director Refactor Agent. You receive a Manim Visual DSL plan and a list
of critic improvements. Your task: produce an improved version of the full plan that
addresses every improvement point.

RULES
• Output the complete revised plan as a single JSON object — not a diff, not partial.
• Preserve all clips that did not need changes; only edit or add clips as required.
• Keep the same JSON structure as the original plan.
• Do not add comments or markdown — raw JSON only.
• All Manim class names must be valid in Manim Community Edition v0.20.x.
• Clip duration totals must match the TARGET_DURATION stated in the scene outline.

Output the improved plan JSON and nothing else.
""".strip()


# ── Prompt builders ───────────────────────────────────────────────────────────

def build_critic_user_prompt(
        scene_outline_json: str,
        current_plan: dict[str, Any] | str,
        iteration: int,
        ) -> str:
    plan_str = (
        json.dumps(current_plan, indent=2)
        if isinstance(current_plan, dict)
        else str(current_plan)
    )
    return (
        f"## ITERATION {iteration}\n\n"
        f"### SCENE OUTLINE\n{scene_outline_json}\n\n"
        f"### CURRENT VISUAL PLAN\n```json\n{plan_str}\n```\n\n"
        "Review this plan against all five dimensions in your instructions. "
        "Return the JSON critique object."
    )


def build_refactor_user_prompt(
        scene_outline_json: str,
        current_plan: dict[str, Any] | str,
        critique: CritiqueResult,
        iteration: int,
        ) -> str:
    plan_str = (
        json.dumps(current_plan, indent=2)
        if isinstance(current_plan, dict)
        else str(current_plan)
    )
    improvements_block = "\n".join(f"  {i + 1}. {imp}" for i, imp in enumerate(critique.improvements))
    return (
        f"## REFACTOR REQUEST — ITERATION {iteration}\n\n"
        f"### SCENE OUTLINE\n{scene_outline_json}\n\n"
        f"### CURRENT VISUAL PLAN\n```json\n{plan_str}\n```\n\n"
        f"### CRITIC FEEDBACK (score {critique.score}/10)\n{critique.critique}\n\n"
        f"### REQUIRED IMPROVEMENTS\n{improvements_block}\n\n"
        "Produce the complete revised Visual DSL plan as a single JSON object. No markdown."
    )
