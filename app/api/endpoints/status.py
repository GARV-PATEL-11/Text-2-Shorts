"""status.py — Endpoints for pipeline and stage status."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.pipeline_runner import _task_errors, _tasks, make_serializable
from app.api.schemas.intermediate import StageRecordSchema
from app.api.schemas.response import StageDetailResponse, StagesResponse, StatusResponse
from app.core.artifact_store import SessionIndex
from app.core.stage_tracker import StageTracker
from app.graph.workflow import pipeline


router = APIRouter()

_STAGE_LABELS = {
    "validate_input": "Validate & Refine Input",
    "generate_outline": "Generate Outline",
    "map_outline": "Map Outline to Scenes",
    "visual_planning": "Generate Visual Plans",
    "manim_code_generation": "Generate Manim Code",
    "scene_rendering": "Render Scenes",
    "video_assembly": "Assemble Video",
    }
_ALL_STAGES = list(_STAGE_LABELS)


def _infer_stage(values: dict) -> str:
    status = values.get("status", "pending")
    if status == "failed":
        return "Failed"
    if not values.get("outline"):
        return "Generating Outline" if status == "ready" else "Queued"
    if not values.get("video_outline"):
        return "Mapping Outline"
    if not values.get("scene_visual_plans"):
        return "Generating Visual Plan"
    if not values.get("scene_manim_codes"):
        return "Generating Manim Code"
    if not values.get("scene_render_results"):
        return "Rendering Scenes"
    if not values.get("final_video_path"):
        return "Assembling Video"
    return "Completed"


@router.get("/status/{session_id}", response_model=StatusResponse)
async def get_status(session_id: str) -> StatusResponse:
    if session_id not in _tasks:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    config = {"configurable": {"thread_id": session_id}}
    try:
        state = await pipeline.aget_state(config)
    except Exception:
        state = None

    if not state or not state.values:
        err = _task_errors.get(session_id)
        return StatusResponse(
            session_id=session_id,
            workflow_id=session_id,
            stage="Failed" if err else "Queued",
            status="failed" if err else "queued",
            error=err,
            )

    values = state.values if isinstance(state.values, dict) else dict(state.values)

    ext_err = _task_errors.get(session_id)
    if ext_err and not values.get("error"):
        values["error"] = ext_err
        values["status"] = "failed"

    return StatusResponse(
        session_id=session_id,
        workflow_id=values.get("workflow_id", session_id),
        stage=_infer_stage(values),
        status=values.get("status", "pending"),
        outline_type=values.get("outline_type"),
        outline=values.get("outline"),
        video_outline=make_serializable(values.get("video_outline", [])),
        scene_visual_plans=make_serializable(values.get("scene_visual_plans", [])),
        total_scenes=values.get("total_scenes", 0),
        error=values.get("error"),
        )


@router.get("/stages/{session_id}", response_model=StagesResponse)
async def get_stages(session_id: str) -> StagesResponse:
    """Per-stage status with timing and output summaries.

    Falls back to the session index for sessions no longer in the in-memory
    task registry (e.g. after a server restart).
    """
    if session_id not in _tasks:
        entry = SessionIndex.get(session_id)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
        completed = set(entry.get("completed_stages", []))
        p_status = entry.get("pipeline_status", "unknown")
        stages = [
            StageRecordSchema(
                stage=k,
                label=_STAGE_LABELS[k],
                status="completed" if k in completed
                else ("skipped" if p_status in ("failed", "completed") else "pending"),
                node_name="",
                )
            for k in _ALL_STAGES
            ]
        return StagesResponse(session_id=session_id, pipeline_status=p_status, stages=stages)

    tracker = StageTracker.for_session(session_id)
    task = _tasks.get(session_id)

    pipeline_status = tracker.pipeline_status
    if task is not None and task.done() and pipeline_status == "running":
        exc = task.exception() if not task.cancelled() else None
        pipeline_status = "failed" if exc else tracker.pipeline_status

    stages = [StageRecordSchema(**s) for s in tracker.get_stages()]
    return StagesResponse(
        session_id=session_id,
        pipeline_status=pipeline_status,
        stages=stages,
        error=_task_errors.get(session_id),
        )


@router.get("/stages/{session_id}/{stage_name}", response_model=StageDetailResponse)
async def get_stage_detail(session_id: str, stage_name: str) -> StageDetailResponse:
    """Full output for one pipeline stage."""
    if session_id not in _tasks:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    tracker = StageTracker.for_session(session_id)
    stages_by_name = {s["stage"]: s for s in tracker.get_stages()}
    stage_info = stages_by_name.get(stage_name)

    if stage_info is None:
        raise HTTPException(
            status_code=404,
            detail=f"Stage '{stage_name}' not found. Valid stages: {list(stages_by_name)}",
            )

    output = tracker.get_stage_output(stage_name)

    return StageDetailResponse(
        session_id=session_id,
        stage=stage_name,
        label=stage_info["label"],
        status=stage_info["status"],
        node_name=stage_info["node_name"],
        duration_ms=stage_info["duration_ms"],
        output_summary=stage_info["output_summary"],
        output=output,
        error=stage_info["error"],
        )
