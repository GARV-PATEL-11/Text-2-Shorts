# Manim template kit — 16:9, English, dark/light

A template fixes the **look and sound** of a video. Layout, motion, emphasis, line weights and pacing are left to the planning agent.

## Elements (in `elements.json`)
| Group | Element | Options |
|---|---|---|
| Mode | theme_mode | dark, light |
| Canvas | frame | 5 (480p draft to 4K, all 16:9) |
| Background | background_type | 7: plain, plain + grid, gradient, gradient + grid, centre glow, textured, textured + grid |
| | background_color | 7, each with dark and light values |
| Grid | grid_type / grid_color / grid_opacity | 7 / 5 / 5 |
| Colour | primary_palette / secondary_palette / accent_color | 7 / 7 / 7, each with dark and light sets |
| Type | text_font / math_font / typography | 7 / 7 / 5 |
| Border | border_style / border_color | 7 / 5 |
| Voice | voice / speaking_speed / narration_tone | 7 / 5 / 7 |
| Subtitles | subtitles / subtitle_style / caption_position / word_highlighting | on-off / 7 / 6 / 7 |

`gallery/*.png` shows every visual variant rendered by Manim in both modes (regenerate with `python gallery.py`).

## Files
- `elements.json` – the option library
- `templates/*.json` – 7 ready templates (each works in both modes)
- `template_kit.py` – validation, agent brief, linter, `TemplateScene` (backdrop, border, safe area, narration, subtitles)
- `narration.py` – Amazon Polly and Google Cloud TTS, word timings, subtitle chunking
- `install_fonts.py` – downloads every font from google/fonts
- `gallery.py`, `example_scene.py`

## Setup on a render machine
```
pip install manim boto3 google-cloud-texttospeech
apt install texlive-latex-extra texlive-fonts-recommended texlive-fonts-extra dvisvgm ffmpeg
python install_fonts.py
python narration.py --check-voices      # confirms every voice id on your AWS and Google accounts
```

## Use
```
python template_kit.py templates/x.json --brief       # validate + rules for the agent's system prompt
python template_kit.py --lint generated_scene.py      # reject hard-coded colours/fonts/sizes
TEMPLATE=templates/blueprint.json MANIM_TEMPLATE_MODE=light NARRATION_ENGINE=polly manim scene.py Scene
```
Env: `MANIM_TEMPLATE_FRAME` (preview resolution), `MANIM_TEMPLATE_MODE`, `TEMPLATE_STRICT=0` (warn instead of fail).

## Audio providers
| NARRATION_ENGINE | Setting | Word timings |
|---|---|---|
| polly | `POLLY_ENGINE=neural` (default) | exact (speech marks) |
| polly | `POLLY_ENGINE=generative` | estimated, fitted to audio length |
| google | `GOOGLE_VOICE_TIER=neural2` (default) | exact (SSML marks, v1beta1 API) |
| google | `GOOGLE_VOICE_TIER=chirp3_hd` | estimated, fitted to audio length |
| silent | – | estimated, no audio (layout previews) |

Polly uses SSML prosody rate only (no pitch), and the newscaster style for documentary/formal tones on Joanna, Matthew and Amy. Audio is cached in `narration_cache/`; every render also writes an `.srt`.
