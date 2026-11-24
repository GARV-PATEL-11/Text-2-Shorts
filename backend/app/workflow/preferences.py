"""Standing preferences (preferences.json) and the speech settings they control."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError
from schemas.requirements import Preferences

from app import narration
from app.utilities import format_validation_errors


def load_preferences(run: Path) -> Preferences:
    try:
        return Preferences.model_validate_json((run / "preferences.json").read_text())
    except (FileNotFoundError, ValueError):
        return Preferences()


def validate_preferences(run: Path) -> list[str]:
    try:
        Preferences.model_validate_json((run / "preferences.json").read_text())
    except FileNotFoundError:
        return []
    except ValidationError as validation_error:
        return format_validation_errors(validation_error)
    return []


def clip_speech(run: Path, ssml: str, pairs) -> str:
    """The SSML the voice speaks: symbols by name, [pause] at the preferred length, at the template's speaking rate."""
    from app.workflow.templates import sound

    speech = narration.speakable_ssml(ssml, pairs, pause_ms=load_preferences(run).pause_ms)
    if (rate := sound(run)["rate_percent"]) != 100:
        speech = speech.replace("<speak>", f'<speak><prosody rate="{rate}%">', 1)
        speech = speech[: speech.rindex("</speak>")] + "</prosody></speak>"
    return speech
