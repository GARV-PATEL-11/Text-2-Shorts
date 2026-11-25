"""The video approaches: seven ways of teaching a topic and a custom one. Each is data, not code: its stages (the
outline's segment types, in order), how many segments, its rules, its visual language in Manim and its narration.

One source for the outline prompts (runtime-environment/prompts/script_prompts/approach_outline.py writes
references/outline-<id>.md from it), the outline gate (app/workflow/validation.py) and the website's choices. The
approach is how the topic is taught; the template is how it looks; the delivery format is how it is produced.
"""

from __future__ import annotations

from typing import Literal, NamedTuple

ApproachName = Literal[
    "eli5", "visual_intuition", "story_driven", "step_by_step", "feynman", "technical", "case_study", "custom"
]

MINUTES = (3, 20)  # a new video: at least 3 minutes of teaching narration (intro, bridges and closing not counted)


class Approach(NamedTuple):
    name: str
    tagline: str
    form: str  # short · medium · long · custom
    minutes: tuple[float, float]  # the usual length; the brief's minutes decide
    objective: str
    best_for: str
    stages: tuple[tuple[str, str], ...]  # (segment_type, what that stage does), in order; every stage appears
    segments: tuple[int, int]
    rules: tuple[str, ...]
    visuals: str  # the Manim visual language
    narration: str


