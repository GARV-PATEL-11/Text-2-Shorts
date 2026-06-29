"""pipeline_runner.py — Shared pipeline task state and background runner."""
from __future__ import annotations

import asyncio
from typing import Any

from app.core.artifact_store import ArtifactStore, SessionIndex
from app.core.context import request_logger_var
from app.core.logger import StructuredLogger
from app.core.stage_tracker import NODE_TO_STAGE, StageTracker
from app.graph.workflow import pipeline


logger = StructuredLogger.get_logger(__name__)

# Module-level task registry shared across all endpoint modules
_tasks: dict[str, asyncio.Task] = {}
_task_errors: dict[str, str] = {}

_APPROACH_TO_OUTLINE_NODE: dict[str, str] = {
    "Classic Linear Narrative": "classic_linear_narrative",
    "Conceptual Zoom": "conceptual_zoom",
    "Problem-Solution Arc": "problem_solution_arc",
    }


def make_serializable(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return make_serializable(obj.model_dump())
    if isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [make_serializable(item) for item in obj]
    return obj


async def run_pipeline(
        session_id: str,
        initial_state: dict | None,
        *,
        approach: str = "",
        requirement: str = "",
        pre_completed_stages: list[str] | None = None,
        ) -> None:
    """Stream the LangGraph pipeline, saving artifacts and updating the session index."""
    rl = request_logger_var.get()
    config = {"configurable": {"thread_id": session_id}}
    tracker = StageTracker.for_session(session_id)
    store = ArtifactStore(session_id)

    if pre_completed_stages:
        for stage_name in pre_completed_stages:
            rec = tracker._stage_map.get(stage_name)
            if rec and rec.status == "pending":
                rec.status = "completed"

    tracker.mark_started()
    completed_stages: list[str] = list(pre_completed_stages or [])

    if rl is not None:
        rl.pipeline_step("pipeline.ainvoke.start", {"session_id": session_id})

    try:
        async for chunk in pipeline.astream(initial_state, config=config, stream_mode="updates"):
            if not isinstance(chunk, dict):
                continue
            for node_name, updates in chunk.items():
                if node_name.startswith("__") or node_name not in NODE_TO_STAGE:
                    continue
                updates_dict = (
                    updates.model_dump() if hasattr(updates, "model_dump")
                    else updates if isinstance(updates, dict)
                    else {}
                )
                tracker.complete_node(node_name, updates_dict)
                stage_name = NODE_TO_STAGE.get(node_name, "")

                if stage_name == "validate_input":
                    store.save("refined_input", {
                        "session_id": session_id,
                        "requirement": requirement,
                        "approach": approach,
                        "workflow_id": updates_dict.get("workflow_id"),
                        "system_prompt": updates_dict.get("system_prompt"),
                        "refined_requirement": updates_dict.get("refined_requirement"),
                        "status": updates_dict.get("status"),
                        },
                        )
                elif stage_name == "generate_outline":
                    store.save("outline", {
                        "outline": updates_dict.get("outline"),
                        "outline_type": updates_dict.get("outline_type"),
                        "status": updates_dict.get("status"),
                        },
                        )
                elif stage_name == "map_outline":
                    store.save("scene_map", {
                        "total_scenes": updates_dict.get("total_scenes"),
                        "metadata": make_serializable(updates_dict.get("metadata")),
                        "video_outline": make_serializable(updates_dict.get("video_outline", [])),
                        },
                        )
                    total_scenes = updates_dict.get("total_scenes", 0)
                    SessionIndex.upsert(
                        session_id,
                        pipeline_status="running",
                        completed_stages=completed_stages,
                        total_scenes=total_scenes,
                        )
                elif stage_name == "manim_code_generation":
                    codes = make_serializable(updates_dict.get("scene_manim_codes", []))
                    store.save("manim_codes", {"scene_manim_codes": codes, "status": updates_dict.get("status")})
                elif stage_name == "scene_rendering":
                    results = make_serializable(updates_dict.get("scene_render_results", []))
                    store.save("render_results",
                        {"scene_render_results": results, "status": updates_dict.get("status")},
                        )
                elif stage_name == "video_assembly":
                    store.save("video_stats", updates_dict.get("render_stats") or {})

                if stage_name and stage_name not in completed_stages:
                    completed_stages.append(stage_name)
                    SessionIndex.upsert(session_id, pipeline_status="running", completed_stages=completed_stages)

        final_state = await pipeline.aget_state(config)
        final_values = (
            dict(final_state.values) if final_state and final_state.values else {}
        )

        tracker.mark_complete()
        SessionIndex.upsert(
            session_id,
            pipeline_status="completed",
            completed_stages=completed_stages,
            total_scenes=final_values.get("total_scenes", 0),
            )

        logger.info(
            "Pipeline completed",
            extra={
                "session_id": session_id,
                "status": final_values.get("status"),
                "outline_type": final_values.get("outline_type"),
                "total_scenes": final_values.get("total_scenes", 0),
                },
            )

        if rl is not None:
            rl.summary(
                status=final_values.get("status", "completed"),
                outline_type=final_values.get("outline_type"),
                total_scenes=final_values.get("total_scenes", 0),
                final_stage=final_values.get("status", "completed"),
                )

    except Exception as exc:
        _task_errors[session_id] = str(exc)
        tracker.mark_failed(str(exc))
        SessionIndex.upsert(session_id, pipeline_status="failed", completed_stages=completed_stages)
        logger.error("Pipeline raised unhandled exception", extra={"session_id": session_id, "error": str(exc)})
        if rl is not None:
            rl.error(exc=exc, context="run_pipeline")
            rl.summary(status="failed", error=str(exc))
