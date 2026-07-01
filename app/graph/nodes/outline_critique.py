"""outline_critique.py — Node: critic→refactor loop on the raw outline before visual planning."""
from __future__ import annotations

import json
from typing import Any

from app.core.config import settings
from app.core.context import node_name_var, request_logger_var, session_id_var, workflow_id_var
from app.core.logger import log_call, StructuredLogger
from app.graph.models.graph_state import GraphState
from app.graph.prompts.outline_critic_prompt import (build_outline_critic_prompt,
    build_outline_refactor_prompt,
    OUTLINE_CRITIC_SYSTEM,
    OUTLINE_REFACTOR_SYSTEM,
    OutlineCritiqueResult,
)
from app.graph.retry import ainvoke_structured_with_fallback, ainvoke_with_fallback
from app.services.factory import get_client, LLMProvider
from app.storage.artifact_store import ArtifactStore


logger = StructuredLogger.get_logger(__name__)

MAX_OUTLINE_ITERATIONS = 5


def _extract_json(raw: str) -> dict | None:
    """Extract the first JSON object from raw LLM text."""
    raw = raw.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        return None
    try:
        return json.loads(raw[start:end])
    except json.JSONDecodeError:
        return None


@log_call(stage="node:outline_critique")
async def outline_critique_node(state: GraphState) -> dict:
    """Critic-refactor loop that improves the raw outline before visual planning.

    Reviews theoretical accuracy, narrative coherence, talking-point quality,
    visual plan descriptions, timing distribution, and educational completeness.
    Runs up to MAX_OUTLINE_ITERATIONS critic → refactor cycles. The critic can
    approve early to skip remaining iterations.
    """
    if not state.outline:
        return {
            "outline": state.outline,
            "status": "failed",
            "error": "outline_critique requires generate_outline to run first",
            }

    rl = request_logger_var.get()
    llm = get_client(LLMProvider.GEMINI)
    store = ArtifactStore(state.session_id)

    raw_outline: dict[str, Any] = state.outline
    current_meta: dict[str, Any] = raw_outline.get("meta", {})
    current_segments: list[dict[str, Any]] = list(raw_outline.get("outline", []))

    if rl is not None:
        rl.pipeline_step("outline_critique.start", {
            "session_id": state.session_id,
            "scene_count": len(current_segments),
            "max_iterations": MAX_OUTLINE_ITERATIONS,
            },
            )

    for iteration in range(1, MAX_OUTLINE_ITERATIONS + 1):
        tok_s = session_id_var.set(state.session_id)
        tok_w = workflow_id_var.set(state.workflow_id)
        tok_n = node_name_var.set(f"outline_critique/iter_{iteration}")

        try:
            # ── Critic ────────────────────────────────────────────────────
            try:
                critique, _, _ = await ainvoke_structured_with_fallback(
                    llm,
                    primary_model=settings.GEMINI_MODEL,
                    fallback_model=settings.GEMINI_FALLBACK_MODEL,
                    user_prompt=build_outline_critic_prompt(
                        current_meta, current_segments, iteration,
                        ),
                    schema=OutlineCritiqueResult,
                    system_prompt=OUTLINE_CRITIC_SYSTEM,
                    temperature=0.3,
                    )
            except Exception as critic_exc:
                logger.warning(
                    "Outline critic call failed — keeping current outline",
                    extra={"session_id": state.session_id, "iteration": iteration,
                        "error": str(critic_exc),
                        },
                    )
                break

            logger.info(
                "Outline critic evaluation",
                extra={
                    "session_id": state.session_id,
                    "iteration": iteration,
                    "approved": critique.approved,
                    "score": critique.score,
                    },
                )

            if rl is not None:
                rl.pipeline_step("outline_critique.evaluated", {
                    "iteration": iteration,
                    "approved": critique.approved,
                    "score": critique.score,
                    "improvements_count": len(critique.improvements),
                    },
                    )

            if critique.approved or iteration >= MAX_OUTLINE_ITERATIONS:
                break

            # ── Refactor ──────────────────────────────────────────────────
            try:
                raw_response, _, _ = await ainvoke_with_fallback(
                    llm,
                    primary_model=settings.GEMINI_MODEL,
                    fallback_model=settings.GEMINI_FALLBACK_MODEL,
                    user_prompt=build_outline_refactor_prompt(
                        current_meta, current_segments, critique, iteration,
                        ),
                    system_prompt=OUTLINE_REFACTOR_SYSTEM,
                    temperature=0.4,
                    )
            except Exception as refactor_exc:
                logger.warning(
                    "Outline refactor call failed — keeping current outline",
                    extra={"session_id": state.session_id, "iteration": iteration,
                        "error": str(refactor_exc),
                        },
                    )
                break

            revised = _extract_json(raw_response)
            if not revised or "outline" not in revised:
                logger.warning(
                    "Outline refactor returned unparseable JSON — keeping current outline",
                    extra={"session_id": state.session_id, "iteration": iteration},
                    )
                break

            current_meta = revised.get("meta", current_meta)
            current_segments = revised.get("outline", current_segments)

            logger.info(
                "Outline refactor succeeded",
                extra={"session_id": state.session_id, "iteration": iteration,
                    "scene_count": len(current_segments),
                    },
                )

        finally:
            session_id_var.reset(tok_s)
            workflow_id_var.reset(tok_w)
            node_name_var.reset(tok_n)

    # Reconstruct refined outline, preserving any extra keys from the original
    refined_outline: dict[str, Any] = {**raw_outline, "meta": current_meta, "outline": current_segments}

    store.save("outline", {
        "outline": refined_outline,
        "outline_type": state.outline_type,
        "status": "completed",
        },
        )
    store.save("outline_critique", {
        "session_id": state.session_id,
        "scene_count": len(current_segments),
        "status": "completed",
        },
        )

    if rl is not None:
        rl.pipeline_step("outline_critique.done", {
            "scene_count": len(current_segments),
            },
            )

    return {
        "outline": refined_outline,
        "outline_type": state.outline_type,
        "status": "completed",
        "error": None,
        }
