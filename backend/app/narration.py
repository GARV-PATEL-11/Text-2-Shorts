"""Narration → speakable text / SSML, and word timings → beat start times.

Narration convention (the clip planner writes it, VIDEO_STANDARDS states it):
  `a`, `M`, `r_1`, `θ`   a math symbol in backticks → spoken as its name ("ay", "capital em", "ar one", "theta")
  [pause]                 a deliberate pause (SSML <break>, or an ellipsis when a voice rejects SSML)
Everything else is plain-spoken English; this module is the safety net for what slips through: math symbols,
units after numbers and common abbreviations are spoken by name, and a letter used in both cases in one video
is always disambiguated ("capital M" vs "small m").
"""

from __future__ import annotations

import html
import json
import logging
import re
from collections.abc import Set as AbstractSet
from xml.etree import ElementTree

LETTERS = dict(
    zip(
        "abcdefghijklmnopqrstuvwxyz",
        [
            "ay",
            "bee",
            "see",
            "dee",
            "ee",
            "ef",
            "gee",
            "aitch",
            "eye",
            "jay",
            "kay",
            "el",
            "em",
            "en",
            "oh",
            "pee",
            "cue",
            "ar",
            "ess",
            "tee",
            "you",
            "vee",
            "double-you",
            "ex",
            "why",
            "zee",
        ],
    )
)
GREEK = {
    "α": "alpha",
    "β": "beta",
    "γ": "gamma",
    "δ": "delta",
    "Δ": "capital delta",
    "ε": "epsilon",
    "θ": "theta",
    "λ": "lambda",
    "μ": "mu",
    "π": "pi",
    "ρ": "rho",
    "σ": "sigma",
    "Σ": "capital sigma",
    "τ": "tau",
    "φ": "phi",
    "ω": "omega",
    "Ω": "capital omega",
}
SYMBOLS = {
    "≈": " approximately ",
    "≠": " is not equal to ",
    "≤": " is less than or equal to ",
    "≥": " is greater than or equal to ",
    "×": " times ",
    "÷": " divided by ",
    "±": " plus or minus ",
    "√": " the square root of ",
    "∞": " infinity ",
    "→": " goes to ",
    "²": " squared",
    "³": " cubed",
    "%": " percent",
    "=": " equals ",
    "<": " is less than ",
    ">": " is greater than ",
    "+": " plus ",
    "−": " minus ",
    "∝": " is proportional to ",
}
UNITS = {
    "km/h": "kilometers per hour",
    "m/s²": "meters per second squared",
    "m/s": "meters per second",
    "km": "kilometers",
    "cm": "centimeters",
    "mm": "millimeters",
    "m": "meters",
    "kg": "kilograms",
    "g": "grams",
    "ms": "milliseconds",
    "s": "seconds",
    "min": "minutes",
    "h": "hours",
    "Hz": "hertz",
    "kHz": "kilohertz",
    "N": "newtons",
    "J": "joules",
    "W": "watts",
    "kW": "kilowatts",
    "V": "volts",
    "A": "amperes",
    "°C": "degrees Celsius",
    "°F": "degrees Fahrenheit",
    "°": "degrees",
    "K": "kelvin",
    "AU": "astronomical units",
    "ly": "light years",
    "L": "liters",
    "mL": "milliliters",
    "nm": "nanometers",
}
ABBREVIATIONS = {
    "e.g.": "for example",
    "i.e.": "that is",
    "etc.": "et cetera",
    "vs.": "versus",
    "approx.": "approximately",
    "AU": "A U",
    "Fig.": "figure",
    "Eq.": "equation",
    "No.": "number",
}
PAUSE = "[pause]"
PAUSE_MS = 600
SSML_TAGS = {"speak", "break", "prosody", "emphasis", "s", "p", "sub", "say-as"}  # supported by Polly and Google
EMPHASIS_VOLUME = {"strong": "+4dB", "moderate": "+2dB", "reduced": "-3dB", "none": "medium"}
TAG = re.compile(r"(<[^>]+>)")


def symbol_name(token: str, both_cases: AbstractSet[str]) -> str:
    """`M` → "capital em" when m and M both occur in the video, else "em"; `r_1` → "ar one"; `θ` → "theta"."""
    base, _, subscript = token.partition("_")
    if base in GREEK:
        name = GREEK[base]
    elif len(base) == 1 and base.lower() in LETTERS:
        name = LETTERS[base.lower()]
        if base.lower() in both_cases:
            name = ("capital " if base.isupper() else "small ") + name
    else:
        name = " ".join(LETTERS.get(character.lower(), character) for character in base)  # `AB` → "ay bee"
    return (
        f"{name} {' '.join(LETTERS.get(part, part) if part.isalpha() else part for part in subscript)}".strip()
        if subscript
        else name
    )


