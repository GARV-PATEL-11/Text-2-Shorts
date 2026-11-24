"""Validators for what the session writes: brief, topics, content, outline, script, scene plans and accuracy reviews."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import ValidationError
from schemas.outline_models.base_outline import VideoOutline
from schemas.outline_models.classic_linear_narrative import ClassicLinearNarrativeOutline
from schemas.outline_models.conceptual_zoom import ConceptualZoomOutline
from schemas.outline_models.problem_solution_arc import ProblemSolutionArcOutline
from schemas.plans import ScenePlan
from schemas.requirements import Brief
from schemas.reviews import ReviewReport
from schemas.script import Script

from app import narration
from app.config import WORD_BUDGET_TOLERANCE
from app.utilities import format_validation_errors
from app.workflow.artifacts import load_brief, load_outline, load_scene_plans, load_script, read_topics, spoken_text
from app.workflow.checkpoints import stage_approval_problem


def scene_end_problems(plan: ScenePlan) -> list[str]:
    """Each scene renders as its own Manim Scene, so no object can cross a scene boundary."""
    problems = []
    if plan.clips[0].entry.persistent_objects:
        problems.append(f"{plan.clips[0].clip_id} entry must be empty (scenes start on an empty frame)")
    if plan.clips[-1].exit.persistent_objects:
        problems.append(f"{plan.clips[-1].clip_id} exit must be empty (scenes end with everything faded out)")
    return problems


REVIEW_FILES = {"script": "script_review.json", "plan": "plan_review.json"}


OUTLINE_MODELS = {
    "linear": ClassicLinearNarrativeOutline,
    "arc": ProblemSolutionArcOutline,
    "zoom": ConceptualZoomOutline,
    "creative": VideoOutline,
}


SEGMENT_ORDER = {  # rules A2, B2, C2 of the outline prompts: segment types in this relative order (any may be skipped)
    "linear": [
        {"hook", "problem"},
        {"intro", "concept"},
        {"math"},
        {"visualization"},
        {"mechanism"},
        {"application", "tradeoffs"},
        {"recap", "cta"},
    ],
    "arc": [
        {"problem", "hook"},
        {"intro", "concept"},
        {"math"},
        {"mechanism"},
        {"application"},
        {"tradeoffs"},
        {"cta", "recap"},
    ],
    "zoom": [{"intro", "concept"}, {"math"}, {"mechanism"}, {"tradeoffs", "application"}, {"recap"}],
}


FIRST_SEGMENT = {"linear": ({"hook"}, "A7"), "arc": ({"problem", "hook"}, "B3")}


LAST_SEGMENT = {"zoom": ({"recap"}, "C2: the zoom-out recap closes the video")}


def validate_brief(run: Path) -> list[str]:
    """Stage 1: brief.json holds the user's requirements."""
    try:
        Brief.model_validate_json((run / "brief.json").read_text())
    except FileNotFoundError:
        return ["brief.json does not exist"]
    except ValidationError as validation_error:
        return format_validation_errors(validation_error)
    return []


def validate_topics(run: Path) -> list[str]:
    """Stage 1: topics.md, the request-modifier's numbered topic list (references/topic-list.md)."""
    if not (run / "topics.md").exists():
        return ["topics.md does not exist"]
    lines = [line.strip() for line in (run / "topics.md").read_text().splitlines() if line.strip()]
    numbered = [re.match(r"^(\d+)\.\s+\S", line) for line in lines]
    if not lines or not all(numbered) or [int(m[1]) for m in numbered if m] != list(range(1, len(lines) + 1)):
        return ["topics.md must be a numbered list (1., 2., 3., …) with one topic per line and nothing else"]
    return []


def validate_content(run: Path) -> list[str]:
    """Stage 1: content.md, the educational text the outline is built from (raw_content): one '## <topic>' section
    per topic, in the topic list's order."""
    if not (run / "content.md").exists():
        return ["content.md does not exist"]
    text = (run / "content.md").read_text()
    headings = re.findall(r"^## (.+)$", text, re.MULTILINE)
    topics = read_topics(run)
    errors = [f"content.md has no '## {topic}' section" for topic in topics if topic not in headings]
    if not errors and [heading for heading in headings if heading in topics] != topics:
        errors.append("content.md sections must follow the topic list's order")
    sections = re.split(r"^## .+$", text, flags=re.MULTILINE)[1:]
    errors += [
        f"content.md section '{heading}' is empty" for heading, body in zip(headings, sections) if not body.strip()
    ]
    return errors


