"""visual_planning.py — Node: generate per-scene Visual DSL plans."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.core.context import node_name_var, request_logger_var, session_id_var, workflow_id_var
from app.core.logger import log_call, StructuredLogger
from app.core.stage_tracker import StageTracker
from app.graph.models.graph_state import GraphState
from app.graph.models.visual_planning_state import SceneVisualPlan
from app.graph.nodes.utils import save_output_to_log
from app.graph.prompts.visual_plan_gen_prompt import generate_visual_plan_prompt, SceneDirectorInput
from app.graph.retry import ainvoke_with_fallback
from app.services.factory import get_client, LLMProvider
from app.storage.artifact_store import ArtifactStore


logger = StructuredLogger.get_logger(__name__)

_HANDOFF_KEYS: tuple[str, ...] = (
    "next_scene_context", "ending_state", "canvas_state", "final_state",
    )


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


@log_call(stage="node:visual_planning")
async def visual_planning_node(state: GraphState) -> dict:
    """Generates a structured Visual DSL plan for every scene sequentially."""
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
            "primary_model": settings.CLOUDFLARE_PRIMARY_MODEL,
            "pre_existing_scenes": len(pre_existing),
            },
            )

    video_metadata_json = json.dumps({
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
        }, indent=2,
        )

    for scene in state.video_outline:
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
            else {"0": "Scene 0: None — this is the first scene. Screen is blank at t=0."}
        )

        director_input = SceneDirectorInput(
            video_metadata=video_metadata_json,
            prior_scenes=prior_scenes,
            target_scene_id=f"scene_{scene.scene_index:03d}",
            target_scene=json.dumps({
                "scene_index": scene.scene_index,
                "title": scene.title,
                "description": scene.description,
                "duration_seconds": scene.duration_hint_seconds,
                "narration_text": scene.narration_text,
                }, indent=2,
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
                primary_model=settings.CLOUDFLARE_PRIMARY_MODEL,
                fallback_model=settings.CLOUDFLARE_FALLBACK_MODEL,
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
            "primary_model": settings.CLOUDFLARE_PRIMARY_MODEL,
            "fallback_model": settings.CLOUDFLARE_FALLBACK_MODEL,
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
