"""generate_outline.py — Node: generate narrative outline using the chosen approach."""
from __future__ import annotations

from app.core.logger import log_call
from app.graph.models.classic_linear_narrative import ClassicLinearNarrativeOutline
from app.graph.models.conceptual_zoom import ConceptualZoomOutline
from app.graph.models.enums import NarrativeApproach
from app.graph.models.graph_state import GraphState
from app.graph.models.problem_solution_arc import ProblemSolutionArcOutline
from app.graph.nodes.utils import generate_outline


_APPROACH_TO_SCHEMA: dict[str, tuple] = {
    NarrativeApproach.CONCEPTUAL_ZOOM.value: (ConceptualZoomOutline, "ConceptualZoom"),
    NarrativeApproach.PROBLEM_SOLUTION_ARC.value: (ProblemSolutionArcOutline, "ProblemSolutionArc"),
    NarrativeApproach.CLASSIC_LINEAR_NARRATIVE.value: (ClassicLinearNarrativeOutline, "ClassicLinearNarrative"),
    }


@log_call(stage="node:generate_outline")
async def generate_outline_node(state: GraphState) -> dict:
    # state.approach is a plain str due to use_enum_values=True on GraphState
    schema_cls, outline_label = _APPROACH_TO_SCHEMA.get(
        state.approach,
        (ClassicLinearNarrativeOutline, "ClassicLinearNarrative"),
        )
    result = await generate_outline(state, schema_cls, outline_label)
    return result.model_dump()
