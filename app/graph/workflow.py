"""
workflow.py
-----------
LangGraph StateGraph wiring for the video outline generation pipeline.

Flow
----
    START
      → validate_input
      → [route_by_approach]
          → generate_outline ── [route_after_outline]
                                    → map_outline_to_visual_plan
                                    → visual_planning
                                    → [route_after_visual_planning]
                                        → manim_code_generation
                                        → scene_rendering
                                        → [route_after_rendering]
                                            → video_assembly
                                            → END
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph


if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

from app.graph.edges import (
    NODE_GENERATE_OUTLINE,
    NODE_MANIM_CODE_GENERATION,
    NODE_MAP_OUTLINE,
    NODE_SCENE_RENDERING,
    NODE_VALIDATE_INPUT,
    NODE_VIDEO_ASSEMBLY,
    NODE_VISUAL_PLANNING,
    route_after_map_outline,
    route_after_outline,
    route_after_rendering,
    route_after_visual_planning,
    route_by_approach,
    )
from app.graph.models.graph_state import GraphState
from app.graph.nodes import (
    generate_outline_node,
    manim_code_generation_node,
    map_outline_to_visual_plan_node,
    scene_rendering_node,
    validate_input,
    video_assembly_node,
    visual_planning_node,
    )


# ── Build graph ───────────────────────────────────────────────────────────────

graph = StateGraph(GraphState)

graph.add_node(NODE_VALIDATE_INPUT, validate_input)
graph.add_node(NODE_GENERATE_OUTLINE, generate_outline_node)
graph.add_node(NODE_MAP_OUTLINE, map_outline_to_visual_plan_node)
graph.add_node(NODE_VISUAL_PLANNING, visual_planning_node)
graph.add_node(NODE_MANIM_CODE_GENERATION, manim_code_generation_node)
graph.add_node(NODE_SCENE_RENDERING, scene_rendering_node)
graph.add_node(NODE_VIDEO_ASSEMBLY, video_assembly_node)

# Entry
graph.add_edge(START, NODE_VALIDATE_INPUT)

# Route to outline generator (or END on validation failure)
graph.add_conditional_edges(
    NODE_VALIDATE_INPUT,
    route_by_approach,
    {
        NODE_GENERATE_OUTLINE: NODE_GENERATE_OUTLINE,
        END: END,
        },
    )

# Outline → map to scenes (or END on failure)
graph.add_conditional_edges(
    NODE_GENERATE_OUTLINE,
    route_after_outline,
    {
        NODE_MAP_OUTLINE: NODE_MAP_OUTLINE,
        END: END,
        },
    )

# Map outline → visual planning (conditional: END if outline had 0 scenes)
graph.add_conditional_edges(
    NODE_MAP_OUTLINE,
    route_after_map_outline,
    {
        NODE_VISUAL_PLANNING: NODE_VISUAL_PLANNING,
        END: END,
        },
    )

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

# Checkpoints are persisted to SQLite so pipeline state survives server restarts.
_DB_PATH = Path(__file__).parent.parent.parent / "artifacts" / "checkpoints.db"
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Compiled pipeline — set by init_pipeline() during FastAPI lifespan startup.
# All runtime code accesses this via `app.graph.workflow.pipeline`.
pipeline: CompiledStateGraph | None = None
_db_conn: aiosqlite.Connection | None = None


async def init_pipeline() -> None:
    """Open the SQLite checkpoint database and compile the LangGraph pipeline.

    Called once during FastAPI lifespan startup. Subsequent requests read the
    module-level ``pipeline`` attribute which is set here.
    """
    global pipeline, _db_conn
    _db_conn = await aiosqlite.connect(str(_DB_PATH))
    saver = AsyncSqliteSaver(_db_conn)
    await saver.setup()
    pipeline = graph.compile(checkpointer=saver)


async def close_pipeline() -> None:
    """Close the SQLite connection on server shutdown."""
    global _db_conn
    if _db_conn is not None:
        await _db_conn.close()
        _db_conn = None
