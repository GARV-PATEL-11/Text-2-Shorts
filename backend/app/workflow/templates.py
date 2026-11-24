"""Template selection and management: the starter library in runtime-environment/templates/, template.json with
the user's overrides, its preview, and the resulting video style and font."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import ValidationError
from schemas.requirements import VideoTemplate

from app.config import TEMPLATES_DIRECTORY, VIDEO_STYLE
from app.utilities import format_validation_errors, read_json, write_json
from app.workflow.artifacts import load_brief
from app.workflow.preferences import load_preferences


def template_names() -> list[str]:
    return sorted(path.stem for path in TEMPLATES_DIRECTORY.glob("*.json"))


def starter_templates() -> list[VideoTemplate]:
    """The template library (runtime-environment/templates/), each validated."""
    return [
        VideoTemplate.model_validate_json((TEMPLATES_DIRECTORY / f"{name}.json").read_text())
        for name in template_names()
    ]


def load_template(run: Path) -> VideoTemplate | None:
    try:
        return VideoTemplate.model_validate_json((run / "template.json").read_text())
    except (FileNotFoundError, ValueError):
        return None


def validate_template(run: Path) -> list[str]:
    try:
        VideoTemplate.model_validate_json((run / "template.json").read_text())
    except FileNotFoundError:
        return ["template.json does not exist: choose one (`text-2-shorts templates`, then `template . <name>`)"]
    except ValidationError as validation_error:
        return format_validation_errors(validation_error)
    music = VideoTemplate.model_validate_json((run / "template.json").read_text()).music
    return [f"music {music} not found (relative to the run folder)"] if music and not (run / music).is_file() else []


def manim_hex(colour: str) -> str:
    import manim  # only for the preview swatch

    constant = getattr(manim, colour, None)
    return constant.to_hex() if hasattr(constant, "to_hex") else colour


def choose_template(run: Path, name: str, overrides: list[str]) -> Path:
    """template.json = a starter template + standing preferences + the user's `key=value` overrides (dotted keys
    reach into palette and type_scale; values are JSON when they parse), and template_preview.svg to show the user."""
    if name not in template_names():
        sys.exit(f"no template {name}: choose one of {', '.join(template_names())}")
    template = read_json(TEMPLATES_DIRECTORY / f"{name}.json")
    preferences = load_preferences(run)  # standing preferences fill the starter; the user's overrides come last
    template["palette"] = template.get("palette", {}) | preferences.palette
    template["background"] = preferences.background or template["background"]
    template["font"] = template.get("font") or preferences.font
    for override in overrides:
        key, _, text = override.partition("=")
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            value = text
        *parents, leaf = key.split(".")
        target = template
        for parent in parents:
            target = target.setdefault(parent, {})
        target[leaf] = value
    try:
        chosen = VideoTemplate.model_validate(template)
    except ValidationError as validation_error:
        sys.exit("template.json would be invalid:\n" + "\n".join(format_validation_errors(validation_error)))
    if chosen.music and not (run / chosen.music).is_file():
        sys.exit(f"music {chosen.music} not found: the user's own file, relative to the run folder")
    write_json(run / "template.json", chosen.model_dump())
    chips = "".join(
        f'<rect x="{40 + i * 200}" y="230" width="160" height="90" rx="10" fill="{manim_hex(colour)}"/>'
        f'<text x="{120 + i * 200}" y="350" fill="{manim_hex(chosen.palette.get("text", "WHITE"))}" '
        f'font-size="{chosen.type_scale["caption"]}" text-anchor="middle">{role}</text>'
        for i, (role, colour) in enumerate(chosen.palette.items())
    )
    font = f' font-family="{chosen.font}"' if chosen.font else ""
    (run / "template_preview.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720"{font}>'
        f'<rect width="1280" height="720" fill="{chosen.background}"/>'
        f'<text x="40" y="100" fill="{manim_hex(chosen.palette.get("text", "WHITE"))}" '
        f'font-size="{chosen.type_scale["title"]}">{chosen.name}: title</text>'
        f'<text x="40" y="170" fill="{manim_hex(chosen.palette.get("text", "WHITE"))}" '
        f'font-size="{chosen.type_scale["body"]}">Body text · {chosen.density} · {chosen.scene_transition}</text>'
        f"{chips}</svg>\n"
    )
    return run / "template.json"


def template_line(run: Path) -> str:
    """The chosen template's look and motion, for the clip-builder."""
    template = load_template(run)
    if template is None:
        return "none (standards.md)"
    return (
        f"{template.name} — type scale {json.dumps(template.type_scale)}; animation: {template.animation_style}; "
        f"density: {template.density}; composition: {template.composition}; pacing: {template.pacing}"
    )


def video_style(run: Path) -> dict:
    """The standard palette and background < the user's standing preferences < the chosen template."""
    preferences, template = load_preferences(run), load_template(run)
    return {
        **VIDEO_STYLE,
        **preferences.palette,
        **({"background": preferences.background} if preferences.background else {}),
        **(template.palette | {"background": template.background} if template else {}),
    }


def video_font(run: Path) -> str | None:
    brief = load_brief(run)
    template = load_template(run)
    return (brief.font if brief else None) or (template.font if template else None) or load_preferences(run).font
