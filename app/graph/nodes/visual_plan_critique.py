"""visual_plan_critique.py — Node: per-scene critic→refactor loop before DSL code generation."""
from __future__ import annotations

import asyncio
import json

from app.core.config import settings
from app.core.context import node_name_var, request_logger_var, session_id_var, workflow_id_var
from app.core.logger import log_call, StructuredLogger
from app.core.stage_tracker import StageTracker
from app.graph.models.graph_state import GraphState
from app.graph.models.visual_planning_state import SceneOutline, SceneVisualPlan
from app.graph.nodes.visual_planning import _parse_plan
from app.graph.prompts.visual_plan_critic_prompt import (build_critic_user_prompt,
    build_refactor_user_prompt,
    CRITIC_SYSTEM,
    CritiqueResult,
    REFACTOR_SYSTEM,
)
from app.graph.retry import ainvoke_structured_with_fallback, ainvoke_with_fallback
from app.services.factory import get_client, LLMProvider
from app.storage.artifact_store import ArtifactStore


logger = StructuredLogger.get_logger(__name__)

MAX_CRITIQUE_ITERATIONS = 5


def _scene_outline_json(scene: SceneOutline) -> str:
    return json.dumps({
        "scene_index": scene.scene_index,
        "title": scene.title,
        "description": scene.description,
        "duration_seconds": scene.duration_hint_seconds,
        "narration_text": scene.narration_text,
        }, indent=2,
        )


async def _critique_one_scene(
        visual_plan: SceneVisualPlan,
        scene: SceneOutline,
        state: GraphState,
        llm,
        store: ArtifactStore,
        tracker: StageTracker,
        rl,
        ) -> SceneVisualPlan:
    """Run critic→refactor for a single scene's visual plan (up to MAX_CRITIQUE_ITERATIONS)."""
    idx = visual_plan.scene_index

    if visual_plan.error:
        return visual_plan

    current_plan = visual_plan
    scene_json = _scene_outline_json(scene)

    for iteration in range(1, MAX_CRITIQUE_ITERATIONS + 1):
        tok_s = session_id_var.set(state.session_id)
        tok_w = workflow_id_var.set(state.workflow_id)
        tok_n = node_name_var.set(f"visual_plan_critique/scene_{idx}/iter_{iteration}")

        try:
            if rl is not None:
                rl.pipeline_step("scene.critique.start", {
                    "scene_index": idx,
                    "iteration": iteration,
                    },
                    )

            # ── Critic ────────────────────────────────────────────────────
            try:
                critique, _, _ = await ainvoke_structured_with_fallback(
                    llm,
                    primary_model=settings.GEMINI_MODEL,
                    fallback_model=settings.GEMINI_FALLBACK_MODEL,
                    user_prompt=build_critic_user_prompt(scene_json, current_plan.plan, iteration),
                    schema=CritiqueResult,
                    system_prompt=CRITIC_SYSTEM,
                    temperature=0.3,
                    )
            except Exception as critic_exc:
                logger.warning(
                    "Critic call failed — skipping iteration",
                    extra={"session_id": state.session_id, "scene_index": idx,
                        "iteration": iteration, "error": str(critic_exc),
                        },
                    )
                break

            logger.info(
                "Critic evaluation",
                extra={
                    "session_id": state.session_id,
                    "scene_index": idx,
                    "iteration": iteration,
                    "approved": critique.approved,
                    "score": critique.score,
                    },
                )

            if rl is not None:
                rl.pipeline_step("scene.critique.done", {
                    "scene_index": idx,
                    "iteration": iteration,
                    "approved": critique.approved,
                    "score": critique.score,
                    "improvements_count": len(critique.improvements),
                    },
                    )

            if critique.approved or iteration >= MAX_CRITIQUE_ITERATIONS:
                break

            # ── Refactor ──────────────────────────────────────────────────
            try:
                plan_raw, model_used, _ = await ainvoke_with_fallback(
                    llm,
                    primary_model=settings.GEMINI_MODEL,
                    fallback_model=settings.GEMINI_FALLBACK_MODEL,
                    user_prompt=build_refactor_user_prompt(
                        scene_json, current_plan.plan, critique, iteration,
                        ),
                    system_prompt=REFACTOR_SYSTEM,
                    temperature=0.4,
                    )
            except Exception as refactor_exc:
                logger.warning(
                    "Refactor call failed — keeping current plan",
                    extra={"session_id": state.session_id, "scene_index": idx,
                        "iteration": iteration, "error": str(refactor_exc),
                        },
                    )
                break

            new_plan = _parse_plan(plan_raw)
            if not new_plan or new_plan == plan_raw:
                logger.warning(
                    "Refactor returned unparseable plan — keeping current plan",
                    extra={"session_id": state.session_id, "scene_index": idx},
                    )
                break

            current_plan = SceneVisualPlan(
                scene_index=idx,
                title=visual_plan.title,
                model_used=model_used,
                total_attempts=iteration,
                plan=new_plan,
                )

            logger.info(
                "Refactor produced improved plan",
                extra={"session_id": state.session_id, "scene_index": idx,
                    "iteration": iteration,
                    },
                )

        finally:
            session_id_var.reset(tok_s)
            workflow_id_var.reset(tok_w)
            node_name_var.reset(tok_n)

    store.save_scene(idx, current_plan.model_dump())
    tracker.complete_scene(idx)
    return current_plan


