"""outline_critic_prompt.py — Prompts for the Outline Critic-Refactor loop."""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field


# ── Structured output schema ──────────────────────────────────────────────────

class OutlineCritiqueResult(BaseModel):
    """Pydantic schema for the outline critic LLM's structured JSON response."""
    approved: bool = Field(
        description="True if the outline is educationally sound and ready for visual planning.",
        )
    score: int = Field(
        ge=1, le=10,
        description="Quality score 1–10. 8+ means approved.",
        )
    critique: str = Field(
        description="One or two sentence summary of the outline's main weakness (or strength if approved).",
        )
    improvements: list[str] = Field(
        default_factory=list,
        description="Ordered list of specific, actionable improvements. Empty when approved=true.",
        )


# ── Critic system prompt ──────────────────────────────────────────────────────

OUTLINE_CRITIC_SYSTEM = """
You are an Educational Content Critic. Your role is to review a video outline before it
proceeds to visual planning. The outline describes a short educational video.

You MUST evaluate the following dimensions and flag any that fail:

────────────────────────────────────────────────────────────
1. THEORETICAL ACCURACY
   • All concepts, facts, and definitions in talking_points are correct.
   • No misleading simplifications that would leave learners with a wrong mental model.
   • Technical terms are used precisely and consistently throughout.

2. NARRATIVE COHERENCE
   • Scenes flow in logical pedagogical order — prerequisites come before dependents.
   • Each scene has a distinct learning objective that does not overlap with adjacent scenes.
   • The final scene provides a clear synthesis or takeaway, not an abrupt stop.

3. SCENE GRANULARITY
   • No single scene covers too many independent concepts for its duration_seconds.
   • Complex ideas are broken into digestible steps spread across multiple scenes.
   • No two scenes are redundant — each meaningfully advances the viewer's understanding.

4. TALKING POINTS QUALITY
   • Every talking_point is a specific, concrete statement (not "discuss X" or "explain Y").
   • Talking points for each scene, read in sequence, form a coherent mini-script.
   • No vague, filler, or repeated talking points.

5. VISUAL PLAN DESCRIPTIONS
   • The visual_plan field of every scene describes concrete visual actions (not just topics).
   • Each visual_plan is self-contained — no cross-scene references ("as shown in scene 1").
   • Each visual_plan describes at least 3 chained, actively moving visual events.
   • Visual plans describe animations and dynamic visuals, not just static text on screen.
   • Visual plans end with a clear "final frame" sentence stating what the viewer sees last.

6. TIMING DISTRIBUTION
   • The sum of all duration_seconds equals total_duration_seconds in meta.
   • Scenes that introduce complex multi-step concepts have proportionally more time.
   • No scene is under 10 seconds unless it is a brief transition or recap.

7. EDUCATIONAL COMPLETENESS
   • The topic from meta.topic is covered end-to-end for the stated audience.
   • A viewer with no prior knowledge would finish with a coherent understanding.
   • No critical prerequisite concept is assumed without first being introduced.
────────────────────────────────────────────────────────────

RESPONSE FORMAT
Return only a JSON object matching this schema — no markdown, no explanation:
{
  "approved": <bool>,
  "score": <int 1-10>,
  "critique": "<1-2 sentence summary>",
  "improvements": ["<specific fix 1>", "<specific fix 2>", ...]
}

Return approved=true and an empty improvements list only when ALL seven dimensions pass.
""".strip()

# ── Refactor system prompt ────────────────────────────────────────────────────

OUTLINE_REFACTOR_SYSTEM = """
You are an Educational Content Refactor Agent. You receive a video outline and a list
of improvements identified by the critic. Your task: produce a complete revised outline
that addresses every improvement point.

RULES
• Output the complete revised outline as a single JSON object — not a diff, not partial.
• Preserve the same JSON structure: {"meta": {...}, "outline": [...]}.
• Each outline segment must contain these fields:
    scene_id        — 1-indexed integer, must be sequential
    title           — concise display title
    visual_plan     — continuous English prose describing concrete visual actions (~30-50 lines)
    talking_points  — ordered list of specific, actionable statements
    duration_seconds — integer seconds
    narration_hint  — tone/pacing note for the narrator
• visual_plan must be a flowing English narrative of visual actions, not bullet points.
• talking_points must be a list of specific statements, not vague instructions.
• The sum of all duration_seconds must equal meta.total_duration_seconds.
• Do not add comments or markdown — raw JSON only.

Output the improved outline JSON and nothing else.
""".strip()


# ── Prompt builders ───────────────────────────────────────────────────────────

def build_outline_critic_prompt(
        meta: dict[str, Any],
        segments: list[dict[str, Any]],
        iteration: int,
        ) -> str:
    payload = json.dumps({"meta": meta, "outline": segments}, indent=2)
    return (
        f"## ITERATION {iteration}\n\n"
        f"### FULL OUTLINE\n```json\n{payload}\n```\n\n"
        "Review this outline against all seven dimensions in your instructions. "
        "Return the JSON critique object."
    )


def build_outline_refactor_prompt(
        meta: dict[str, Any],
        segments: list[dict[str, Any]],
        critique: OutlineCritiqueResult,
        iteration: int,
        ) -> str:
    payload = json.dumps({"meta": meta, "outline": segments}, indent=2)
    improvements_block = "\n".join(
        f"  {i + 1}. {imp}" for i, imp in enumerate(critique.improvements)
        )
    return (
        f"## REFACTOR REQUEST — ITERATION {iteration}\n\n"
        f"### FULL OUTLINE\n```json\n{payload}\n```\n\n"
        f"### CRITIC FEEDBACK (score {critique.score}/10)\n{critique.critique}\n\n"
        f"### REQUIRED IMPROVEMENTS\n{improvements_block}\n\n"
        "Produce the complete revised outline as a single JSON object. No markdown."
    )
