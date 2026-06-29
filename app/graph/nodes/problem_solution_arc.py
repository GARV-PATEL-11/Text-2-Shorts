"""problem_solution_arc.py — Node: generate Problem-Solution Arc outline."""
from __future__ import annotations

from app.core.logger import log_call
from app.graph.models.graph_state import GraphState
from app.graph.models.problem_solution_arc import ProblemSolutionArcOutline
from app.graph.nodes.utils import generate_outline


@log_call(stage="node:problem_solution_arc")
async def problem_solution_arc_node(state: GraphState) -> dict:
    result = await generate_outline(state, ProblemSolutionArcOutline, "ProblemSolutionArc")
    return result.model_dump()
