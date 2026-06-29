"""classic_linear_narrative.py — Node: generate Classic Linear Narrative outline."""
from __future__ import annotations

from app.core.logger import log_call
from app.graph.models.classic_linear_narrative import ClassicLinearNarrativeOutline
from app.graph.models.graph_state import GraphState
from app.graph.nodes.utils import generate_outline


@log_call(stage="node:classic_linear_narrative")
async def classic_linear_narrative_node(state: GraphState) -> dict:
    result = await generate_outline(state, ClassicLinearNarrativeOutline, "ClassicLinearNarrative")
    return result.model_dump()
