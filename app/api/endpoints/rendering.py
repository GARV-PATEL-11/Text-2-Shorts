"""rendering.py — Endpoints for render status and final video download."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.api.pipeline_runner import _tasks
from app.core.artifact_store import ArtifactStore
from app.core.stage_tracker import StageTracker


router = APIRouter()


@router.get("/render/status/{session_id}")
async def get_render_status(session_id: str) -> dict:
    """Per-scene render status with attempt counts and error details."""
    store = ArtifactStore(session_id)
    data = store.load("render_results")
    if data:
        return {"session_id": session_id, **data}

    if session_id not in _tasks:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    tracker = StageTracker.for_session(session_id)
    progress = tracker.get_scene_progress()
    return {"session_id": session_id, "scene_render_results": [], **progress}


@router.get("/video/{session_id}")
async def get_final_video(session_id: str) -> FileResponse:
    """Download the final assembled video for a session."""
    store = ArtifactStore(session_id)
    video_path = store.session_dir / "final_video.mp4"
    if not video_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Final video not yet available for session '{session_id}'.",
            )
    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=f"{session_id}_final.mp4",
        )
