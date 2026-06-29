"""validate_input.py — Node: validate and refine user input."""
from __future__ import annotations

from uuid import uuid4

from app.core.config import settings
from app.core.context import node_name_var, request_logger_var, session_id_var, workflow_id_var
from app.core.logger import log_call, StructuredLogger
from app.graph.models.classic_linear_narrative import ClassicLinearNarrativeOutline
from app.graph.models.conceptual_zoom import ConceptualZoomOutline
from app.graph.models.enums import NarrativeApproach
from app.graph.models.graph_state import GraphState
from app.graph.models.problem_solution_arc import ProblemSolutionArcOutline
from app.graph.prompts.script_gen_prompt import (
    CLASSIC_LINEAR_NARRATIVE_SYSTEM,
    CONCEPTUAL_ZOOM_SYSTEM,
    PROBLEM_TO_SOLUTION_ARC_SYSTEM,
    REQ_MODIFIER_SYSTEM,
    )
from app.services.factory import get_client, LLMProvider


logger = StructuredLogger.get_logger(__name__)

# Keys are plain strings because GraphState uses use_enum_values=True
_APPROACH_CONFIG: dict[str, tuple[str, type, str]] = {
    NarrativeApproach.CONCEPTUAL_ZOOM.value: (
        CONCEPTUAL_ZOOM_SYSTEM, ConceptualZoomOutline, "ConceptualZoom",
        ),
    NarrativeApproach.PROBLEM_SOLUTION_ARC.value: (
        PROBLEM_TO_SOLUTION_ARC_SYSTEM, ProblemSolutionArcOutline, "ProblemSolutionArc",
        ),
    NarrativeApproach.CLASSIC_LINEAR_NARRATIVE.value: (
        CLASSIC_LINEAR_NARRATIVE_SYSTEM, ClassicLinearNarrativeOutline, "ClassicLinearNarrative",
        ),
    }


@log_call(stage="util:refine_requirement")
async def refine_requirement(*, session_id: str, workflow_id: str, requirement: str) -> str:
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


@log_call(stage="node:validate_input")
async def validate_input(state: GraphState) -> dict:
    """Refine the raw requirement and resolve the approach-specific system prompt."""
    rl = request_logger_var.get()
    wf_id: str = uuid4().hex

    cfg = _APPROACH_CONFIG.get(
        state.approach,
        _APPROACH_CONFIG[NarrativeApproach.CLASSIC_LINEAR_NARRATIVE.value],
        )
    outline_gen_system_prompt, _, _ = cfg

    if rl is not None:
        rl.pipeline_step("validate_input.start", {
            "session_id": state.session_id,
            "approach": state.approach,
            "requirement_len": len(state.requirement),
            "workflow_id": wf_id,
            },
            )

    try:
        refined_req = await refine_requirement(
            session_id=state.session_id,
            workflow_id=wf_id,
            requirement=state.requirement,
            )
        status = "ready"
        error = None

    except Exception as exc:
        refined_req = state.requirement
        status = "failed"
        error = str(exc)
        if rl is not None:
            rl.warning(
                message=f"Requirement refinement failed, using original: {exc}",
                context="validate_input",
                )

    logger.info(
        "Input validated",
        extra={
            "session_id": state.session_id,
            "workflow_id": wf_id,
            "approach": state.approach,
            "status": status,
            },
        )

    if rl is not None:
        rl.pipeline_step("validate_input.done", {
            "status": status,
            "refined_len": len(refined_req),
            "error": error,
            },
            )

    return {
        "workflow_id": wf_id,
        "system_prompt": outline_gen_system_prompt,
        "refined_requirement": refined_req,
        "status": status,
        "error": error,
        }