def validate_outline(run: Path) -> list[str]:
    """Stage 2: outline.json against the approach's model (backend/schemas/outline_models) and the outline prompts'
    checkable rules: segment order and first/last type, 10–120 s per segment, transitions, and the visual-plan
    standard."""
    for stage in ("requirements", "template"):  # the outline starts from confirmed requirements and a template
        if problem := stage_approval_problem(run, stage):
            return [problem]
    brief = load_brief(run)
    approach = brief.approach if brief else "linear"
    try:
        outline = OUTLINE_MODELS[approach].model_validate_json((run / "outline.json").read_text())
    except FileNotFoundError:
        return ["outline.json does not exist"]
    except ValidationError as validation_error:
        return format_validation_errors(validation_error)
    segments, errors = outline.outline, []
    if [segment.scene_id for segment in segments] != list(range(1, len(segments) + 1)):
        errors.append("segment scene_id values must be 1, 2, 3, … in order")
    if approach in SEGMENT_ORDER:
        order, last_rank = SEGMENT_ORDER[approach], 0
        for segment in segments:
            rank = next((i for i, group in enumerate(order) if segment.segment_type in group), None)
            if rank is None:
                errors.append(
                    f"segment {segment.scene_id}: {segment.segment_type} is not used in the {approach} approach"
                )
            elif rank < last_rank:
                errors.append(
                    f"segment {segment.scene_id} ({segment.segment_type}) breaks the {approach} order: "
                    + " → ".join("|".join(sorted(group)) for group in order)
                )
            else:
                last_rank = rank
    if approach in FIRST_SEGMENT and segments[0].segment_type not in FIRST_SEGMENT[approach][0]:
        allowed, rule = FIRST_SEGMENT[approach]
        errors.append(f"segment 1 must be a {' or '.join(sorted(allowed))} ({rule})")
    if approach in LAST_SEGMENT and segments[-1].segment_type not in LAST_SEGMENT[approach][0]:
        errors.append(f"the last segment must be a recap ({LAST_SEGMENT[approach][1]})")
    for number, segment in enumerate(segments, 1):
        label = f"segment {segment.scene_id}"
        if not 10 <= segment.duration_seconds <= 120:
            errors.append(f"{label}: {segment.duration_seconds}s — every segment is 10–120 s (G2)")
        if (segment.transition_to_next is None) != (number == len(segments)):
            errors.append(f"{label}: transition_to_next is null only on the last segment (S13)")
        plan = segment.visual_plan.strip()
        sentences = [sentence for sentence in re.split(r"(?<=[.!?])\s+", plan) if sentence]
        needed = min(max(round(segment.duration_seconds * 0.7), 20), 60)
        if len(sentences) < needed:
            errors.append(f"{label}: visual_plan has {len(sentences)} sentences, needs at least {needed} (VP2)")
        if sentences and "empty canvas" not in sentences[0]:
            errors.append(f"{label}: visual_plan's first sentence describes the empty canvas (VP3)")
        if sentences and not sentences[-1].startswith("The scene ends with"):
            errors.append(f"{label}: visual_plan's last sentence must begin 'The scene ends with' (VP4)")
        if '"' in plan:
            errors.append(f"{label}: visual_plan uses double quotes; on-screen text goes in single quotes (VP5)")
    return errors


def validate_script(run: Path) -> list[str]:
    """Stage 2: script.json — every objective covered, every scene after the first bridged, each scene's narration
    sized for its duration, the whole video within ±20% of the requested length."""
    if problem := stage_approval_problem(run, "outline"):
        return [problem]
    brief = load_brief(run)
    try:
        script = Script.model_validate_json((run / "script.json").read_text())
    except FileNotFoundError:
        return ["script.json does not exist"]
    except ValidationError as validation_error:
        return format_validation_errors(validation_error)
    outline = load_outline(run)
    segment_ids = [segment.scene_id for segment in outline.outline] if outline else []
    narrated = [scene.outline_segment for scene in script.scenes if scene.outline_segment is not None]
    unmapped = [scene.scene_id for scene in script.scenes if scene.role != "index" and scene.outline_segment is None]
    mapping_errors = (
        [
            f"outline_segment: the scenes after the index must narrate outline segments {segment_ids} once each, in "
            f"order; got {narrated}" + (f" (none on {unmapped})" if unmapped else "")
        ]
        if narrated != segment_ids or unmapped
        else []
    )
    covered = {index for scene in script.scenes for index in scene.covers}
    errors = mapping_errors + [
        f"objective {index} is not covered by any scene: {objective!r}"
        for index, objective in enumerate(script.objectives, 1)
        if index not in covered
    ]
    errors += [
        f"brief objective missing from the script's objectives: {objective!r}"
        for objective in (brief.objectives if brief else [])
        if objective not in script.objectives
    ]
    for scene in script.scenes:
        budget = scene.duration_seconds * script.target_wpm / 60
        count = len([word for word in spoken_text(scene).split() if word != narration.PAUSE])
        if abs(count - budget) > WORD_BUDGET_TOLERANCE * budget:
            errors.append(
                f"{scene.scene_id} has {count} spoken words, but {scene.duration_seconds:g}s "
                f"at {script.target_wpm} wpm "
                f"needs about {budget:.0f} (±25%): rewrite the narration or change duration_seconds"
            )
    if brief and (minutes := brief.minutes):
        total, target = sum(scene.duration_seconds for scene in script.scenes), minutes * 60
        if abs(total - target) > 0.2 * target:
            errors.append(
                f"scenes total {total:g}s but the target is {target:.0f}s (±20%): "
                "rescale duration_seconds, drop or merge scenes"
            )
    return errors


