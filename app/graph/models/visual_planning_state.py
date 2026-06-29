from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.graph.models.base_models import BaseVideoMeta


class SceneOutline(BaseModel):
    scene_index: int
    title: str
    description: str
    duration_hint_seconds: int
    narration_text: str | None = None


class SceneVisualPlan(BaseModel):
    scene_index: int
    title: str
    model_used: str | None = None
    total_attempts: int | None = None
    plan: dict[str, Any] | str = Field(
        description=(
            "LLM-generated Visual DSL output for this scene. "
            "Inner schema to be formalised in a follow-up iteration."
        ),
        )
    error: str | None = None

    @property
    def failed(self) -> bool:
        return self.error is not None


class VisualDSLInputState(BaseModel):
    session_id: str
    workflow_id: str
    total_scenes: int
    metadata: BaseVideoMeta
    video_outline: list[SceneOutline]


class VisualDSLOutputState(BaseModel):
    session_id: str
    workflow_id: str
    total_scenes: int
    video_outline: list[SceneOutline]
    scene_visual_plans: list[SceneVisualPlan]
    status: Literal["completed", "failed"]
    error: str | None = None
