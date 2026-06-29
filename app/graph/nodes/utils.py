"""nodes/utils.py — Shared utilities used by multiple node files."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

from app.core.config import settings
from app.core.context import node_name_var, request_logger_var, session_id_var, workflow_id_var
from app.core.logger import log_call, StructuredLogger
from app.graph.models.graph_state import GraphState
from app.graph.models.outline_state import OutlineOutputState
from app.graph.retry import ainvoke_structured_with_fallback
from app.services.factory import get_client, LLMProvider


logger = StructuredLogger.get_logger(__name__)

_LOGS_DIR = "logs"


def extract_class_name(code: str) -> str | None:
    """Extract the Manim Scene subclass name from Python source code."""
    match = re.search(r"^class\s+(\w+)\s*\(.*?Scene.*?\)", code, re.MULTILINE)
    return match.group(1) if match else None


def save_output_to_log(filename: str, payload: dict) -> None:
    """Write payload as pretty-printed JSON to logs/<filename>."""
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


@log_call(stage="util:generate_outline")
async def generate_outline(
        state: GraphState,
        schema_class: type,
        outline_type: str,
        ) -> OutlineOutputState:
    """Structured outline generation shared by all three outline generator nodes."""
    tok_s = session_id_var.set(state.session_id)
    tok_w = workflow_id_var.set(state.workflow_id)
    tok_n = node_name_var.set(outline_type)

    rl = request_logger_var.get()
    refined_req = state.refined_requirement or state.requirement

    if rl is not None:
        rl.pipeline_step("outline.generate.start", {
            "outline_type": outline_type,
            "schema": schema_class.__name__,
            "primary_model": settings.CLOUDFLARE_PRIMARY_MODEL,
            "fallback_model": settings.CLOUDFLARE_FALLBACK_MODEL,
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
            primary_model=settings.CLOUDFLARE_PRIMARY_MODEL,
            fallback_model=settings.CLOUDFLARE_FALLBACK_MODEL,
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
                "primary_model": settings.CLOUDFLARE_PRIMARY_MODEL,
                "fallback_model": settings.CLOUDFLARE_FALLBACK_MODEL,
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
