"""Manim Visual Director prompt (v7: atomic, time-ordered event plans), wired into the run.

Prompt text lives in Markdown files; this module only loads, orders and fills them, and reads the plan back.

    references/visual-director-system.md         role + D-rules       (the scene-planner reads it first)
    manim-vocabulary.md                          which names exist    (the Manim reference skill's topics/)
    manim-construction-patterns.md               how to write calls; PART 9 is this project's clip harness
    manim-common-mistakes.md                     what still goes wrong
    references/visual-director-output-spec.md    the task + output format (printed by plan-task)

`text-2-shorts plan-task . --scene sNN` prints the filled prompt (the inputs, the output spec) for the scene-planner
subagent, which writes the Scene Execution Plan into plan.json (`execution_plan`) with the fields derived from it. No
file is written and no Claude call happens here. The output spec uses __SCENE_ID__ and __TARGET_DURATION__ tokens, filled with str.replace (never
.format: the files contain literal braces).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from schemas.outline_models.approaches import APPROACHES

from app.config import ALWAYS_LOADED_TOPICS, RUN_ENVIRONMENT, TOPICS_DIRECTORY
from app.workflow.artifacts import load_brief, load_outline, load_scene_plans, load_script

REFERENCES_DIRECTORY = RUN_ENVIRONMENT / "skills" / "text-2-shorts-produce" / "references"
SYSTEM_FILE = REFERENCES_DIRECTORY / "visual-director-system.md"
OUTPUT_SPEC_FILE = REFERENCES_DIRECTORY / "visual-director-output-spec.md"
SYSTEM_FILES = (SYSTEM_FILE, *(TOPICS_DIRECTORY / f"{topic}.md" for topic in ALWAYS_LOADED_TOPICS))
SECTIONS = (  # the Scene Execution Plan's sections, in order (visual-director-output-spec.md)
    "SCENE_OVERVIEW",
    "INPUTS_USED",
    "LAYOUT_PLAN",
    "CONTINUITY",
    "MANIM_PRIMITIVE_SELECTION",
    "OBJECT_REGISTRY",
    "COLOR_MAP",
    "CLIP_SEQUENCE",
    "CAMERA_SCRIPT",
    "SCENE_END",
    "TIMING_SUMMARY",
    "IMPLEMENTATION_NOTES",
)
_SEPARATOR = "\n\n---\n\n"
_CLIP_HEADER = re.compile(r"^CLIP (\d+)\s*\|", re.MULTILINE)


@dataclass(frozen=True)
class SceneDirectorInput:
    """Everything the director needs for one scene."""

    video_metadata: str  # title, subject, audience of the whole video
    target_scene_id: str  # e.g. "s03"
    target_scene: str  # talking points + visual_plan for this scene
    target_duration: float  # seconds; the script's estimate of the scene's narration length
    template_reference: str  # the TEMPLATE block: colour roles, font, text sizes, safe area
    narration: str = ""  # this scene's spoken text (no timestamps before CP2)
    previous_scenes: str = ""  # earlier scenes: key ideas, object names, looks


def _format_duration(seconds: float) -> str:
    return f"{seconds:g}"


def build_user_prompt(inp: SceneDirectorInput) -> str:
    if not inp.template_reference.strip():
        raise ValueError("template_reference is required: rule D5 needs the template's color roles")
    read_first = "READ FIRST, in this order: " + ", ".join(str(path) for path in SYSTEM_FILES)
    inputs = (
        "## Inputs\n\n"
        f"### VIDEO_METADATA\n{inp.video_metadata.strip()}\n\n"
        f"### TARGET_SCENE (Scene ID: {inp.target_scene_id})\n{inp.target_scene.strip()}\n\n"
        f"### TARGET_DURATION\n{_format_duration(inp.target_duration)} seconds\n\n"
        f"### TEMPLATE_REFERENCE\n{inp.template_reference.strip()}\n\n"
        f"### NARRATION\n{inp.narration.strip() or '(not provided: estimate from the talking points)'}\n\n"
        f"### PREVIOUS_SCENES\n{inp.previous_scenes.strip() or '(none: this is the first scene, or no summary provided)'}"
    )
    task = (
        OUTPUT_SPEC_FILE.read_text(encoding="utf-8")
        .strip()
        .replace("__SCENE_ID__", inp.target_scene_id)
        .replace("__TARGET_DURATION__", _format_duration(inp.target_duration))
    )
    return read_first + _SEPARATOR + inputs + _SEPARATOR + task


def task(run: Path, scene_id: str) -> str:
    """The Visual Director's filled prompt for one scene (printed by `text-2-shorts plan-task`)."""
    return build_user_prompt(scene_input(run, scene_id))


