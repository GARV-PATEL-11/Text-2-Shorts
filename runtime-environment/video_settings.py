"""The video's look, finalised from the run's template.json — the one place clips get colours, fonts, text sizes,
background and safe area from.

A template names one variant per element of template_kit/elements.json (plus `overrides`: custom values merged into
a variant). This module resolves it from that JSON alone (no Manim, no kit code), checks it, and writes the rules the
clip-builder follows (clips.py puts `brief()` into every TASK.md). The delivery format is ours, not the template's:
drafts 1280×720 at 30 fps, final 2560×1440 at 120 fps — the template's `frame` only sizes previews.
"""

from __future__ import annotations

import copy
import json
import random
import re
from pathlib import Path

KIT_DIRECTORY = Path(__file__).resolve().parent / "template_kit"
TEMPLATES_DIRECTORY = KIT_DIRECTORY / "templates"
GALLERY_DIRECTORY = KIT_DIRECTORY / "gallery"
DEFAULT_TEMPLATE = "standard"

VISUAL = (
    "theme_mode", "frame", "background_type", "background_color", "grid_type", "grid_color", "grid_opacity",
    "primary_palette", "secondary_palette", "accent_color", "text_font", "math_font", "typography", "border_style",
    "border_color",
)  # fmt: skip
SOUND = ("voice", "speaking_speed", "narration_tone", "subtitles", "subtitle_style", "caption_position",
         "word_highlighting")  # fmt: skip
ELEMENTS = VISUAL + SOUND
TEXT_STYLES = ("title", "heading", "body", "label", "caption")
ROLES = ("text", "focus", "given", "derived", "warning", "secondary", "accent", "outline", "dim", "surface")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
# The elements a user may set to their own value, and what the value is: it becomes an override of the variant.
CUSTOM = {
    "background_color": "colour or gradient",  # one colour, or "base,shade": the gradient's top and bottom
    "accent_color": "colour",
    "text_font": "font family",
    "voice": "Polly voice id or Google voice name",
    "speaking_speed": "rate 0.8–1.2",
}

# What the optional last stage may reshuffle, by group. Never typography or the frame: text sizes keep every clip's
# layout, so a reshuffled video needs a re-render, not a rebuild.
RESHUFFLE_GROUPS = {
    "colours": ("primary_palette", "secondary_palette", "accent_color"),
    "fonts": ("text_font", "math_font"),
    "background": ("background_type", "background_color"),
    "grid": ("grid_type", "grid_color", "grid_opacity"),
    "border": ("border_style", "border_color"),
}


def library() -> dict[str, dict]:
    """element → {group, description, variants: {id: variant}} (template_kit/elements.json)."""
    elements = json.loads((KIT_DIRECTORY / "elements.json").read_text())["elements"]
    return {
        name: {**{k: v for k, v in spec.items() if k != "variants"}, "variants": {v["id"]: v for v in spec["variants"]}}
        for name, spec in elements.items()
    }


def starter(name: str) -> dict:
    return json.loads((TEMPLATES_DIRECTORY / f"{name}.json").read_text())


def starter_names() -> list[str]:
    return sorted(path.stem for path in TEMPLATES_DIRECTORY.glob("*.json"))


def custom_override(element: str, value: str, mode: str) -> dict:
    """The override a custom value becomes (merged into the chosen variant)."""
    if element == "background_color":
        base, _, shade = value.partition(",")
        return {mode: {"base": base.strip(), "shade": (shade or base).strip(), "glow": base.strip()}}
    if element == "accent_color":
        return {mode: {"accent": value}}
    if element == "text_font":
        return {"family": value}
    if element == "voice":
        return {"polly": {"voice_id": value}, "google": {"neural2": value}}
    return {"rate": float(value)}  # speaking_speed


def custom_value(element: str, override: dict, mode: str) -> str:
    """The value a user typed, read back from its override (the reverse of custom_override)."""
    if element == "background_color":
        base, shade = override[mode]["base"], override[mode]["shade"]
        return base if base == shade else f"{base},{shade}"
    if element == "accent_color":
        return override[mode]["accent"]
    if element == "text_font":
        return override["family"]
    if element == "voice":
        return override["polly"]["voice_id"]
    return str(override["rate"])


