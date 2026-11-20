"""pipeline.py — the `t2s` CLI entry point: deterministic steps only (no LLM calls).
Reasoning (outline, clip plans, clip code, math review) is done by the Claude Code session that runs inside the
run workspace (env/ plugin: skills, subagents, hooks); it calls these commands. Clip-level commands: app/clips.py.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from app import speech

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable  # the venv interpreter — manim is installed here
FPS = int(os.environ.get("T2S_FPS", 60))  # final render is always 2560x1440 (-qp, 16:9); 60–120 fps
MAX_PARALLEL = int(os.environ.get("T2S_PARALLEL", 4))  # scenes at a time (user's call: 4)
CACHE = Path.home() / ".cache"
BWRAP = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp",
         "--bind", str(CACHE), str(CACHE), "--unshare-net", "--die-with-parent"]


# ── Schemas for new stages ────────────────────────────────────────────────────

def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def probe_seconds(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def parallel(fn, items):
    with ThreadPoolExecutor(MAX_PARALLEL) as ex:
        return list(ex.map(fn, items))


# ── Steps ─────────────────────────────────────────────────────────────────────

def cmd_new(a) -> None:
    pf = subprocess.run([PYTHON, str(ROOT / "tools" / "preflight.py")], capture_output=True, text=True)
    if pf.returncode:  # fail before any paid call: missing LaTeX/ffmpeg/bwrap/… would only surface at render
        sys.exit(f"Preflight failed: {json.loads(pf.stdout)['problems']}")
    if a.tts == "polly":
        import boto3
        if boto3.Session().get_credentials() is None:
            sys.exit("AWS credentials not found for Polly — run `aws configure` or set AWS_PROFILE (or use --tts google)")
    else:
        import google.auth
        try:
            google.auth.default()
        except google.auth.exceptions.DefaultCredentialsError:
            sys.exit("Google credentials not found — run `gcloud auth application-default login` or set "
                     "GOOGLE_APPLICATION_CREDENTIALS (or use --tts polly)")
    families = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True).stdout
    if a.font and a.font.lower() not in {f.strip().lower() for line in families.splitlines() for f in line.split(",")}:
        sys.exit(f"Font not installed: {a.font!r} — pick one from `fc-list : family`")
    slug =re.sub(r"[^a-z0-9]+", "-", a.requirement.lower())[:40].strip("-")
    run = ROOT / "runs" / f"{datetime.now():%Y%m%d-%H%M%S}-{slug}"
    run.mkdir(parents=True)
    write_json(run / "brief.json", {
        "requirement": a.requirement, "approach": a.approach, "minutes": a.minutes, "pace": a.pace,
        "audience": a.audience, "notes": a.notes, "tts": a.tts, "voice": a.voice, "engine": a.engine, "font": a.font,
        })
    print(run.relative_to(ROOT))


def tts_for(brief: dict):
    """The narration synthesiser the user chose for this video: AWS Polly or Google Cloud TTS."""
    return google_tts(brief["voice"]) if brief.get("tts") == "google" else polly_tts(brief["voice"], brief["engine"])


def polly_tts(voice: str, engine: str):
    """AWS Polly with SSML (pauses) and word speech marks (beat timing). Falls back to plain text when an engine
    rejects a tag, and to no marks when an engine has none."""
    import boto3

    polly = boto3.client("polly")

    def call(text: str, **kw):
        try:
            return polly.synthesize_speech(Text=speech.to_ssml(text), TextType="ssml", VoiceId=voice, Engine=engine, **kw)
        except polly.exceptions.InvalidSsmlException:
            return polly.synthesize_speech(Text=speech.to_plain(text), VoiceId=voice, Engine=engine, **kw)

    def synth(text: str) -> tuple[bytes, list[tuple[str, float]] | None]:
        # ponytail: one request per clip (clips are ≤ 30 s, far under Polly's 3000-char limit)
        audio = call(text, OutputFormat="mp3")["AudioStream"].read()
        try:
            raw = call(text, OutputFormat="json", SpeechMarkTypes=["word"])["AudioStream"].read().decode()
            marks = [(m["value"], m["time"] / 1000) for m in map(json.loads, raw.splitlines()) if m["type"] == "word"]
        except Exception:  # noqa: BLE001 — speech marks are a timing aid, never a reason to fail the voice step
            marks = None
        return audio, marks
    return synth


def google_tts(voice: str):
    """Google Cloud TTS (v1beta1 for timepoints): SSML with a <mark/> per word → word timings for beat sync.
    Voices without SSML support (e.g. Chirp 3 HD) fall back to plain text without timings."""
    from google.api_core.exceptions import InvalidArgument
    from google.cloud import texttospeech_v1beta1 as gtts

    client = gtts.TextToSpeechClient()
    voice_cfg = {"language_code": "-".join(voice.split("-")[:2]), "name": voice}
    mp3 = {"audio_encoding": gtts.AudioEncoding.MP3}

    def synth(text: str) -> tuple[bytes, list[tuple[str, float]] | None]:
        ssml, words = speech.to_ssml_marked(text)
        try:
            r = client.synthesize_speech(request={
                "input": {"ssml": ssml}, "voice": voice_cfg, "audio_config": mp3,
                "enable_time_pointing": [gtts.SynthesizeSpeechRequest.TimepointType.SSML_MARK]})
        except InvalidArgument:
            r = client.synthesize_speech(request={"input": {"text": speech.to_plain(text)}, "voice": voice_cfg,
                                                  "audio_config": mp3})
            return r.audio_content, None
        return r.audio_content, [(words[int(tp.mark_name)], tp.time_seconds) for tp in r.timepoints] or None
    return synth


def main() -> None:
    ap = argparse.ArgumentParser(prog="t2s")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new")
    p.add_argument("requirement")
    p.add_argument("--approach", choices=["zoom", "arc", "linear"], default="zoom")
    p.add_argument("--minutes", type=float, default=2)
    p.add_argument("--pace", choices=["slow", "medium", "fast"], default="medium")
    p.add_argument("--audience", default="curious beginners")
    p.add_argument("--notes", default="")
    p.add_argument("--tts", choices=["polly", "google"], default=os.environ.get("T2S_TTS", "polly"),
                   help="narration provider: AWS Polly or Google Cloud Text-to-Speech")
    p.add_argument("--engine", choices=["neural", "generative", "standard"],
                   default=os.environ.get("POLLY_ENGINE", "neural"), help="Polly engine (ignored for Google)")
    p.add_argument("--font", help="font family for all Text (any name from `fc-list : family`); default: Manim's")
    p.add_argument("--voice", help="Polly: Matthew, Joanna, Ruth, Stephen … · Google: en-US-Neural2-D, en-US-Studio-O …")
    p.set_defaults(fn=cmd_new)

    from app import clips  # clip-level commands (imports pipeline, so register late)
    clips.register(sub)
    a = ap.parse_args()
    if a.cmd == "new" and not a.voice:
        a.voice = (os.environ.get("GOOGLE_VOICE", "en-US-Neural2-D") if a.tts == "google"
                   else os.environ.get("POLLY_VOICE", "Matthew"))
    if getattr(a, "run", None):
        a.run = str(Path(a.run).resolve())
    a.fn(a)


if __name__ == "__main__":
    main()
