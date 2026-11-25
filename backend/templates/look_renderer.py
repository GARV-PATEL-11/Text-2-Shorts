"""Draws a template's look in Manim from `video_settings.drawing()`: the backdrop (fill, texture, grid), the border,
text and maths in the template's font and sizes, the Faraday mark (top right) and a still subtitle line. One drawing for both uses, so a preview
never shows something a video does not get:
  - the scene harness puts the backdrop and border behind every clip of a video (z-index -100 / 400);
  - generate_preview.py renders previews of every option, and of the user's own values.
"""

from __future__ import annotations

import math
import random
from pathlib import Path
from typing import ClassVar

import manim as M
import numpy as np

FONT_DIRECTORY = Path.home() / ".cache" / "text-2-shorts" / "fonts"  # fetched by `generate_preview.py fonts`
LOGO = Path(__file__).with_name("faraday-logo.webp")  # mark + wordmark, white on transparent (copied with this file)
BACKDROP_Z, BORDER_Z, SUBTITLE_Z = -100, 400, 500


def register_fonts() -> None:
    """Make the templates' fonts visible to Pango in this process only (nothing is installed system-wide)."""
    import manimpango

    for font_file in sorted(FONT_DIRECTORY.glob("*.[ot]tf")):
        manimpango.register_font(str(font_file))


def colour(hex_colour: str) -> M.ManimColor:
    return M.ManimColor(hex_colour)


# ── backdrop: fill, texture, grid ─────────────────────────────────────────────────────────────────────────────
def backdrop(look: dict) -> list[M.Mobject]:
    width, height = M.config.frame_width, M.config.frame_height
    background, parts = look["background"], []
    if background["fill"] == "linear":
        gradient = M.Rectangle(width=width + 0.2, height=height + 0.2).set_stroke(width=0)
        gradient.set_fill(color=[colour(background["base"]), colour(background["shade"])], opacity=1)
        gradient.set_sheen_direction(M.DOWN)  # base at the top, shade at the bottom
        parts.append(gradient)
    elif background["fill"] == "radial":
        glow, rings = M.VGroup(), 14
        for ring in range(rings):
            radius = math.hypot(width, height) / 2 * (1 - ring / rings) * 0.9
            glow.add(
                M.Ellipse(width=2 * radius * 1.15, height=2 * radius * 0.8)
                .set_stroke(width=0)
                .set_fill(colour(background["glow"]), opacity=0.09)
            )
        parts.append(glow)
    if background["texture"]:
        parts.append(texture(look, width, height))
    if background["grid"]:
        parts.append(grid(look, width, height))
    if (mark := brand(look)) is not None:
        parts.append(mark)
    for index, part in enumerate(parts):
        part.set_z_index(BACKDROP_Z + index)
    return parts