def case_pairs(texts: list[str]) -> set[str]:
    """Letters used in backticks in BOTH cases anywhere in the video (e.g. M and m)."""
    seen = {symbol.partition("_")[0] for text in texts for symbol in re.findall(r"`([^`]+)`", text)}
    return {letter.lower() for letter in seen if len(letter) == 1 and letter.isalpha() and letter.swapcase() in seen}


def speakable(text: str, both_cases: AbstractSet[str] = frozenset()) -> str:
    """Plain text any TTS engine reads correctly; [pause] stays as a marker for to_ssml/to_plain."""
    text = re.sub(r"`([^`]+)`", lambda match: symbol_name(match[1], both_cases), text)
    for written, spoken in ABBREVIATIONS.items():
        if written != "AU":
            text = text.replace(written, spoken)
    units = "|".join(re.escape(unit) for unit in sorted(UNITS, key=len, reverse=True))
    text = re.sub(rf"(\d(?:[\d,.]*\d)?)\s?({units})(?![A-Za-z])", lambda match: f"{match[1]} {UNITS[match[2]]}", text)
    text = re.sub(r"(\d)[-–](\d)", r"\1 to \2", text)  # "10-20 s", "3–5": a range
    text = re.sub(r"(\d)\s+-\s+(\d)", r"\1 minus \2", text)  # "9 - 1": spaced, a subtraction
    for written, spoken in {**GREEK, **SYMBOLS}.items():
        text = text.replace(written, spoken if written in SYMBOLS else f" {spoken} ")
    text = re.sub(r"\bAU\b", "A U", text)
    return re.sub(r"\s+", " ", re.sub(r"\s+([,.!?;:])", r"\1", text)).strip()


def ssml_problems(ssml: str) -> list[str]:
    """A clip's planned SSML: one <speak> element, well-formed, only tags every voice provider understands."""
    try:
        root = ElementTree.fromstring(ssml)
    except ElementTree.ParseError as error:
        return [f"not well-formed SSML: {error}"]
    problems = [] if root.tag == "speak" else ["SSML must be one <speak>…</speak> element"]
    if unsupported := sorted({element.tag for element in root.iter()} - SSML_TAGS):
        problems.append(f"unsupported SSML tags {unsupported}; use only {sorted(SSML_TAGS)}")
    return problems


def ssml_words(ssml: str) -> list[str]:
    """The written words inside the SSML (tags removed): must equal the clip's narration."""
    return " ".join(ElementTree.fromstring(ssml).itertext()).split()


def speakable_ssml(ssml: str, both_cases: AbstractSet[str] = frozenset(), pause_ms: int = PAUSE_MS) -> str:
    """The planned SSML with every text part made speakable (symbols, units, abbreviations) and [pause] → <break>."""
    parts = []
    for chunk in TAG.split(ssml):
        if not chunk or chunk.startswith("<"):
            parts.append(chunk)
            continue
        text = html.unescape(chunk)
        core = text.strip()
        if not core:  # whitespace between tags stays as it is
            parts.append(chunk)
            continue
        lead, trail = text[: len(text) - len(text.lstrip())], text[len(text.rstrip()) :]
        tokens = []
        for piece_index, piece in enumerate(core.split(PAUSE)):
            if piece_index:
                tokens.append(f'<break time="{pause_ms}ms"/>')
            if spoken := speakable(piece, both_cases):
                tokens.append(html.escape(spoken, quote=False))
        parts.append(lead + " ".join(tokens) + trail)
    return "".join(parts)


def polly_ssml(ssml: str, engine: str) -> str:
    """The SSML in the form this Polly engine speaks (probed live 2026-11-27). Standard voices take everything and get
    breaths between phrases. Neural, long-form and generative reject <emphasis> and prosody pitch, and a rejected clip
    loses all its markup (plain text): emphasis becomes a louder word, pitch is dropped, the rest is kept."""
    if engine == "standard":
        return ssml.replace("<speak>", "<speak><amazon:auto-breaths>", 1).replace(
            "</speak>", "</amazon:auto-breaths></speak>"
        )
    parts = []
    for chunk in TAG.split(ssml):
        if chunk.startswith("<emphasis"):
            level = re.search(r"""level=["'](\w+)""", chunk)
            chunk = f'<prosody volume="{EMPHASIS_VOLUME.get(level[1] if level else "moderate", "+2dB")}">'
        elif chunk == "</emphasis>":
            chunk = "</prosody>"
        elif chunk.startswith("<prosody"):
            chunk = re.sub(r"""\s+pitch=["'][^"']*["']""", "", chunk)
            chunk = '<prosody volume="medium">' if chunk == "<prosody>" else chunk
        parts.append(chunk)
    return "".join(parts)


def mark_words(ssml: str) -> tuple[str, list[str]]:
    """SSML with <mark name="i"/> before every word (Google TTS returns a time per mark) + the word list."""
    words, parts = [], []
    for chunk in TAG.split(ssml):
        if chunk.startswith("<"):
            parts.append(chunk)
            continue

        def mark(match):
            words.append(html.unescape(match[0]))
            return f'<mark name="{len(words) - 1}"/>{match[0]}'

        parts.append(re.sub(r"\S+", mark, chunk))
    return "".join(parts), words


