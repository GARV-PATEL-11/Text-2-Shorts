"""
install_fonts.py - download every font the templates use from the google/fonts GitHub repo
into ~/.local/share/fonts/manim-templates and refresh fontconfig, so Manim (Pango) can render them.

    python install_fonts.py            install / update
    python install_fonts.py --check    only report which families Pango can see
"""
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

FONTS = {   # family name as Pango reports it -> files in github.com/google/fonts (main branch)
    "Inter": ["ofl/inter/Inter[opsz,wght].ttf"],
    "Source Sans 3": ["ofl/sourcesans3/SourceSans3[wght].ttf"],
    "IBM Plex Sans": ["ofl/ibmplexsans/IBMPlexSans[wdth,wght].ttf"],
    "Atkinson Hyperlegible": ["ofl/atkinsonhyperlegible/AtkinsonHyperlegible-Regular.ttf",
                              "ofl/atkinsonhyperlegible/AtkinsonHyperlegible-Bold.ttf"],
    "Merriweather": ["ofl/merriweather/Merriweather[opsz,wdth,wght].ttf"],
    "Patrick Hand": ["ofl/patrickhand/PatrickHand-Regular.ttf"],
    "JetBrains Mono": ["ofl/jetbrainsmono/JetBrainsMono[wght].ttf"],
    "Source Code Pro": ["ofl/sourcecodepro/SourceCodePro[wght].ttf"],
    "IBM Plex Mono": ["ofl/ibmplexmono/IBMPlexMono-Regular.ttf", "ofl/ibmplexmono/IBMPlexMono-Bold.ttf"],
}
RAW = "https://raw.githubusercontent.com/google/fonts/main/"
DEST = Path.home() / ".local/share/fonts/manim-templates"


def check() -> int:
    import manimpango
    have = set(manimpango.list_fonts())
    missing = [f for f in FONTS if f not in have]
    for f in FONTS:
        print(f"{'ok     ' if f in have else 'MISSING'} {f}")
    return 1 if missing else 0


def install():
    DEST.mkdir(parents=True, exist_ok=True)
    for family, files in FONTS.items():
        for path in files:
            target = DEST / Path(path).name
            if not target.exists():
                urllib.request.urlretrieve(RAW + urllib.parse.quote(path, safe="/,"), target)
        print(f"{family}: {len(files)} file(s)")
    subprocess.run(["fc-cache", "-f", str(DEST)], check=False)


if __name__ == "__main__":
    if "--check" not in sys.argv:
        install()
    sys.exit(check())
