"""
classic_linear_narrative.py
----------------------------
Pydantic v2 schema for the **Classic Linear Narrative** video outline approach.

Narrative style: descriptive title, dependency-ordered segments, steady
tone/pacing notes suited to a traditional explainer format.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.base_models import OutlineSegment, Pace, RACLoop


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------

class ClassicLinearNarrativeMeta(BaseModel):
    title: str = Field(
            ...,
            description="Descriptive, plainly stated video title.",
            )
    topic: str = Field(
            ..., description="Short topic name / slug.",
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
            default="Classic Linear Narrative",
            description="Fixed identifier for this approach.",
            )
    approach_style: str = Field(
            ...,
            description=(
                    "One-line description of this outline's style, "
                    "e.g. 'Sequential concept build-up with worked examples'."
            ),
            )


# ---------------------------------------------------------------------------
# Segment
# ---------------------------------------------------------------------------

class ClassicLinearNarrativeSegment(OutlineSegment):
    """
    Segment for Classic Linear Narrative.

    `narration_hint`    — tone / pacing note for narrator or editor.
    `transition_to_next`— bridge sentence into the next segment (null on last).
    """


# ---------------------------------------------------------------------------
# Root document
# ---------------------------------------------------------------------------

class ClassicLinearNarrativeOutline(BaseModel):
    """
    Full Classic Linear Narrative video outline document.
    """

    meta: ClassicLinearNarrativeMeta = Field(
            ...,
            description="Video-level metadata for the Classic Linear Narrative approach.",
            )
    rac_loop: RACLoop = Field(
            ...,
            description=(
                    "Reason-Act-Correct loop: content decomposition, dependency analysis, "
                    "time allocation, and violation corrections."
            ),
            )
    outline: list[ClassicLinearNarrativeSegment] = Field(
            ...,
            min_length=1,
            description="Ordered list of segments; ids must be 1-indexed and sequential.",
            )
