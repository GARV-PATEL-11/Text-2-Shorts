"""
api/endpoints/generate.py
--------------------------
FastAPI router: POST /generate and GET /status/{session_id}

POST /generate  — starts the pipeline in a background task and returns the
                  session_id immediately so the client can poll for status.
GET  /status/{session_id} — reads the latest LangGraph checkpoint for the session.

A RequestLogger is created for every POST /generate call and stored in the
request_logger_var ContextVar.  asyncio.create_task() copies the current
context, so the background pipeline task automatically inherits the logger.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from app.api.schemas.request import GenerateRequest
from app.api.schemas.response import GenerateResponse
from app.core.config import settings
from app.core.context import request_logger_var
from app.core.logger import RequestLogger, StructuredLogger
from app.graph.workflow import pipeline


router = APIRouter()
logger = StructuredLogger.get_logger(__name__)

# In-process task + error registry (process-local; adequate for single-worker dev)
_tasks: dict[str, asyncio.Task] = {}
_task_errors: dict[str, str] = {}


# ── Background runner ─────────────────────────────────────────────────────────

async def _run_pipeline(session_id: str, initial_state: dict) -> None:
    rl = request_logger_var.get()
    config = {"configurable": {"thread_id": session_id}}

    if rl is not None:
        rl.pipeline_step("pipeline.ainvoke.start", {"session_id": session_id})

    try:
        result = await pipeline.ainvoke(initial_state, config=config)
        values = result if isinstance(result, dict) else {}

        logger.info(
            "Pipeline completed",
            extra={
                "session_id": session_id,
                "status": values.get("status"),
                "outline_type": values.get("outline_type"),
                "total_scenes": values.get("total_scenes", 0),
                },
            )

        if rl is not None:
            rl.summary(
                status=values.get("status", "completed"),
                outline_type=values.get("outline_type"),
                total_scenes=values.get("total_scenes", 0),
                final_stage=values.get("status", "completed"),
                )

    except Exception as exc:
        _task_errors[session_id] = str(exc)
        logger.error(
            "Pipeline raised unhandled exception",
            extra={"session_id": session_id, "error": str(exc)},
            )
        if rl is not None:
            rl.error(exc=exc, context="_run_pipeline")
            rl.summary(status="failed", error=str(exc))


# ── Stage inference ────────────────────────────────────────────────────────────

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
    return "Completed"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/generate", response_model=GenerateResponse)
async def generate_video(body: GenerateRequest) -> GenerateResponse:
    rl = RequestLogger(
        session_id=body.session_id,
        endpoint="/generate",
        payload={
            "approach": str(body.approach),
            "requirement_preview": body.requirement[:300],
            "requirement_len": len(body.requirement),
            },
        config={
            "primary_model": settings.GEMINI_35_FLASH_MODEL,
            "fallback_model": settings.GEMINI_3_FLASH_MODEL,
            "refine_model": settings.GEMINI_25_FLASH_MODEL,
            },
        )
    tok = request_logger_var.set(rl)

    logger.info(
        "Generate request received",
        extra={
            "session_id": body.session_id,
            "approach": str(body.approach),
            "requirement_len": len(body.requirement),
            },
        )

    initial_state = {
        "session_id": body.session_id,
        "approach": body.approach,
        "requirement": body.requirement,
        }

    # create_task copies the current context, so the task inherits request_logger_var
    _tasks[body.session_id] = asyncio.create_task(
        _run_pipeline(body.session_id, initial_state),
        )

    rl.pipeline_step("task.queued", {"session_id": body.session_id})

    # Reset in the handler's context after the task inherits it
    request_logger_var.reset(tok)

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