def section(plan_text: str, tag: str) -> str:
    """One tagged section of an execution plan, without its tags ('' when absent)."""
    match = re.search(rf"<{tag}>(.*?)</{tag}>", plan_text, re.DOTALL)
    return match.group(1).strip() if match else ""


def clip_block(plan_text: str, index: int) -> str:
    """Clip N's block of CLIP_SEQUENCE: its header line up to the next clip's ('' when absent)."""
    lines = section(plan_text, "CLIP_SEQUENCE").splitlines()
    starts = [i for i, line in enumerate(lines) if _CLIP_HEADER.match(line)]
    for n, start in enumerate(starts):
        if int(_CLIP_HEADER.match(lines[start]).group(1)) == index:
            body = lines[start : starts[n + 1] if n + 1 < len(starts) else len(lines)]
            while body and set(body[-1].strip()) <= {"=", "`"}:  # the next clip's rule line, a closing fence
                body.pop()
            return "\n".join(body).strip()
    return ""


def problems(plan_text: str, clip_count: int) -> list[str]:
    """What the gate checks: every section present, in order, and one CLIP block per plan.json clip."""
    errors = [f"missing <{tag}> … </{tag}> section" for tag in SECTIONS if f"<{tag}>" not in plan_text]
    positions = [plan_text.find(f"<{tag}>") for tag in SECTIONS if f"<{tag}>" in plan_text]
    if positions != sorted(positions):
        errors.append("sections are out of order (visual-director-output-spec.md)")
    clips = sorted({int(number) for number in _CLIP_HEADER.findall(section(plan_text, "CLIP_SEQUENCE"))})
    if clips != list(range(1, clip_count + 1)):
        errors.append(f"CLIP_SEQUENCE has clips {clips or 'none'}; plan.json has clips 1-{clip_count}: one block each")
    return errors


def scene_input(run: Path, scene_id: str) -> SceneDirectorInput:
    """The director's inputs for one scene, from the run's approved files."""
    from app.workflow.templates import look_brief

    script, brief, outline = load_script(run), load_brief(run), load_outline(run)
    scene = next((s for s in script.scenes if s.scene_id == scene_id), None) if script else None
    if scene is None:
        raise SystemExit(f"{scene_id} is not a scene of the approved script")
    metadata = [f"Title: {script.title}", f"Objectives: {'; '.join(script.objectives)}"]
    if brief:
        approach = APPROACHES[brief.approach]
        metadata += [
            f"Subject: {brief.requirement}",
            f"Audience: {brief.audience} ({brief.technical_complexity})",
            (
                f"Approach: {approach.name} ({approach.tagline}); visual language: {approach.visuals}; "
                f"narration: {approach.narration}"
            ),
        ]
    target = [
        f"Title: {scene.title}",
        f"Objective: {scene.objective}",
        f"Key concepts: {'; '.join(scene.key_concepts)}",
        f"Visual idea: {scene.visual_idea or '-'}",
        f"On-screen text that must appear: {'; '.join(scene.on_screen_text) or '-'}",
        f"Required animations: {'; '.join(scene.animations) or '-'}",
        f"Audio requirements: {scene.audio_requirements or '-'}",
        f"Transition requirements: {scene.transition_requirements or '-'}",
    ]
    segment = (
        outline.outline[scene.outline_segment - 1]
        if outline and scene.outline_segment and scene.outline_segment <= len(outline.outline)
        else None
    )
    if segment:
        target += [f"Talking points: {'; '.join(segment.talking_points)}", f"Visual plan: {segment.visual_plan}"]
    earlier = []
    for plan in (p for p in load_scene_plans(run) if p.scene_id < scene_id):
        registry = section(plan.execution_plan, "OBJECT_REGISTRY")
        earlier.append(
            f"{plan.scene_id} {plan.title}: {plan.objective}\n"
            f"  colour roles: {', '.join(f'{k} -> {v}' for k, v in plan.color_roles.items()) or '-'}\n"
            + (f"  objects:\n{registry}" if registry else f"  composition: {plan.composition}")
        )
    narration = f"{scene.bridge_in} {scene.narration}".strip()
    rate = f"(no timestamps: the voice is made after CP2; the script's rate is {script.target_wpm} words a minute)"
    return SceneDirectorInput(
        video_metadata="\n".join(metadata),
        target_scene_id=scene_id,
        target_scene="\n".join(target),
        target_duration=scene.duration_seconds,
        template_reference=look_brief(run),
        narration=f"{narration}\n{rate}",
        previous_scenes="\n\n".join(earlier),
    )
