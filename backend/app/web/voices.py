"""Voices for the website: every English Amazon Polly voice with the engines it really has (from Polly, per region),
and spoken previews made from one template filled with the chosen agent, tone, speed and engine.

Previews use the narration's own Polly path (app.narration), so a preview sounds as the video will, and are kept on
disk by what they say and how (Polly is asked once per combination). Credentials come from the environment (.env) as
for narration; they are never sent to the page or written to the log.
"""

from __future__ import annotations

import functools
import hashlib
import logging
import os
import re
import secrets

from app.config import REPOSITORY_ROOT

PROVIDER = "Amazon Polly"
TEMPLATE = "Hello! I'm {agent}. I'm speaking at {speed} speed, powered by {provider}'s {engine} engine."
PREVIEWS = REPOSITORY_ROOT / "artifacts" / "voice-previews"  # git-ignored, like every artifact
ENGINE_NAMES = {"standard": "Standard", "neural": "Neural", "long-form": "Long-Form", "generative": "Generative"}
log = logging.getLogger(__name__)


class VoicesUnavailable(Exception):
    """Polly could not be asked (credentials, network, permissions): a sentence the page can show."""


def describe_voices() -> list[dict]:
    """Every voice Polly offers in this region (all pages)."""
    import boto3
    import botocore.exceptions

    try:
        polly, voices, token = boto3.client("polly"), [], None
        while True:
            page = polly.describe_voices(**({"NextToken": token} if token else {}))
            voices += page["Voices"]
            token = page.get("NextToken")
            if not token:
                return voices
    except botocore.exceptions.NoCredentialsError as missing:
        raise VoicesUnavailable("No AWS credentials found. Add them to .env (see the README).") from missing
    except botocore.exceptions.ClientError as refused:
        code = refused.response.get("Error", {}).get("Code", "")
        log.warning("Polly describe_voices refused: %s", code)
        if code in ("AccessDenied", "AccessDeniedException", "UnauthorizedOperation"):
            raise VoicesUnavailable(
                "These AWS credentials may not use Amazon Polly (polly:DescribeVoices)."
            ) from refused
        raise VoicesUnavailable("Amazon Polly refused the AWS credentials in .env. Check them.") from refused
    except botocore.exceptions.BotoCoreError as broken:
        log.warning("Polly unreachable: %s", type(broken).__name__)
        raise VoicesUnavailable(
            "Amazon Polly did not answer. Check the network and the AWS credentials in .env."
        ) from broken


@functools.lru_cache(maxsize=1)
def voice_list() -> tuple[dict, ...]:
    """English voices by name: id, name, gender, language, engines (Polly's own order). Kept for the server's life;
    voices change with Polly releases, not between page loads."""
    return tuple(
        {
            "id": voice["Id"],
            "name": voice.get("Name", voice["Id"]),
            "gender": voice.get("Gender", ""),
            "language_code": voice["LanguageCode"],
            "language": voice.get("LanguageName", voice["LanguageCode"]),
            "engines": sorted(voice.get("SupportedEngines", [])),
        }
        for voice in sorted(describe_voices(), key=lambda voice: voice.get("Name", voice["Id"]))
        if voice["LanguageCode"].startswith("en-")
    )


def find(voice_id: str) -> dict | None:
    return next((voice for voice in voice_list() if voice["id"] == voice_id), None)


def preview_ssml(voice: dict, engine: str, speed: dict) -> str:
    """TEMPLATE's words (the line the page shows), spoken like someone introducing themselves: one sentence at a time,
    a beat after the greeting, the name stressed, a breath at the comma. Polly engines without <emphasis> get the
    nearest thing they can speak (narration.polly_ssml)."""
    name = f'<emphasis level="moderate">{voice["name"]}</emphasis>'
    line = TEMPLATE.format(agent=name, speed=speed["label"].title(), provider=PROVIDER, engine=ENGINE_NAMES[engine])
    sentences = " ".join(
        f"<s>{sentence}</s>" + (' <break time="300ms"/>' if index == 0 else "")
        for index, sentence in enumerate(re.split(r"(?<=[.!?])\s+", line.replace(", ", ', <break time="150ms"/> ')))
    )
    return f'<speak><prosody rate="{round(speed["rate"] * 100)}%">{sentences}</prosody></speak>'


def synthesize(voice: str, engine: str, ssml: str) -> bytes:
    import botocore.exceptions

    from app import narration

    try:
        audio, _ = narration.create_polly_synthesizer(voice, engine)(ssml)
    except botocore.exceptions.NoCredentialsError as missing:
        raise VoicesUnavailable("No AWS credentials found. Add them to .env (see the README).") from missing
    except botocore.exceptions.ClientError as refused:
        code = refused.response.get("Error", {}).get("Code", "")
        log.warning("Polly synthesize_speech refused: %s", code)
        if code in ("AccessDenied", "AccessDeniedException"):
            raise VoicesUnavailable(
                "These AWS credentials may not speak with Amazon Polly (polly:SynthesizeSpeech)."
            ) from refused
        raise VoicesUnavailable(
            f"Amazon Polly could not make this preview ({code or 'an error'}). Try another voice."
        ) from refused
    except botocore.exceptions.BotoCoreError as broken:
        log.warning("Polly unreachable: %s", type(broken).__name__)
        raise VoicesUnavailable("Amazon Polly did not answer. Check the network and try again.") from broken
    return audio


def preview(voice_id: str, engine: str, speed: dict) -> bytes:
    """The preview's audio, from the cache or from Polly. ValueError: no such English voice, or not with that engine."""
    voice = find(voice_id)
    if voice is None or engine not in voice["engines"]:
        raise ValueError(f"{voice_id} does not speak English with the {engine} engine in this region")
    ssml = preview_ssml(voice, engine, speed)
    path = PREVIEWS / f"{hashlib.sha256(f'{voice_id}|{engine}|{ssml}'.encode()).hexdigest()[:24]}.mp3"
    if path.exists():
        return path.read_bytes()
    audio = synthesize(voice_id, engine, ssml)
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(f".{secrets.token_hex(4)}.part")  # written whole, then renamed: never read half-made
    partial.write_bytes(audio)
    os.replace(partial, path)
    return audio
