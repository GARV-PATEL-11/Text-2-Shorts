"""
nodes.py
--------
All node functions for the video outline generation graph.

Graph nodes
-----------
validate_input                  Refines requirement and resolves system prompt.  (async)
conceptual_zoom_node            Generates ConceptualZoomOutline via Gemini.      (async)
problem_solution_arc_node       Generates ProblemSolutionArcOutline via Gemini.  (async)
classic_linear_narrative_node   Generates ClassicLinearNarrativeOutline.         (async)
map_outline_to_visual_plan_node Transform: outline fields → scene outline fields.  (sync)
visual_planning_node            Generates scene-wise Visual DSL plan via Gemini. (async)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.artifact_store import ArtifactStore
from app.core.config import settings
from app.core.context import node_name_var, request_logger_var, session_id_var, workflow_id_var
from app.core.logger import log_call, StructuredLogger
from app.core.stage_tracker import StageTracker
from app.graph.models.classic_linear_narrative import ClassicLinearNarrativeOutline
from app.graph.models.conceptual_zoom import ConceptualZoomOutline
from app.graph.models.enums import NarrativeApproach
from app.graph.models.problem_solution_arc import ProblemSolutionArcOutline
from app.graph.prompts.script_gen_prompt import (
    CLASSIC_LINEAR_NARRATIVE_SYSTEM,
    CONCEPTUAL_ZOOM_SYSTEM,
    PROBLEM_TO_SOLUTION_ARC_SYSTEM,
    )
from app.graph.prompts.visual_plan_gen_prompt import (generate_visual_plan_prompt, SceneDirectorInput)
from app.graph.retry import ainvoke_with_fallback
from app.graph.state import (
    GraphState,
    SceneVisualPlan,
    )
from app.graph.utils import (
    extract_next_scene_context,
    generate_outline,
    map_outline_to_visual_plan,
    refine_requirement,
    save_output_to_log,
    )
from app.services import get_client, LLMProvider


logger = StructuredLogger.get_logger(__name__)

# Approach string value → (system_prompt, schema_class, outline_type_label)
# Keys are plain strings because GraphState uses use_enum_values=True
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


# ── Node: validate_input ──────────────────────────────────────────────────────

@log_call(stage="node:validate_input")
async def validate_input(state: GraphState) -> dict:
    """Refine the raw requirement and resolve the approach-specific system prompt."""
    rl = request_logger_var.get()
    wf_id: str = uuid4().hex

    # state.approach is already a str (use_enum_values=True on GraphState)
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


# ── Outline generator nodes ───────────────────────────────────────────────────

@log_call(stage="node:conceptual_zoom")
async def conceptual_zoom_node(state: GraphState) -> dict:
    result = await generate_outline(state, ConceptualZoomOutline, "ConceptualZoom")
    return result.model_dump()


@log_call(stage="node:problem_solution_arc")
async def problem_solution_arc_node(state: GraphState) -> dict:
    result = await generate_outline(state, ProblemSolutionArcOutline, "ProblemSolutionArc")
    return result.model_dump()


@log_call(stage="node:classic_linear_narrative")
async def classic_linear_narrative_node(state: GraphState) -> dict:
    result = await generate_outline(state, ClassicLinearNarrativeOutline, "ClassicLinearNarrative")
    return result.model_dump()


# ── Node: map_outline_to_visual_plan ─────────────────────────────────────────

@log_call(stage="node:map_outline_to_visual_plan")
def map_outline_to_visual_plan_node(state: GraphState) -> dict:
    """LangGraph node: transforms outline into VisualDSL input fields."""
    result = map_outline_to_visual_plan(state)
    return {
        "total_scenes": result.total_scenes,
        "metadata": result.metadata,
        "video_outline": result.video_outline,
        }


# ── Node: visual_planning ─────────────────────────────────────────────────────

@log_call(stage="node:visual_planning")
async def visual_planning_node(state: GraphState) -> dict:
    """Generates a structured Visual DSL plan for every scene sequentially.

    Model strategy
    ──────────────
    Primary  : settings.GEMINI_35_FLASH_MODEL
    Fallback : settings.GEMINI_3_FLASH_MODEL
    Retry / backoff handled transparently by ainvoke_with_fallback.

    Failure semantics
    ─────────────────
    - Per-scene failure  → SceneVisualPlan.error is set; loop continues.
    - All scenes failed  → status = "failed".
    - Partial failure    → status = "completed"; inspect individual plans.
    """
    if state.metadata is None or not state.video_outline:
        return {
            "scene_visual_plans": [],
            "status": "failed",
            "error": "visual_planning requires map_outline_to_visual_plan to run first",
            }

    rl = request_logger_var.get()
    llm = get_client(LLMProvider.GEMINI)
    store = ArtifactStore(state.session_id)
    tracker = StageTracker.for_session(state.session_id)
    tracker.init_scenes(state.video_outline)

    # Load pre-existing scene artifacts for resume support
    pre_existing: dict[int, SceneVisualPlan] = {}
    for scene in state.video_outline:
        existing = store.load_scene(scene.scene_index)
        if existing and not existing.get("error"):
            try:
                pre_existing[scene.scene_index] = SceneVisualPlan(**existing)
                tracker.complete_scene(scene.scene_index)
            except Exception:
                pass

    scene_visual_plans: list[SceneVisualPlan] = []

    if rl is not None:
        rl.pipeline_step("visual_planning.start", {
            "session_id": state.session_id,
            "total_scenes": state.total_scenes,
            "primary_model": settings.GEMINI_35_FLASH_MODEL,
            "pre_existing_scenes": len(pre_existing),
            },
            )

    video_metadata_json = json.dumps(
        {
            "title": state.metadata.title,
            "topic": state.metadata.topic,
            "total_scenes": state.total_scenes,
            "total_duration_seconds": state.metadata.total_duration_seconds,
            "scenes": [
                {
                    "scene_index": s.scene_index,
                    "title": s.title,
                    "duration_hint_seconds": s.duration_hint_seconds,
                    }
                for s in state.video_outline
                ],
            },
        indent=2,
        )

    for scene in state.video_outline:
        # Resume: skip scenes that already have a persisted artifact
        if scene.scene_index in pre_existing:
            scene_visual_plans.append(pre_existing[scene.scene_index])
            continue

        tracker.start_scene(scene.scene_index)

        prior_scenes: dict = (
            {
                str(i + 1): f"Scene {i + 1}: {extract_next_scene_context(scene_plan)}"
                for i, scene_plan in enumerate(scene_visual_plans)
                }
            if scene_visual_plans
            else {
                "0": "Scene 0: None — this is the first scene. Screen is blank at t=0.",
                }
        )

        director_input = SceneDirectorInput(
            video_metadata=video_metadata_json,
            prior_scenes=prior_scenes,
            target_scene_id=f"scene_{scene.scene_index:03d}",
            target_scene=json.dumps(
                {
                    "scene_index": scene.scene_index,
                    "title": scene.title,
                    "description": scene.description,
                    "duration_seconds": scene.duration_hint_seconds,
                    "narration_text": scene.narration_text,
                    },
                indent=2,
                ),
            target_duration=scene.duration_hint_seconds,
            )

        prompts = generate_visual_plan_prompt(director_input)

        tok_s = session_id_var.set(state.session_id)
        tok_w = workflow_id_var.set(state.workflow_id)
        tok_n = node_name_var.set(f"visual_planning/scene_{scene.scene_index}")

        if rl is not None:
            rl.pipeline_step("scene.plan.start", {
                "scene_index": scene.scene_index,
                "title": scene.title,
                "duration_s": scene.duration_hint_seconds,
                },
                )

        try:
            plan_raw, model_used, total_attempts = await ainvoke_with_fallback(
                llm,
                primary_model=settings.GEMINI_35_FLASH_MODEL,
                fallback_model=settings.GEMINI_3_FLASH_MODEL,
                user_prompt=prompts["user"],
                system_prompt=prompts["system"],
                temperature=0.4,
                )

            plan = _parse_plan(plan_raw)

            visual_plan = SceneVisualPlan(
                scene_index=scene.scene_index,
                title=scene.title,
                model_used=model_used,
                total_attempts=total_attempts,
                plan=plan,
                )

            store.save_scene(scene.scene_index, visual_plan.model_dump())
            tracker.complete_scene(scene.scene_index)

            logger.info(
                "Visual DSL plan generated",
                extra={
                    "session_id": state.session_id,
                    "scene_index": scene.scene_index,
                    "model_used": model_used,
                    "total_attempts": total_attempts,
                    "plan_type": "dict" if isinstance(plan, dict) else "str",
                    },
                )

            if rl is not None:
                rl.pipeline_step("scene.plan.done", {
                    "scene_index": scene.scene_index,
                    "status": "success",
                    "model_used": model_used,
                    "total_attempts": total_attempts,
                    "plan_type": "dict" if isinstance(plan, dict) else "str",
                    },
                    )

        except Exception as exc:
            logger.error(
                "Visual DSL plan failed — all models exhausted",
                extra={
                    "session_id": state.session_id,
                    "scene_index": scene.scene_index,
                    "error": str(exc),
                    },
                )
            if rl is not None:
                rl.pipeline_step("scene.plan.done", {
                    "scene_index": scene.scene_index,
                    "status": "error",
                    "error": str(exc)[:200],
                    },
                    )
            tracker.fail_scene(scene.scene_index, str(exc))
            visual_plan = SceneVisualPlan(
                scene_index=scene.scene_index,
                title=scene.title,
                plan={},
                error=str(exc),
                )

        finally:
            session_id_var.reset(tok_s)
            workflow_id_var.reset(tok_w)
            node_name_var.reset(tok_n)

        scene_visual_plans.append(visual_plan)

    all_failed = all(p.failed for p in scene_visual_plans)
    final_status = "failed" if all_failed else "completed"

    store.save("visual_plans", {
        "session_id": state.session_id,
        "workflow_id": state.workflow_id,
        "total_scenes": state.total_scenes,
        "status": final_status,
        "scene_visual_plans": [p.model_dump() for p in scene_visual_plans],
        },
        )

    save_output_to_log(
        f"visual_plans_{state.session_id}.txt",
        {
            "session_id": state.session_id,
            "workflow_id": state.workflow_id,
            "primary_model": settings.GEMINI_35_FLASH_MODEL,
            "fallback_model": settings.GEMINI_3_FLASH_MODEL,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_scenes": state.total_scenes,
            "scene_visual_plans": [p.model_dump() for p in scene_visual_plans],
            },
        )

    if rl is not None:
        rl.pipeline_step("visual_planning.done", {
            "total_scenes": state.total_scenes,
            "failed_scenes": sum(1 for p in scene_visual_plans if p.failed),
            "status": final_status,
            },
            )

    return {
        "scene_visual_plans": scene_visual_plans,
        "status": final_status,
        "error": scene_visual_plans[0].error if all_failed else None,
        }


# ── Private helpers ───────────────────────────────────────────────────────────

def _parse_plan(raw: str) -> dict[str, Any] | str:
    """Try to deserialise the LLM's raw output into a dict; fall back to str."""
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            cleaned = cleaned.rsplit("```", 1)[0].strip()
        return json.loads(cleaned)
    except (json.JSONDecodeError, AttributeError, ValueError):
        return raw
