"""
api/endpoints/generate.py
--------------------------
FastAPI router for the video outline pipeline.

Endpoints
---------
POST /generate                           Start the pipeline; returns session_id.
POST /resume/{session_id}                Resume pipeline from last completed stage.
GET  /status/{session_id}                Full LangGraph checkpoint snapshot.
GET  /stages/{session_id}                Per-stage status, timing, and summaries.
GET  /stages/{session_id}/{stage}        Full output for one stage.
GET  /outputs/{session_id}/outline       Convenience: outline output.
GET  /outputs/{session_id}/scenes        Convenience: scene visual plans.
GET  /scenes/{session_id}/progress       Per-scene progress during visual planning.
GET  /sessions                           List all previously run sessions.
GET  /sessions/{session_id}              Detail for one session.
GET  /artifacts/{session_id}             List all artifacts for a session.
GET  /artifact/{session_id}/{atype}      Content of one artifact.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.schemas.request import GenerateRequest
from app.api.schemas.response import GenerateResponse
from app.core.artifact_store import ArtifactStore, SessionIndex
from app.core.config import settings
from app.core.context import request_logger_var
from app.core.logger import RequestLogger, StructuredLogger
from app.core.stage_tracker import NODE_TO_STAGE, StageTracker
from app.graph.workflow import pipeline


router = APIRouter()
logger = StructuredLogger.get_logger(__name__)

_tasks: dict[str, asyncio.Task] = {}
_task_errors: dict[str, str] = {}

# approach value → LangGraph outline node name (used for resume injection)
_APPROACH_TO_OUTLINE_NODE: dict[str, str] = {
    "Classic Linear Narrative": "classic_linear_narrative",
    "Conceptual Zoom": "conceptual_zoom",
    "Problem-Solution Arc": "problem_solution_arc",
    }


# ── Serialization helper ──────────────────────────────────────────────────────

def _make_serializable(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return _make_serializable(obj.model_dump())
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serializable(item) for item in obj]
    return obj


# ── Background pipeline runner ────────────────────────────────────────────────

async def _run_pipeline(
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

    # Pre-mark any stages that were already completed before this run (resume)
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
        async for chunk in pipeline.astream(
                initial_state, config=config, stream_mode="updates",
                ):
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

                # Save stage artifacts
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
                        "metadata": _make_serializable(updates_dict.get("metadata")),
                        "video_outline": _make_serializable(updates_dict.get("video_outline", [])),
                        },
                        )
                    total_scenes = updates_dict.get("total_scenes", 0)
                    SessionIndex.upsert(
                        session_id,
                        pipeline_status="running",
                        completed_stages=completed_stages,
                        total_scenes=total_scenes,
                        )

                if stage_name and stage_name not in completed_stages:
                    completed_stages.append(stage_name)
                    SessionIndex.upsert(
                        session_id,
                        pipeline_status="running",
                        completed_stages=completed_stages,
                        )

        final_state = await pipeline.aget_state(config)
        final_values = (
            dict(final_state.values)
            if final_state and final_state.values
            else {}
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
        SessionIndex.upsert(
            session_id,
            pipeline_status="failed",
            completed_stages=completed_stages,
            )
        logger.error(
            "Pipeline raised unhandled exception",
            extra={"session_id": session_id, "error": str(exc)},
            )
        if rl is not None:
            rl.error(exc=exc, context="_run_pipeline")
            rl.summary(status="failed", error=str(exc))


# ── Stage inference (legacy) ──────────────────────────────────────────────────

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


# ── Endpoints: pipeline control ───────────────────────────────────────────────

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
        _run_pipeline(
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

    # Determine what we have and what needs to run
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
        # Resume from visual_planning: inject state after map_outline_to_visual_plan
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
        # Resume from map_outline: inject state after outline node
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
        # Resume from generate_outline: inject state after validate_input
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

    # Clear any prior task error for this session
    _task_errors.pop(session_id, None)

    _tasks[session_id] = asyncio.create_task(
        _run_pipeline(
            session_id,
            None,  # None → use injected checkpoint
            approach=approach,
            requirement=requirement,
            pre_completed_stages=pre_completed,
            ),
        )

    logger.info(
        "Pipeline resumed",
        extra={"session_id": session_id, "resume_from": resume_from},
        )

    return {
        "session_id": session_id,
        "resumed_from": resume_from,
        "pre_completed_stages": pre_completed,
        "status": "resuming",
        }


# ── Endpoints: status ─────────────────────────────────────────────────────────

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
        "video_outline": _make_serializable(values.get("video_outline", [])),
        "scene_visual_plans": _make_serializable(values.get("scene_visual_plans", [])),
        "total_scenes": values.get("total_scenes", 0),
        "error": values.get("error"),
        }


@router.get("/stages/{session_id}")
async def get_stages(session_id: str) -> dict:
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
        _LABELS = {
            "validate_input": "Validate & Refine Input",
            "generate_outline": "Generate Outline",
            "map_outline": "Map Outline to Scenes",
            "visual_planning": "Generate Visual Plans",
            }
        stages = [
            {
                "stage": k,
                "label": _LABELS[k],
                "status": "completed" if k in completed
                else ("skipped" if p_status in ("failed", "completed") else "pending"),
                "node_name": "",
                "duration_ms": None,
                "output_summary": {},
                "error": None,
                }
            for k in ["validate_input", "generate_outline", "map_outline", "visual_planning"]
            ]
        return {"session_id": session_id, "pipeline_status": p_status, "stages": stages, "error": None}

    tracker = StageTracker.for_session(session_id)
    task = _tasks.get(session_id)

    pipeline_status = tracker.pipeline_status
    if task is not None and task.done() and pipeline_status == "running":
        exc = task.exception() if not task.cancelled() else None
        pipeline_status = "failed" if exc else tracker.pipeline_status

    return {
        "session_id": session_id,
        "pipeline_status": pipeline_status,
        "stages": tracker.get_stages(),
        "error": _task_errors.get(session_id),
        }


@router.get("/stages/{session_id}/{stage_name}")
async def get_stage_detail(session_id: str, stage_name: str) -> dict:
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

    return {
        "session_id": session_id,
        "stage": stage_name,
        "label": stage_info["label"],
        "status": stage_info["status"],
        "node_name": stage_info["node_name"],
        "duration_ms": stage_info["duration_ms"],
        "output_summary": stage_info["output_summary"],
        "output": output,
        "error": stage_info["error"],
        }


@router.get("/outputs/{session_id}/outline")
async def get_outline_output(session_id: str) -> dict:
    """Convenience endpoint: returns the generated outline."""
    if session_id not in _tasks:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    tracker = StageTracker.for_session(session_id)
    output = tracker.get_stage_output("generate_outline")

    if output is not None:
        return {
            "session_id": session_id,
            "outline": output.get("outline"),
            "outline_type": output.get("outline_type"),
            "status": output.get("status"),
            }

    config = {"configurable": {"thread_id": session_id}}
    try:
        state = await pipeline.aget_state(config)
        if state and state.values:
            v = dict(state.values)
            return {
                "session_id": session_id,
                "outline": v.get("outline"),
                "outline_type": v.get("outline_type"),
                "status": v.get("status"),
                }
    except Exception:
        pass

    return {"session_id": session_id, "outline": None, "outline_type": None, "status": None}


@router.get("/outputs/{session_id}/scenes")
async def get_scenes_output(session_id: str) -> dict:
    """Convenience endpoint: returns scene visual plans."""
    if session_id not in _tasks:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    tracker = StageTracker.for_session(session_id)
    output = tracker.get_stage_output("visual_planning")

    if output is not None:
        return {
            "session_id": session_id,
            "scene_visual_plans": output.get("scene_visual_plans", []),
            "total_scenes": output.get("total_scenes", len(output.get("scene_visual_plans", []))),
            "status": output.get("status"),
            }

    config = {"configurable": {"thread_id": session_id}}
    try:
        state = await pipeline.aget_state(config)
        if state and state.values:
            v = dict(state.values)
            return {
                "session_id": session_id,
                "scene_visual_plans": _make_serializable(v.get("scene_visual_plans", [])),
                "total_scenes": v.get("total_scenes", 0),
                "status": v.get("status"),
                }
    except Exception:
        pass

    return {"session_id": session_id, "scene_visual_plans": [], "total_scenes": 0, "status": None}


@router.get("/scenes/{session_id}/progress")
async def get_scene_progress(session_id: str) -> dict:
    """Per-scene progress during the visual planning stage."""
    if session_id not in _tasks:
        # Allow reading scene progress from artifacts for completed sessions
        store = ArtifactStore(session_id)
        completed_indices = store.list_completed_scene_indices()
        if not completed_indices:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
        return {
            "session_id": session_id,
            "total": len(completed_indices),
            "completed": len(completed_indices),
            "failed": 0,
            "running_index": None,
            "scenes": [
                {"scene_index": i, "title": "", "status": "completed",
                    "duration_ms": None, "error": None,
                    }
                for i in completed_indices
                ],
            }

    tracker = StageTracker.for_session(session_id)
    progress = tracker.get_scene_progress()
    return {"session_id": session_id, **progress}


# ── Endpoints: sessions ───────────────────────────────────────────────────────

@router.get("/sessions")
async def list_sessions() -> dict:
    """List all previously run sessions from the global session index."""
    sessions = SessionIndex.list_all()
    return {"sessions": sessions, "total": len(sessions)}


@router.get("/sessions/{session_id}")
async def get_session_detail(session_id: str) -> dict:
    """Detail for one session including artifact inventory."""
    entry = SessionIndex.get(session_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    store = ArtifactStore(session_id)
    artifacts = store.list_artifacts()
    completed_scenes = store.list_completed_scene_indices()

    return {
        **entry,
        "artifacts": artifacts,
        "completed_scene_count": len(completed_scenes),
        "can_resume": (
                entry.get("pipeline_status") in ("failed", "running")
                and store.exists("refined_input")
        ),
        }


# ── Endpoints: artifacts ──────────────────────────────────────────────────────

@router.get("/artifacts/{session_id}")
async def list_artifacts(session_id: str) -> dict:
    """List all artifacts stored for a session."""
    store = ArtifactStore(session_id)
    return {
        "session_id": session_id,
        "artifacts": store.list_artifacts(),
        }


@router.get("/artifact/{session_id}/{artifact_type}")
async def get_artifact(session_id: str, artifact_type: str) -> dict:
    """Return the content of a named artifact.

    Use ``scene_NNN`` (e.g. ``scene_003``) for per-scene visual plans.
    """
    store = ArtifactStore(session_id)

    if artifact_type.startswith("scene_"):
        try:
            idx = int(artifact_type.split("_")[1])
        except (IndexError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid scene artifact name.")
        data = store.load_scene(idx)
    else:
        data = store.load(artifact_type)

    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Artifact '{artifact_type}' not found for session '{session_id}'.",
            )

    return {"session_id": session_id, "artifact_type": artifact_type, "data": data}
