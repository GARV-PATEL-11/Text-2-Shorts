"""artifacts.py — Endpoints to list and retrieve stored pipeline artifacts."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.artifact_store import ArtifactStore


router = APIRouter()


@router.get("/artifacts/{session_id}")
async def list_artifacts(session_id: str) -> dict:
    """List all artifacts stored for a session."""
    store = ArtifactStore(session_id)
    return {"session_id": session_id, "artifacts": store.list_artifacts()}


@router.get("/artifact/{session_id}/{artifact_type}")
async def get_artifact(session_id: str, artifact_type: str) -> dict:
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

    return {"session_id": session_id, "artifact_type": artifact_type, "data": data}
