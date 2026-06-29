"""video_assembly.py — Node: compose rendered scene clips into a final video."""
from __future__ import annotations

import asyncio
import time
from pathlib import Path

from app.core.config import settings
from app.core.context import request_logger_var
from app.core.logger import log_call, StructuredLogger
from app.graph.models.graph_state import GraphState
from app.storage.artifact_store import ArtifactStore


logger = StructuredLogger.get_logger(__name__)


async def _run_ffmpeg_concat(concat_file: Path, output_path: Path) -> tuple[int, str, str]:
    """Run FFmpeg stream-copy concat. Returns (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=settings.FFMPEG_TIMEOUT_S,
            )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return 1, "", f"FFmpeg timed out after {settings.FFMPEG_TIMEOUT_S}s"
    return proc.returncode or 0, stdout_bytes.decode(errors="replace"), stderr_bytes.decode(errors="replace")


@log_call(stage="node:video_assembly")
async def video_assembly_node(state: GraphState) -> dict:
    """Compose all READY scene clips into a single silent video using FFmpeg."""
    ready_clips = sorted(
        [r for r in state.scene_render_results if r.status == "READY"],
        key=lambda r: r.scene_index,
        )

    if not ready_clips:
        return {
            "final_video_path": None,
            "render_stats": None,
            "status": "failed",
            "error": "No rendered scene clips available for assembly",
            }

    rl = request_logger_var.get()
    store = ArtifactStore(state.session_id)

    if rl:
        rl.pipeline_step("video_assembly.start", {
            "session_id": state.session_id,
            "ready_clips": len(ready_clips),
            "total_scenes": state.total_scenes,
            },
            )

    concat_path = store.session_dir / "concat.txt"
    concat_lines = [f"file '{Path(r.clip_path).resolve()}'" for r in ready_clips]
    concat_path.write_text("\n".join(concat_lines))

    output_path = store.session_dir / "final_video.mp4"

    logger.info(
        "Assembling video",
        extra={
            "session_id": state.session_id,
            "clip_count": len(ready_clips),
            "output": str(output_path),
            },
        )

    t_start = time.monotonic()
    returncode, stdout, stderr = await _run_ffmpeg_concat(concat_path, output_path)
    duration_ms = round((time.monotonic() - t_start) * 1000, 1)

    if returncode != 0:
        logger.error(
            "FFmpeg assembly failed",
            extra={"session_id": state.session_id, "stderr": stderr[-500:]},
            )
        return {
            "final_video_path": None,
            "render_stats": None,
            "status": "failed",
            "error": f"FFmpeg assembly failed: {stderr[-500:]}",
            }

    video_path_str = str(output_path)
    render_stats = {
        "total_scenes": state.total_scenes,
        "ready_scenes": len(ready_clips),
        "failed_scenes": sum(1 for r in state.scene_render_results if r.status == "FAILED"),
        "scene_indices": [r.scene_index for r in ready_clips],
        "assembly_duration_ms": int(duration_ms),
        }

    store.save("video_stats", render_stats)

    logger.info(
        "Video assembled successfully",
        extra={"session_id": state.session_id, "output": video_path_str, "duration_ms": duration_ms},
        )

    if rl:
        rl.pipeline_step("video_assembly.done", {
            "status": "completed",
            "output": video_path_str,
            "duration_ms": duration_ms,
            },
            )

    return {
        "final_video_path": video_path_str,
        "render_stats": render_stats,
        "status": "completed",
        "error": None,
        }
