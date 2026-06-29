"""
workflow.py
-----------
LangGraph StateGraph wiring for the video outline generation pipeline.

Flow
----
    START
      → validate_input
      → [route_by_approach]
          → conceptual_zoom       ──┐
          → problem_solution_arc  ──┤── [route_after_outline]
          → classic_linear_narrative ─┘       → map_outline_to_visual_plan
                                              → visual_planning
                                              → [route_after_visual_planning]
                                                  → manim_code_generation
                                                  → scene_rendering
                                                  → [route_after_rendering]
                                                      → video_assembly
                                                      → END
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.edges import (
    NODE_CLASSIC_LINEAR_NARRATIVE,
    NODE_CONCEPTUAL_ZOOM,
    NODE_MANIM_CODE_GENERATION,
    NODE_MAP_OUTLINE,
    NODE_PROBLEM_SOLUTION_ARC,
    NODE_SCENE_RENDERING,
    NODE_VALIDATE_INPUT,
    NODE_VIDEO_ASSEMBLY,
    NODE_VISUAL_PLANNING,
    route_after_outline,
    route_after_rendering,
    route_after_visual_planning,
    route_by_approach,
    )
from app.graph.models.graph_state import GraphState
from app.graph.nodes import (
    classic_linear_narrative_node,
    conceptual_zoom_node,
    manim_code_generation_node,
    map_outline_to_visual_plan_node,
    problem_solution_arc_node,
    scene_rendering_node,
    validate_input,
    video_assembly_node,
    visual_planning_node,
    )


# ── Build graph ───────────────────────────────────────────────────────────────

graph = StateGraph(GraphState)

graph.add_node(NODE_VALIDATE_INPUT, validate_input)
graph.add_node(NODE_CONCEPTUAL_ZOOM, conceptual_zoom_node)
graph.add_node(NODE_PROBLEM_SOLUTION_ARC, problem_solution_arc_node)
graph.add_node(NODE_CLASSIC_LINEAR_NARRATIVE, classic_linear_narrative_node)
graph.add_node(NODE_MAP_OUTLINE, map_outline_to_visual_plan_node)
graph.add_node(NODE_VISUAL_PLANNING, visual_planning_node)
graph.add_node(NODE_MANIM_CODE_GENERATION, manim_code_generation_node)
graph.add_node(NODE_SCENE_RENDERING, scene_rendering_node)
graph.add_node(NODE_VIDEO_ASSEMBLY, video_assembly_node)

# Entry
graph.add_edge(START, NODE_VALIDATE_INPUT)

# Route to the correct outline generator (or END on validation failure)
graph.add_conditional_edges(
    NODE_VALIDATE_INPUT,
    route_by_approach,
    {
        NODE_CONCEPTUAL_ZOOM: NODE_CONCEPTUAL_ZOOM,
        NODE_PROBLEM_SOLUTION_ARC: NODE_PROBLEM_SOLUTION_ARC,
        NODE_CLASSIC_LINEAR_NARRATIVE: NODE_CLASSIC_LINEAR_NARRATIVE,
        END: END,
        },
    )

# All outline generators route to the transform node (or END on failure)
for outline_node in (
        NODE_CONCEPTUAL_ZOOM,
        NODE_PROBLEM_SOLUTION_ARC,
        NODE_CLASSIC_LINEAR_NARRATIVE,
        ):
    graph.add_conditional_edges(
        outline_node,
        route_after_outline,
        {
            NODE_MAP_OUTLINE: NODE_MAP_OUTLINE,
            END: END,
            },
        )

# Map outline → visual planning (fixed)
graph.add_edge(NODE_MAP_OUTLINE, NODE_VISUAL_PLANNING)

# Visual planning → code generation (conditional: skip if all plans failed)
graph.add_conditional_edges(
    NODE_VISUAL_PLANNING,
    route_after_visual_planning,
    {
        NODE_MANIM_CODE_GENERATION: NODE_MANIM_CODE_GENERATION,
        END: END,
        },
    )

# Code generation → rendering (fixed: always attempt rendering)
graph.add_edge(NODE_MANIM_CODE_GENERATION, NODE_SCENE_RENDERING)

# Rendering → video assembly (conditional: only if ≥1 clip ready)
graph.add_conditional_edges(
    NODE_SCENE_RENDERING,
    route_after_rendering,
    {
        NODE_VIDEO_ASSEMBLY: NODE_VIDEO_ASSEMBLY,
        END: END,
        },
    )

# Video assembly → done
graph.add_edge(NODE_VIDEO_ASSEMBLY, END)

# ── Compile ───────────────────────────────────────────────────────────────────

checkpointer = MemorySaver()
pipeline = graph.compile(checkpointer=checkpointer)
