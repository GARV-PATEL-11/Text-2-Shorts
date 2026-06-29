"""sessions.py — Endpoints for listing and inspecting saved sessions."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.artifact_store import ArtifactStore, SessionIndex


router = APIRouter()


@router.get("/sessions")
async def list_sessions() -> dict:
    """List all previously run sessions from the global session index."""
    sessions = SessionIndex.list_all()
    return {"sessions": sessions, "total": len(sessions)}


@router.get("/sessions/{session_id}")
async def get_session_detail(session_id: str) -> dict:
    """Detail for one session including artifact inventory."""
    entry = SessionIndex.get(session_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    store = ArtifactStore(session_id)
    artifacts = store.list_artifacts()
    completed_scenes = store.list_completed_scene_indices()

    return {
        **entry,
        "artifacts": artifacts,
        "completed_scene_count": len(completed_scenes),
        "can_resume": (
                entry.get("pipeline_status") in ("failed", "running")
                and store.exists("refined_input")
        ),
        }
