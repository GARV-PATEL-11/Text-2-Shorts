"""pipeline.py — Endpoints to start and resume the generation pipeline."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from app.api.pipeline_runner import _APPROACH_TO_OUTLINE_NODE, _task_errors, _tasks, run_pipeline
from app.api.schemas.request import GenerateRequest
from app.api.schemas.response import GenerateResponse
from app.core.artifact_store import ArtifactStore, SessionIndex
from app.core.config import settings
from app.core.context import request_logger_var
from app.core.logger import RequestLogger, StructuredLogger
from app.graph.workflow import pipeline


router = APIRouter()
logger = StructuredLogger.get_logger(__name__)


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

    approach_str = str(body.approach)
    SessionIndex.upsert(
        body.session_id,
        approach=approach_str,
        requirement_preview=body.requirement[:200],
        pipeline_status="running",
        completed_stages=[],
        )

    _tasks[body.session_id] = asyncio.create_task(
        run_pipeline(
            body.session_id,
            initial_state,
            approach=approach_str,
            requirement=body.requirement,
            ),
        )

    rl.pipeline_step("task.queued", {"session_id": body.session_id})
    request_logger_var.reset(tok)

    return GenerateResponse(
        session_id=body.session_id,
        workflow_id=body.session_id,
        approach=body.approach,
        status="queued",
        )


@router.post("/resume/{session_id}")
async def resume_pipeline(session_id: str) -> dict:
    """Resume the pipeline from the last successfully completed stage."""
    store = ArtifactStore(session_id)

    has_refined = store.exists("refined_input")
    has_outline = store.exists("outline")
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
        await pipeline.aupdate_state(config, state_dict, as_node="map_outline_to_visual_plan")
        resume_from = "visual_planning"
        pre_completed = ["validate_input", "generate_outline", "map_outline"]

    elif has_outline:
        outline_data = store.load("outline") or {}
        outline_node = _APPROACH_TO_OUTLINE_NODE.get(approach, "classic_linear_narrative")
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
        await pipeline.aupdate_state(config, state_dict, as_node=outline_node)
        resume_from = "map_outline"
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
        await pipeline.aupdate_state(config, state_dict, as_node="validate_input")
        resume_from = "generate_outline"
        pre_completed = ["validate_input"]

    _task_errors.pop(session_id, None)

    _tasks[session_id] = asyncio.create_task(
        run_pipeline(
            session_id,
            None,
            approach=approach,
            requirement=requirement,
            pre_completed_stages=pre_completed,
            ),
        )

    logger.info("Pipeline resumed", extra={"session_id": session_id, "resume_from": resume_from})

    return {
        "session_id": session_id,
        "resumed_from": resume_from,
        "pre_completed_stages": pre_completed,
        "status": "resuming",
        }
