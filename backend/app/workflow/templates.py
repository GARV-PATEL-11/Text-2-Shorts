"""The run's template.json: chosen from the starter library (backend/templates/template_kit/templates/), one
variant per element, a few elements set to the user's own value. What it means for the picture and the voice is
resolved by backend/templates/video_settings.py and audio_settings.py — the one source for both. Once chosen, it is
copied into the run environment (install_template)."""

from __future__ import annotations

import json
import logging
import shutil
import sys
from pathlib import Path

import audio_settings
import generate_preview
import video_settings
from pydantic import ValidationError
from schemas.api import LookCatalogue, LookElement, LookOption, LookTemplate, LookView
from schemas.requirements import VideoTemplate

from app.config import TEMPLATES_DIRECTORY, runtime_template_directory
from app.utilities import format_validation_errors, write_json
from app.workflow.artifacts import load_brief


def template_names() -> list[str]:
    return video_settings.starter_names()


def starter_templates() -> list[VideoTemplate]:
    return [VideoTemplate.model_validate(video_settings.starter(name)) for name in template_names()]


def load_template(run: Path) -> VideoTemplate | None:
    try:
        return VideoTemplate.model_validate_json((run / "template.json").read_text())
    except (FileNotFoundError, ValueError):
        return None


def current_template(run: Path) -> dict:
    """The run's template, or the default starter until one is chosen."""
    template = load_template(run)
    return template.model_dump() if template else video_settings.starter(video_settings.DEFAULT_TEMPLATE)


def template_problems(template: dict, run: Path) -> list[str]:
    try:
        chosen = VideoTemplate.model_validate(template)
    except ValidationError as validation_error:
        return format_validation_errors(validation_error)
    errors = video_settings.problems(chosen.model_dump())
    if chosen.music and not (run / chosen.music).is_file():
        errors.append(f"music {chosen.music} not found: the user's own file, relative to the run folder")
    return errors


def validate_template(run: Path) -> list[str]:
    if not (run / "template.json").exists():
        return ["template.json does not exist: choose one on the website (Look & sound) or `template . <name>`"]
    try:
        return template_problems(json.loads((run / "template.json").read_text()), run)
    except json.JSONDecodeError as error:
        return [f"template.json is not JSON: {error}"]


def build_template(name: str, choices: dict[str, str], custom: dict[str, str], extra: dict) -> dict:
    """A starter template with the user's variant choices, custom values (as overrides) and assembly settings."""
    template = video_settings.starter(name) | extra
    template["elements"] = template["elements"] | choices
    mode = template["elements"].get("theme_mode", "dark")
    template["overrides"] = {
        element: video_settings.custom_override(element, value, mode)
        for element, value in custom.items()
        if element in video_settings.CUSTOM  # audio has no custom values any more: its options only
    }
    return template


def save_template(run: Path, template: dict) -> list[str]:
    """Write template.json when it is valid; else its problems (nothing written)."""
    if errors := template_problems(template, run):
        return errors
    write_json(run / "template.json", VideoTemplate.model_validate(template).model_dump())
    logging.getLogger(__name__).info("%s: template %s saved", run.name, template.get("name"))
    install_template(run)
    return []


def install_template(run: Path) -> Path:
    """Copy the chosen template into the run environment (runtime-environment/template/): template.json, the resolved
    look the harness draws (look.json) and the renderer that draws it (look_renderer.py, with the Faraday mark). Everything about templates
    lives in backend/templates/; the run environment gets only what the chosen one needs. The folder is shared, so the
    last template chosen is the one there; renders still take their run's own look (TEXT_2_SHORTS_LOOK)."""
    target = runtime_template_directory()
    target.mkdir(parents=True, exist_ok=True)
    write_json(target / "template.json", current_template(run))
    write_json(target / "look.json", drawing(run))
    for name in ("look_renderer.py", "faraday-logo.svg"):  # the renderer and the mark it draws
        shutil.copyfile(TEMPLATES_DIRECTORY / name, target / name)
    return target