def validate_plan(run: Path, scene_id: str) -> list[str]:
    """Stage 3: scenes/sNN/plan.json — only after CP1; the clips speak exactly the approved script's text for the scene;
    scenes after the first describe their opening transition; empty scene boundaries; one colour per symbol."""
    if problem := stage_approval_problem(run, "script"):
        return [problem]
    try:
        plan = ScenePlan.model_validate_json((run / "scenes" / scene_id / "plan.json").read_text())
    except FileNotFoundError:
        return [f"scenes/{scene_id}/plan.json does not exist"]
    except ValidationError as validation_error:
        return format_validation_errors(validation_error)
    errors = [] if plan.scene_id == scene_id else [f"scene_id is {plan.scene_id}, expected {scene_id}"]
    script = load_script(run)
    script_scene = next((scene for scene in script.scenes if scene.scene_id == scene_id), None) if script else None
    if script_scene is None:
        errors.append(f"{scene_id} is not a scene of the approved script")
    else:
        if " ".join(" ".join(clip.narration for clip in plan.clips).split()) != spoken_text(script_scene):
            errors.append(
                f"{scene_id}: the clips' narration must be the script's spoken text for this scene (bridge_in, then "
                "narration), word for word and in order; to change what is said, edit script.json and get CP1 again"
            )
        shown = " ".join(" ".join([clip.visual_intent, *clip.beats, *clip.on_screen_math]) for clip in plan.clips)
        errors += [
            f"{scene_id}: the script's on-screen text {text!r} appears in no clip (visual_intent, beats or "
            "on_screen_math)"
            for text in script_scene.on_screen_text
            if text not in shown
        ]
        errors += [
            f"{clip.clip_id}: sound effect {effect.file} not found (the user's own file, relative to the run)"
            for clip in plan.clips
            for effect in clip.sound_effects
            if not (run / effect.file).is_file()
        ]
        for clip in plan.clips:
            if undescribed := [n for n in clip.entry.persistent_objects if n not in clip.entry.descriptions]:
                errors.append(
                    f"{clip.clip_id} entry: add {undescribed} to entry.descriptions (type, text or LaTeX, colour) — "
                    "a clip re-creates what it takes over when it runs alone"
                )
            if problems := narration.ssml_problems(clip.ssml):
                errors += [f"{clip.clip_id} ssml: {problem}" for problem in problems]
            elif [w for w in narration.ssml_words(clip.ssml) if w != narration.PAUSE] != [
                w for w in clip.narration.split() if w != narration.PAUSE
            ]:
                errors.append(
                    f"{clip.clip_id} ssml must speak exactly the clip's narration (add tags, never change words)"
                )
        if scene_id != "s01" and not plan.transition_in.strip():
            errors.append(
                f"{scene_id} transition_in is empty: describe how it opens from the previous scene's final image"
            )
    errors += scene_end_problems(plan)
    for earlier in (candidate for candidate in load_scene_plans(run) if candidate.scene_id < scene_id):
        errors += [
            f"`{symbol}` is {color} here but {earlier.color_roles[symbol]} in {earlier.scene_id}: one colour per symbol"
            for symbol, color in plan.color_roles.items()
            if earlier.color_roles.get(symbol, color) != color
        ]
    return errors


def validate_review(run: Path, stage: str) -> list[str]:
    """script_review.json (findings per scene) or plan_review.json (findings per clip), from the accuracy-reviewer."""
    name = REVIEW_FILES[stage]
    try:
        report = ReviewReport.model_validate_json((run / name).read_text())
    except FileNotFoundError:
        return [f"{name} does not exist: run the accuracy-reviewer subagent"]
    except ValidationError as validation_error:
        return [f"{name}: {error}" for error in format_validation_errors(validation_error)]
    if stage == "script":
        script = load_script(run)
        known = {scene.scene_id for scene in script.scenes} if script else set()
    else:
        known = {clip.clip_id for plan in load_scene_plans(run) for clip in plan.clips}
    return [f"{name}: unknown target {finding.target}" for finding in report.findings if finding.target not in known]
