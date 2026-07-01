"""pipeline.py — Endpoints to start and resume the generation pipeline."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

import app.graph.workflow as _workflow
from app.api.pipeline_runner import (_cleanup_task, _OUTLINE_NODE, _task_errors, _tasks, run_pipeline)
from app.api.schemas.request import GenerateRequest
from app.api.schemas.response import GenerateResponse, ResumeResponse
from app.core.config import settings
from app.core.context import request_logger_var
from app.core.id_service import IDService
from app.core.logger import RequestLogger, StructuredLogger
from app.storage.artifact_store import ArtifactStore, SessionIndex


router = APIRouter()
logger = StructuredLogger.get_logger(__name__)


@router.post("/generate", response_model=GenerateResponse)
async def generate_video(body: GenerateRequest) -> GenerateResponse:
    session_id = IDService.next_session_id()

    rl = RequestLogger(
        session_id=session_id,
        endpoint="/generate",
        payload={
            "approach": str(body.approach),
            "requirement_preview": body.requirement[:300],
            "requirement_len": len(body.requirement),
            },
        config={
            "gemini_model": settings.GEMINI_MODEL,
            "gemini_fallback_model": settings.GEMINI_FALLBACK_MODEL,
            },
        )
    tok = request_logger_var.set(rl)

    logger.info(
        "Generate request received",
        extra={
            "session_id": session_id,
            "approach": str(body.approach),
            "requirement_len": len(body.requirement),
            },
        )

    initial_state = {
        "session_id": session_id,
        "approach": body.approach,
        "requirement": body.requirement,
        }

    approach_str = str(body.approach)
    SessionIndex.upsert(
        session_id,
        approach=approach_str,
        requirement_preview=body.requirement[:200],
        pipeline_status="running",
        completed_stages=[],
        )

    task = asyncio.create_task(
        run_pipeline(
            session_id,
            initial_state,
            approach=approach_str,
            requirement=body.requirement,
            ),
        )
    task.add_done_callback(lambda _: _cleanup_task(session_id))
    _tasks[session_id] = task

    rl.pipeline_step("task.queued", {"session_id": session_id})
    request_logger_var.reset(tok)

    return GenerateResponse(
        session_id=session_id,
        workflow_id=session_id,
        approach=body.approach,
        status="queued",
        )


@router.post("/resume/{session_id}", response_model=ResumeResponse)
async def resume_pipeline(session_id: str) -> ResumeResponse:
    """Resume the pipeline from the last successfully completed stage."""
    store = ArtifactStore(session_id)

    has_refined = store.exists("refined_input")
    has_outline = store.exists("outline")
    has_outline_critique = store.exists("outline_critique")
    has_scene_map = store.exists("scene_map")

    if not has_refined:
        raise HTTPException(
            status_code=400,
            detail="No artifacts found for this session. Start a new generation instead.",
            )

    refined = store.load("refined_input") or {}
    approach = refined.get("approach", "Classic Linear Narrative")
    requirement = refined.get("requirement", "")

    config = {"configurable": {"thread_id": session_id}}

    if has_scene_map:
        scene_map = store.load("scene_map") or {}
        outline_data = store.load("outline") or {}
        state_dict = {
            "session_id": session_id,
            "approach": approach,
            "requirement": requirement,
            "workflow_id": refined.get("workflow_id", session_id),
            "system_prompt": refined.get("system_prompt"),
            "refined_requirement": refined.get("refined_requirement", requirement),
            "outline": outline_data.get("outline"),
            "outline_type": outline_data.get("outline_type"),
            "total_scenes": scene_map.get("total_scenes", 0),
            "metadata": scene_map.get("metadata"),
            "video_outline": scene_map.get("video_outline", []),
            "status": "ready",
            }
        await _workflow.pipeline.aupdate_state(config, state_dict, as_node="visual_planning")
        resume_from = "visual_plan_critique"
        pre_completed = ["validate_input", "generate_outline", "outline_critique", "visual_planning"]

    elif has_outline_critique:
        outline_data = store.load("outline") or {}
        state_dict = {
            "session_id": session_id,
            "approach": approach,
            "requirement": requirement,
            "workflow_id": refined.get("workflow_id", session_id),
            "system_prompt": refined.get("system_prompt"),
            "refined_requirement": refined.get("refined_requirement", requirement),
            "outline": outline_data.get("outline"),
            "outline_type": outline_data.get("outline_type"),
            "status": "ready",
            }
        await _workflow.pipeline.aupdate_state(config, state_dict, as_node="outline_critique")
        resume_from = "visual_planning"
        pre_completed = ["validate_input", "generate_outline", "outline_critique"]

    elif has_outline:
        outline_data = store.load("outline") or {}
        state_dict = {
            "session_id": session_id,
            "approach": approach,
            "requirement": requirement,
            "workflow_id": refined.get("workflow_id", session_id),
            "system_prompt": refined.get("system_prompt"),
            "refined_requirement": refined.get("refined_requirement", requirement),
            "outline": outline_data.get("outline"),
            "outline_type": outline_data.get("outline_type"),
            "status": "ready",
            }
        await _workflow.pipeline.aupdate_state(config, state_dict, as_node=_OUTLINE_NODE)
        resume_from = "outline_critique"
        pre_completed = ["validate_input", "generate_outline"]

    else:
        state_dict = {
            "session_id": session_id,
            "approach": approach,
            "requirement": requirement,
            "workflow_id": refined.get("workflow_id", session_id),
            "system_prompt": refined.get("system_prompt"),
            "refined_requirement": refined.get("refined_requirement", requirement),
            "status": "ready",
            }
        await _workflow.pipeline.aupdate_state(config, state_dict, as_node="validate_input")
        resume_from = "generate_outline"
        pre_completed = ["validate_input"]

    _task_errors.pop(session_id, None)

    resume_task = asyncio.create_task(
        run_pipeline(
            session_id,
            None,
            approach=approach,
            requirement=requirement,
            pre_completed_stages=pre_completed,
            ),
        )
    resume_task.add_done_callback(lambda _: _cleanup_task(session_id))
    _tasks[session_id] = resume_task

    logger.info("Pipeline resumed", extra={"session_id": session_id, "resume_from": resume_from})

    return ResumeResponse(
        session_id=session_id,
        resumed_from=resume_from,
        pre_completed_stages=pre_completed,
        status="resuming",
        )