@log_call(stage="node:visual_plan_critique")
async def visual_plan_critique_node(state: GraphState) -> dict:
    """Critic-refactor loop: improves every scene's visual plan before code generation.

    All scenes run concurrently. Each scene performs up to MAX_CRITIQUE_ITERATIONS
    critic → refactor cycles. The critic can approve early to skip remaining iterations.
    """
    if not state.scene_visual_plans:
        return {
            "scene_visual_plans": [],
            "status": "failed",
            "error": "visual_plan_critique requires visual_planning to run first",
            }

    rl = request_logger_var.get()
    llm = get_client(LLMProvider.GEMINI)
    store = ArtifactStore(state.session_id)
    tracker = StageTracker.for_session(state.session_id)

    # Build index from scene_index → SceneOutline for fast lookup
    outline_by_index = {s.scene_index: s for s in (state.video_outline or [])}

    if rl is not None:
        rl.pipeline_step("visual_plan_critique.start", {
            "session_id": state.session_id,
            "total_scenes": len(state.scene_visual_plans),
            "max_iterations": MAX_CRITIQUE_ITERATIONS,
            },
            )

    tracker.init_scenes(state.video_outline or [])

    refined_plans: list[SceneVisualPlan] = list(
        await asyncio.gather(
            *[
                _critique_one_scene(
                    vp,
                    outline_by_index.get(vp.scene_index, SceneOutline(
                        scene_index=vp.scene_index,
                        title=vp.title,
                        description="",
                        duration_hint_seconds=30,
                        ),
                        ),
                    state, llm, store, tracker, rl,
                    )
                for vp in state.scene_visual_plans
                ],
            ),
        )

    all_failed = all(p.failed for p in refined_plans)
    final_status = "failed" if all_failed else "completed"

    store.save("visual_plans", {
        "session_id": state.session_id,
        "workflow_id": state.workflow_id,
        "total_scenes": len(refined_plans),
        "status": final_status,
        "scene_visual_plans": [p.model_dump() for p in refined_plans],
        },
        )

    if rl is not None:
        rl.pipeline_step("visual_plan_critique.done", {
            "total_scenes": len(refined_plans),
            "failed_scenes": sum(1 for p in refined_plans if p.failed),
            "status": final_status,
            },
            )

    return {
        "scene_visual_plans": refined_plans,
        "status": final_status,
        "error": None if not all_failed else "All scene plans failed critique",
        }
