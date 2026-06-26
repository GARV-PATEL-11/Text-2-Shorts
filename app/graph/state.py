"""
state.py
--------
Pydantic input/output state contracts for each graph node.

LangGraph operates on the single GraphState accumulator.  Per-node types
(RefinedOutputState, OutlineOutputState, etc.) document what each node reads
and writes; they are type hints, not runtime-enforced contracts.

Serialisation note: model_config = ConfigDict(use_enum_values=True) on
GraphState ensures Enum fields are stored as their plain string values,
making checkpoints safe for msgpack-based persistent backends.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.graph.models.base_models import BaseVideoMeta
from app.graph.models.enums import NarrativeApproach


# ── Shared sub-models ─────────────────────────────────────────────────────────

class RenderError(BaseModel):
    scene_index: int
    error_message: str
    stdout: str
    stderr: str


# ── LangGraph accumulated state ───────────────────────────────────────────────

class GraphState(BaseModel):
    """Single Pydantic model that LangGraph operates on internally.

    Fields are populated progressively as each node executes.
    use_enum_values=True serialises NarrativeApproach as its string value
    so msgpack-based checkpointers can round-trip the state correctly.
    """

    model_config = ConfigDict(use_enum_values=True)

    # Set at graph entry
    session_id: str
    approach: NarrativeApproach
    requirement: str
    workflow_id: str = Field(default_factory=lambda: uuid4().hex)

    # Written by validate_input
    system_prompt: str | None = None
    routed_to: str | None = None
    refined_requirement: str | None = None

    # Written by outline generators
    outline: dict | None = None
    outline_type: str | None = None

    # Written by map_outline_to_visual_plan
    total_scenes: int = 0
    metadata: BaseVideoMeta | None = None
    video_outline: list[SceneOutline] = Field(default_factory=list)

    # Written by visual_planning
    scene_visual_plans: list[SceneVisualPlan] = Field(default_factory=list)

    # Cross-node tracking
    status: str = "pending"
    error: str | None = None


class UserInputState(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    session_id: str
    workflow_id: str = Field(default_factory=lambda: uuid4().hex)
    approach: NarrativeApproach
    requirement: str
    status: Literal["ready", "routed", "failed"]
    error: str | None = None


class RefinedOutputState(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    session_id: str
    workflow_id: str
    system_prompt: str
    approach: NarrativeApproach
    refined_requirement: str
    status: Literal["ready", "routed", "failed"]
    error: str | None = None


OutlineInputState = RefinedOutputState


class OutlineOutputState(BaseModel):
    session_id: str
    workflow_id: str
    outline: dict
    outline_type: str | None = None
    status: Literal["completed", "failed"]
    error: str | None = None


# ── Scene-level sub-models ────────────────────────────────────────────────────

class SceneOutline(BaseModel):
    """One scene entry within the video plan."""

    scene_index: int
    title: str
    description: str
    duration_hint_seconds: int
    narration_text: str | None = None


# ── Visual DSL states ─────────────────────────────────────────────────────────

class SceneVisualPlan(BaseModel):
    """Structured record for a single scene's completed Visual DSL plan.

    plan is dict[str, Any] | str:
      - dict → successful JSON parse of the LLM's structured output
      - str  → fallback when JSON parsing fails; raw LLM text is preserved
    """

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
    """Input contract for visual_planning_node."""

    session_id: str
    workflow_id: str
    total_scenes: int
    metadata: BaseVideoMeta
    video_outline: list[SceneOutline]


class VisualDSLOutputState(BaseModel):
    """Final output of the visual planning graph node."""

    session_id: str
    workflow_id: str
    total_scenes: int
    video_outline: list[SceneOutline]
    scene_visual_plans: list[SceneVisualPlan]
    status: Literal["completed", "failed"]
    error: str | None = None
