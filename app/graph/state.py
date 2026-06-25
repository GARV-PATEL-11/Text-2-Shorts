"""
state.py
--------
Pydantic input/output state contracts for each graph node.

Design: strict input/output pairs — each node has its own InputState and
OutputState. The transform functions in edges.py explicitly map a node's
output to the next node's input before it enters that node.

LangGraph operates on the single GraphState accumulator at runtime.
The per-node types document what each node reads and writes.
"""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.graph.models.enums import NarrativeApproach


# ── Shared sub-models ─────────────────────────────────────────────────────────

class SceneOutline(BaseModel):
    scene_index: int
    title: str
    description: str
    duration_hint_seconds: int
    narration_text: str | None = None


class RenderError(BaseModel):
    scene_index: int
    error_message: str
    stdout: str
    stderr: str


# ── Node: validate_input ──────────────────────────────────────────────────────

class ValidateInputState(BaseModel):
    """Entry state — provided by the API caller."""
    session_id: str
    approach: NarrativeApproach
    requirement: str
    workflow_id: str = Field(default_factory=lambda: uuid4().hex)


class ValidateOutputState(BaseModel):
    """Output of validate_input; consumed by the three outline generator nodes."""
    session_id: str
    workflow_id: str
    approach: NarrativeApproach
    requirement: str
    system_prompt: str
    status: Literal["ready", "failed"]
    error: str | None = None


# ── Nodes: conceptual_zoom / problem_solution_arc / classic_linear_narrative ──
# All three share the same input contract (ValidateOutputState).
OutlineInputState = ValidateOutputState


class OutlineOutputState(BaseModel):
    """Output produced by any of the three outline generator nodes."""
    session_id: str
    workflow_id: str
    approach: NarrativeApproach
    outline: dict  # serialised typed Pydantic outline model
    outline_type: str  # "ConceptualZoom" | "ProblemSolutionArc" | "ClassicLinearNarrative"
    status: Literal["completed", "failed"]
    error: str | None = None


# ── Node: map_outline_to_visual_plan (transform) ──────────────────────────────

class VisualPlanInputState(BaseModel):
    """
    Input to the visual_planning node.
    Explicitly produced by map_outline_to_visual_plan() from OutlineOutputState.
    """
    session_id: str
    workflow_id: str
    total_scenes: int
    video_outline: list[SceneOutline]


# ── Node: visual_planning ─────────────────────────────────────────────────────

class VisualPlanOutputState(BaseModel):
    """Final output of the graph."""
    session_id: str
    workflow_id: str
    total_scenes: int
    video_outline: list[SceneOutline]
    scene_visual_plans: list[str]
    status: Literal["completed", "failed"]
    error: str | None = None


# ── LangGraph accumulated state ───────────────────────────────────────────────

class GraphState(BaseModel):
    """
    Single Pydantic model that LangGraph operates on internally.
    Fields are populated progressively as each node executes.

    ValidateInputState fields  → set at graph entry by the API.
    ValidateOutputState fields → written by validate_input.
    OutlineOutputState fields  → written by the chosen outline generator.
    VisualPlanInputState fields→ written by map_outline_to_visual_plan.
    VisualPlanOutputState fields→ written by visual_planning.
    """
    # ValidateInputState
    session_id: str
    approach: NarrativeApproach
    requirement: str
    workflow_id: str = Field(default_factory=lambda: uuid4().hex)

    # ValidateOutputState
    system_prompt: str | None = None
    routed_to: str | None = None

    # OutlineOutputState
    outline: dict | None = None
    outline_type: str | None = None

    # VisualPlanInputState (produced by map_outline_to_visual_plan)
    total_scenes: int = 0
    video_outline: list[SceneOutline] = Field(default_factory=list)

    # VisualPlanOutputState
    scene_visual_plans: list[str] = Field(default_factory=list)

    # Cross-node tracking
    status: str = "pending"
    error: str | None = None
