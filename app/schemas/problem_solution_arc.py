"""
problem_solution_arc.py
-----------------------
Pydantic v2 schema for the **Problem-Solution Arc** video outline approach.

Narrative style: question or statement title, narrative tension map,
emotional register matched to each segment.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.base_models import OutlineSegment, Pace, RACLoop


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------

class ProblemSolutionArcMeta(BaseModel):
    title: str = Field(
            ...,
            description=(
                    "Narrative-style video title phrased as a question or dramatic statement."
            ),
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
            default="Problem-Solution Arc",
            description="Fixed identifier for this approach.",
            )
    approach_style: str = Field(
            ...,
            description=(
                    "One-line description of this outline's narrative arc and emotional journey."
            ),
            )


# ---------------------------------------------------------------------------
# Segment
# ---------------------------------------------------------------------------

class ProblemSolutionArcSegment(OutlineSegment):
    """
    Segment for Problem-Solution Arc.

    `narration_hint`    — tone + emotional register note for narrator or editor.
    `transition_to_next`— tension-building bridge sentence (null on last segment).
    """


# ---------------------------------------------------------------------------
# Root document
# ---------------------------------------------------------------------------

class ProblemSolutionArcOutline(BaseModel):
    """
    Full Problem-Solution Arc video outline document.
    """

    meta: ProblemSolutionArcMeta = Field(
            ...,
            description="Video-level metadata for the Problem-Solution Arc approach.",
            )
    rac_loop: RACLoop = Field(
            ...,
            description=(
                    "Reason-Act-Correct loop: narrative tension map, arc design decisions, "
                    "and violation corrections."
            ),
            )
    outline: list[ProblemSolutionArcSegment] = Field(
            ...,
            min_length=1,
            description="Ordered list of segments; ids must be 1-indexed and sequential.",
            )
