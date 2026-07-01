"""scene_rendering.py — Node: render Manim scenes fully async (all scenes concurrent)."""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from app.core.config import settings
from app.core.context import node_name_var, request_logger_var, session_id_var, workflow_id_var
from app.core.logger import log_call, StructuredLogger
from app.core.stage_tracker import StageTracker
from app.graph.models.graph_state import GraphState
from app.graph.models.render_state import SceneManimCode, SceneRenderResult
from app.graph.nodes.manim_code_generation import _extract_python_block
from app.graph.nodes.utils import extract_class_name as _extract_class_name
from app.graph.prompts.render_debug_prompt import build_debug_user_prompt, RENDER_DEBUG_SYSTEM
from app.graph.retry import ainvoke_with_fallback
from app.services.factory import get_client, LLMProvider
from app.storage.artifact_store import ArtifactStore


logger = StructuredLogger.get_logger(__name__)

MAX_RENDER_ATTEMPTS = 5


def _find_rendered_clip(media_dir: Path) -> Path | None:
    """Find the first MP4 produced by Manim under the media directory."""
    clips = list(media_dir.rglob("*.mp4"))
    return clips[0] if clips else None


async def _run_manim_render(
        code_path: Path,
        class_name: str,
        media_dir: Path,
        ) -> tuple[int, str, str]:
    """Run `manim render` as an async subprocess. Returns (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        "python", "-m", "manim", "render",
        str(code_path),
        class_name,
        "-ql",
        "--media_dir", str(media_dir),
        "--disable_caching",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=settings.MANIM_TIMEOUT_S,
            )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return 1, "", f"Manim render timed out after {settings.MANIM_TIMEOUT_S}s"
    return proc.returncode or 0, stdout_bytes.decode(errors="replace"), stderr_bytes.decode(errors="replace")


async def _extract_thumbnail(clip_path: str, store: ArtifactStore, scene_index: int) -> str | None:
    """Extract the first frame of a clip as a JPEG thumbnail."""
    thumb_path = store.get_scene_thumbnail_path(scene_index, create=True)
    if not thumb_path:
        return None
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", clip_path,
        "-vframes", "1", "-q:v", "2",
        thumb_path,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
        )
    try:
        await asyncio.wait_for(proc.communicate(), timeout=30)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return None
    return thumb_path if proc.returncode == 0 else None


async def _render_one_scene(
        code_record: SceneManimCode,
        visual_plan_map: dict,
        llm,
        store: ArtifactStore,
        tracker: StageTracker,
        state: GraphState,
        ) -> SceneRenderResult:
    """Render a single scene with an iterative debug/refactor retry loop (max 5 attempts).

    The per-attempt debug loop within this coroutine is intentionally sequential
    because each attempt depends on the stderr of the previous render.
    All scenes' coroutines run concurrently via asyncio.gather in the node.
    """
    idx = code_record.scene_index

    if code_record.status == "FAILED":
        return SceneRenderResult(
            scene_index=idx,
            title=code_record.title,
            status="FAILED",
            last_error="Skipped: code generation failed",
            )

    existing_clip = store.get_scene_clip_path(idx)
    if existing_clip and Path(existing_clip).exists():
        return SceneRenderResult(
            scene_index=idx,
            title=code_record.title,
            status="READY",
            clip_path=existing_clip,
            thumbnail_path=store.get_scene_thumbnail_path(idx),
            )

    current_code = code_record.python_code
    result = SceneRenderResult(scene_index=idx, title=code_record.title)

    for attempt in range(1, MAX_RENDER_ATTEMPTS + 1):
        result.render_attempts = attempt

        attempt_dir = store.get_render_attempt_dir(idx, attempt)
        attempt_dir.mkdir(parents=True, exist_ok=True)
        code_path = attempt_dir / f"scene_{idx:03d}.py"
        code_path.write_text(current_code)

        tracker.update_scene_render_status(idx, "RENDERING")
        result.status = "RENDERING"

        class_name = _extract_class_name(current_code)
        if not class_name:
            result.status = "FAILED"
            result.last_error = "Could not extract Scene class name from generated code"
            break

        t_start = time.monotonic()

        logger.info(
            "Starting Manim render",
            extra={
                "session_id": state.session_id,
                "scene_index": idx,
                "attempt": attempt,
                "class_name": class_name,
                },
            )

        returncode, stdout, stderr = await _run_manim_render(
            code_path=code_path,
            class_name=class_name,
            media_dir=attempt_dir / "media",
            )

        duration_ms = round((time.monotonic() - t_start) * 1000, 1)
        result.render_duration_ms = int(duration_ms)

        (attempt_dir / "stdout.txt").write_text(stdout)
        (attempt_dir / "stderr.txt").write_text(stderr)

        if returncode == 0:
            clip_src = _find_rendered_clip(attempt_dir / "media")
            if clip_src:
                clip_dst = store.save_scene_clip(idx, clip_src)
                thumb_path = await _extract_thumbnail(clip_dst, store, idx)
                result.status = "READY"
                result.clip_path = clip_dst
                result.thumbnail_path = thumb_path
                result.final_code_path = str(code_path)
                tracker.update_scene_render_status(idx, "READY")

                logger.info(
                    "Scene rendered successfully",
                    extra={
                        "session_id": state.session_id,
                        "scene_index": idx,
                        "attempt": attempt,
                        "duration_ms": duration_ms,
                        },
                    )
                break
            else:
                stderr = "Manim exited 0 but no MP4 file found in media directory"
                returncode = 1

        result.status = "DEBUGGING"
        result.last_error = stderr[-2000:]
        result.render_stderr = stderr[-2000:]
        tracker.update_scene_render_status(idx, "DEBUGGING")

        logger.warning(
            "Manim render failed — invoking error debugger",
            extra={
                "session_id": state.session_id,
                "scene_index": idx,
                "attempt": attempt,
                "returncode": returncode,
                "stderr_tail": stderr[-500:],
                },
            )

        if attempt >= MAX_RENDER_ATTEMPTS:
            result.status = "FAILED"
            tracker.update_scene_render_status(idx, "FAILED")
            break

        visual_plan = visual_plan_map.get(idx)
        scene_dsl = (
            json.dumps(visual_plan.plan, indent=2)
            if visual_plan and isinstance(visual_plan.plan, dict)
            else (str(visual_plan.plan) if visual_plan else "")
        )

        debug_user_prompt = build_debug_user_prompt(
            scene_title=code_record.title,
            scene_dsl=scene_dsl,
            python_code=current_code,
            manim_stderr=stderr,
            attempt_number=attempt,
            )

        tok_s = session_id_var.set(state.session_id)
        tok_w = workflow_id_var.set(state.workflow_id)
        tok_n = node_name_var.set(f"scene_rendering/debug/scene_{idx}/attempt_{attempt}")

        try:
            result.status = "REFACTORING"
            tracker.update_scene_render_status(idx, "REFACTORING")

            debug_raw, _, _ = await ainvoke_with_fallback(
                llm,
                primary_model=settings.GEMINI_MODEL,
                fallback_model=settings.GEMINI_FALLBACK_MODEL,
                user_prompt=debug_user_prompt,
                system_prompt=RENDER_DEBUG_SYSTEM,
                temperature=0.1,
                )

            corrected_code = _extract_python_block(debug_raw)
            if corrected_code:
                current_code = corrected_code
                (attempt_dir / "debug_analysis.json").write_text(
                    json.dumps({
                        "attempt": attempt,
                        "fix_summary": debug_raw.split("B. CORRECTED PYTHON CODE")[0].strip(),
                        }, indent=2,
                        ),
                    )
                logger.info(
                    "Error debugger produced corrected code",
                    extra={"session_id": state.session_id, "scene_index": idx, "attempt": attempt},
                    )
            else:
                logger.warning(
                    "Error debugger returned no Python code block",
                    extra={"session_id": state.session_id, "scene_index": idx},
                    )

        except Exception as debug_exc:
            logger.error(
                "Error debugger LLM call failed",
                extra={"session_id": state.session_id, "scene_index": idx, "error": str(debug_exc)},
                )

        finally:
            session_id_var.reset(tok_s)
            workflow_id_var.reset(tok_w)
            node_name_var.reset(tok_n)

    return result


@log_call(stage="node:scene_rendering")
async def scene_rendering_node(state: GraphState) -> dict:
    """Render all Manim scenes fully concurrently (each with its own debug/refactor retry loop)."""
    if not state.scene_manim_codes:
        return {
            "scene_render_results": [],
            "status": "failed",
            "error": "scene_rendering requires manim_code_generation to run first",
            }

    rl = request_logger_var.get()
    llm = get_client(LLMProvider.GEMINI)
    store = ArtifactStore(state.session_id)
    tracker = StageTracker.for_session(state.session_id)

    if rl:
        rl.pipeline_step("scene_rendering.start", {
            "session_id": state.session_id,
            "total_scenes": len(state.scene_manim_codes),
            },
            )

    visual_plan_map = {p.scene_index: p for p in state.scene_visual_plans}

    scene_render_results: list[SceneRenderResult] = list(
        await asyncio.gather(
            *[
                _render_one_scene(code_record, visual_plan_map, llm, store, tracker, state)
                for code_record in state.scene_manim_codes
                ],
            ),
        )

    all_failed = all(r.status == "FAILED" for r in scene_render_results)
    final_status = "failed" if all_failed else "completed"

    if rl:
        rl.pipeline_step("scene_rendering.done", {
            "total_scenes": len(scene_render_results),
            "ready_scenes": sum(1 for r in scene_render_results if r.status == "READY"),
            "failed_scenes": sum(1 for r in scene_render_results if r.status == "FAILED"),
            "status": final_status,
            }
            )

    store.save("render_results", {
        "session_id": state.session_id,
        "total_scenes": len(scene_render_results),
        "ready": sum(1 for r in scene_render_results if r.status == "READY"),
        "failed": sum(1 for r in scene_render_results if r.status == "FAILED"),
        "results": [r.model_dump() for r in scene_render_results],
        }
        )

    return {
        "scene_render_results": scene_render_results,
        "status": final_status,
        "error": None if not all_failed else "All scenes failed rendering",
        }
