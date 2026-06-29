"""response.py — Typed response models for all API endpoints."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.api.schemas.enums import NarrativeApproach
from app.api.schemas.intermediate import (
    ArtifactRecordSchema,
    SceneOutlineSchema,
    SceneProgressItemSchema,
    SceneRenderResultSchema,
    SceneVisualPlanSchema,
    SessionRecordSchema,
    StageRecordSchema,
    )


# ── pipeline.py ───────────────────────────────────────────────────────────────

class GenerateResponse(BaseModel):
    session_id: str
    workflow_id: str
    approach: NarrativeApproach
    status: Literal["queued", "running", "completed", "failed"]


class ResumeResponse(BaseModel):
    session_id: str
    resumed_from: str
    pre_completed_stages: list[str]
    status: str


# ── status.py ─────────────────────────────────────────────────────────────────

class StatusResponse(BaseModel):
    session_id: str
    workflow_id: str
    stage: str
    status: str
    outline_type: str | None = None
    outline: dict[str, Any] | None = None
    video_outline: list[SceneOutlineSchema] = Field(default_factory=list)
    scene_visual_plans: list[SceneVisualPlanSchema] = Field(default_factory=list)
    total_scenes: int = 0
    error: str | None = None


class StagesResponse(BaseModel):
    session_id: str
    pipeline_status: str
    stages: list[StageRecordSchema]
    error: str | None = None


class StageDetailResponse(BaseModel):
    session_id: str
    stage: str
    label: str
    status: str
    node_name: str
    duration_ms: float | None = None
    output_summary: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] | None = None
    error: str | None = None


# ── outputs.py ────────────────────────────────────────────────────────────────

class OutlineOutputResponse(BaseModel):
    session_id: str
    outline: dict[str, Any] | None = None
    outline_type: str | None = None
    status: str | None = None


class ScenesOutputResponse(BaseModel):
    session_id: str
    scene_visual_plans: list[SceneVisualPlanSchema] = Field(default_factory=list)
    total_scenes: int = 0
    status: str | None = None


# ── scenes.py ─────────────────────────────────────────────────────────────────

class SceneProgressResponse(BaseModel):
    session_id: str
    total: int
    completed: int
    failed: int
    running_index: int | None = None
    scenes: list[SceneProgressItemSchema] = Field(default_factory=list)


# ── rendering.py ──────────────────────────────────────────────────────────────

class RenderStatusResponse(BaseModel):
    session_id: str
    total_scenes: int = 0
    ready: int = 0
    failed: int = 0
    scene_render_results: list[SceneRenderResultSchema] = Field(default_factory=list)


# ── sessions.py ───────────────────────────────────────────────────────────────

class SessionsListResponse(BaseModel):
    sessions: list[SessionRecordSchema]
    total: int


class SessionDetailResponse(BaseModel):
    session_id: str
    approach: str = ""
    requirement_preview: str = ""
    pipeline_status: str
    completed_stages: list[str] = Field(default_factory=list)
    total_scenes: int = 0
    created_at: float
    last_updated: float
    artifacts: list[ArtifactRecordSchema] = Field(default_factory=list)
    completed_scene_count: int = 0
    can_resume: bool = False


# ── artifacts.py ──────────────────────────────────────────────────────────────

class ArtifactsListResponse(BaseModel):
    session_id: str
    artifacts: list[ArtifactRecordSchema]


class ArtifactDetailResponse(BaseModel):
    session_id: str
    artifact_type: str
    data: dict[str, Any]
