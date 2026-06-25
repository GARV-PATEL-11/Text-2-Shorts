"""
api/endpoints/generate.py
--------------------------
FastAPI router: POST /generate and GET /status/{session_id}

POST /generate  — starts the pipeline in the background and returns immediately
                  with the session_id so the client can poll for status.
GET  /status/{session_id} — reads the latest LangGraph checkpoint for the session.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from app.api.schemas.request import GenerateRequest
from app.api.schemas.response import GenerateResponse
from app.graph.workflow import pipeline


router = APIRouter()

# In-process task + error registry (process-local, adequate for single-worker dev)
_tasks: dict[str, asyncio.Task] = {}
_task_errors: dict[str, str] = {}


# ── Background runner ─────────────────────────────────────────────────────────

async def _run_pipeline(session_id: str, initial_state: dict) -> None:
    config = {"configurable": {"thread_id": session_id}}
    try:
        await pipeline.ainvoke(initial_state, config=config)
    except Exception as exc:
        _task_errors[session_id] = str(exc)


# ── Stage inference ────────────────────────────────────────────────────────────

def _infer_stage(values: dict) -> str:
    status = values.get("status", "pending")
    if status == "failed":
        return "Failed"
    if not values.get("outline"):
        if status == "ready":
            return "Generating Outline"
        return "Queued"
    if not values.get("video_outline"):
        return "Mapping Outline"
    if not values.get("scene_visual_plans"):
        return "Generating Visual Plan"
    return "Completed"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/generate", response_model=GenerateResponse)
async def generate_video(body: GenerateRequest) -> GenerateResponse:
    initial_state = {
        "session_id": body.session_id,
        "approach": body.approach,
        "requirement": body.requirement,
        }
    _tasks[body.session_id] = asyncio.create_task(
        _run_pipeline(body.session_id, initial_state),
        )
    return GenerateResponse(
        session_id=body.session_id,
        workflow_id=body.session_id,
        approach=body.approach,
        status="queued",
        )


@router.get("/status/{session_id}")
async def get_status(session_id: str) -> dict:
    if session_id not in _tasks:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    config = {"configurable": {"thread_id": session_id}}
    try:
        state = await pipeline.aget_state(config)
    except Exception:
        state = None

    # No checkpoint yet (pipeline just started or failed before first node)
    if not state or not state.values:
        err = _task_errors.get(session_id)
        return {
            "session_id": session_id,
            "workflow_id": session_id,
            "stage": "Failed" if err else "Queued",
            "status": "failed" if err else "queued",
            "outline_type": None,
            "outline": None,
            "video_outline": [],
            "scene_visual_plans": [],
            "total_scenes": 0,
            "error": err,
            }

    values = state.values if isinstance(state.values, dict) else dict(state.values)

    # Merge any unhandled task-level error
    ext_err = _task_errors.get(session_id)
    if ext_err and not values.get("error"):
        values["error"] = ext_err
        values["status"] = "failed"

    return {
        "session_id": session_id,
        "workflow_id": values.get("workflow_id", session_id),
        "stage": _infer_stage(values),
        "status": values.get("status", "pending"),
        "outline_type": values.get("outline_type"),
        "outline": values.get("outline"),
        "video_outline": values.get("video_outline", []),
        "scene_visual_plans": values.get("scene_visual_plans", []),
        "total_scenes": values.get("total_scenes", 0),
        "error": values.get("error"),
        }
