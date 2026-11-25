"""
gallery.py - render every variant of every visual element with Manim, in dark and light mode,
into one contact sheet per element (gallery/<element>.png). Proves each variant is reproducible.

    python gallery.py                      all elements
    python gallery.py border_style grid_type
"""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("MANIM_TEMPLATE_FRAME", "draft_480p15")
os.environ.setdefault("TEMPLATE_STRICT", "0")

from manim import DOWN, LEFT, RIGHT, UP, UR, Circle, Polygon, VGroup, tempconfig  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import narration  # noqa: E402
import template_kit as K  # noqa: E402

KIT = Path(__file__).resolve().parent
BASE = json.loads((KIT / "templates" / "standard.json").read_text())
SHEETS = {   # element -> base overrides that make the element visible
    "background_type": {}, "background_color": {"background_type": "gradient"},
    "grid_type": {"background_type": "plain_grid", "grid_opacity": "visible"},
    "grid_color": {"background_type": "plain_grid", "grid_type": "graph_paper", "grid_opacity": "visible"},
    "grid_opacity": {"background_type": "plain_grid", "grid_type": "square"},
    "primary_palette": {}, "secondary_palette": {}, "accent_color": {},
    "text_font": {}, "math_font": {}, "typography": {},
    "border_style": {"border_color": "accent"}, "border_color": {"border_style": "double"},
    "subtitle_style": {}, "caption_position": {}, "word_highlighting": {"subtitle_style": "clean_bar"},
}
SUBTITLE_SHEETS = ("subtitle_style", "caption_position", "word_highlighting")
CAPTION = "Square the short sides, add them, and you get the long side squared."


class Swatch(K.TemplateScene):
    zoom_math = False

    def construct(self):
        T = self.T
        x0, x1, y0, y1 = T.safe_area
        title = T.text("Title Aa 123", style="title").to_corner(UP + LEFT, buff=T.inset)
        body = T.text("Body text, read aloud", style="body").next_to(title, DOWN, aligned_edge=LEFT, buff=0.3)
        label = T.text("label · caption", style="label", role="secondary").next_to(body, DOWN, aligned_edge=LEFT, buff=0.2)
        eq = T.math(r"c=\sqrt{a^2+b^2}", role="derived").next_to(label, DOWN, aligned_edge=LEFT, buff=0.35)
        roles = ["text", "focus", "given", "derived", "warning", "secondary", "accent"]
        chips = VGroup(*[Circle(radius=0.28).set_stroke(width=0).set_fill(T.color(r), 1) for r in roles]).arrange(RIGHT, buff=0.15)
        chips.to_corner(UR, buff=T.inset + 0.1)
        tri = Polygon([0, 0, 0], [2.6, 0, 0], [2.6, 1.95, 0]).set_stroke(T.color("given"), 4)
        tri.next_to(chips, DOWN, buff=0.5)
        if self.zoom_math:   # gallery only: make the maths font comparable at thumbnail size
            eq = K.M.MathTex(r"\int_0^1 x^2\,dx=\frac{1}{3},\quad \sum \alpha\beta", tex_template=T.tex_template,
                             color=T.color("derived")).scale(1.9).move_to([0, -0.6, 0])
        self.add(title, body, label, eq, chips, tri)
        for m in (title, body, label, eq, chips, tri):
            T.fit(m)
        if T.t["subtitles"]["burn_in"]:
            clip = narration.Narrator(T.t, "silent").speak(CAPTION)
            subs = K.SubtitleTrack(T, clip, occupied=self.content)
            subs.set_z_index(500)
            self.add(subs)
            subs._tick(clip.words[6].start + 0.05)   # freeze on the 7th word


def render(elements: dict):
    tpl = json.loads(json.dumps(BASE))
    tpl["elements"].update(elements)
    with tempconfig({"write_to_movie": False, "save_last_frame": False, "disable_caching": True,
                     "media_dir": "/tmp/gallery_media", "verbosity": "ERROR", "progress_bar": "none"}):
        K.use_template(tpl)
        scene = Swatch()
        scene.zoom_math = ZOOM_MATH
        scene.render()
        return Image.fromarray(scene.renderer.get_frame()).convert("RGB")


ZOOM_MATH = False


def sheet(element: str, out_dir: Path):
    global ZOOM_MATH
    ZOOM_MATH = element == "math_font"
    lib = json.loads((KIT / "elements.json").read_text())["elements"][element]["variants"]
    base = dict(SHEETS[element])
    if element in SUBTITLE_SHEETS:
        base["subtitles"] = "on"
    thumbs = []
    for v in lib:
        row = []
        for mode in ("dark", "light"):
            row.append(render({**base, "theme_mode": mode, element: v["id"]}).resize((427, 240)))
        thumbs.append((v["label"], row))
    W, H, pad, head = 427, 240, 8, 26
    img = Image.new("RGB", (len(thumbs) * (W + pad) + pad, 2 * (H + pad) + head + pad + 30), (40, 40, 44))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 15)
        big = ImageFont.truetype("DejaVuSans-Bold.ttf", 18)
    except OSError:
        font = big = ImageFont.load_default()
    d.text((pad, 6), f"{element}   (top: dark mode, bottom: light mode)", fill=(240, 240, 240), font=big)
    for i, (label, (dark, light)) in enumerate(thumbs):
        x = pad + i * (W + pad)
        d.text((x, 34), label, fill=(220, 220, 220), font=font)
        img.paste(dark, (x, 34 + head))
        img.paste(light, (x, 34 + head + H + pad))
    out_dir.mkdir(exist_ok=True)
    img.save(out_dir / f"{element}.png")
    print(f"{element}: {len(thumbs)} variants")


if __name__ == "__main__":
    for el in (sys.argv[1:] or list(SHEETS)):
        sheet(el, KIT / "gallery")
