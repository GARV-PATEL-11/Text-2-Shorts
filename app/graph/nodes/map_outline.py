"""map_outline.py — Node: transform outline dict into structured scene list."""
from __future__ import annotations

from typing import Any

from app.core.context import request_logger_var
from app.core.logger import log_call, StructuredLogger
from app.graph.models.base_models import BaseVideoMeta
from app.graph.models.graph_state import GraphState
from app.graph.models.visual_planning_state import SceneOutline, VisualDSLInputState


logger = StructuredLogger.get_logger(__name__)


@log_call(stage="util:map_outline_to_visual_plan")
def map_outline_to_visual_plan(state: GraphState) -> VisualDSLInputState:
    """Pure data transform: outline dict → typed VisualDSLInputState."""
    rl = request_logger_var.get()
    raw_outline: dict[str, Any] = state.outline or {}
    raw_meta: dict[str, Any] = raw_outline.get("meta", {})
    segments: list[dict[str, Any]] = raw_outline.get("outline", [])

    metadata = BaseVideoMeta(
        title=raw_meta.get("title", ""),
        topic=raw_meta.get("topic", ""),
        total_duration_seconds=raw_meta.get("total_duration_seconds", 0),
        pace=raw_meta.get("pace", "medium"),
        target_wpm=raw_meta.get("target_wpm", 140),
        approach_name=raw_meta.get("approach_name", ""),
        approach_style=raw_meta.get("approach_style", ""),
        )

    video_outline: list[SceneOutline] = [
        SceneOutline(
            scene_index=seg.get("scene_id", i + 1) - 1,
            title=seg.get("title", ""),
            description="\n".join(filter(None, [
                seg.get("visual_plan", ""),
                *seg.get("talking_points", []),
                ],
                ),
                ),
            duration_hint_seconds=seg.get("duration_seconds", 30),
            narration_text=seg.get("narration_hint"),
            )
        for i, seg in enumerate(segments)
        ]

    if rl is not None:
        rl.pipeline_step("outline.mapped", {
            "session_id": state.session_id,
            "scene_count": len(video_outline),
            "title": metadata.title,
            "total_duration_s": metadata.total_duration_seconds,
            },
            )

    logger.info(
        "Outline mapped to VisualDSLInputState",
        extra={"session_id": state.session_id, "scene_count": len(video_outline)},
        )

    return VisualDSLInputState(
        session_id=state.session_id,
        workflow_id=state.workflow_id,
        total_scenes=len(video_outline),
        metadata=metadata,
        video_outline=video_outline,
        )


@log_call(stage="node:map_outline_to_visual_plan")
def map_outline_to_visual_plan_node(state: GraphState) -> dict:
    """LangGraph node wrapper for map_outline_to_visual_plan."""
    # Guard: empty outline → fail fast before Pydantic validation runs
    raw_outline = state.outline or {}
    segments = raw_outline.get("outline", [])
    if not segments:
        logger.warning(
            "Outline produced zero scenes — aborting pipeline",
            extra={"session_id": state.session_id},
            )
        return {
            "total_scenes": 0,
            "video_outline": [],
            "status": "failed",
            "error": "Outline contained no scenes; cannot proceed to visual planning",
            }

    result = map_outline_to_visual_plan(state)
    return {
        "total_scenes": result.total_scenes,
        "metadata": result.metadata,
        "video_outline": result.video_outline,
        }
