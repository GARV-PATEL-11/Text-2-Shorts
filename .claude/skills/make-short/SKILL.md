---
name: make-short
description: Start a Text-2-Shorts video (2560x1440, 60–120 fps) from a topic — ask the setup questions, provision an isolated run workspace with `t2s new`, and hand over to `t2s open`, which runs the whole production in its own Claude Code session. Use when the user says /make-short, "make a video/short about X", or asks how to continue a run in runs/.
---

# make-short (launcher)

Production does NOT happen in this session. Each video runs in its own isolated Claude Code session inside its run
folder (only that folder is writable; the env/ plugin supplies the workflow skill, subagents and hooks). This
skill only sets the run up.

## 1. Ask (one AskUserQuestion call; skip what the user already said)
- **Approach**: `zoom` Conceptual Zoom · `arc` Problem → Solution · `linear` Classic linear lesson.
- **Audience / level**: curious beginners · students with high-school math · practitioners.
- **Length**: 1 · 2 · 3 · 5 minutes.
- **Voice**: AWS Polly (`--tts polly`, `--engine neural`): Matthew · Joanna · Ruth · Stephen — or Google Cloud TTS
  (`--tts google`): en-US-Neural2-D · en-US-Neural2-F · en-US-Studio-O · en-GB-Neural2-B.
- **Font** (optional): Roboto · Noto Sans · DejaVu Sans · Latin Modern Roman (`fc-list : family` for all).

## 2. Provision
```
uv run t2s new "<topic in the user's words>" --approach <a> --minutes <m> --audience "<aud>" --tts <polly|google> --voice <v> [--font "<family>"] [--notes "<extra>"]
```
It runs the preflight and the voice-credential check, then creates `runs/<id>/` (brief, CLAUDE.md, environment
report). Show the user the printed run folder.

## 3. Hand over
Tell the user to run, in a terminal of their own (it is an interactive session):
```
uv run t2s open runs/<id>
```
That session asks them at the four checkpoints and produces `runs/<id>/final.mp4`. To continue an interrupted run,
the same command resumes it (the session starts with the run's status and next steps). `uv run t2s status runs/<id>`
shows progress from here at any time.