def merge(base: dict, extra: dict) -> dict:
    merged = copy.deepcopy(base)
    for key, value in extra.items():
        merged[key] = (
            merge(merged[key], value) if isinstance(value, dict) and isinstance(merged.get(key), dict) else value
        )
    return merged


def problems(template: dict) -> list[str]:
    """What makes a template unusable: unknown or missing elements and variants, bad custom values, unreadable text."""
    lib, chosen = library(), template.get("elements", {})
    errors = [f"unknown element {name}" for name in chosen if name not in lib]
    errors += [f"{name}: not set" for name in ELEMENTS if name not in chosen]
    errors += [
        f"{name}: {chosen[name]} is not one of {', '.join(lib[name]['variants'])}"
        for name in ELEMENTS
        if name in chosen and chosen[name] not in lib[name]["variants"]
    ]
    for name, override in template.get("overrides", {}).items():
        if name not in CUSTOM:
            errors.append(f"{name}: no custom value allowed (custom: {', '.join(CUSTOM)})")
        elif CUSTOM[name].startswith("colour") and not all(
            HEX.match(colour) for part in override.values() for colour in part.values()
        ):
            errors.append(f"{name}: a custom colour is #RRGGBB")
        elif name == "speaking_speed" and not 0.8 <= override.get("rate", 0) <= 1.2:
            errors.append("speaking_speed: a custom rate is 0.8–1.2")
    if errors:
        return errors
    look = resolve(template)
    errors = [
        f"{role} {look['roles'][role]} has {ratio:.2f}:1 contrast on the background (needs 4.5:1)"
        for role in ("text",)
        if (ratio := min(contrast(look["roles"][role], colour) for colour in backgrounds(look))) < 4.5
    ]
    return errors


def resolve(template: dict) -> dict:
    """Every element's full settings for the chosen variant (overrides merged), plus the mode's colours."""
    lib = library()
    look = {
        name: merge(lib[name]["variants"][template["elements"][name]], template.get("overrides", {}).get(name, {}))
        for name in ELEMENTS
    }
    mode = look["theme_mode"]["id"]
    roles = {**look["primary_palette"][mode], **look["secondary_palette"][mode], **look["accent_color"][mode]}
    return {**look, "name": template.get("name", ""), "mode": mode, "background": look["background_color"][mode],
            "roles": roles}  # fmt: skip


