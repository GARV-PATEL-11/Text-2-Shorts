"""outputs.py — Convenience endpoints for outline and scene visual plan outputs."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

import app.graph.workflow as _workflow
from app.api.pipeline_runner import _tasks, make_serializable
from app.api.schemas.response import OutlineOutputResponse, ScenesOutputResponse
from app.core.stage_tracker import StageTracker


router = APIRouter()


@router.get("/outputs/{session_id}/outline", response_model=OutlineOutputResponse)
async def get_outline_output(session_id: str) -> OutlineOutputResponse:
    """Convenience endpoint: returns the generated outline."""
    if session_id not in _tasks:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    tracker = StageTracker.for_session(session_id)
    output = tracker.get_stage_output("generate_outline")

    if output is not None:
        return OutlineOutputResponse(
            session_id=session_id,
            outline=output.get("outline"),
            outline_type=output.get("outline_type"),
            status=output.get("status"),
            )

    config = {"configurable": {"thread_id": session_id}}
    try:
        state = await _workflow.pipeline.aget_state(config)
        if state and state.values:
            v = dict(state.values)
            return OutlineOutputResponse(
                session_id=session_id,
                outline=v.get("outline"),
                outline_type=v.get("outline_type"),
                status=v.get("status"),
                )
    except Exception:
        pass

    return OutlineOutputResponse(session_id=session_id)


@router.get("/outputs/{session_id}/scenes", response_model=ScenesOutputResponse)
async def get_scenes_output(session_id: str) -> ScenesOutputResponse:
    """Convenience endpoint: returns scene visual plans."""
    if session_id not in _tasks:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    tracker = StageTracker.for_session(session_id)
    output = tracker.get_stage_output("visual_planning")

    if output is not None:
        return ScenesOutputResponse(
            session_id=session_id,
            scene_visual_plans=output.get("scene_visual_plans", []),
            total_scenes=output.get("total_scenes", len(output.get("scene_visual_plans", []))),
            status=output.get("status"),
            )

    config = {"configurable": {"thread_id": session_id}}
    try:
        state = await _workflow.pipeline.aget_state(config)
        if state and state.values:
            v = dict(state.values)
            return ScenesOutputResponse(
                session_id=session_id,
                scene_visual_plans=make_serializable(v.get("scene_visual_plans", [])),
                total_scenes=v.get("total_scenes", 0),
                status=v.get("status"),
                )
    except Exception:
        pass

    return ScenesOutputResponse(session_id=session_id)
