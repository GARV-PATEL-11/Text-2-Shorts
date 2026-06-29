"""sessions.py — Endpoints for listing and inspecting saved sessions."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.schemas.intermediate import ArtifactRecordSchema, SessionRecordSchema
from app.api.schemas.response import SessionDetailResponse, SessionsListResponse
from app.core.artifact_store import ArtifactStore, SessionIndex


router = APIRouter()


@router.get("/sessions", response_model=SessionsListResponse)
async def list_sessions() -> SessionsListResponse:
    """List all previously run sessions from the global session index."""
    sessions = SessionIndex.list_all()
    return SessionsListResponse(
        sessions=[SessionRecordSchema(**s) for s in sessions],
        total=len(sessions),
        )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(session_id: str) -> SessionDetailResponse:
    """Detail for one session including artifact inventory."""
    entry = SessionIndex.get(session_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    store = ArtifactStore(session_id)
    artifacts = store.list_artifacts()
    completed_scenes = store.list_completed_scene_indices()

    return SessionDetailResponse(
        session_id=session_id,
        approach=entry.get("approach", ""),
        requirement_preview=entry.get("requirement_preview", ""),
        pipeline_status=entry.get("pipeline_status", "unknown"),
        completed_stages=entry.get("completed_stages", []),
        total_scenes=entry.get("total_scenes", 0),
        created_at=entry.get("created_at", 0.0),
        last_updated=entry.get("last_updated", 0.0),
        artifacts=[ArtifactRecordSchema(**a) for a in artifacts],
        completed_scene_count=len(completed_scenes),
        can_resume=(
                entry.get("pipeline_status") in ("failed", "running")
                and store.exists("refined_input")
        ),
        )
