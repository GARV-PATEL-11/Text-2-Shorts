"""
nodes.py
--------
All node functions for the video outline generation graph.

Graph nodes
-----------
validate_input                  Validates approach; resolves system prompt.     (sync)
conceptual_zoom_node            Generates ConceptualZoomOutline via LLM.        (async)
problem_solution_arc_node       Generates ProblemSolutionArcOutline via LLM.    (async)
classic_linear_narrative_node   Generates ClassicLinearNarrativeOutline.        (async)
map_outline_to_visual_plan      Transform: OutlineOutputState→VisualPlanInput.  (sync)
visual_planning_node            Generates scene-wise visual plan.               (async)

LLM calls use AWS Bedrock via BedrockClient (thread-offloaded async).
max_completion_tokens is always set to settings.MAX_COMPLETION_TOKENS (8192).
"""

from __future__ import annotations

import json
from uuid import uuid4

from app.core.config import settings
from app.core.context import node_name_var, session_id_var, workflow_id_var
from app.core.logger import StructuredLogger
from app.graph.models.classic_linear_narrative import ClassicLinearNarrativeOutline
from app.graph.models.conceptual_zoom import ConceptualZoomOutline
from app.graph.models.enums import NarrativeApproach
from app.graph.models.problem_solution_arc import ProblemSolutionArcOutline
from app.graph.prompts.script_gen_prompt import (
    CLASSIC_LINEAR_NARRATIVE_SYSTEM,
    CONCEPTUAL_ZOOM_SYSTEM,
    PROBLEM_TO_SOLUTION_ARC_SYSTEM,
    )
from app.graph.prompts.visual_gen_prompt import (build_director_prompt,
    extract_next_scene_context,
    VISUAL_DIRECTOR_SYSTEM,
)
from app.graph.state import GraphState, SceneOutline
from app.services import get_client, LLMProvider


logger = StructuredLogger.get_logger(__name__)

_MODEL = settings.BEDROCK_MODEL_ID
_MAX_TOKENS = settings.MAX_COMPLETION_TOKENS

# Approach → (system_prompt, schema_class, outline_type_label)
_APPROACH_CONFIG: dict[str, tuple[str, type, str]] = {
    NarrativeApproach.CONCEPTUAL_ZOOM.value: (
        CONCEPTUAL_ZOOM_SYSTEM,
        ConceptualZoomOutline,
        "ConceptualZoom",
        ),
    NarrativeApproach.PROBLEM_SOLUTION_ARC.value: (
        PROBLEM_TO_SOLUTION_ARC_SYSTEM,
        ProblemSolutionArcOutline,
        "ProblemSolutionArc",
        ),
    NarrativeApproach.CLASSIC_LINEAR_NARRATIVE.value: (
        CLASSIC_LINEAR_NARRATIVE_SYSTEM,
        ClassicLinearNarrativeOutline,
        "ClassicLinearNarrative",
        ),
    }


# ── Node: validate_input (sync — no LLM call) ─────────────────────────────────

def validate_input(state: GraphState) -> dict:
    """
    Validates approach and resolves the approach-specific system prompt.

    Reads:  ValidateInputState fields
    Writes: ValidateOutputState fields
    """
    approach_value: str = state.approach.value
    cfg = _APPROACH_CONFIG.get(approach_value)

    if cfg is None:
        logger.error(
            "Unknown approach",
            extra={"approach": approach_value},
            )
        return {
            "status": "failed",
            "error": (
                f"Unknown approach {approach_value!r}. "
                f"Valid: {[a.value for a in NarrativeApproach]}"
            ),
            }

    system_prompt, _, _ = cfg
    wf_id = state.workflow_id or uuid4().hex
    logger.info(
        "Input validated",
        extra={"session_id": state.session_id, "approach": approach_value, "workflow_id": wf_id},
        )
    return {
        "workflow_id": wf_id,
        "system_prompt": system_prompt,
        "routed_to": None,
        "status": "ready",
        "error": None,
        }


# ── Shared async outline generation helper ────────────────────────────────────

async def _generate_outline(
        state: GraphState,
        schema_class: type,
        outline_type: str,
        ) -> dict:
    """
    Async LLM call via Bedrock:
      Approach-specific system prompt generates a structured Pydantic outline.

    Reads:  OutlineInputState fields (requirement, system_prompt, session_id)
    Writes: OutlineOutputState fields (outline, outline_type, status, error)
    """
    tok_s = session_id_var.set(state.session_id)
    tok_w = workflow_id_var.set(state.workflow_id)
    tok_n = node_name_var.set(outline_type)
    try:
        llm = get_client(LLMProvider.BEDROCK)
        outline_user_msg = (
            f"raw_content: {state.requirement}\n"
            f"topic: {state.requirement}\n"
            f"duration_minutes: 5\n"
            f"pace: medium"
        )
        outline = await llm.ainvoke_structured(
            user_prompt=outline_user_msg,
            schema=schema_class,
            model=_MODEL,
            system_prompt=state.system_prompt,
            temperature=0.15,
            max_tokens=_MAX_TOKENS,
            )
        logger.info(
            "Outline generated",
            extra={
                "session_id": state.session_id,
                "outline_type": outline_type,
                "segment_count": len(outline.outline),
                },
            )
        return {
            "outline": outline.model_dump(),
            "outline_type": outline_type,
            "status": "completed",
            "error": None,
            }

    except Exception as exc:
        logger.exception(
            "Outline generation failed",
            extra={"session_id": state.session_id, "outline_type": outline_type},
            )
        return {"status": "failed", "error": str(exc)}
    finally:
        session_id_var.reset(tok_s)
        workflow_id_var.reset(tok_w)
        node_name_var.reset(tok_n)


