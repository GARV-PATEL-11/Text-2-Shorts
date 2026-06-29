"""intermediate.py — Shared sub-schemas used across multiple API response models."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SceneOutlineSchema(BaseModel):
    scene_index: int
    title: str
    description: str
    duration_hint_seconds: int
    narration_text: str | None = None


class SceneVisualPlanSchema(BaseModel):
    scene_index: int
    title: str
    model_used: str | None = None
    total_attempts: int | None = None
    plan: dict[str, Any] | str
    error: str | None = None


class SceneManimCodeSchema(BaseModel):
    scene_index: int
    title: str
    python_code: str | None = None
    python_file_path: str | None = None
    implementation_summary: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    model_used: str | None = None
    total_code_gen_attempts: int = 0
    status: str = "PENDING"
    error: str | None = None


class SceneRenderResultSchema(BaseModel):
    scene_index: int
    title: str
    status: str = "PENDING"
    clip_path: str | None = None
    thumbnail_path: str | None = None
    render_attempts: int = 0
    last_error: str | None = None
    render_stderr: str | None = None
    render_duration_ms: int | None = None
    final_code_path: str | None = None


class StageRecordSchema(BaseModel):
    stage: str
    label: str
    status: str
    node_name: str
    duration_ms: float | None = None
    output_summary: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class SceneProgressItemSchema(BaseModel):
    scene_index: int
    title: str
    status: str
    duration_ms: float | None = None
    error: str | None = None


class ArtifactRecordSchema(BaseModel):
    artifact_type: str
    label: str
    path: str
    size_bytes: int
    modified_at: float


class SessionRecordSchema(BaseModel):
    session_id: str
    approach: str = ""
    requirement_preview: str = ""
    pipeline_status: str
    completed_stages: list[str] = Field(default_factory=list)
    total_scenes: int = 0
    created_at: float
    last_updated: float
