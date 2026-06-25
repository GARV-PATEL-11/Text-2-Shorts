"""
base_models.py
--------------
Shared Pydantic v2 schemas used across all three video outline schemas:
  - Conceptual Zoom
  - Problem-Solution Arc
  - Classic Linear Narrative
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Pace(str, Enum):
    """
    Enum for pace type
    """
    slow = "slow"
    medium = "medium"
    fast = "fast"


class SegmentType(str, Enum):
    """
    Enum for segments type
    """
    hook = "hook"
    problem = "problem"
    intro = "intro"
    concept = "concept"
    math = "math"
    visualization = "visualization"
    mechanism = "mechanism"
    application = "application"
    tradeoffs = "tradeoffs"
    recap = "recap"
    cta = "cta"


# ---------------------------------------------------------------------------
# Shared sub-schemas
# ---------------------------------------------------------------------------

class RACLoop(BaseModel):
    """Reason → Act → Correct loop shared by every approach."""

    reason: str = Field(
        ...,
        description="Content decomposition, dependency / tension / layer analysis.",
        )
    act: str = Field(
        ...,
        description="Structural / arc / zoom decisions and rule applications.",
        )
    correct: str = Field(
        ...,
        description="Violations found and corrections applied, or 'PASSED'.",
        )


class OutlineSegment(BaseModel):
    """One segment inside the outline array — common across all approaches."""

    id: Annotated[int, Field(ge=1)] = Field(
        ..., description="1-indexed segment identifier.",
        )
    segment_type: SegmentType = Field(
        ..., description="Allowed type from the shared SegmentType enum.",
        )
    title: str = Field(
        ..., description="Display title for the segment.",
        )
    duration_seconds: Annotated[int, Field(ge=1)] = Field(
        ..., description="Wall-clock duration of the segment in seconds.",
        )
    talking_points: list[str] = Field(
        ..., min_length=1, description="Ordered list of talking points.",
        )
    visual_cues: list[str] = Field(
        ..., min_length=1, description="Ordered list of visual / animation cues.",
        )
    narration_hint: str = Field(
        ...,
        description="Tone, pacing, or depth note for the narrator or editor.",
        )
    transition_to_next: str | None = Field(
        default=None,
        description="Bridge sentence leading into the next segment; null for the last segment.",
        )
