"""Previews of the look and sound, rendered by Manim through look_renderer.py (no Claude, no kit code).

    uv run python backend/templates/generate_preview.py fonts        fetch the templates' fonts (OFL, Google Fonts)
    uv run python backend/templates/generate_preview.py starters     every starter template, in its own mode, as one 2560×1440 frame
    uv run python backend/templates/generate_preview.py warm         every option of every element, drawn in every
        [--small-only] [--only STARTER]                                     starter's look → the cache
    uv run python backend/templates/generate_preview.py batch JOBS_JSON      what the website asks for, in one process
    uv run python backend/templates/generate_preview.py still TEMPLATE_JSON OUT     the whole chosen look
    uv run python backend/templates/generate_preview.py voice TEMPLATE_JSON OUT [--provider polly|google]

An option preview is the user's own look with that one element changed (option_in_look), saved losslessly, so its
colours are exactly the video's. Previews are cached by what they draw in ~/.cache/text-2-shorts/previews: 854×480
for the cards, 2560×1440 for full screen. `warm` fills the cache for every starter template as it comes,
so a new run's options open at once; anything else is rendered when the website first asks for it.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import logging
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "runtime-environment"))  # faraday_logging, by name
import faraday_logging
import video_settings

log = logging.getLogger("generate_preview")

PREVIEW_DIRECTORY = Path(__file__).resolve().parent / "previews"
CUSTOM_DIRECTORY = Path.home() / ".cache" / "text-2-shorts" / "previews"
SIZE = (854, 480)  # the option cards
LAYOUT = "frame-3"  # the preview layout (look_renderer.swatch): part of every cache key, so a new layout re-renders
FULL = (2560, 1440)  # full screen and the look's still: the delivery size, pixel for pixel
SOUND_ONLY = {"voice", "speaking_speed", "narration_tone"}  # heard, not seen
PREVIEWED = [name for name in video_settings.ELEMENTS if name not in SOUND_ONLY | {"frame", "theme_mode"}]
FONTS = {  # family → files in github.com/google/fonts (all SIL Open Font License)
    "Inter": ["ofl/inter/Inter[opsz,wght].ttf"],
    "Source Sans 3": ["ofl/sourcesans3/SourceSans3[wght].ttf"],
    "IBM Plex Sans": ["ofl/ibmplexsans/IBMPlexSans[wdth,wght].ttf"],
    "Atkinson Hyperlegible": [
        "ofl/atkinsonhyperlegible/AtkinsonHyperlegible-Regular.ttf",
        "ofl/atkinsonhyperlegible/AtkinsonHyperlegible-Bold.ttf",
    ],
    "Merriweather": ["ofl/merriweather/Merriweather[opsz,wdth,wght].ttf"],
    "Patrick Hand": ["ofl/patrickhand/PatrickHand-Regular.ttf"],
    "JetBrains Mono": ["ofl/jetbrainsmono/JetBrainsMono[wght].ttf"],
    "Source Code Pro": ["ofl/sourcecodepro/SourceCodePro[wght].ttf"],
    "IBM Plex Mono": ["ofl/ibmplexmono/IBMPlexMono-Regular.ttf", "ofl/ibmplexmono/IBMPlexMono-Bold.ttf"],
    "Space Grotesk": ["ofl/spacegrotesk/SpaceGrotesk[wght].ttf"],
    "EB Garamond": ["ofl/ebgaramond/EBGaramond[wght].ttf"],
    "Nunito": ["ofl/nunito/Nunito[wght].ttf"],
    "Lora": ["ofl/lora/Lora[wght].ttf"],
}
FONTS_URL = "https://raw.githubusercontent.com/google/fonts/main/"


def fetch_fonts() -> list[Path]:
    from look_renderer import FONT_DIRECTORY

    FONT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    fetched = []
    for files in FONTS.values():
        for path in files:
            target = FONT_DIRECTORY / Path(path).name
            if not target.exists():  # complete files only: an interrupted download is fetched again
                partial = target.with_suffix(".part")
                urllib.request.urlretrieve(FONTS_URL + urllib.parse.quote(path, safe="/,"), partial)
                partial.rename(target)
            fetched.append(target)
    return fetched


GRID_TWIN = {"plain": "plain_grid", "gradient": "gradient_grid", "textured": "textured_grid", "glow": "gradient_grid"}
SUBTITLE_PARTS = {"subtitle_style", "caption_position", "word_highlighting"}


def option_in_look(template: dict, element: str, variant: str | None = None, custom: str | None = None) -> dict:
    """The user's own look with one element set: the option exactly as their video would show it. Only what would
    hide the element is changed (a grid to see grid colours, a border to see its colour, subtitles to see their style)."""
    chosen = copy.deepcopy(template)
    elements, mode = chosen["elements"], template["elements"].get("theme_mode", "dark")
    if element.startswith("grid_") and elements.get("background_type") in GRID_TWIN:
        elements["background_type"] = GRID_TWIN[elements["background_type"]]
    if element == "border_color" and elements.get("border_style") in ("none", "letterbox"):
        elements["border_style"] = "double"
    if element in SUBTITLE_PARTS:
        elements["subtitles"] = "on"
    overrides = {name: value for name, value in chosen.get("overrides", {}).items() if name != element}
    if variant:
        elements[element] = variant
    if custom:
        overrides[element] = video_settings.custom_override(element, custom, mode)
    chosen["overrides"] = overrides
    return chosen


def warm_jobs(names: list[str]) -> tuple[list[tuple[dict, Path]], list[tuple[dict, Path]]]:
    """Every option of every previewed element in each starter's look: the pictures the website asks for before
    anything is changed (same templates, so the same cache names). Missing ones only, each once."""
    library, small, full, seen = video_settings.library(), {}, {}, set()
    for name in names:
        base = video_settings.starter(name)  # one look per starter: its own mode
        for element in PREVIEWED:
            for variant in library[element]["variants"]:
                template = option_in_look(base, element, variant)
                key = json.dumps(video_settings.drawing(template), sort_keys=True)
                if key in seen or video_settings.problems(template):
                    continue
                seen.add(key)
                card, large = custom_path(template), still_path(template)
                if not card.exists():
                    small[card] = template
                if not large.exists():
                    full[large] = template
                    large.parent.mkdir(parents=True, exist_ok=True)
                    (large.parent / f"{large.stem}.json").write_text(json.dumps(template))
    return [(t, p) for p, t in small.items()], [(t, p) for p, t in full.items()]


def starter_path(name: str) -> Path:
    """A starter template, in its own mode, as one frame at the delivery size (generate_preview.py starters)."""
    return PREVIEW_DIRECTORY / "starters" / f"{name}.webp"


CARD = (1280, 720)  # a gallery card: twice its on-screen width, so it is sharp on high-density screens


def starter_card(name: str) -> Path:
    """The starter's frame scaled down for its gallery card (made from the full frame once; shrinking 2560 px into a
    400 px card in the browser makes thin lines shimmer and downloads what the card never shows)."""
    from PIL import Image

    card = PREVIEW_DIRECTORY / "starters" / f"{name}-card.webp"
    if not card.exists() or card.stat().st_mtime < starter_path(name).stat().st_mtime:
        Image.open(starter_path(name)).resize(CARD, Image.Resampling.LANCZOS).save(card, quality=92)
    return card


def still_path(template: dict) -> Path:
    """A whole look as one 2560×1440 frame (cached by what it draws)."""
    key = hashlib.sha256(
        (json.dumps(video_settings.drawing(template), sort_keys=True) + "|full|" + LAYOUT).encode()
    ).hexdigest()[:20]
    return CUSTOM_DIRECTORY / f"{key}.webp"


def custom_path(template: dict) -> Path:
    key = hashlib.sha256((json.dumps(video_settings.drawing(template), sort_keys=True) + LAYOUT).encode()).hexdigest()[
        :20
    ]
    return CUSTOM_DIRECTORY / f"{key}.webp"


def render(jobs: list[tuple[dict, Path]], size: tuple[int, int] = SIZE) -> None:
    """Render each (template, path) as one frame, in this process (Manim and its LaTeX cache stay warm)."""
    from look_renderer import LookScene, register_fonts
    from manim import tempconfig
    from PIL import Image

    register_fonts()
    settings = {
        "pixel_width": size[0], "pixel_height": size[1], "write_to_movie": False, "save_last_frame": False,
        "disable_caching": True, "verbosity": "ERROR", "progress_bar": "none",
        "media_dir": str(CUSTOM_DIRECTORY.parent / "preview-media"),
    }  # fmt: skip
    for template, path in jobs:
        started = time.perf_counter()
        with tempconfig(settings):
            LookScene.look = video_settings.drawing(template)
            scene = LookScene()
            scene.render()
            path.parent.mkdir(parents=True, exist_ok=True)
            # lossless: every pixel keeps the template's exact colour (lossy WebP shifts saturated colours)
            part = path.with_name(f"{path.name}.part")  # written whole, then renamed: no reader sees half a file
            Image.fromarray(scene.renderer.get_frame()).convert("RGB").save(part, "WEBP", lossless=True, method=4)
            part.replace(path)
        log.info("rendered %s at %d×%d in %.1f s", path.name, *size, time.perf_counter() - started)


def render_in_subprocess(arguments: list[str]) -> None:
    """For the web server: Manim's global config stays out of the server process."""
    process = subprocess.run([sys.executable, __file__, *arguments], capture_output=True, text=True, timeout=300)
    if process.returncode != 0:
        log.error("preview %s failed: %s", " ".join(arguments)[:300], (process.stderr or process.stdout)[-1500:])
        raise RuntimeError((process.stderr or process.stdout)[-1500:] or "the preview could not be rendered")


