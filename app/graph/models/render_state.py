from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SceneCodeStatus(str, Enum):
    PENDING = "PENDING"
    GENERATING = "GENERATING"
    READY = "READY"
    FAILED = "FAILED"


class SceneRenderStatus(str, Enum):
    PENDING = "PENDING"
    RENDERING = "RENDERING"
    DEBUGGING = "DEBUGGING"
    REFACTORING = "REFACTORING"
    READY = "READY"
    FAILED = "FAILED"


class RenderError(BaseModel):
    scene_index: int
    error_message: str
    stdout: str
    stderr: str


class SceneManimCode(BaseModel):
    scene_index: int
    title: str
    python_code: str | None = None
    python_file_path: str | None = None
    implementation_summary: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    model_used: str | None = None
    total_code_gen_attempts: int = 0
    status: SceneCodeStatus = SceneCodeStatus.PENDING
    error: str | None = None


class SceneRenderResult(BaseModel):
    scene_index: int
    title: str
    status: SceneRenderStatus = SceneRenderStatus.PENDING
    clip_path: str | None = None
    thumbnail_path: str | None = None
    render_attempts: int = 0
    last_error: str | None = None
    render_stderr: str | None = None
    render_duration_ms: int | None = None
    final_code_path: str | None = None
