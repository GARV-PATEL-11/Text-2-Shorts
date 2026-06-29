from __future__ import annotations

from pydantic import BaseModel, Field


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
    status: str = "PENDING"  # PENDING | GENERATING | READY | FAILED
    error: str | None = None


class SceneRenderResult(BaseModel):
    scene_index: int
    title: str
    status: str = "PENDING"  # PENDING | RENDERING | DEBUGGING | REFACTORING | READY | FAILED
    clip_path: str | None = None
    thumbnail_path: str | None = None
    render_attempts: int = 0
    last_error: str | None = None
    render_stderr: str | None = None
    render_duration_ms: int | None = None
    final_code_path: str | None = None
