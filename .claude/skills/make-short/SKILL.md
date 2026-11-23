---
name: make-short
description: Use when the user wants a narrated explainer video or "short" made from a topic, script or outline, or asks how to start, continue or check a Text-2-Shorts video run in runs/.
---

# Starting a Text-2-Shorts video

Turn the user's request into a provisioned run workspace and hand it to that run's own isolated Claude Code
session. Production never happens in this session. If the current folder is already a run workspace (it has `brief.json`), use
`text-2-shorts-produce` instead.

## What the product supports (check before promising)
| Need | Supported | How |
|---|---|---|
| Length | any number of minutes > 0 | `--minutes 7` (decimals fine; longer = more scenes, longer build) |
| Objectives, style | what the viewer should be able to do afterwards · tone (default ELI5 / Feynman) | `--objective "…"` (repeat), `--style "…"` |
| Structure | `zoom` big picture → detail · `arc` problem → solution · `linear` lesson · `creative` a structure designed for the topic | `--approach`; a user's own outline/script → `--approach creative` + paste it in the run session |
| Audience, pace | free text · slow / medium / fast | `--audience`, `--pace` |
| Voice | AWS Polly (any voice id; `--engine neural`, `generative` or `standard`) or Google Cloud TTS (any voice name) | `--tts polly\|google --voice <id>` |
| Font | any installed family | `--font "<family>"`; list: `fc-list : family` |
| Output | drafts 720p30; delivery 2560×1440 (16:9) at 120 fps (60–120) | fixed; fps via `TEXT_2_SHORTS_FPS` |

`uv run text-2-shorts new --help` is the source of truth for flags. A request outside this table (another TTS vendor,
vertical 9:16, the user's own audio, …) is not supported: say so plainly, offer the closest supported option, and
ask before substituting. Never invent a flag or quietly change what the user asked for.

## Steps
1. In one question round: flag anything unsupported (with the closest option) and ask only for what is missing;
   offer common choices as suggestions, not as the only options (e.g. voices Matthew/Joanna for Polly,
   en-US-Neural2-D/F for Google).
2. `uv run text-2-shorts new "<topic in the user's words>" --objective "…" --approach … --minutes … --audience "…" [--style "…"] --tts … --voice … [--engine …] [--pace …] [--font …] [--notes "…"]`.
   It checks the machine (LaTeX, ffmpeg, bubblewrap, Claude Code version) and the voice credentials, then prints
   `runs/<id>`. On failure, relay the fix it prints.
3. Tell the user to run `uv run text-2-shorts open runs/<id>` in their own terminal: an interactive session that produces
   the video and asks them at four checkpoints. The same command resumes an interrupted run;
   `uv run text-2-shorts status runs/<id>` shows progress from anywhere.

Done when the run exists and the user has the `text-2-shorts open` command (plus anything unsupported clearly flagged).

Related: `text-2-shorts-produce` (inside the run session) · `text-2-shorts-clip-debugging` · `text-2-shorts-prompt-maintenance`.
Voices: [Polly](https://docs.aws.amazon.com/polly/latest/dg/available-voices.html) ·
[Google Cloud TTS](https://cloud.google.com/text-to-speech/docs/list-voices-and-types).