def to_plain(text: str) -> str:
    """Plain text for a voice that rejects SSML: tags removed, pauses as an ellipsis."""
    text = html.unescape(re.sub(r"<[^>]+>", "", re.sub(r"<break[^>]*>", f" {PAUSE} ", text)))
    return re.sub(r"\s+", " ", text.replace(PAUSE, " … ")).strip()


def phrase_times(
    marks: list[tuple[str, float]], beats: list[str], both_cases: AbstractSet[str] = frozenset()
) -> list[float | None]:
    """Start time (s) of each beat's quoted narration phrase, from word marks [(word, start_s)], in order."""
    normalized_words = lambda text: re.sub(r"[^a-z0-9 ]", "", text.lower()).split()
    words = [normalized_words(word)[0] if normalized_words(word) else "" for word, _ in marks]
    beat_times, i = [], 0
    for beat in beats:
        quote_match = re.search(r"[\"“]([^\"”]+)[\"”]", beat)
        phrase = normalized_words(speakable(quote_match[1], both_cases).replace(PAUSE, "")) if quote_match else []
        match_start = next(
            (j for j in range(i, len(words) - len(phrase) + 1) if phrase and words[j : j + len(phrase)] == phrase), None
        )
        beat_times.append(round(marks[match_start][1], 2) if match_start is not None else None)
        i = match_start + 1 if match_start is not None else i
    return beat_times


# ── synthesis: the voice provider the user chose (AWS Polly or Google Cloud TTS) ──────────────────────────────


def create_speech_synthesizer(sound: dict):
    """The narration synthesiser for this video: the provider from the brief, the voice from the template
    (`templates.sound`)."""
    if sound["provider"] == "google":
        return create_google_synthesizer(sound["voice"])
    return create_polly_synthesizer(sound["voice"], sound["engine"])


def create_polly_synthesizer(voice: str, engine: str):
    """AWS Polly from the clip's speakable SSML in the form this engine speaks, plus word speech marks (beat timing).
    Falls back to plain text when an engine still rejects the SSML, and to no marks when an engine has none."""
    import boto3

    polly_client = boto3.client("polly")

    def synthesize_request(ssml: str, **request_options):
        ssml = polly_ssml(ssml, engine)
        try:
            return polly_client.synthesize_speech(
                Text=ssml, TextType="ssml", VoiceId=voice, Engine=engine, **request_options
            )
        except polly_client.exceptions.InvalidSsmlException:
            return polly_client.synthesize_speech(Text=to_plain(ssml), VoiceId=voice, Engine=engine, **request_options)

    def synthesize_clip(text: str) -> tuple[bytes, list[tuple[str, float]] | None]:
        # ponytail: one request per clip (clips are ≤ 30 s, far under Polly's 3000-char limit)
        audio = synthesize_request(text, OutputFormat="mp3")["AudioStream"].read()
        try:
            speech_marks_json = (
                synthesize_request(text, OutputFormat="json", SpeechMarkTypes=["word"])["AudioStream"].read().decode()
            )
            marks = [
                (mark["value"], mark["time"] / 1000)
                for mark in map(json.loads, speech_marks_json.splitlines())
                if mark["type"] == "word"
            ]
        except Exception:
            logging.getLogger(__name__).warning("Polly speech marks failed: beats will not be synced", exc_info=True)
            marks = None
        return audio, marks

    return synthesize_clip


def create_google_synthesizer(voice: str):
    """Google Cloud TTS (v1beta1 for timepoints): the clip's SSML with a <mark/> per word → word timings.
    Voices without SSML support (e.g. Chirp 3 HD) fall back to plain text without timings."""
    from google.api_core.exceptions import InvalidArgument
    from google.cloud import texttospeech_v1beta1 as texttospeech

    client = texttospeech.TextToSpeechClient()
    voice_selection = {"language_code": "-".join(voice.split("-")[:2]), "name": voice}
    audio_config = {"audio_encoding": texttospeech.AudioEncoding.MP3}

    def synthesize_clip(text: str) -> tuple[bytes, list[tuple[str, float]] | None]:
        ssml, words = mark_words(text)
        try:
            response = client.synthesize_speech(
                request={
                    "input": {"ssml": ssml},
                    "voice": voice_selection,
                    "audio_config": audio_config,
                    "enable_time_pointing": [texttospeech.SynthesizeSpeechRequest.TimepointType.SSML_MARK],
                }
            )
        except InvalidArgument:
            logging.getLogger(__name__).warning("Google refused the marked SSML: plain text, beats will not be synced")
            response = client.synthesize_speech(
                request={"input": {"text": to_plain(text)}, "voice": voice_selection, "audio_config": audio_config}
            )
            return response.audio_content, None
        return response.audio_content, [
            (words[int(timepoint.mark_name)], timepoint.time_seconds) for timepoint in response.timepoints
        ] or None

    return synthesize_clip
