"""
template_kit.py - enforce a 16:9 look-and-sound template on agent-generated Manim scenes.

The template fixes: dark/light mode, resolution, background, grid, palettes, accent, fonts, type scale,
border, narrator voice, speaking speed, narration tone and subtitles. Everything else (layout, motion,
emphasis, line weights, how much is on screen) is the planning agent's call.

In a generated scene file:

    from manim import *
    from template_kit import use_template, TemplateScene
    T = use_template("templates/chalkboard.json")   # module level, before scenes render

    class Lesson(TemplateScene):
        def construct(self):
            title = T.text("Pythagoras", style="title").to_edge(UP, buff=T.inset)
            with self.narrate("Let's look at a right triangle.") as n:
                self.play(Write(title))

CLI:
    python template_kit.py [templates/*.json] [--brief]   validate templates (and print the agent brief)
    python template_kit.py --lint scene.py                 flag hard-coded styling in generated code

Env:
    MANIM_TEMPLATE_FRAME=draft_480p15    swap the frame variant for quick previews
    MANIM_TEMPLATE_MODE=dark|light       override theme_mode
    NARRATION_ENGINE=silent|polly|google see narration.py
"""
from __future__ import annotations

import copy
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import warnings
from contextlib import contextmanager
from pathlib import Path

KIT_DIR = Path(__file__).resolve().parent
VISUAL = ("theme_mode", "frame", "background_type", "background_color", "grid_type", "grid_color", "grid_opacity",
          "primary_palette", "secondary_palette", "accent_color", "text_font", "math_font", "typography",
          "border_style", "border_color")
AUDIO = ("voice", "speaking_speed", "narration_tone", "subtitles", "subtitle_style", "caption_position",
         "word_highlighting")
ELEMENTS = VISUAL + AUDIO
TEXT_STYLES = ("title", "heading", "body", "label", "caption")
CONTENT_ROLES = ("text", "focus", "given", "derived", "warning", "secondary", "accent")
FRAME_HEIGHT, ASPECT = 8.0, 16 / 9


class TemplateError(ValueError):
    pass


# --------------------------------------------------------------------------- resolve

