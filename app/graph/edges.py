"""
edges.py
--------
Routing functions for the video outline generation graph.

Edge map
--------
    START
      → validate_input
      → [route_by_approach] ──► conceptual_zoom
                             ──► problem_solution_arc
                             ──► classic_linear_narrative
                             ──► END  (validation failure)
      → [route_after_outline] ─► map_outline_to_visual_plan
                              ─► END  (outline failure)
      → visual_planning
      → END
"""

from __future__ import annotations

from langgraph.graph import END

from app.graph.models.enums import NarrativeApproach
from app.graph.state import GraphState


# ── Node name constants ───────────────────────────────────────────────────────

NODE_VALIDATE_INPUT = "validate_input"
NODE_CONCEPTUAL_ZOOM = "conceptual_zoom"
NODE_PROBLEM_SOLUTION_ARC = "problem_solution_arc"
NODE_CLASSIC_LINEAR_NARRATIVE = "classic_linear_narrative"
NODE_MAP_OUTLINE = "map_outline_to_visual_plan"
NODE_VISUAL_PLANNING = "visual_planning"

_APPROACH_TO_NODE: dict[str, str] = {
    NarrativeApproach.CONCEPTUAL_ZOOM.value: NODE_CONCEPTUAL_ZOOM,
    NarrativeApproach.PROBLEM_SOLUTION_ARC.value: NODE_PROBLEM_SOLUTION_ARC,
    NarrativeApproach.CLASSIC_LINEAR_NARRATIVE.value: NODE_CLASSIC_LINEAR_NARRATIVE,
    }


# ── Routing functions ─────────────────────────────────────────────────────────

def route_by_approach(state: GraphState) -> str | END:
    """
    Conditional edge after validate_input.

    Routes to the correct outline generator based on the validated approach.
    Falls through to END if validation failed.
    """
    if state.status == "failed":
        return END
    return _APPROACH_TO_NODE.get(state.approach.value, END)


def route_after_outline(state: GraphState) -> str:
    """
    Conditional edge after any outline generator node.

    Routes to map_outline_to_visual_plan on success, END on failure.
    """
    if state.status == "failed" or not state.outline:
        return END
    return NODE_MAP_OUTLINE