def font_note(template: dict) -> str | None:
    """Say so when the template's font is neither fetched nor installed (Pango would show a default)."""
    from look_renderer import FONT_DIRECTORY

    family = video_settings.settings(template)["font"]
    fetched = {name for name, files in FONTS.items() if all((FONT_DIRECTORY / Path(f).name).exists() for f in files)}
    listed = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True).stdout
    installed = {name.strip().lower() for line in listed.splitlines() for name in line.split(",")}
    if family in fetched or family.lower() in installed:
        return None
    return (
        f"The font {family} is not available, so a default font is shown. Fetch the template fonts with "
        "`uv run python backend/templates/generate_preview.py fonts`."
    )


def voice_sample(template: dict, provider: str, output: Path) -> Path:
    """A few seconds of the template's voice at its speed (calls Polly or Google with your credentials)."""
    import audio_settings

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/, for app.narration
    from app import narration

    sound = audio_settings.settings(template, provider)
    speech = (
        f'<speak><prosody rate="{sound["rate_percent"]}%">Here is how your narrator will sound. Square the short '
        "sides, add them, and you get the long side squared.</prosody></speak>"
    )
    audio, _ = narration.create_speech_synthesizer(sound)(speech)
    output.write_bytes(audio)
    return output


def main() -> None:
    faraday_logging.configure("runtime", console=False)  # stderr stays for errors the server shows
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("fonts")
    starters = commands.add_parser("starters", help=f"every starter template as one frame at {FULL[0]}×{FULL[1]}")
    starters.add_argument("--force", action="store_true")
    starters.add_argument("--only", help="one starter template")
    warm = commands.add_parser("warm", help="pre-render every option in every starter's look, both modes")
    warm.add_argument("--small-only", action="store_true", help="the 854×480 cards only, not the 2560×1440 ones")
    warm.add_argument("--only", help="one starter template")
    batch = commands.add_parser("batch", help="render [{template, path, full}] from a JSON file, in one process")
    batch.add_argument("jobs", type=Path)
    still = commands.add_parser("still")
    still.add_argument("template", type=Path)
    still.add_argument("output", type=Path)
    voice = commands.add_parser("voice")
    voice.add_argument("template", type=Path)
    voice.add_argument("output", type=Path)
    voice.add_argument("--provider", choices=["polly", "google"], default="polly")
    arguments = parser.parse_args()

    if arguments.command == "fonts":
        for path in fetch_fonts():
            print("font:", path)
    elif arguments.command == "starters":
        names = [arguments.only] if arguments.only else video_settings.starter_names()
        jobs = [
            (video_settings.starter(name), starter_path(name))
            for name in names
            if arguments.force or not starter_path(name).exists()
        ]
        render(jobs, FULL)
        for name in names:
            starter_card(name)
        print(f"rendered {len(jobs)} starter templates into {PREVIEW_DIRECTORY / 'starters'}")
    elif arguments.command == "warm":
        small, full = warm_jobs([arguments.only] if arguments.only else video_settings.starter_names())
        log.info("warming the cache: %d cards, %d full-size", len(small), len(full))
        render(small)
        print(f"rendered {len(small)} option cards into {CUSTOM_DIRECTORY}", flush=True)
        if not arguments.small_only:
            render(full, FULL)
            print(f"rendered {len(full)} full-size options into {CUSTOM_DIRECTORY}")
    elif arguments.command == "batch":
        jobs = json.loads(arguments.jobs.read_text())
        render([(job["template"], Path(job["path"])) for job in jobs if not job.get("full")])
        render([(job["template"], Path(job["path"])) for job in jobs if job.get("full")], FULL)
    else:
        template = json.loads(arguments.template.read_text())
        if problems := video_settings.problems(template):
            sys.exit("; ".join(problems))
        if arguments.command == "still":
            render([(template, arguments.output)], FULL)
            if note := font_note(template):
                print("note:", note)
        else:
            print(voice_sample(template, arguments.provider, arguments.output))


if __name__ == "__main__":
    main()