def _deep_merge(base: dict, extra: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in extra.items():
        out[k] = _deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out


def load_library(path=None) -> dict:
    path = Path(path) if path else KIT_DIR / "elements.json"
    data = json.loads(path.read_text(encoding="utf-8"))["elements"]
    return {el: {v["id"]: v for v in data[el]["variants"]} for el in ELEMENTS}


def resolve(template, library=None) -> dict:
    """Expand a template (path or dict of element ids) into full settings plus mode-resolved colours."""
    lib = library or load_library()
    if not isinstance(template, dict):
        template = json.loads(Path(template).read_text(encoding="utf-8"))
    chosen, overrides = template.get("elements", {}), template.get("overrides", {})
    for bad in set(chosen) | set(overrides):
        if bad not in ELEMENTS:
            raise TemplateError(f"{template.get('name')}: unknown element '{bad}'")
    t = {"name": template["name"], "description": template.get("description", "")}
    for el in ELEMENTS:
        vid = chosen.get(el)
        if vid is None:
            raise TemplateError(f"{template['name']}: element '{el}' is not set")
        if vid not in lib[el]:
            raise TemplateError(f"{template['name']}: '{vid}' is not a {el} variant; use one of {sorted(lib[el])}")
        t[el] = _deep_merge(lib[el][vid], overrides.get(el, {}))
    mode = t["theme_mode"]["id"]
    t["mode"] = mode
    t["bg"] = t["background_color"][mode]
    t["roles"] = mode_roles(t, mode)
    gc = t["grid_color"]
    t["grid_hex"] = ("#FFFFFF" if mode == "dark" else "#000000") if gc["source"] == "auto" else t["roles"][gc["role"]]
    role = t["border_color"]["role"]
    t["border_hex"] = t["bg"]["shade"] if role == "__shade__" else t["roles"][role]
    return t


def mode_roles(t: dict, mode: str) -> dict:
    return {**t["primary_palette"][mode], **t["secondary_palette"][mode], **t["accent_color"][mode]}


# --------------------------------------------------------------------------- validate

def _luminance(hex_: str) -> float:
    h = hex_.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def background_colors(t: dict) -> list:
    bg, fill = t["bg"], t["background_type"]["fill"]
    return {"solid": [bg["base"]], "linear": [bg["base"], bg["shade"]], "radial": [bg["shade"], bg["glow"]]}[fill]


def subtitle_mode(t: dict) -> str:
    """Mode of whatever sits behind the subtitles: their own box if opaque enough, else the page."""
    box = t["subtitle_style"]["box"]
    if box and box["opacity"] >= 0.6:
        return "dark" if _luminance(box["color"]) < 0.18 else "light"
    return t["mode"]


def subtitle_text_color(t: dict) -> str:
    c = t["subtitle_style"]["text_color"]
    return mode_roles(t, subtitle_mode(t))["text"] if c == "auto" else c


def subtitle_highlight_color(t: dict) -> str:
    return mode_roles(t, subtitle_mode(t))[t["subtitle_style"]["highlight_role"]]


def validate(t: dict) -> tuple[list, list]:
    """Return (errors, warnings). Errors make the template unusable."""
    errors, warns = [], []
    fr = t["frame"]
    if abs(fr["pixel_width"] / fr["pixel_height"] - ASPECT) > 0.01:
        errors.append(f"frame '{fr['id']}' is not 16:9")
    bgs = background_colors(t)
    for role in CONTENT_ROLES:
        need = 4.5 if role == "text" else 3.0
        worst = min(contrast(t["roles"][role], c) for c in bgs)
        if worst < need:
            (errors if role == "text" else warns).append(
                f"{role} {t['roles'][role]} has {worst:.2f}:1 on the {t['mode']} background (needs {need}:1)")
    if t["subtitles"]["burn_in"]:
        st = t["subtitle_style"]
        behind = [st["box"]["color"]] if st["box"] and st["box"]["opacity"] >= 0.6 else bgs
        if not st["outline"]:
            txt = subtitle_text_color(t)
            worst = min(contrast(txt, c) for c in behind)
            if worst < 4.5:
                errors.append(f"subtitle text {txt} has {worst:.2f}:1 contrast (needs 4.5:1); pick a boxed or outlined style")
            if t["word_highlighting"]["mode"] in ("karaoke", "current_color"):
                hl = subtitle_highlight_color(t)
                worst = min(contrast(hl, c) for c in behind)
                if worst < 3.0:
                    warns.append(f"highlight colour {hl} has {worst:.2f}:1 against the subtitle background")
    return errors, warns


def pick_font(family: str, fallbacks=()) -> tuple[str, str | None]:
    """Return (installed family, note). Without manimpango, trust the requested family."""
    try:
        import manimpango
        installed = set(manimpango.list_fonts())
    except Exception:
        return family, None
    for fam in (family, *fallbacks):
        if fam in installed:
            return fam, None if fam == family else f"font '{family}' not installed (run install_fonts.py); using '{fam}'"
    return "Sans", f"none of {[family, *fallbacks]} installed (run install_fonts.py); using 'Sans'"


def missing_tex_packages(preamble: str) -> list[str]:
    if not preamble or not shutil.which("kpsewhich"):
        return []
    pkgs = [p.strip() for grp in re.findall(r"\\usepackage(?:\[[^\]]*\])?\{([^}]*)\}", preamble) for p in grp.split(",")]
    return [p for p in pkgs
            if not subprocess.run(["kpsewhich", f"{p}.sty"], capture_output=True, text=True).stdout.strip()]


# --------------------------------------------------------------------------- agent brief + lint

def safe_area_numbers(t: dict) -> tuple[float, float, float, float]:
    """(x_min, x_max, y_min, y_max) in Manim units where content may go."""
    fw, fh = FRAME_HEIGHT * ASPECT, FRAME_HEIGHT
    inset = max(0.3, t["border_style"]["inset"])
    x_min, x_max, y_min, y_max = -fw / 2 + inset, fw / 2 - inset, -fh / 2 + inset, fh / 2 - inset
    cp = t["caption_position"]
    if t["subtitles"]["burn_in"] and cp["reserve"] > 0:
        if cp["anchor"] == "bottom":
            y_min = max(y_min, -fh / 2 + cp["reserve"] * fh)
        else:
            y_max = min(y_max, fh / 2 - cp["reserve"] * fh)
    return x_min, x_max, y_min, y_max


def agent_brief(t: dict) -> str:
    """Rules for the planning/code/script agent's system prompt."""
    x0, x1, y0, y1 = safe_area_numbers(t)
    tone = t["narration_tone"]
    ty = t["typography"]
    return "\n".join([
        f"VIDEO TEMPLATE '{t['name']}' ({t['mode']} mode, 16:9): {t['description']}",
        "The template owns colours, fonts, text sizes, background, grid, border, voice and subtitles. "
        "You own layout, motion, emphasis, line weights and pacing.",
        "Text and maths:  T.text(s, style=title|heading|body|label|caption, role=...)   T.math(*tex, role=...)   T.code(s)",
        f"  sizes: " + ", ".join(f"{k} {ty['sizes'][k]}" for k in TEXT_STYLES) + f", math {ty['sizes']['math']}",
        "Colour:  T.color(role) for any colour argument (fill, stroke, Arrow, Axes...). Roles: "
        + ", ".join(CONTENT_ROLES) + ", outline, dim, surface. given = known inputs, derived = results, focus = current point.",
        f"Safe area: x {x0:.2f}..{x1:.2f}, y {y0:.2f}..{y1:.2f} (T.safe_area). Keep every mobject inside; "
        "T.fit(mob) shrinks and nudges one in. Use buff=T.inset with to_edge/to_corner.",
        "Narration: with self.narrate(\"...\") as n: play the matching animations inside; n.wait_until(\"word\") syncs to a word.",
        f"  Write English. Tone '{tone['label']}': {tone['script_rules']} Max {tone['max_sentence_words']} words per sentence.",
        "Never write hex codes, Manim colour constants, font=, font_size=, config.*, background or border mobjects, "
        "add_sound or subtitles.",
    ])


_LINT_RULES = [
    (r"#[0-9a-fA-F]{6}\b", "hex colour literal - use T.color(role)"),
    (r"\b(?:WHITE|BLACK|PURE_(?:RED|GREEN|BLUE)|(?:GRAY|GREY|BLUE|TEAL|GREEN|YELLOW|GOLD|RED|MAROON|PURPLE|PINK|ORANGE)(?:_[A-E])?)\b",
     "Manim colour constant - use T.color(role)"),
    (r"\bfont\s*=", "font= - fonts come from the template"),
    (r"\bfont_size\s*=", "font_size= - use style="),
    (r"\badd_sound\(|\badd_subcaption\(", "audio and subtitles are added by narrate()"),
    (r"\bconfig\.", "config.* - frame and background belong to the template"),
    (r"\bbackground_color\b|\bset_background\b", "background is owned by the template"),
]


def lint(source: str) -> list[tuple[int, str, str]]:
    issues = []
    for n, line in enumerate(source.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        code = re.sub(r"\s#\s.*$", "", line)
        for pat, msg in _LINT_RULES:
            if re.search(pat, code):
                issues.append((n, msg, line.strip()))
    return issues


# --------------------------------------------------------------------------- Manim side

try:
    import numpy as np
    import manim as M
    from manim import config
    HAVE_MANIM = True
except ImportError:  # resolve/validate/lint still work without Manim
    HAVE_MANIM = False

_ACTIVE = None


def use_template(path, library=None, strict: bool | None = None):
    """Resolve, validate and activate a template, and apply it to Manim's config.
    strict (default: env TEMPLATE_STRICT, else True) turns rule breaks into errors instead of warnings."""
    global _ACTIVE
    lib = library or load_library()
    tpl = copy.deepcopy(path) if isinstance(path, dict) else json.loads(Path(path).read_text(encoding="utf-8"))
    for env, el in (("MANIM_TEMPLATE_FRAME", "frame"), ("MANIM_TEMPLATE_MODE", "theme_mode")):
        if os.environ.get(env):
            tpl["elements"][el] = os.environ[env]
    t = resolve(tpl, lib)
    errors, warns = validate(t)
    for w in warns:
        warnings.warn(f"[template {t['name']}] {w}")
    if errors:
        raise TemplateError(f"template '{t['name']}': " + "; ".join(errors))
    if not HAVE_MANIM:
        raise ImportError("manim is required to render")
    if strict is None:
        strict = os.environ.get("TEMPLATE_STRICT", "1") != "0"
    _ACTIVE = Theme(t, strict)
    _ACTIVE.apply_config()
    return _ACTIVE


class Theme:
    def __init__(self, t: dict, strict: bool = True):
        self.t, self.strict, self.name = t, strict, t["name"]
        tf = t["text_font"]
        self.font, note = pick_font(tf["family"], tuple(tf.get("fallbacks", ())))
        if note:
            warnings.warn(f"[template {self.name}] {note}")
        self._code_font = None
        missing = missing_tex_packages(t["math_font"]["preamble"])
        if missing:
            self._violation(f"math_font '{t['math_font']['id']}' needs TeX packages {missing} "
                            f"(TeX Live: {t['math_font']['tex_packages']})")
        self.tex_template = M.TexTemplate()
        if t["math_font"]["preamble"]:
            self.tex_template.add_to_preamble(t["math_font"]["preamble"])
        try:   # compile once now (cached by Manim) so a broken TeX setup fails before any rendering
            M.MathTex(r"x^2", tex_template=self.tex_template)
        except Exception as e:
            raise TemplateError(f"math_font '{t['math_font']['id']}' does not compile on this machine "
                                f"(TeX Live: {t['math_font']['tex_packages']}): {e}") from None

    # -- config
    def apply_config(self):
        fr = self.t["frame"]
        config.pixel_width, config.pixel_height = fr["pixel_width"], fr["pixel_height"]
        config.frame_rate = fr["frame_rate"]
        config.frame_height = FRAME_HEIGHT
        config.frame_width = FRAME_HEIGHT * fr["pixel_width"] / fr["pixel_height"]
        bg, fill = self.t["bg"], self.t["background_type"]["fill"]
        config.background_color = bg["base"] if fill == "solid" else bg["shade"]

    def _violation(self, msg):
        if self.strict:
            raise TemplateError(f"[{self.name}] {msg}")
        warnings.warn(f"[template {self.name}] {msg}")

    def _forbid(self, kw, *keys):
        bad = [k for k in keys if k in kw]
        if bad:
            self._violation(f"{bad} are set by the template and may not be passed")
            for k in bad:
                kw.pop(k)

    # -- geometry the agent works within
    @property
    def inset(self) -> float:
        return max(0.3, self.t["border_style"]["inset"])

    @property
    def safe_area(self):
        return safe_area_numbers(self.t)

    def fit(self, mob, buff: float = 0.0):
        """Shrink mob if it is larger than the safe area, then nudge it fully inside."""
        x0, x1, y0, y1 = self.safe_area
        w, h = x1 - x0 - 2 * buff, y1 - y0 - 2 * buff
        if mob.width > w:
            mob.scale_to_fit_width(w)
        if mob.height > h:
            mob.scale_to_fit_height(h)
        dx = max(0, x0 + buff - mob.get_left()[0]) - max(0, mob.get_right()[0] - (x1 - buff))
        dy = max(0, y0 + buff - mob.get_bottom()[1]) - max(0, mob.get_top()[1] - (y1 - buff))
        mob.shift([dx, dy, 0])
        return mob

    # -- colour and type
    def color(self, role: str):
        if role not in self.t["roles"]:
            raise TemplateError(f"unknown colour role '{role}'; use one of {list(self.t['roles'])}")
        return M.ManimColor(self.t["roles"][role])

    def text(self, s: str, style: str = "body", role: str = "text", **kw):
        self._forbid(kw, "font", "font_size", "weight")
        if style not in TEXT_STYLES:
            raise TemplateError(f"style must be one of {TEXT_STYLES}")
        if "color" in kw:
            self._violation("pass role= instead of color=")
            kw.pop("color")
        tf, ty = self.t["text_font"], self.t["typography"]
        weight = tf["title_weight"] if style in ("title", "heading") else tf["body_weight"]
        kw.setdefault("line_spacing", ty["line_spacing"])
        return M.Text(s, font=self.font, font_size=ty["sizes"][style], color=self.color(role), weight=weight, **kw)

    @property
    def code_font(self):
        if self._code_font is None:
            self._code_font, note = pick_font(self.t["text_font"]["code_family"], ("DejaVu Sans Mono", "Monospace"))
            if note:
                warnings.warn(f"[template {self.name}] {note}")
        return self._code_font

    def code(self, s: str, role: str = "text", **kw):
        self._forbid(kw, "font", "font_size", "color")
        return M.Text(s, font=self.code_font, font_size=self.t["typography"]["sizes"]["label"], color=self.color(role), **kw)

    def math(self, *tex: str, role: str = "text", **kw):
        self._forbid(kw, "font_size", "color", "tex_template")
        return M.MathTex(*tex, font_size=self.t["typography"]["sizes"]["math"], color=self.color(role),
                         tex_template=self.tex_template, **kw)

    # -- backdrop (background, texture, grid) and border
    def build_backdrop(self) -> list:
        fw, fh = config.frame_width, config.frame_height
        bt, bg = self.t["background_type"], self.t["bg"]
        parts = []
        if bt["fill"] == "linear":
            rect = M.Rectangle(width=fw + 0.2, height=fh + 0.2).set_stroke(width=0)
            rect.set_fill(color=[M.ManimColor(bg["base"]), M.ManimColor(bg["shade"])], opacity=1)
            rect.set_sheen_direction(M.DOWN)  # base at the top, shade at the bottom
            parts.append(rect)
        elif bt["fill"] == "radial":
            glow, n = M.VGroup(), 14
            for k in range(n):
                r = math.hypot(fw, fh) / 2 * (1 - k / n) * 0.9
                glow.add(M.Ellipse(width=2 * r * 1.15, height=2 * r * 0.8).set_stroke(width=0)
                         .set_fill(M.ManimColor(bg["glow"]), opacity=0.09))
            parts.append(glow)
        if bt["texture"]:
            parts.append(self._texture(fw, fh))
        if bt["grid"]:
            parts.append(self._grid(fw, fh))
        for i, p in enumerate(parts):
            p.set_z_index(-100 + i)
        return parts

    def _texture(self, fw, fh):
        dark = self.t["mode"] == "dark"   # chalk dust on dark, paper grain on light
        rng = random.Random(11 if dark else 5)
        col = M.ManimColor("#ffffff" if dark else "#5a4a30")
        n, rad, op = (700, (0.004, 0.018), 0.07) if dark else (900, (0.003, 0.010), 0.05)
        return M.VGroup(*[
            M.Dot([rng.uniform(-fw / 2, fw / 2), rng.uniform(-fh / 2, fh / 2), 0],
                  radius=rng.uniform(*rad), color=col, fill_opacity=op * rng.uniform(0.3, 1.0))
            for _ in range(n)])

    def _grid(self, fw, fh):
        g = self.t["grid_type"]
        col, op = M.ManimColor(self.t["grid_hex"]), self.t["grid_opacity"]["opacity"]
        hw, hh, sw = fw / 2, fh / 2, g.get("stroke_width", 1.0)

        def lines(step, width, opacity, vertical=True):
            grp = M.VGroup()
            if vertical:
                for i in range(-int(hw // step) - 1, int(hw // step) + 2):
                    grp.add(M.Line([i * step, -hh, 0], [i * step, hh, 0]))
            for j in range(-int(hh // step) - 1, int(hh // step) + 2):
                grp.add(M.Line([-hw, j * step, 0], [hw, j * step, 0]))
            return grp.set_stroke(col, width, opacity)

        kind, diag = g["kind"], math.hypot(fw, fh)
        if kind == "square":
            return lines(g["spacing"], sw, op)
        if kind == "graph_paper":
            return M.VGroup(lines(g["minor"], g["minor_stroke"], op * g["minor_opacity_ratio"]),
                            lines(g["major"], g["major_stroke"], op))
        if kind == "ruled":
            margin = M.Line([-hw + g["margin_line_x"], -hh, 0], [-hw + g["margin_line_x"], hh, 0])
            margin.set_stroke(self.color("accent"), sw * 1.5, min(1.0, op * 1.6))
            return M.VGroup(lines(g["spacing"], sw, op, vertical=False), margin)
        if kind == "dots":
            s = g["spacing"]
            return M.VGroup(*[M.Dot([i * s, j * s, 0], radius=g["dot_radius"], color=col, fill_opacity=min(1, op * 2))
                              for i in range(-int(hw // s), int(hw // s) + 1)
                              for j in range(-int(hh // s), int(hh // s) + 1)])
        if kind == "number_plane":
            X, Y = math.ceil(hw), math.ceil(hh)
            plane = M.NumberPlane(x_range=[-X, X, g["spacing"]], y_range=[-Y, Y, g["spacing"]],
                                  x_length=2 * X, y_length=2 * Y, faded_line_ratio=g.get("faded_line_ratio", 1))
            plane.background_lines.set_stroke(col, sw, op)
            plane.faded_lines.set_stroke(col, sw * 0.5, op * 0.5)
            M.VGroup(plane.x_axis, plane.y_axis).set_stroke(col, g["axis_stroke"], min(1, op * g["axis_opacity_ratio"]))
            return plane
        if kind == "isometric":
            grp, s = M.VGroup(), g["spacing"]
            for ang in (0, 60, 120):
                a = math.radians(ang)
                d, nrm = np.array([math.cos(a), math.sin(a), 0]), np.array([-math.sin(a), math.cos(a), 0])
                for k in range(-int(diag / 2 / s) - 1, int(diag / 2 / s) + 2):
                    o = nrm * k * s
                    grp.add(M.Line(o - d * diag / 2, o + d * diag / 2))
            return grp.set_stroke(col, sw, op)
        if kind == "polar":
            grp, rs = M.VGroup(), g["ring_spacing"]
            for k in range(1, int(diag / 2 / rs) + 2):
                grp.add(M.Circle(radius=k * rs))
            for k in range(g["spokes"]):
                a = 2 * math.pi * k / g["spokes"]
                grp.add(M.Line(M.ORIGIN, [diag / 2 * math.cos(a), diag / 2 * math.sin(a), 0]))
            return grp.set_stroke(col, sw, op)
        raise TemplateError(f"unknown grid kind '{kind}'")

    def build_border(self):
        b = self.t["border_style"]
        if b["kind"] == "none":
            return None
        fw, fh = config.frame_width, config.frame_height
        col = M.ManimColor(self.t["border_hex"])

        def frame_rect(margin, radius=0.0):
            w, h = fw - 2 * margin, fh - 2 * margin
            r = M.RoundedRectangle(width=w, height=h, corner_radius=radius) if radius else M.Rectangle(width=w, height=h)
            return r.set_stroke(col, b.get("width", 2)).set_fill(opacity=0)

        kind = b["kind"]
        if kind == "rect":
            out = frame_rect(b["margin"], b.get("corner_radius", 0))
        elif kind == "double":
            out = M.VGroup(frame_rect(b["margin"]), frame_rect(b["margin"] + b["gap"]))
        elif kind == "dashed":
            out = M.DashedVMobject(frame_rect(b["margin"]), num_dashes=b["dashes"]).set_stroke(col, b["width"])
        elif kind == "corners":
            m, L = b["margin"], b["length"]
            out = M.VGroup()
            for sx in (-1, 1):
                for sy in (-1, 1):
                    c = np.array([sx * (fw / 2 - m), sy * (fh / 2 - m), 0])
                    out.add(M.Line(c, c - [sx * L, 0, 0]), M.Line(c, c - [0, sy * L, 0]))
            out.set_stroke(col, b["width"])
        elif kind == "bars":
            out = M.VGroup(*[M.Rectangle(width=fw + 0.2, height=b["height"]).set_stroke(width=0)
                             .set_fill(col, b["opacity"]).move_to([0, sy * (fh / 2 - b["height"] / 2), 0])
                             for sy in (-1, 1)])
        else:
            raise TemplateError(f"unknown border kind '{kind}'")
        out.set_z_index(400)   # above content, below subtitles
        return out


if HAVE_MANIM:
    from narration import Narrator, chunk_words

    class SubtitleTrack(M.VGroup):
        """Burned-in subtitles for one narration clip, with live word highlighting.

        Every chunk and marker is built up front and only shown/hidden through opacity: Manim snapshots
        the list of moving mobjects when each play() starts, so removing parts mid-animation would leave
        stale copies on screen."""

        def __init__(self, theme: Theme, clip, occupied=None):
            super().__init__()
            self.T, self.clip, self.occupied = theme, clip, occupied
            t = theme.t
            self.st, self.cp, self.hl = t["subtitle_style"], t["caption_position"], t["word_highlighting"]
            self.base = M.ManimColor(subtitle_text_color(t))
            self.hcol = M.ManimColor(subtitle_highlight_color(t))
            cpl = self.st["max_chars_per_line"]
            self.chunks = chunk_words(clip.words, cpl, self.st["max_lines"])
            self.built = [self._build(c) for c in self.chunks]
            for b in self.built:
                self._hide(b)
                self.add(b["group"])
            self.current, self.elapsed = None, 0.0
            self.add_updater(SubtitleTrack._tick)

        def _word_texts(self, words, idxs):
            """One Text per line (keeps baseline and kerning), split back into per-word glyph groups."""
            st = self.st
            line_text = " ".join(words[i].text for i in idxs)
            if st["uppercase"]:
                line_text = line_text.upper()
            kw = dict(font=self.T.font, font_size=st["font_size"], weight=st["weight"], color=self.base)
            full = M.Text(line_text, **kw)
            # glyph count per word (not character count) so conjuncts/ligatures in any script slice correctly
            lens = [len(w) for w in line_text.split(" ")]
            if len(full.submobjects) != sum(lens):
                lens = [len(M.Text(w, **kw).submobjects) for w in line_text.split(" ")]
            if len(full.submobjects) == sum(lens):
                parts, k = [], 0
                for n in lens:
                    parts.append(M.VGroup(*full.submobjects[k:k + n]))
                    k += n
                return M.VGroup(*parts)
            # ligature mismatch - lay out word by word instead
            return M.VGroup(*[M.Text(w, **kw) for w in line_text.split(" ")]).arrange(
                M.RIGHT, buff=st["font_size"] / 48 * 0.2, aligned_edge=M.DOWN)

        def _build(self, chunk):
            words, st = self.clip.words, self.st
            rows = M.VGroup(*[self._word_texts(words, line) for line in chunk.lines])
            rows.arrange(M.DOWN, buff=st["font_size"] / 48 * 0.25)
            max_w = self.cp["width_fraction"] * config.frame_width
            if rows.width > max_w:
                rows.scale_to_fit_width(max_w)
            if st["outline"]:
                oc = st["outline"]["color"]
                if oc == "auto":
                    oc = "#000000" if _luminance(subtitle_text_color(self.T.t)) > 0.4 else "#FFFFFF"
                rows.set_stroke(M.ManimColor(oc), st["outline"]["width"], background=True)
            group, box = M.VGroup(), None
            if st["box"]:
                pad = st["padding"]
                box = M.RoundedRectangle(width=rows.width + 2 * pad, height=rows.height + 1.4 * pad,
                                         corner_radius=st["corner_radius"]).move_to(rows)
                box.set_stroke(width=0).set_fill(M.ManimColor(st["box"]["color"]), st["box"]["opacity"])
                group.add(box)
            marker = None
            if self.hl["mode"] in ("underline", "box"):
                marker = M.RoundedRectangle(width=1, height=1, corner_radius=0.0).set_stroke(width=0)
                marker.set_fill(self.hcol, 0)
                group.add(marker)            # above the subtitle box, below the words
            group.add(rows)
            return {"group": group, "box": box, "marker": marker, "words": [w for row in rows for w in row],
                    "chunk": chunk, "placed": False}

        def _hide(self, b):
            b["group"].set_opacity(0)

        def _show(self, b):
            if b["box"] is not None:
                b["box"].set_fill(opacity=self.st["box"]["opacity"])
            self._position(b["group"])

        def _overlap(self, group, y):
            """Area of content bounding boxes that a subtitle centred at height y would cover."""
            if not self.occupied:
                return 0.0
            w, h = group.width, group.height
            x0, x1, y0, y1 = group.get_x() - w / 2, group.get_x() + w / 2, y - h / 2, y + h / 2
            area = 0.0
            for m in self.occupied():
                if not m.get_family() or m.width == 0 and m.height == 0:
                    continue
                (mx0, my0, _), (mx1, my1, _) = m.get_corner(M.DL), m.get_corner(M.UR)
                area += max(0, min(x1, mx1) - max(x0, mx0)) * max(0, min(y1, my1) - max(y0, my0))
            return area

        def _position(self, group):
            fw, fh, cp = config.frame_width, config.frame_height, self.cp
            edge = max(cp["edge_offset"], self.T.t["border_style"]["inset"] + 0.05)
            x = {"center": 0, "left": -fw / 2 + 0.4 + group.width / 2, "right": fw / 2 - 0.4 - group.width / 2}[cp["x_align"]]
            group.set_x(x)
            y_bottom = -fh / 2 + edge + group.height / 2
            y_top = fh / 2 - edge - group.height / 2
            if not cp.get("avoid_content"):
                group.set_y(y_bottom if cp["anchor"] == "bottom" else y_top)
                return
            # adaptive: stay put unless content is in the way and the other edge is clearer
            here = group.get_y() if abs(group.get_y() - y_top) < 1e-6 else y_bottom
            there = y_top if here == y_bottom else y_bottom
            if self._overlap(group, here) > 0 and self._overlap(group, there) < self._overlap(group, here):
                here = there
            group.set_y(here)

        def _tick(self, dt):
            self.elapsed += dt
            t = self.elapsed
            idx = next((i for i, c in enumerate(self.chunks) if c.start <= t < c.end), None)
            if idx is None and self.chunks and t >= self.chunks[-1].start:
                idx = len(self.chunks) - 1
            if idx != self.current:
                if self.current is not None:
                    self._hide(self.built[self.current])
                if idx is not None:
                    self._show(self.built[idx])
                self.current = idx
            if self.current is not None:
                if self.cp.get("avoid_content"):
                    self._position(self.built[self.current]["group"])
                self._highlight(self.built[self.current], t)

        def _highlight(self, b, t):
            mode, words, idxs, mobs = self.hl["mode"], self.clip.words, b["chunk"].indices, b["words"]
            cur = None
            for j, wi in enumerate(idxs):
                if words[wi].start <= t:
                    cur = j
            for j, mob in enumerate(mobs):
                state = "future" if cur is None or j > cur else ("current" if j == cur else "past")
                color, opacity = self.base, 1.0
                if mode == "karaoke" and state != "future":
                    color = self.hcol
                elif mode == "current_color" and state == "current":
                    color = self.hcol
                elif mode == "reveal" and state == "future":
                    opacity = 0.0
                elif mode == "dim_past" and state == "past":
                    opacity = self.hl["dim_opacity"]
                mob.set_fill(color, opacity)
                if self.st["outline"]:
                    mob.set_stroke(opacity=opacity, background=True)
            marker = b["marker"]
            if marker is None:
                return
            if cur is None:
                marker.set_fill(opacity=0)
                return
            target = mobs[cur]
            if mode == "underline":
                h = self.st["font_size"] / 48 * 0.06
                marker.stretch_to_fit_width(max(target.width, 0.05)).stretch_to_fit_height(h)
                marker.next_to(target, M.DOWN, buff=h * 1.5)
                marker.set_fill(self.hcol, 1)
            else:
                marker.stretch_to_fit_width(target.width + 0.12).stretch_to_fit_height(target.height + 0.12)
                marker.move_to(target)
                marker.set_fill(self.hcol, self.hl["box_opacity"])

    class NarrationHandle:
        def __init__(self, scene, clip, tracker):
            self.scene, self.clip, self.tracker = scene, clip, tracker

        @property
        def elapsed(self):
            return self.tracker.elapsed

        @property
        def remaining(self):
            return max(0.0, self.clip.duration - self.tracker.elapsed)

        def time_of(self, word: str, occurrence: int = 1) -> float:
            target = re.sub(r"[\W_]+", "", word.lower())
            seen = 0
            for w in self.clip.words:
                if re.sub(r"[\W_]+", "", w.text.lower()) == target:
                    seen += 1
                    if seen == occurrence:
                        return w.start
            raise TemplateError(f"'{word}' (occurrence {occurrence}) is not in the narration: {self.clip.text!r}")

        def wait_until(self, word: str, occurrence: int = 1):
            """Pause the animation timeline until that word is spoken."""
            gap = self.time_of(word, occurrence) - self.elapsed
            if gap > 1 / config.frame_rate:
                self.scene.wait(gap)

    class _Clock(M.Mobject):
        def __init__(self):
            super().__init__()
            self.elapsed = 0.0
            self.add_updater(lambda m, dt: setattr(m, "elapsed", m.elapsed + dt))

    class TemplateScene(M.Scene):
        """Scene base: draws background, grid and border, narrates, and keeps content in the safe area."""

        def setup(self):
            if _ACTIVE is None:
                raise TemplateError("call use_template(...) at module level before rendering")
            self.T = _ACTIVE
            self._persistent = self.T.build_backdrop()
            border = self.T.build_border()
            if border is not None:
                self._persistent.append(border)
            self._narrator = None
            self._reported = set()
            if self._persistent:
                self.add(*self._persistent)

        def content(self):
            return [m for m in self.mobjects
                    if m not in self._persistent and not isinstance(m, (SubtitleTrack, _Clock))]

        def _check_safe_area(self):
            x0, x1, y0, y1 = self.T.safe_area
            tol = 0.05
            for m in self.content():
                if not m.get_family() or (m.width == 0 and m.height == 0) or id(m) in self._reported:
                    continue
                if (m.get_left()[0] < x0 - tol or m.get_right()[0] > x1 + tol or
                        m.get_bottom()[1] < y0 - tol or m.get_top()[1] > y1 + tol):
                    self._reported.add(id(m))
                    self.T._violation(
                        f"{type(m).__name__} at x {m.get_left()[0]:.2f}..{m.get_right()[0]:.2f}, "
                        f"y {m.get_bottom()[1]:.2f}..{m.get_top()[1]:.2f} leaves the safe area "
                        f"x {x0:.2f}..{x1:.2f}, y {y0:.2f}..{y1:.2f} (use T.fit)")

        def play(self, *args, **kwargs):
            super().play(*args, **kwargs)
            self._check_safe_area()

        @contextmanager
        def narrate(self, text: str):
            """Speak text (audio + subtitles); animations inside the block run while it plays."""
            t = self.T.t
            maxw = t["narration_tone"]["max_sentence_words"]
            for s in re.split(r"(?<=[.!?])\s+", text.strip()):
                if len(s.split()) > maxw:
                    self.T._violation(f"narration sentence has {len(s.split())} words > {maxw}: {s[:50]!r}")
            if self._narrator is None:
                self._narrator = Narrator(t)
            clip = self._narrator.speak(text)
            if clip.audio:
                self.add_sound(clip.audio)
            for ch in chunk_words(clip.words, 80, 1):
                self.add_subcaption(" ".join(clip.words[i].text for i in ch.indices),
                                    duration=max(0.3, ch.end - ch.start), offset=ch.start)
            clock = _Clock()
            self.add(clock)
            subs = None
            if t["subtitles"]["burn_in"]:
                subs = SubtitleTrack(self.T, clip, occupied=self.content)
                subs.set_z_index(500)
                self.add(subs)
            handle = NarrationHandle(self, clip, clock)
            yield handle
            if handle.remaining > 1 / config.frame_rate:
                self.wait(handle.remaining)
            self.remove(clock)
            if subs is not None:
                self.remove(subs)


# --------------------------------------------------------------------------- CLI

def main(argv: list[str]) -> int:
    if argv and argv[0] == "--lint":
        bad = 0
        for f in argv[1:]:
            for n, msg, line in lint(Path(f).read_text(encoding="utf-8")):
                print(f"{f}:{n}: {msg}\n    {line}")
                bad += 1
        print(f"{bad} issue(s)")
        return 1 if bad else 0
    brief = "--brief" in argv
    files = [a for a in argv if a != "--brief"]
    lib, failed = load_library(), 0
    for f in files or sorted(str(p) for p in (KIT_DIR / "templates").glob("*.json")):
        for mode in ("dark", "light"):
            try:
                tpl = json.loads(Path(f).read_text(encoding="utf-8"))
                tpl["elements"]["theme_mode"] = mode
                t = resolve(tpl, lib)
                errors, warns = validate(t)
            except TemplateError as e:
                t, errors, warns = None, [str(e)], []
            print(f"[{'OK' if not errors else 'FAIL'}] {f} ({mode})")
            for e in errors:
                print(f"   error: {e}")
            for w in warns:
                print(f"   warning: {w}")
            if t and not errors and brief:
                print("   " + agent_brief(t).replace("\n", "\n   "))
            failed += bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
