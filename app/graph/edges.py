"""
edges.py
--------
Routing functions for the video outline generation graph.

Edge map
--------
    START
      → validate_input
      → [route_by_approach]   ──► conceptual_zoom
                              ──► problem_solution_arc
                              ──► classic_linear_narrative
                              ──► END  (validation failure)
      → [route_after_outline] ──► map_outline_to_visual_plan
                              ──► END  (outline failure)
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
NODE_MANIM_CODE_GENERATION = "manim_code_generation"
NODE_SCENE_RENDERING = "scene_rendering"
NODE_VIDEO_ASSEMBLY = "video_assembly"

_APPROACH_TO_NODE: dict[str, str] = {
    NarrativeApproach.CONCEPTUAL_ZOOM.value: NODE_CONCEPTUAL_ZOOM,
    NarrativeApproach.PROBLEM_SOLUTION_ARC.value: NODE_PROBLEM_SOLUTION_ARC,
    NarrativeApproach.CLASSIC_LINEAR_NARRATIVE.value: NODE_CLASSIC_LINEAR_NARRATIVE,
    }


# ── Routing functions ─────────────────────────────────────────────────────────

def route_by_approach(state: GraphState) -> str:
    """Conditional edge after validate_input.

    Routes to the correct outline generator based on the validated approach.
    Falls through to END if validation failed.
    """
    from app.core.context import request_logger_var

    rl = request_logger_var.get()

    if state.status == "failed":
        if rl:
            rl.routing_decision(
                from_node=NODE_VALIDATE_INPUT,
                to_node="END",
                reason=f"validation failed: {state.error}",
                )
        return END

    # With use_enum_values=True on GraphState, state.approach is already a str
    target = _APPROACH_TO_NODE.get(state.approach, END)

    if rl:
        rl.routing_decision(
            from_node=NODE_VALIDATE_INPUT,
            to_node=str(target),
            reason=f"approach={state.approach}",
            )

    return target


def route_after_visual_planning(state: GraphState) -> str:
    """Conditional edge after visual_planning.

    Routes to manim_code_generation if any scene plan succeeded, else END.
    """
    from app.core.context import request_logger_var

    rl = request_logger_var.get()
    any_ready = any(
        not p.error for p in (state.scene_visual_plans or []),
        )
    failed = state.status == "failed" or not any_ready
    target = END if failed else NODE_MANIM_CODE_GENERATION

    if rl:
        rl.routing_decision(
            from_node=NODE_VISUAL_PLANNING,
            to_node=str(target),
            reason="failed" if failed else "visual_plans_ready",
            )

    return target


def route_after_rendering(state: GraphState) -> str:
    """Conditional edge after scene_rendering.

    Routes to video_assembly if at least one scene is READY, else END.
    """
    from app.core.context import request_logger_var

    rl = request_logger_var.get()
    any_ready = any(r.status == "READY" for r in (state.scene_render_results or []))
    target = NODE_VIDEO_ASSEMBLY if any_ready else END

    if rl:
        rl.routing_decision(
            from_node=NODE_SCENE_RENDERING,
            to_node=str(target),
            reason="clips_ready" if any_ready else "all_failed",
            )

    return target


def route_after_outline(state: GraphState) -> str:
    """Conditional edge after any outline generator node.

    Routes to map_outline_to_visual_plan on success, END on failure.
    """
    from app.core.context import request_logger_var

    rl = request_logger_var.get()
    failed = state.status == "failed" or not state.outline
    target = END if failed else NODE_MAP_OUTLINE

    if rl:
        rl.routing_decision(
            from_node=state.outline_type or "outline_node",
            to_node=str(target),
            reason="failed" if failed else "outline_ready",
            )

    return target
