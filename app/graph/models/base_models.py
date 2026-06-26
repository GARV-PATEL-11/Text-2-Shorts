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


class OutlineSegment(BaseModel):
    """One segment inside the outline array — common across all approaches."""

    scene_id: Annotated[int, Field(ge=1)] = Field(
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
    visual_plan: str = Field(
        ..., min_length=1, description="A paragraph of the visual plan.",
        )
    narration_hint: str = Field(
        ...,
        description="Tone, pacing, or depth note for the narrator or editor.",
        )
    transition_to_next: str | None = Field(
        default=None,
        description="Bridge sentence leading into the next segment; null for the last segment.",
        )


from pydantic import BaseModel, Field


class BaseVideoMeta(BaseModel):
    title: str = Field(
        ...,
        description="Video title.",
        )
    topic: str = Field(
        ...,
        description="Short topic name / slug.",
        )
    total_duration_seconds: int = Field(
        ..., ge=1, description="Total runtime of the video in seconds.",
        )
    pace: Pace = Field(
        ..., description="Overall delivery pace: slow | medium | fast.",
        )
    target_wpm: int = Field(
        ..., ge=1, description="Target words-per-minute for narration.",
        )
    approach_name: str = Field(
        ...,
        description="Fixed identifier for this approach.",
        )
    approach_style: str = Field(
        ...,
        description="One-line description of this outline's narrative arc and style.",
        )
