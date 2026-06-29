"""scenes.py — Endpoints for scene-level progress and clip downloads."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.api.pipeline_runner import _tasks
from app.api.schemas.intermediate import SceneProgressItemSchema
from app.api.schemas.response import SceneProgressResponse
from app.core.artifact_store import ArtifactStore
from app.core.stage_tracker import StageTracker


router = APIRouter()


@router.get("/scenes/{session_id}/progress", response_model=SceneProgressResponse)
async def get_scene_progress(session_id: str) -> SceneProgressResponse:
    """Per-scene progress during the visual planning stage."""
    if session_id not in _tasks:
        store = ArtifactStore(session_id)
        completed_indices = store.list_completed_scene_indices()
        if not completed_indices:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
        return SceneProgressResponse(
            session_id=session_id,
            total=len(completed_indices),
            completed=len(completed_indices),
            failed=0,
            running_index=None,
            scenes=[
                SceneProgressItemSchema(
                    scene_index=i, title="", status="completed", duration_ms=None, error=None,
                    )
                for i in completed_indices
                ],
            )

    tracker = StageTracker.for_session(session_id)
    progress = tracker.get_scene_progress()
    return SceneProgressResponse(session_id=session_id, **progress)


@router.get("/scenes/{session_id}/{scene_index}/clip")
async def get_scene_clip(session_id: str, scene_index: int) -> FileResponse:
    """Download the rendered clip for a single scene."""
    store = ArtifactStore(session_id)
    clip_path = store.get_scene_clip_path(scene_index)
    if not clip_path or not Path(clip_path).exists():
        raise HTTPException(
            status_code=404,
            detail=f"Clip for scene {scene_index} not found in session '{session_id}'.",
            )
    return FileResponse(path=clip_path, media_type="video/mp4", filename=f"scene_{scene_index:03d}.mp4")