# ── Outline generator nodes (async) ──────────────────────────────────────────

async def conceptual_zoom_node(state: GraphState) -> dict:
    """
    Reads:  OutlineInputState (ValidateOutputState fields)
    Writes: OutlineOutputState fields
    """
    return await _generate_outline(state, ConceptualZoomOutline, "ConceptualZoom")


async def problem_solution_arc_node(state: GraphState) -> dict:
    """
    Reads:  OutlineInputState (ValidateOutputState fields)
    Writes: OutlineOutputState fields
    """
    return await _generate_outline(state, ProblemSolutionArcOutline, "ProblemSolutionArc")


async def classic_linear_narrative_node(state: GraphState) -> dict:
    """
    Reads:  OutlineInputState (ValidateOutputState fields)
    Writes: OutlineOutputState fields
    """
    return await _generate_outline(state, ClassicLinearNarrativeOutline, "ClassicLinearNarrative")


# ── Transform node (sync — pure data reshaping, no LLM) ──────────────────────

def map_outline_to_visual_plan(state: GraphState) -> dict:
    """
    Explicit state transform between outline generation and visual planning.

    Reads:  OutlineOutputState fields (outline, outline_type)
    Writes: VisualPlanInputState fields (total_scenes, video_outline)
    """
    outline: dict = state.outline or {}
    segments: list[dict] = outline.get("outline", [])

    video_outline: list[SceneOutline] = [
        SceneOutline(
            scene_index=seg.get("id", i + 1) - 1,
            title=seg.get("title", ""),
            description="\n".join(
                seg.get("visual_cues", []) + seg.get("talking_points", []),
                ),
            duration_hint_seconds=seg.get("duration_seconds", 30),
            narration_text=seg.get("narration_hint"),
            )
        for i, seg in enumerate(segments)
        ]

    logger.info(
        "Outline mapped to visual plan input",
        extra={"session_id": state.session_id, "scene_count": len(video_outline)},
        )
    return {
        "total_scenes": len(video_outline),
        "video_outline": [s.model_dump() for s in video_outline],
        }


# ── Node: visual_planning (async) ─────────────────────────────────────────────

async def visual_planning_node(state: GraphState) -> dict:
    """
    Generates a structured visual specification for every scene in video_outline.

    Reads:  VisualPlanInputState fields (total_scenes, video_outline)
    Writes: VisualPlanOutputState fields (scene_visual_plans, status, error)
    """
    llm = get_client(LLMProvider.BEDROCK)
    video_outline: list[SceneOutline] = [
        SceneOutline(**s) if isinstance(s, dict) else s
        for s in state.video_outline
        ]
    scene_visual_plans: list[str] = []

    video_metadata = json.dumps(
        {
            "total_scenes": state.total_scenes,
            "scenes": [
                {
                    "scene_index": s.scene_index,
                    "title": s.title,
                    "duration_hint_seconds": s.duration_hint_seconds,
                    }
                for s in video_outline
                ],
            },
        indent=2,
        )

    for scene in video_outline:
        prior_scenes: str = (
            extract_next_scene_context(scene_visual_plans[-1])
            if scene_visual_plans
            else "None — this is the first scene. Screen is blank at t=0."
        )
        target_scene_json = json.dumps(
            {
                "scene_index": scene.scene_index,
                "title": scene.title,
                "description": scene.description,
                "duration_seconds": scene.duration_hint_seconds,
                "narration_text": scene.narration_text,
                },
            indent=2,
            )
        user_prompt = build_director_prompt(
            video_metadata=video_metadata,
            target_scene_id=scene.scene_index,
            target_scene=target_scene_json,
            prior_scenes=prior_scenes,
            )
        tok_s = session_id_var.set(state.session_id)
        tok_w = workflow_id_var.set(state.workflow_id)
        tok_n = node_name_var.set(f"visual_planning/scene_{scene.scene_index}")
        try:
            plan = await llm.ainvoke(
                user_prompt=user_prompt,
                model=_MODEL,
                system_prompt=VISUAL_DIRECTOR_SYSTEM,
                temperature=0.4,
                max_tokens=_MAX_TOKENS,
                )
            logger.info(
                "Visual plan generated",
                extra={"session_id": state.session_id, "scene_index": scene.scene_index},
                )
        except Exception as exc:
            logger.error(
                "Visual plan failed",
                extra={
                    "session_id": state.session_id,
                    "scene_index": scene.scene_index,
                    "error": str(exc),
                    },
                )
            plan = f"VISUAL_PLAN_ERROR:{exc}"
        finally:
            session_id_var.reset(tok_s)
            workflow_id_var.reset(tok_w)
            node_name_var.reset(tok_n)

        scene_visual_plans.append(plan)

    all_failed = all(p.startswith("VISUAL_PLAN_ERROR:") for p in scene_visual_plans)
    return {
        "scene_visual_plans": scene_visual_plans,
        "status": "failed" if all_failed else "completed",
        "error": scene_visual_plans[0] if all_failed else None,
        }
