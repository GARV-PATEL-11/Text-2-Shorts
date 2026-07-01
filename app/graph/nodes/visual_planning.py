"""visual_planning.py — Node: generate per-scene Visual DSL plans."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.core.context import node_name_var, request_logger_var, session_id_var, workflow_id_var
from app.core.logger import log_call, StructuredLogger
from app.core.stage_tracker import StageTracker
from app.graph.models.base_models import BaseVideoMeta
from app.graph.models.graph_state import GraphState
from app.graph.models.visual_planning_state import SceneOutline, SceneVisualPlan
from app.graph.nodes.utils import save_output_to_log
from app.graph.prompts.visual_plan_gen_prompt import generate_visual_plan_prompt, SceneDirectorInput
from app.graph.retry import ainvoke_with_fallback
from app.services.factory import get_client, LLMProvider
from app.storage.artifact_store import ArtifactStore


logger = StructuredLogger.get_logger(__name__)


def _parse_plan(raw: str) -> dict | str:
    """Try to deserialise the LLM's raw output into a dict; fall back to str."""
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            cleaned = cleaned.rsplit("```", 1)[0].strip()
        return json.loads(cleaned)
    except (json.JSONDecodeError, AttributeError, ValueError):
        return raw


def _map_outline(raw_outline: dict[str, Any]) -> tuple[BaseVideoMeta, list[SceneOutline]]:
    """Pure transform: outline dict → (metadata, video_outline).

    This was previously a separate ``map_outline`` LangGraph node.  It is
    inlined here because it is a trivial synchronous data transform with no
    I/O and no value as a standalone pipeline stage.
    """
    raw_meta: dict[str, Any] = raw_outline.get("meta", {})
    segments: list[dict[str, Any]] = raw_outline.get("outline", [])

    metadata = BaseVideoMeta(
        title=raw_meta.get("title", ""),
        topic=raw_meta.get("topic", "video"),
        total_duration_seconds=max(1, raw_meta.get("total_duration_seconds", 60)),
        pace=raw_meta.get("pace", "medium"),
        target_wpm=max(1, raw_meta.get("target_wpm", 140)),
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

    return metadata, video_outline


async def _plan_one_scene(
        scene: SceneOutline,
        video_metadata_json: str,
        llm,
        store: ArtifactStore,
        tracker: StageTracker,
        state: GraphState,
        rl,
        ) -> SceneVisualPlan:
    """Generate a Visual DSL plan for one scene (runs concurrently with all others)."""
    existing = store.load_scene(scene.scene_index)
    if existing and not existing.get("error"):
        try:
            plan = SceneVisualPlan(**existing)
            tracker.complete_scene(scene.scene_index)
            return plan
        except Exception:
            pass

    tracker.start_scene(scene.scene_index)

    director_input = SceneDirectorInput(
        video_metadata=video_metadata_json,
        target_scene_id=f"scene_{scene.scene_index:03d}",
        target_scene=json.dumps({
            "scene_index": scene.scene_index,
            "title": scene.title,
            "description": scene.description,
            "duration_seconds": scene.duration_hint_seconds,
            "narration_text": scene.narration_text,
            }, indent=2
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
            }
            )

    try:
        plan_raw, model_used, total_attempts = await ainvoke_with_fallback(
            llm,
            primary_model=settings.GEMINI_MODEL,
            fallback_model=settings.GEMINI_FALLBACK_MODEL,
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
                }
                )

        return visual_plan

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
                }
                )
        tracker.fail_scene(scene.scene_index, str(exc))
        return SceneVisualPlan(
            scene_index=scene.scene_index,
            title=scene.title,
            plan={},
            error=str(exc),
            )

    finally:
        session_id_var.reset(tok_s)
        workflow_id_var.reset(tok_w)
        node_name_var.reset(tok_n)


@log_call(stage="node:visual_planning")
async def visual_planning_node(state: GraphState) -> dict:
    """Map the raw outline dict to typed scenes, then generate Visual DSL plans concurrently."""
    raw_outline: dict[str, Any] = state.outline or {}
    segments = raw_outline.get("outline", [])

    if not segments:
        return {
            "scene_visual_plans": [],
            "total_scenes": 0,
            "video_outline": [],
            "status": "failed",
            "error": "Outline contained no scenes; cannot proceed to visual planning",
            }

    metadata, video_outline = _map_outline(raw_outline)
    total_scenes = len(video_outline)

    rl = request_logger_var.get()
    llm = get_client(LLMProvider.GEMINI)
    store = ArtifactStore(state.session_id)
    tracker = StageTracker.for_session(state.session_id)
    tracker.init_scenes(video_outline)

    if rl is not None:
        rl.pipeline_step("visual_planning.start", {
            "session_id": state.session_id,
            "total_scenes": total_scenes,
            "primary_model": settings.GEMINI_MODEL,
            }
            )

    video_metadata_json = json.dumps({
        "title": metadata.title,
        "topic": metadata.topic,
        "total_scenes": total_scenes,
        "total_duration_seconds": metadata.total_duration_seconds,
        "scenes": [
            {
                "scene_index": s.scene_index,
                "title": s.title,
                "duration_hint_seconds": s.duration_hint_seconds,
                }
            for s in video_outline
            ],
        }, indent=2
        )

    scene_visual_plans: list[SceneVisualPlan] = list(
        await asyncio.gather(
            *[
                _plan_one_scene(scene, video_metadata_json, llm, store, tracker, state, rl)
                for scene in video_outline
                ],
            )
        )

    all_failed = all(p.failed for p in scene_visual_plans)
    final_status = "failed" if all_failed else "completed"

    store.save("visual_plans", {
        "session_id": state.session_id,
        "workflow_id": state.workflow_id,
        "total_scenes": total_scenes,
        "status": final_status,
        "scene_visual_plans": [p.model_dump() for p in scene_visual_plans],
        }
        )

    save_output_to_log(
        f"visual_plans_{state.session_id}.txt",
        {
            "session_id": state.session_id,
            "workflow_id": state.workflow_id,
            "primary_model": settings.GEMINI_MODEL,
            "fallback_model": settings.GEMINI_FALLBACK_MODEL,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_scenes": total_scenes,
            "scene_visual_plans": [p.model_dump() for p in scene_visual_plans],
            },
        )

    if rl is not None:
        rl.pipeline_step("visual_planning.done", {
            "total_scenes": total_scenes,
            "failed_scenes": sum(1 for p in scene_visual_plans if p.failed),
            "status": final_status,
            }
            )

    return {
        "total_scenes": total_scenes,
        "metadata": metadata,
        "video_outline": video_outline,
        "scene_visual_plans": scene_visual_plans,
        "status": final_status,
        "error": scene_visual_plans[0].error if all_failed else None,
        }