def choose_template(run: Path, name: str, settings: list[str]) -> Path:
    """`text-2-shorts template . <name> [--set element=variant | custom.element=value | key=value …]`."""
    if name not in template_names():
        sys.exit(f"no template {name}: choose one of {', '.join(template_names())}")
    choices, custom, extra = {}, {}, {}
    for setting in settings:
        key, _, text = setting.partition("=")
        if key.startswith("custom."):
            if key.removeprefix("custom.") not in video_settings.CUSTOM:
                sys.exit(f"{key.removeprefix('custom.')} has no custom value: choose one of its options")
            custom[key.removeprefix("custom.")] = text
        elif key in video_settings.ELEMENTS:
            choices[key] = text
        else:
            try:
                extra[key] = json.loads(text)
            except json.JSONDecodeError:
                extra[key] = text
    if errors := save_template(run, build_template(name, choices, custom, extra)):
        sys.exit("template.json would be invalid:\n" + "\n".join(errors))
    return run / "template.json"


def look(run: Path) -> dict:
    """What clips take from the template: background, colour roles, font, sizes, safe area."""
    return video_settings.settings(current_template(run))


def drawing(run: Path) -> dict:
    """What the scene harness draws behind every clip (backdrop, grid, border) and with what (look_renderer.py)."""
    return video_settings.drawing(current_template(run))


def look_brief(run: Path) -> str:
    return video_settings.brief(current_template(run))


def sound(run: Path) -> dict:
    """What narration takes from the template, for the brief's provider: voice, rate, pauses, tone."""
    brief = load_brief(run)
    return audio_settings.settings(current_template(run), brief.tts if brief else "polly")


HIDDEN = {"frame"}  # the delivery format is ours (1440p120), not a template choice


def catalogue() -> LookCatalogue:
    """Every starter template and every element the user can set (the website's Look & sound tree)."""
    library = video_settings.library()
    return LookCatalogue(
        templates=[
            LookTemplate(name=name, description=starter["description"], elements=starter["elements"])
            for name in template_names()
            if (starter := video_settings.starter(name))
        ],
        elements=[
            LookElement(
                id=name,
                label=name.replace("_", " ").capitalize(),
                group=library[name]["group"],
                kind="visual" if name in video_settings.VISUAL else "sound",
                description=library[name].get("description", ""),
                options=[
                    LookOption(id=variant["id"], label=variant["label"], detail=option_detail(name, variant))
                    for variant in library[name]["variants"].values()
                ],
                custom=video_settings.CUSTOM.get(name),
                previewed=name in generate_preview.PREVIEWED,
            )
            for name in video_settings.ELEMENTS
            if name not in HIDDEN
        ],
    )


def option_detail(element: str, variant: dict) -> str:
    """What a sound option means beyond its name."""
    if element == "voice":
        return f"Polly {variant['polly']['voice_id']} · Google {variant['google']['neural2']}"
    if element == "speaking_speed":
        return f"{round(variant['rate'] * 100)}% · about {round(variant['base_wpm'] * variant['rate'])} words a minute"
    if element == "narration_tone":
        return variant["script_rules"]
    return ""


def look_view(run: Path) -> LookView:
    template = current_template(run)
    mode = template["elements"].get("theme_mode", "dark")
    return LookView(
        template=template["name"],
        elements=template["elements"],
        custom={
            element: video_settings.custom_value(element, override, mode)
            for element, override in template.get("overrides", {}).items()
        },
        saved=(run / "template.json").exists(),
        provider=brief.tts if (brief := load_brief(run)) else "polly",
    )


def chosen_template(run: Path, name: str, choices: dict[str, str], custom: dict[str, str]) -> dict:
    """A website choice as a template: the assembly settings already saved (transitions, music) carry over."""
    if name not in template_names():
        raise ValueError(f"no template {name}: choose one of {', '.join(template_names())}")
    saved = load_template(run)
    extra = (
        saved.model_dump(include={"scene_transition", "transition_seconds", "music", "music_volume_db"})
        if saved
        else {}
    )
    return build_template(name, choices, {element: value for element, value in custom.items() if value.strip()}, extra)