def brand(look: dict) -> M.ImageMobject | None:
    """The Faraday mark and wordmark in the top-right corner, tinted with the template's text colour."""
    spec = look.get("brand")
    if not spec or not LOGO.exists():
        return None
    from PIL import Image

    alpha = np.asarray(Image.open(LOGO).convert("RGBA"))[:, :, 3]
    red, green, blue = (int(spec["color"].lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    pixels = np.zeros((*alpha.shape, 4), dtype=np.uint8)
    pixels[:, :, :3] = (red, green, blue)
    pixels[:, :, 3] = (alpha * spec["opacity"]).astype(np.uint8)
    mark = M.ImageMobject(pixels).set_resampling_algorithm(M.RESAMPLING_ALGORITHMS["bicubic"])
    mark.height = spec["height"]
    inset = look["inset"]
    return mark.move_to(
        [M.config.frame_width / 2 - inset - mark.width / 2, M.config.frame_height / 2 - inset - mark.height / 2, 0]
    )


def background_colour(look: dict) -> str:
    """The camera colour under the backdrop: the base, or the shade under a gradient or glow."""
    return look["background"]["base"] if look["background"]["fill"] == "solid" else look["background"]["shade"]


def texture(look: dict, width: float, height: float) -> M.VGroup:
    dark = look["mode"] == "dark"  # chalk dust on dark, paper grain on light
    rng = random.Random(11 if dark else 5)
    dust = colour("#ffffff" if dark else "#5a4a30")
    count, radii, opacity = (700, (0.004, 0.018), 0.07) if dark else (900, (0.003, 0.010), 0.05)
    return M.VGroup(
        *[
            M.Dot(
                [rng.uniform(-width / 2, width / 2), rng.uniform(-height / 2, height / 2), 0],
                radius=rng.uniform(*radii),
                color=dust,
                fill_opacity=opacity * rng.uniform(0.3, 1.0),
            )
            for _ in range(count)
        ]
    )


def grid(look: dict, width: float, height: float) -> M.Mobject:
    spec = look["grid"]
    line_colour, opacity = colour(spec["color"]), spec["opacity"]
    half_width, half_height, stroke = width / 2, height / 2, spec.get("stroke_width", 1.0)
    diagonal = math.hypot(width, height)

    def lines(step, stroke_width, line_opacity, vertical=True):
        group = M.VGroup()
        if vertical:
            for i in range(-int(half_width // step) - 1, int(half_width // step) + 2):
                group.add(M.Line([i * step, -half_height, 0], [i * step, half_height, 0]))
        for j in range(-int(half_height // step) - 1, int(half_height // step) + 2):
            group.add(M.Line([-half_width, j * step, 0], [half_width, j * step, 0]))
        return group.set_stroke(line_colour, stroke_width, line_opacity)

    kind = spec["kind"]
    if kind == "square":
        return lines(spec["spacing"], stroke, opacity)
    if kind == "graph_paper":
        return M.VGroup(
            lines(spec["minor"], spec["minor_stroke"], opacity * spec["minor_opacity_ratio"]),
            lines(spec["major"], spec["major_stroke"], opacity),
        )
    if kind == "ruled":
        margin = M.Line(
            [-half_width + spec["margin_line_x"], -half_height, 0],
            [-half_width + spec["margin_line_x"], half_height, 0],
        )
        margin.set_stroke(colour(look["roles"]["accent"]), stroke * 1.5, min(1.0, opacity * 1.6))
        return M.VGroup(lines(spec["spacing"], stroke, opacity, vertical=False), margin)
    if kind == "dots":
        step = spec["spacing"]
        return M.VGroup(
            *[
                M.Dot(
                    [i * step, j * step, 0],
                    radius=spec["dot_radius"],
                    color=line_colour,
                    fill_opacity=min(1, opacity * 2),
                )
                for i in range(-int(half_width // step), int(half_width // step) + 1)
                for j in range(-int(half_height // step), int(half_height // step) + 1)
            ]
        )
    if kind == "number_plane":
        x, y = math.ceil(half_width), math.ceil(half_height)
        plane = M.NumberPlane(
            x_range=[-x, x, spec["spacing"]],
            y_range=[-y, y, spec["spacing"]],
            x_length=2 * x,
            y_length=2 * y,
            faded_line_ratio=spec.get("faded_line_ratio", 1),
        )
        plane.background_lines.set_stroke(line_colour, stroke, opacity)
        plane.faded_lines.set_stroke(line_colour, stroke * 0.5, opacity * 0.5)
        M.VGroup(plane.x_axis, plane.y_axis).set_stroke(
            line_colour, spec["axis_stroke"], min(1, opacity * spec["axis_opacity_ratio"])
        )
        return plane
    if kind == "isometric":
        group, step = M.VGroup(), spec["spacing"]
        for angle in (0, 60, 120):
            radians = math.radians(angle)
            direction = np.array([math.cos(radians), math.sin(radians), 0])
            normal = np.array([-math.sin(radians), math.cos(radians), 0])
            for k in range(-int(diagonal / 2 / step) - 1, int(diagonal / 2 / step) + 2):
                offset = normal * k * step
                group.add(M.Line(offset - direction * diagonal / 2, offset + direction * diagonal / 2))
        return group.set_stroke(line_colour, stroke, opacity)
    if kind == "polar":
        group, ring_spacing = M.VGroup(), spec["ring_spacing"]
        for k in range(1, int(diagonal / 2 / ring_spacing) + 2):
            group.add(M.Circle(radius=k * ring_spacing))
        for k in range(spec["spokes"]):
            angle = 2 * math.pi * k / spec["spokes"]
            group.add(M.Line(M.ORIGIN, [diagonal / 2 * math.cos(angle), diagonal / 2 * math.sin(angle), 0]))
        return group.set_stroke(line_colour, stroke, opacity)
    raise ValueError(f"unknown grid kind {kind}")


# ── border ────────────────────────────────────────────────────────────────────────────────────────────────────
def border(look: dict) -> M.Mobject | None:
    spec = look["border"]
    if spec["kind"] == "none":
        return None
    width, height = M.config.frame_width, M.config.frame_height
    line_colour = colour(spec["color"])

    def frame_rectangle(margin, radius=0.0):
        size = {"width": width - 2 * margin, "height": height - 2 * margin}
        shape = M.RoundedRectangle(corner_radius=radius, **size) if radius else M.Rectangle(**size)
        return shape.set_stroke(line_colour, spec.get("width", 2)).set_fill(opacity=0)

    kind = spec["kind"]
    if kind == "rect":
        drawn = frame_rectangle(spec["margin"], spec.get("corner_radius", 0))
    elif kind == "double":
        drawn = M.VGroup(frame_rectangle(spec["margin"]), frame_rectangle(spec["margin"] + spec["gap"]))
    elif kind == "dashed":
        drawn = M.DashedVMobject(frame_rectangle(spec["margin"]), num_dashes=spec["dashes"]).set_stroke(
            line_colour, spec["width"]
        )
    elif kind == "corners":
        margin, length = spec["margin"], spec["length"]
        drawn = M.VGroup()
        for sx in (-1, 1):
            for sy in (-1, 1):
                corner = np.array([sx * (width / 2 - margin), sy * (height / 2 - margin), 0])
                drawn.add(M.Line(corner, corner - [sx * length, 0, 0]), M.Line(corner, corner - [0, sy * length, 0]))
        drawn.set_stroke(line_colour, spec["width"])
    elif kind == "bars":
        drawn = M.VGroup(
            *[
                M.Rectangle(width=width + 0.2, height=spec["height"])
                .set_stroke(width=0)
                .set_fill(line_colour, spec["opacity"])
                .move_to([0, sy * (height / 2 - spec["height"] / 2), 0])
                for sy in (-1, 1)
            ]
        )
    else:
        raise ValueError(f"unknown border kind {kind}")
    return drawn.set_z_index(BORDER_Z)


# ── text and maths in the template's font and sizes ──────────────────────────────────────────────────────────
# Pango hints glyph positions to whole pixels at the size it typesets, so small Text gets uneven letter spacing
# ("Sq uare"). Typesetting TYPESET times larger and scaling down keeps the spacing even at every output size.
TYPESET = 4


def typeset(words: str, font_size: float, **options) -> M.Text:
    return M.Text(words, font_size=font_size * TYPESET, **options).scale(1 / TYPESET)


def text(look: dict, words: str, style: str = "body", role: str = "text") -> M.Text:
    weight = look["title_weight"] if style in ("title", "heading") else look["body_weight"]
    return typeset(
        words,
        look["sizes"][style],
        font=look["font"],
        color=colour(look["roles"][role]),
        weight=weight,
        line_spacing=look["line_spacing"],
    )


def maths(look: dict, *tex: str, role: str = "text") -> M.MathTex:
    template = M.TexTemplate()
    template.add_to_preamble(look["math_preamble"])
    return M.MathTex(*tex, font_size=look["sizes"]["math"], color=colour(look["roles"][role]), tex_template=template)


def safe_area(look: dict) -> tuple[float, float, float, float]:
    """x_min, x_max, y_min, y_max where content may go (inside the inset, above burned-in subtitles)."""
    half_width, half_height, inset = M.config.frame_width / 2, M.config.frame_height / 2, look["inset"]
    bottom = -half_height + inset
    subtitles = look["subtitles"]
    if subtitles["on"] and subtitles["position"]["anchor"] == "bottom":
        bottom = max(bottom, -half_height + subtitles["position"]["reserve"] * 2 * half_height)
    top = half_height - inset
    if "brand" in look:  # below the Faraday mark's band
        top -= look["brand"]["height"] + look["brand"]["gap"]
    if subtitles["on"] and subtitles["position"]["anchor"] == "top":
        top = min(top, half_height - subtitles["position"]["reserve"] * 2 * half_height)
    return -half_width + inset, half_width - inset, bottom, top


# ── a still subtitle line (burned-in subtitles are drawn by previews only, for now) ───────────────────────────
def subtitle(look: dict, words: list[str], current: int) -> M.VGroup:
    spec = look["subtitles"]
    style, position, highlight = spec["style"], spec["position"], spec["highlight"]["mode"]
    shown = [word.upper() for word in words] if style["uppercase"] else list(words)
    lines, line = [], []
    for index, word in enumerate(shown):  # fill lines up to max_chars_per_line, at most max_lines
        if line and len(" ".join(shown[i] for i in line + [index])) > style["max_chars_per_line"]:
            lines.append(line)
            line = []
        line.append(index)
    lines = (lines + [line])[-style["max_lines"] :]
    base, accent = colour(spec["text_color"]), colour(spec["highlight_color"])
    pieces, rows = {}, M.VGroup()
    for row in lines:  # one Text per line keeps a single baseline; its glyphs are split back into words
        line_text = typeset(
            " ".join(shown[i] for i in row),
            style["font_size"],
            font=look["font"],
            weight=style["weight"],
            color=base,
        )
        glyphs, start = line_text.submobjects, 0
        letters = [len(shown[i]) for i in row]
        gap = 1 if len(glyphs) == sum(letters) + len(row) - 1 else 0  # Manim counts spaces as (empty) glyphs
        if len(glyphs) == sum(letters) + gap * (len(row) - 1):
            for i, count in zip(row, letters):
                pieces[i] = M.VGroup(*glyphs[start : start + count])
                start += count + gap
            rows.add(line_text)
        else:  # ligatures changed the glyph count: lay the words out one by one
            words_row = M.VGroup(
                *[
                    typeset(shown[i], style["font_size"], font=look["font"], weight=style["weight"], color=base)
                    for i in row
                ]
            )
            pieces.update(zip(row, words_row))
            rows.add(words_row.arrange(M.RIGHT, buff=style["font_size"] / 48 * 0.2, aligned_edge=M.DOWN))
    rows.arrange(M.DOWN, buff=style["font_size"] / 48 * 0.25)
    for index, piece in pieces.items():
        state = "current" if index == current else ("past" if index < current else "future")
        if highlight == "karaoke" and state != "future" or highlight == "current_color" and state == "current":
            piece.set_color(accent)
        elif highlight == "reveal" and state == "future":
            piece.set_opacity(0)
        elif highlight == "dim_past" and state == "past":
            piece.set_opacity(spec["highlight"].get("dim_opacity", 0.45))
    if style.get("outline"):
        outline = style["outline"]["color"]
        if outline == "auto":
            outline = "#000000" if luminance(spec["text_color"]) > 0.4 else "#FFFFFF"
        rows.set_stroke(colour(outline), style["outline"]["width"], background=True)
    width, height = M.config.frame_width, M.config.frame_height
    if rows.width > position["width_fraction"] * width:
        rows.scale_to_fit_width(position["width_fraction"] * width)
    group = M.VGroup()
    if style.get("box"):
        padding = style["padding"]
        box = M.RoundedRectangle(
            width=rows.width + 2 * padding, height=rows.height + 1.4 * padding, corner_radius=style["corner_radius"]
        ).move_to(rows)
        group.add(box.set_stroke(width=0).set_fill(colour(style["box"]["color"]), style["box"]["opacity"]))
    if current in pieces and highlight in ("underline", "box"):
        target = pieces[current]
        if highlight == "underline":
            thickness = style["font_size"] / 48 * 0.06
            marker = M.Rectangle(width=target.width, height=thickness).next_to(target, M.DOWN, buff=thickness * 1.5)
            marker.set_stroke(width=0).set_fill(accent, 1)
        else:
            marker = M.Rectangle(width=target.width + 0.12, height=target.height + 0.12).move_to(target)
            marker.set_stroke(width=0).set_fill(accent, spec["highlight"].get("box_opacity", 0.35))
        group.add(marker)
    group.add(rows)
    edge = max(position["edge_offset"], look["border"].get("inset", 0) + 0.05)
    x = {"center": 0, "left": -width / 2 + 0.4 + group.width / 2, "right": width / 2 - 0.4 - group.width / 2}[
        position["x_align"]
    ]
    y = (
        (-height / 2 + edge + group.height / 2)
        if position["anchor"] == "bottom"
        else (height / 2 - edge - group.height / 2)
    )
    return group.move_to([x, y, 0]).set_z_index(SUBTITLE_Z)


def luminance(hex_colour: str) -> float:
    channels = [int(hex_colour.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


# ── the preview: every part of the look in one frame ─────────────────────────────────────────────────────────
CAPTION = "The area under x squared, from zero to a, is a cubed over three."
ROLES = ("text", "focus", "given", "derived", "warning", "secondary", "accent")


def swatch(look: dict) -> list[M.Mobject]:
    x_min, x_max, y_min, y_max = safe_area(look)
    roles = look["roles"]
    title = text(look, "Curves and Areas", "title")
    body = text(look, "How much space sits under a parabola?", "body")
    function = maths(look, r"f(x) = x^2 + 2x + 1", role="given")
    integral = maths(look, r"\int_0^a x^2\,dx = \frac{a^3}{3}", role="derived")
    label = text(look, "label · caption 123", "label", "secondary")
    column = M.VGroup(title, body, function, integral, label).arrange(M.DOWN, aligned_edge=M.LEFT, buff=0.3)
    chips = M.VGroup(
        *[M.Circle(radius=0.26).set_stroke(width=0).set_fill(colour(roles[role]), 1) for role in ROLES]
    ).arrange(M.RIGHT, buff=0.14)
    axes = M.Axes(x_range=[0, 2, 1], y_range=[0, 4, 1], x_length=3.2, y_length=2.6, tips=False,
                  axis_config={"color": colour(roles["outline"]), "stroke_width": 2})  # fmt: skip
    curve = axes.plot(lambda x: x**2, x_range=[0, 2], color=colour(roles["focus"]), stroke_width=4)
    area = axes.get_area(curve, x_range=[0, 1.5], color=colour(roles["accent"]), opacity=0.35)
    marker = text(look, "a", "label", "secondary").next_to(axes.c2p(1.5, 0), M.DOWN, buff=0.12)
    triangle = M.Polygon([0, 0, 0], [1.8, 0, 0], [1.8, 1.35, 0]).set_stroke(colour(roles["given"]), 4)
    figures = M.VGroup(M.VGroup(axes, area, curve, marker), triangle).arrange(M.RIGHT, buff=0.5, aligned_edge=M.DOWN)
    side = M.VGroup(chips, figures).arrange(M.DOWN, buff=0.45, aligned_edge=M.RIGHT)
    for group in (column, side):
        if group.width > (x_max - x_min) / 2 - 0.2:
            group.scale_to_fit_width((x_max - x_min) / 2 - 0.2)
        if group.height > y_max - y_min:
            group.scale_to_fit_height(y_max - y_min)
    middle = (y_max + y_min) / 2  # centred in the safe area, at the video's real sizes
    column.move_to([x_min + column.width / 2, middle, 0])
    side.move_to([x_max - side.width / 2, middle, 0])
    return [column, side]


class LookScene(M.Scene):
    """One frame of a look: backdrop, border, the swatch and, when on, a subtitle line (the 7th word spoken)."""

    look: ClassVar[dict] = {}

    def construct(self):
        self.camera.background_color = colour(background_colour(self.look))
        self.add(*backdrop(self.look))
        if (frame := border(self.look)) is not None:
            self.add(frame)
        self.add(*swatch(self.look))
        if self.look["subtitles"]["on"]:
            self.add(subtitle(self.look, CAPTION.split(), 6))
