from enum import Enum


class NarrativeApproach(str, Enum):
    """
    Define the narrative approach.
    """
    CONCEPTUAL_ZOOM = "Conceptual Zoom"
    PROBLEM_SOLUTION_ARC = "Problem-Solution Arc"
    CLASSIC_LINEAR_NARRATIVE = "Classic Linear Narrative"
