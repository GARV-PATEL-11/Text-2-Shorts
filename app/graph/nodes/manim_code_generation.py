"""manim_code_generation.py — Node: generate Manim Python code from Visual DSL."""
from __future__ import annotations

import asyncio
import json
import re

from app.core.config import settings
from app.core.context import node_name_var, request_logger_var, session_id_var, workflow_id_var
from app.core.logger import log_call, StructuredLogger
from app.core.stage_tracker import StageTracker
from app.graph.models.graph_state import GraphState
from app.graph.models.render_state import SceneManimCode
from app.graph.models.visual_planning_state import SceneVisualPlan
from app.graph.nodes.utils import extract_class_name as _extract_class_name  # noqa: F401 (re-exported for
# scene_rendering)
from app.graph.prompts.visual_code_gen_prompt import build_user_prompt, SYSTEM_PROMPT as CODE_GEN_SYSTEM
from app.graph.retry import ainvoke_with_fallback
from app.services.factory import get_client, LLMProvider
from app.storage.artifact_store import ArtifactStore


logger = StructuredLogger.get_logger(__name__)


def _extract_python_block(text: str) -> str | None:
    """Extract the first ```python ... ``` code block from LLM output."""
    match = re.search(r"```python\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"```\s*\n(from manim.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def _parse_code_gen_response(raw: str) -> tuple[str | None, str, list[str]]:
    """Parse the LLM code-gen response into (python_code, summary, assumptions)."""
    summary_match = re.search(
        r"A\.\s*IMPLEMENTATION\s*SUMMARY\s*\n(.*?)(?=B\.\s*PYTHON\s*CODE)",
        raw, re.DOTALL | re.IGNORECASE,
        )
    summary = summary_match.group(1).strip() if summary_match else ""

    python_code = _extract_python_block(raw)

    assumptions_match = re.search(
        r"C\.\s*ASSUMPTIONS\s*\n(.*?)$",
        raw, re.DOTALL | re.IGNORECASE,
        )
    assumptions: list[str] = []
    if assumptions_match:
        for line in assumptions_match.group(1).strip().splitlines():
            line = line.strip()
            if line:
                assumptions.append(line)

    return python_code, summary, assumptions


async def _generate_scene_code(
        visual_plan: SceneVisualPlan,
        llm,
        store: ArtifactStore,
        tracker,
        session_id: str,
        workflow_id: str,
        ) -> SceneManimCode:
    """Generate Manim code for a single scene."""
    idx = visual_plan.scene_index

    if visual_plan.error:
        tracker.update_scene_render_status(idx, "FAILED")
        return SceneManimCode(
            scene_index=idx,
            title=visual_plan.title,
            status="FAILED",
            error=f"Skipped: upstream visual plan failed — {visual_plan.error}",
            )

    existing_meta = store.load_scene_code_meta(idx)
    if existing_meta and existing_meta.get("status") == "READY":
        return SceneManimCode(**existing_meta)

    tracker.update_scene_render_status(idx, "GENERATING")

    tok_s = session_id_var.set(session_id)
    tok_w = workflow_id_var.set(workflow_id)
    tok_n = node_name_var.set(f"manim_code_generation/scene_{idx}")

    try:
        plan_str = (
            json.dumps(visual_plan.plan, indent=2)
            if isinstance(visual_plan.plan, dict)
            else str(visual_plan.plan)
        )
        user_prompt = build_user_prompt(plan_str)

        raw, model_used, total_attempts = await ainvoke_with_fallback(
            llm,
            primary_model=settings.GEMINI_MODEL,
            fallback_model=settings.GEMINI_FALLBACK_MODEL,
            user_prompt=user_prompt,
            system_prompt=CODE_GEN_SYSTEM,
            temperature=0.2,
            )

        python_code, summary, assumptions = _parse_code_gen_response(raw)

        if python_code is None:
            raise ValueError("LLM response did not contain a Python code block")

        py_path = store.save_scene_code(idx, python_code)

        code_record = SceneManimCode(
            scene_index=idx,
            title=visual_plan.title,
            python_code=python_code,
            python_file_path=py_path,
            implementation_summary=summary,
            assumptions=assumptions,
            model_used=model_used,
            total_code_gen_attempts=total_attempts,
            status="READY",
            )
        store.save_scene_code_meta(idx, code_record.model_dump())
        tracker.update_scene_render_status(idx, "READY")

        logger.info(
            "Manim code generated",
            extra={
                "session_id": session_id,
                "scene_index": idx,
                "model_used": model_used,
                "total_attempts": total_attempts,
                "code_lines": len(python_code.splitlines()),
                },
            )
        return code_record

    except Exception as exc:
        logger.error(
            "Manim code generation failed",
            extra={"session_id": session_id, "scene_index": idx, "error": str(exc)},
            )
        tracker.update_scene_render_status(idx, "FAILED")
        return SceneManimCode(
            scene_index=idx,
            title=visual_plan.title,
            status="FAILED",
            error=str(exc),
            )

    finally:
        session_id_var.reset(tok_s)
        workflow_id_var.reset(tok_w)
        node_name_var.reset(tok_n)


@log_call(stage="node:manim_code_generation")
async def manim_code_generation_node(state: GraphState) -> dict:
    """Generate Manim Python for every scene with a valid Visual DSL plan (all scenes in parallel)."""
    if not state.scene_visual_plans:
        return {
            "scene_manim_codes": [],
            "status": "failed",
            "error": "manim_code_generation requires visual_planning to run first",
            }

    rl = request_logger_var.get()
    llm = get_client(LLMProvider.GEMINI)
    store = ArtifactStore(state.session_id)
    tracker = StageTracker.for_session(state.session_id)

    if rl:
        rl.pipeline_step("manim_code_generation.start", {
            "session_id": state.session_id,
            "total_scenes": len(state.scene_visual_plans),
            },
            )

    scene_manim_codes: list[SceneManimCode] = list(
        await asyncio.gather(
            *[
                _generate_scene_code(
                    vp, llm, store, tracker,
                    state.session_id, state.workflow_id,
                    )
                for vp in state.scene_visual_plans
                ],
            ),
        )

    all_failed = all(c.status == "FAILED" for c in scene_manim_codes)
    final_status = "failed" if all_failed else "completed"

    if rl:
        rl.pipeline_step("manim_code_generation.done", {
            "total_scenes": len(scene_manim_codes),
            "failed_scenes": sum(1 for c in scene_manim_codes if c.status == "FAILED"),
            "status": final_status,
            },
            )

    return {
        "scene_manim_codes": scene_manim_codes,
        "status": final_status,
        "error": None if not all_failed else "All scenes failed code generation",
        }
