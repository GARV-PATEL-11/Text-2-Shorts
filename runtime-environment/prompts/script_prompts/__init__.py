"""Script-generation prompts.

Import names match the original single-file module, so existing callers
keep working:
    from script_prompts import (REQ_MODIFIER_SYSTEM,
        CLASSIC_LINEAR_NARRATIVE_SYSTEM, PROBLEM_TO_SOLUTION_ARC_SYSTEM,
        CONCEPTUAL_ZOOM_SYSTEM)
"""

from .classic_linear_narrative import CLASSIC_LINEAR_NARRATIVE_SYSTEM
from .conceptual_zoom import CONCEPTUAL_ZOOM_SYSTEM
from .problem_to_solution_arc import PROBLEM_TO_SOLUTION_ARC_SYSTEM
from .req_modifier import REQ_MODIFIER_SYSTEM

__all__ = [
    "REQ_MODIFIER_SYSTEM",
    "CLASSIC_LINEAR_NARRATIVE_SYSTEM",
    "PROBLEM_TO_SOLUTION_ARC_SYSTEM",
    "CONCEPTUAL_ZOOM_SYSTEM",
]
