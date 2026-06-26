"""utils.py — Shared helpers for the video outline pipeline."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.core.context import node_name_var, request_logger_var, session_id_var, workflow_id_var
from app.core.logger import log_call, StructuredLogger
from app.graph.models.base_models import BaseVideoMeta
from app.graph.prompts.script_gen_prompt import REQ_MODIFIER_SYSTEM
from app.graph.retry import ainvoke_structured_with_fallback
from app.graph.state import (
    GraphState,
    OutlineOutputState,
    SceneOutline,
    SceneVisualPlan,
    VisualDSLInputState,
    )
from app.services.factory import get_client, LLMProvider


logger = StructuredLogger.get_logger(__name__)

_LOGS_DIR = "logs"

# Keys the LLM is instructed to produce for explicit canvas hand-off.
_HANDOFF_KEYS: tuple[str, ...] = (
    "next_scene_context",
    "ending_state",
    "canvas_state",
    "final_state",
    )


# ── Log / artifact writer ─────────────────────────────────────────────────────

def save_output_to_log(filename: str, payload: dict) -> None:
    """Write *payload* as pretty-printed JSON to logs/<filename>.

    Also records the file write in the active per-request log.
    """
    os.makedirs(_LOGS_DIR, exist_ok=True)
    path = os.path.join(_LOGS_DIR, filename)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        size = os.path.getsize(path)
        logger.info("Artifact saved", extra={"path": path, "size_bytes": size})

        rl = request_logger_var.get()
        if rl is not None:
            content_type = filename.split("_")[0] if "_" in filename else filename
            rl.file_written(path=path, size_bytes=size, content_type=content_type)

    except Exception as exc:
        logger.warning("Failed to save artifact", extra={"path": path, "error": str(exc)})


# ── Scene context extraction ──────────────────────────────────────────────────

def extract_next_scene_context(plan: SceneVisualPlan) -> dict[str, Any]:
    """Distil a compact context snapshot from a completed SceneVisualPlan.

    Injected as PRIOR_SCENES_CONTEXT into the next scene's Visual Director
    prompt so the model knows the exact Manim canvas state.
    """
    base: dict[str, Any] = {"scene_index": plan.scene_index, "title": plan.title}

    if plan.failed:
        return {
            **base,
            "status": "failed",
            "note": (
                "The previous scene's visual plan could not be generated. "
                "Treat the canvas as an unknown state and open this scene cleanly."
            ),
            }

    context: dict[str, Any] = {**base, "status": "ok"}

    if isinstance(plan.plan, dict):
        for key in _HANDOFF_KEYS:
            if key in plan.plan:
                context["ending_state"] = plan.plan[key]
                return context
        context["plan"] = plan.plan
    else:
        context["plan"] = plan.plan

    return context


# ── Outline → VisualDSL transform ─────────────────────────────────────────────

@log_call(stage="util:map_outline_to_visual_plan")
def map_outline_to_visual_plan(state: GraphState) -> VisualDSLInputState:
    """Pure data transform between the outline node and the visual planning node.

    Reads:  state.outline  (raw dict from the outline agent)
    Writes: VisualDSLInputState (typed contract for visual_planning_node)
    """
    rl = request_logger_var.get()
    raw_outline: dict[str, Any] = state.outline
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


# ── LLM helpers ───────────────────────────────────────────────────────────────

@log_call(stage="util:refine_requirement")
async def refine_requirement(
        *,
        session_id: str,
        workflow_id: str,
        requirement: str,
        ) -> str:
    """Call Gemini 2.5 Flash to refine a raw user requirement."""
    tok_s = session_id_var.set(session_id)
    tok_w = workflow_id_var.set(workflow_id)
    tok_n = node_name_var.set("refine_requirement")

    rl = request_logger_var.get()
    if rl is not None:
        rl.pipeline_step("requirement.refine.start", {
            "original_len": len(requirement),
            "model": settings.GEMINI_25_FLASH_MODEL,
            },
            )

    try:
        llm = get_client(LLMProvider.GEMINI)
        refined = await llm.ainvoke(
            user_prompt=requirement,
            model=settings.GEMINI_25_FLASH_MODEL,
            system_prompt=REQ_MODIFIER_SYSTEM,
            temperature=0.35,
            )
        refined = refined.strip()

        logger.info(
            "Requirement refined",
            extra={
                "session_id": session_id,
                "workflow_id": workflow_id,
                "original_len": len(requirement),
                "refined_len": len(refined),
                },
            )

        if rl is not None:
            rl.pipeline_step("requirement.refine.done", {
                "original_len": len(requirement),
                "refined_len": len(refined),
                },
                )

        return refined

    except Exception:
        logger.exception(
            "Requirement refinement failed",
            extra={"session_id": session_id, "workflow_id": workflow_id},
            )
        raise

    finally:
        session_id_var.reset(tok_s)
        workflow_id_var.reset(tok_w)
        node_name_var.reset(tok_n)


@log_call(stage="util:generate_outline")
async def generate_outline(
        state: GraphState,
        schema_class: type,
        outline_type: str,
        ) -> OutlineOutputState:
    """Gemini 3.5 Flash (with 3.0 fallback) structured outline generation."""
    tok_s = session_id_var.set(state.session_id)
    tok_w = workflow_id_var.set(state.workflow_id)
    tok_n = node_name_var.set(outline_type)

    rl = request_logger_var.get()
    refined_req = state.refined_requirement or state.requirement

    if rl is not None:
        rl.pipeline_step("outline.generate.start", {
            "outline_type": outline_type,
            "schema": schema_class.__name__,
            "primary_model": settings.GEMINI_35_FLASH_MODEL,
            "fallback_model": settings.GEMINI_3_FLASH_MODEL,
            "requirement_len": len(refined_req),
            },
            )

    try:
        llm = get_client(LLMProvider.GEMINI)
        outline_user_msg = (
            f"raw_content: {refined_req}\n"
            f"topic: {refined_req}\n"
            f"duration_minutes: 5\n"
            f"pace: medium"
        )

        outline, model_used, total_attempts = await ainvoke_structured_with_fallback(
            llm,
            primary_model=settings.GEMINI_35_FLASH_MODEL,
            fallback_model=settings.GEMINI_3_FLASH_MODEL,
            user_prompt=outline_user_msg,
            schema=schema_class,
            system_prompt=state.system_prompt or "",
            temperature=0.15,
            )
        outline_dict = outline.model_dump()
        segment_count = len(outline.outline)

        logger.info(
            "Outline generated",
            extra={
                "session_id": state.session_id,
                "outline_type": outline_type,
                "model_used": model_used,
                "total_attempts": total_attempts,
                "segment_count": segment_count,
                },
            )

        if rl is not None:
            rl.pipeline_step("outline.generate.done", {
                "outline_type": outline_type,
                "model_used": model_used,
                "total_attempts": total_attempts,
                "segment_count": segment_count,
                },
                )

        save_output_to_log(
            f"outline_{state.session_id}.txt",
            {
                "session_id": state.session_id,
                "workflow_id": state.workflow_id,
                "outline_type": outline_type,
                "primary_model": settings.GEMINI_35_FLASH_MODEL,
                "fallback_model": settings.GEMINI_3_FLASH_MODEL,
                "model_used": model_used,
                "total_attempts": total_attempts,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "outline": outline_dict,
                },
            )

        return OutlineOutputState(
            session_id=state.session_id,
            workflow_id=state.workflow_id,
            outline=outline_dict,
            outline_type=outline_type,
            status="completed",
            error=None,
            )

    except Exception as exc:
        logger.exception(
            "Outline generation failed (all models exhausted)",
            extra={"session_id": state.session_id, "outline_type": outline_type},
            )
        if rl is not None:
            rl.warning(
                message=f"Outline generation failed: {exc}",
                context="generate_outline",
                extra={"outline_type": outline_type},
                )
        return OutlineOutputState(
            session_id=state.session_id,
            workflow_id=state.workflow_id,
            outline={},
            outline_type=outline_type,
            status="failed",
            error=str(exc),
            )
    finally:
        session_id_var.reset(tok_s)
        workflow_id_var.reset(tok_w)
        node_name_var.reset(tok_n)
