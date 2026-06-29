from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.graph.models.base_models import BaseVideoMeta
from app.graph.models.enums import NarrativeApproach
from app.graph.models.render_state import SceneManimCode, SceneRenderResult
from app.graph.models.visual_planning_state import SceneOutline, SceneVisualPlan


class GraphState(BaseModel):
    """Single Pydantic model that LangGraph operates on internally.

    Fields are populated progressively as each node executes.
    use_enum_values=True serialises NarrativeApproach as its string value
    so msgpack-based checkpointers can round-trip the state correctly.
    """

    model_config = ConfigDict(use_enum_values=True)

    session_id: str
    approach: NarrativeApproach
    requirement: str
    workflow_id: str = Field(default_factory=lambda: uuid4().hex)

    system_prompt: str | None = None
    routed_to: str | None = None
    refined_requirement: str | None = None

    outline: dict | None = None
    outline_type: str | None = None

    total_scenes: int = 0
    metadata: BaseVideoMeta | None = None
    video_outline: list[SceneOutline] = Field(default_factory=list)

    scene_visual_plans: list[SceneVisualPlan] = Field(default_factory=list)
    scene_manim_codes: list[SceneManimCode] = Field(default_factory=list)
    scene_render_results: list[SceneRenderResult] = Field(default_factory=list)

    final_video_path: str | None = None
    render_stats: dict | None = None

    status: str = "pending"
    error: str | None = None