def luminance(colour: str) -> float:
    channels = [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(first: str, second: str) -> float:
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def backgrounds(look: dict) -> list[str]:
    fill, background = look["background_type"].get("fill", "solid"), look["background"]
    return {"solid": [background["base"]], "linear": [background["base"], background["shade"]]}.get(
        fill, [background["shade"], background["glow"]]
    )


def background_colour(look: dict) -> str:
    """The single colour behind every clip (the scene harness sets it; grids, gradients and borders come later)."""
    return (
        look["background"]["base"]
        if look["background_type"].get("fill", "solid") == "solid"
        else look["background"]["shade"]
    )


def brief(template: dict) -> str:
    """The template's rules for the clip-builder (TASK.md) and the scene-planner."""
    look = resolve(template)
    sizes = look["typography"]["sizes"]
    inset = max(0.5, look["border_style"].get("inset", 0))
    return "\n".join(
        [
            (
                f"TEMPLATE {look['name']} ({look['mode']} mode). It owns colours, fonts, text sizes and the "
                "background; you own layout, motion and emphasis."
            ),
            "COLOUR ROLES (pass the hex string as color=; SYMBOL COLORS name these roles): "
            + ", ".join(f"{role} {look['roles'][role]}" for role in ROLES if role in look["roles"]),
            f"TEXT: font=\"{look['text_font']['family']}\" for every Text/MarkupText; font_size by style: "
            + ", ".join(f"{style} {sizes[style]}" for style in TEXT_STYLES)
            + f"; MathTex/Tex font_size {sizes['math']}; line_spacing {look['typography'].get('line_spacing', 1)}.",
            f"SAFE AREA: keep everything {inset} units inside the frame edges.",
            "Never set the background or invent colours or sizes outside these.",
        ]
    )


def settings(template: dict) -> dict:
    """The resolved look in one small dict (what changes a clip's key when the template changes)."""
    look = resolve(template)
    return {
        "background": background_colour(look),
        "roles": look["roles"],
        "font": look["text_font"]["family"],
        "sizes": look["typography"]["sizes"],
        "math_preamble": look["math_font"].get("preamble", ""),
        "inset": max(0.5, look["border_style"].get("inset", 0)),
    }


def mode_roles(look: dict, mode: str) -> dict:
    return {**look["primary_palette"][mode], **look["secondary_palette"][mode], **look["accent_color"][mode]}


def drawing(template: dict) -> dict:
    """Everything look_renderer.py draws (backdrop, grid, border, text, maths, subtitles), as plain JSON."""
    look = resolve(template)
    mode, background, roles = look["mode"], look["background"], look["roles"]
    grid_colour = look["grid_color"]
    border_role = look["border_color"]["role"]
    style = look["subtitle_style"]
    box = style.get("box")
    behind = ("dark" if luminance(box["color"]) < 0.18 else "light") if box and box["opacity"] >= 0.6 else mode
    return {
        "mode": mode,
        "background": {**background, **{k: look["background_type"][k] for k in ("fill", "grid", "texture")}},
        "grid": {
            **look["grid_type"],
            "color": (
                ("#FFFFFF" if mode == "dark" else "#000000")
                if grid_colour["source"] == "auto"
                else roles[grid_colour["role"]]
            ),
            "opacity": look["grid_opacity"]["opacity"],
        },
        "border": {
            **look["border_style"],
            "color": background["shade"] if border_role == "__shade__" else roles[border_role],
        },
        "roles": roles,
        "font": look["text_font"]["family"],
        "title_weight": look["text_font"].get("title_weight", "BOLD"),
        "body_weight": look["text_font"].get("body_weight", "NORMAL"),
        "sizes": look["typography"]["sizes"],
        "line_spacing": look["typography"].get("line_spacing", 1),
        "math_preamble": look["math_font"].get("preamble", ""),
        "inset": max(0.5, look["border_style"].get("inset", 0)),
        "subtitles": {
            "on": look["subtitles"].get("burn_in", False),
            "style": style,
            "position": look["caption_position"],
            "highlight": look["word_highlighting"],
            "text_color": mode_roles(look, behind)["text"] if style["text_color"] == "auto" else style["text_color"],
            "highlight_color": mode_roles(look, behind)[style.get("highlight_role", "focus")],
        },
    }


if __name__ == "__main__":  # self-check: every starter template resolves, in both modes
    for starter_name in starter_names():
        for theme in ("dark", "light"):
            candidate = starter(starter_name)
            candidate["elements"]["theme_mode"] = theme
            assert not problems(candidate), (starter_name, theme, problems(candidate))
    print("ok:", ", ".join(starter_names()))


def reshuffle(template: dict, seed: int, groups: list[str]) -> dict:
    """The template with each element of the chosen groups set to another variant, picked by the seed alone: the same
    template, seed and groups always give the same result. A custom value of a reshuffled element is dropped; a pick
    that would make the text unreadable is skipped, and an element with no usable alternative keeps its variant."""
    unknown = [group for group in groups if group not in RESHUFFLE_GROUPS]
    if unknown:
        raise ValueError(f"no group {', '.join(unknown)}: choose from {', '.join(RESHUFFLE_GROUPS)}")
    lib, chooser, result = library(), random.Random(seed), copy.deepcopy(template)
    for group, elements in RESHUFFLE_GROUPS.items():  # a fixed order, whatever order the groups came in
        if group not in groups:
            continue
        for element in elements:
            options = sorted(variant for variant in lib[element]["variants"] if variant != result["elements"][element])
            chooser.shuffle(options)
            for option in options:
                trial = {
                    **result,
                    "elements": {**result["elements"], element: option},
                    "overrides": {k: v for k, v in result.get("overrides", {}).items() if k != element},
                }
                if not problems(trial):
                    result = trial
                    break
    return result
