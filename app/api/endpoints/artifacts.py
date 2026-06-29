"""artifacts.py — Endpoints to list and retrieve stored pipeline artifacts."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.schemas.intermediate import ArtifactRecordSchema
from app.api.schemas.response import ArtifactDetailResponse, ArtifactsListResponse
from app.core.artifact_store import ArtifactStore


router = APIRouter()


@router.get("/artifacts/{session_id}", response_model=ArtifactsListResponse)
async def list_artifacts(session_id: str) -> ArtifactsListResponse:
    """List all artifacts stored for a session."""
    store = ArtifactStore(session_id)
    return ArtifactsListResponse(
        session_id=session_id,
        artifacts=[ArtifactRecordSchema(**a) for a in store.list_artifacts()],
        )


@router.get("/artifact/{session_id}/{artifact_type}", response_model=ArtifactDetailResponse)
async def get_artifact(session_id: str, artifact_type: str) -> ArtifactDetailResponse:
    """Return the content of a named artifact.

    Use ``scene_NNN`` (e.g. ``scene_003``) for per-scene visual plans.
    """
    store = ArtifactStore(session_id)

    if artifact_type.startswith("scene_"):
        try:
            idx = int(artifact_type.split("_")[1])
        except (IndexError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid scene artifact name.")
        data = store.load_scene(idx)
    else:
        data = store.load(artifact_type)

    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Artifact '{artifact_type}' not found for session '{session_id}'.",
            )

    return ArtifactDetailResponse(
        session_id=session_id,
        artifact_type=artifact_type,
        data=data,
        )
