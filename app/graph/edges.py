"""
edges.py
--------
Routing functions for the video outline generation graph.

Edge map
--------
    START
      → validate_input
      → [route_by_approach]           ──► generate_outline
                                      ──► END  (validation failure)
      → [route_after_outline]         ──► outline_critique
                                      ──► END  (outline failed)
      → [route_after_outline_critique]──► visual_planning
                                      ──► END  (critique failed)
      → [route_after_visual_planning] ──► visual_plan_critique
                                      ──► END  (all plans failed)
      → [route_after_visual_plan_critique]
                                      ──► manim_code_generation
                                      ──► END  (all plans failed critique)
      → [route_after_code_generation] ──► dsl_critique
                                      (always proceeds)
      → [route_after_dsl_critique]    ──► scene_rendering
                                      ──► END  (all codes failed)
      → [route_after_rendering]       ──► video_assembly
                                      ──► END  (all renders failed)
      → END
"""

from __future__ import annotations

from langgraph.graph import END

from app.graph.state import GraphState


# ── Node name constants ───────────────────────────────────────────────────────

NODE_VALIDATE_INPUT = "validate_input"
NODE_GENERATE_OUTLINE = "generate_outline"
NODE_OUTLINE_CRITIQUE = "outline_critique"
NODE_VISUAL_PLANNING = "visual_planning"
NODE_VISUAL_PLAN_CRITIQUE = "visual_plan_critique"
NODE_MANIM_CODE_GENERATION = "manim_code_generation"
NODE_SCENE_RENDERING = "scene_rendering"
NODE_VIDEO_ASSEMBLY = "video_assembly"


# ── Routing functions ─────────────────────────────────────────────────────────

def route_by_approach(state: GraphState) -> str:
    """Conditional edge after validate_input.

    Routes to generate_outline on success, or END if validation failed.
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

    if rl:
        rl.routing_decision(
            from_node=NODE_VALIDATE_INPUT,
            to_node=NODE_GENERATE_OUTLINE,
            reason=f"approach={state.approach}",
            )

    return NODE_GENERATE_OUTLINE


def route_after_outline(state: GraphState) -> str:
    """Conditional edge after any outline generator node.

    Routes to outline_critique on success, END on failure.
    """
    from app.core.context import request_logger_var

    rl = request_logger_var.get()
    failed = state.status == "failed" or not state.outline
    target = END if failed else NODE_OUTLINE_CRITIQUE

    if rl:
        rl.routing_decision(
            from_node=state.outline_type or "outline_node",
            to_node=str(target),
            reason="failed" if failed else "outline_ready",
            )

    return target


def route_after_outline_critique(state: GraphState) -> str:
    """Conditional edge after outline_critique.

    Routes to visual_planning on success, END on failure.
    """
    from app.core.context import request_logger_var

    rl = request_logger_var.get()
    failed = state.status == "failed" or not state.outline
    target = END if failed else NODE_VISUAL_PLANNING

    if rl:
        rl.routing_decision(
            from_node=NODE_OUTLINE_CRITIQUE,
            to_node=str(target),
            reason="failed" if failed else "outline_refined",
            )

    return target


def route_after_visual_planning(state: GraphState) -> str:
    """Conditional edge after visual_planning.

    Routes to visual_plan_critique if any scene plan succeeded, else END.
    """
    from app.core.context import request_logger_var

    rl = request_logger_var.get()
    any_ready = any(not p.error for p in (state.scene_visual_plans or []))
    failed = state.status == "failed" or not any_ready
    target = END if failed else NODE_VISUAL_PLAN_CRITIQUE

    if rl:
        rl.routing_decision(
            from_node=NODE_VISUAL_PLANNING,
            to_node=str(target),
            reason="failed" if failed else "visual_plans_ready",
            )

    return target


def route_after_visual_plan_critique(state: GraphState) -> str:
    """Conditional edge after visual_plan_critique.

    Routes to manim_code_generation if any plan survived critique, else END.
    """
    from app.core.context import request_logger_var

    rl = request_logger_var.get()
    any_ready = any(not p.error for p in (state.scene_visual_plans or []))
    failed = state.status == "failed" or not any_ready
    target = END if failed else NODE_MANIM_CODE_GENERATION

    if rl:
        rl.routing_decision(
            from_node=NODE_VISUAL_PLAN_CRITIQUE,
            to_node=str(target),
            reason="failed" if failed else "plans_refined",
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
