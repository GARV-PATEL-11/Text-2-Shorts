"""
conceptual_zoom.py
------------------
Pydantic v2 schema for the **Conceptual Zoom** video outline approach.

Narrative style: drill-down from system boundary to internals, then zoom out.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.graph.models.base_models import BaseVideoMeta, OutlineSegment


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------

class ConceptualZoomMeta(BaseVideoMeta):
    title: str = Field(
        ...,
        description="Technically framed video title — layered or systems-thinking phrasing.",
        )
    approach_name: str = Field(
        default="Conceptual Zoom",
        description="Fixed identifier for this approach.",
        )
    approach_style: str = Field(
        ...,
        description=(
            "One-line description of the zoom arc, "
            "e.g. 'Drill-down from system boundary to internals, zoom-out'."
        ),
        )


# ---------------------------------------------------------------------------
# Segment (inherits all common fields; no additions needed for this approach)
# ---------------------------------------------------------------------------

class ConceptualZoomSegment(OutlineSegment):
    """
    Segment for Conceptual Zoom.

    `narration_hint`    — pace + depth note matched to zoom level.
    `transition_to_next`— zoom-direction language (e.g. 'zooming in …').
    """


# ---------------------------------------------------------------------------
# Root document
# ---------------------------------------------------------------------------

class ConceptualZoomOutline(BaseModel):
    """
    Full Conceptual Zoom video outline document.
    """

    meta: ConceptualZoomMeta = Field(
        ..., description="Video-level metadata for the Conceptual Zoom approach.",
        )
    outline: list[ConceptualZoomSegment] = Field(
        ...,
        min_length=1,
        description="Ordered list of segments; ids must be 1-indexed and sequential.",
        )