APPROACHES: dict[str, Approach] = {
    "eli5": Approach(
        "ELI5",
        "Explain Like I'm Five",
        "short",
        (3, 5),
        "Simplify",
        "beginners, introductory concepts, quick understanding",
        (
            ("hook", "a familiar everyday situation and the question it raises"),
            ("analogy", "one everyday analogy that carries the idea"),
            ("explanation", "the core idea in plain words, one concept at a time"),
            ("demonstration", "the idea shown working, with simple shapes"),
            ("takeaway", "one memorable sentence the viewer keeps"),
        ),
        (5, 6),
        (
            "Everyday words only; a technical term appears only after the analogy has explained it.",
            "At most one formula in the whole video, never before the analogy.",
            "One new idea per segment.",
            "The takeaway segment is the shortest and ends on one sentence the viewer could repeat.",
        ),
        "simple shapes, everyday objects built from shapes, object transformations, minimal formulas",
        "warm, slow and simple; short sentences",
    ),
    "visual_intuition": Approach(
        "Visual Intuition",
        "See It to Understand It",
        "short",
        (3, 5),
        "Visualize",
        "mathematics, physics, algorithms, engineering",
        (
            ("question", "a visual question the picture will answer"),
            ("visualization", "the objects that make the idea visible, built piece by piece"),
            ("transformation", "the objects moving, changing, interacting: the mechanism revealed"),
            ("understanding", "the picture named: what was seen, said as the idea"),
        ),
        (4, 6),
        (
            "Show before you name: every idea is on screen before its word or symbol.",
            "Equations only after the picture they describe, as a label of it.",
            "The transformation segments get the largest share of the time.",
        ),
        "axes, number planes, graphs, vectors, geometric relationships, transformations",
        "curious and observational; point at what moves",
    ),
    "story_driven": Approach(
        "Story-Driven",
        "Learn Through Discovery",
        "medium",
        (4, 6),
        "Engage",
        "scientific discoveries, inventions, famous algorithms",
        (
            ("mystery", "an intriguing problem or puzzle, never a definition"),
            ("conflict", "why it matters, the obstacles and the attempts that failed"),
            ("discovery", "the insight that breaks it open, revealed"),
            ("explanation", "how the discovery works, step by step"),
            ("resolution", "the mystery answered and tied back to the concept"),
        ),
        (5, 7),
        (
            "One problem carries the whole video; every segment moves the story on.",
            "At least one failed attempt is shown before the discovery.",
            "The resolution answers the opening mystery in its own terms.",
        ),
        "visual metaphors, small worlds and characters built from shapes, dramatic reveals, camera moves",
        "narrative, with tension then relief",
    ),
    "step_by_step": Approach(
        "Step-by-Step Breakdown",
        "Learn by Building",
        "medium",
        (4, 6),
        "Construct",
        "systems, processes, architectures, algorithms",
        (
            ("components", "the parts, each named and shown on its own"),
            ("construction", "the parts joined one at a time, in dependency order"),
            ("interaction", "the assembled parts working on each other"),
            ("system", "the complete system running end to end"),
        ),
        (4, 7),
        (
            "Each construction segment adds exactly one part to what came before (rebuilt from scratch, VP6).",
            "No part is used before the segment that introduces it.",
            "The system segment shows every part at once, working.",
        ),
        "sequential creation, growing groups of shapes, arrows and flow diagrams",
        "clear and methodical",
    ),
    "feynman": Approach(
        "Feynman Deep Dive",
        "Understand From First Principles",
        "long",
        (8, 10),
        "Understand",
        "abstract concepts, foundational knowledge",
        (
            ("question", "the fundamental question the video answers"),
            ("fundamentals", "the elementary principles, and why each one exists"),
            ("simplification", "the idea reduced to its simplest true version"),
            ("reconstruction", "the full concept rebuilt from the principles"),
            ("misconceptions", "common wrong ideas, shown and corrected"),
            ("mastery", "the concept explained again simply, as to someone else"),
        ),
        (6, 10),
        (
            "Every principle answers 'why', not only 'what'.",
            "The reconstruction uses only principles already shown.",
            "At least two misconceptions, each shown wrong before it is corrected.",
            "The mastery segment uses no new terms.",
        ),
        "progressive diagrams, conceptual models that grow within a segment (each segment rebuilds what it needs, VP6), first-principles figures",
        "thoughtful and patient; questions the viewer would ask",
    ),
    "technical": Approach(
        "Mathematical & Technical Breakdown",
        "Derive and Understand",
        "long",
        (8, 10),
        "Derive",
        "advanced mathematics, machine learning, physics, algorithms",
        (
            ("foundation", "the prerequisites and the precise set-up"),
            ("derivation", "the result derived one step at a time"),
            ("visualization", "what the derived result looks like"),
            ("application", "a worked example with real numbers"),
            ("verification", "the result checked: limits, units, a special case"),
        ),
        (5, 10),
        (
            "One algebraic step per sentence of the derivation; no skipped steps.",
            "Every symbol is defined before it is used.",
            "The application segment computes actual numbers.",
            "The verification segment checks the result a second, independent way.",
        ),
        "equations and step-by-step derivations, axes and plots, grids, 3D scenes when the topic needs them",
        "precise and steady",
    ),
    "case_study": Approach(
        "Real-World Case Study",
        "Theory Into Practice",
        "long",
        (8, 10),
        "Apply",
        "engineering, data, applied science, practical problems",
        (
            ("problem", "one real, concrete problem with its numbers"),
            ("analysis", "what makes it hard; the quantities that matter"),
            ("application", "the concept applied to this problem"),
            ("simulation", "the solution running, step by step"),
            ("results", "outcomes compared with the start, and the limits"),
        ),
        (5, 10),
        (
            "The same problem runs through every segment.",
            "Use concrete quantities, never placeholders.",
            "The results segment compares before and after and names one limit.",
        ),
        "system diagrams, procedural simulations, graphs, side-by-side comparisons",
        "practical and grounded",
    ),
    "custom": Approach(
        "Custom",
        "Your Own Approach",
        "custom",
        MINUTES,
        "As the user defines it",
        "anything the presets do not fit",
        (),
        (4, 10),
        (
            (
                "Design the stages from the brief: style (teaching style), technical_complexity, explanation_depth and "
                "detail_level (depth), pace, visual_expectations (visual approach) and notes (narrative, examples, the "
                "user's own structure)."
            ),
            "A user's own structure keeps their order and wording; fill only what is missing.",
            "Name each stage as a short snake_case segment_type and keep them in teaching order.",
            "A new structure is allowed; it need not combine the presets.",
        ),
        "whatever the teaching strategy needs, drawn with Manim",
        "as the user asked",
    ),
}

LEGACY = {"zoom": "feynman", "arc": "story_driven", "linear": "step_by_step", "creative": "custom"}  # before 0.34


def stage_order(approach: str) -> list[str]:
    """The approach's segment types, in order ([] for custom: its stages are designed per video)."""
    return [stage for stage, _ in APPROACHES[approach].stages]
