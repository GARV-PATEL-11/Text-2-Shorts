"""conceptual_zoom.py — Node: generate Conceptual Zoom outline."""
from __future__ import annotations

from app.core.logger import log_call
from app.graph.models.conceptual_zoom import ConceptualZoomOutline
from app.graph.models.graph_state import GraphState
from app.graph.nodes.utils import generate_outline


@log_call(stage="node:conceptual_zoom")
async def conceptual_zoom_node(state: GraphState) -> dict:
    result = await generate_outline(state, ConceptualZoomOutline, "ConceptualZoom")
    return result.model_dump()
