"""The video's sound, finalised from the run's template.json — the one place narration gets its voice, speed, pauses
and tone from. Same template and resolution as video_settings.py; the provider (Polly or Google) comes from the brief.
"""

from __future__ import annotations

from video_settings import resolve


def voice(template: dict, provider: str) -> dict:
    """{'voice', 'engine'} for Polly, {'voice'} for Google."""
    chosen = resolve(template)["voice"]
    if provider == "google":
        return {"voice": chosen["google"]["neural2"]}
    return {"voice": chosen["polly"]["voice_id"], "engine": chosen["polly"].get("engine", "neural")}


def settings(template: dict, provider: str) -> dict:
    look = resolve(template)
    speed, tone = look["speaking_speed"], look["narration_tone"]
    return {
        **voice(template, provider),
        "provider": provider,
        "rate_percent": round(speed["rate"] * 100),
        "sentence_pause_ms": speed["sentence_pause_ms"],
        "tone": tone["label"],
        "script_rules": tone["script_rules"],
        "max_sentence_words": tone["max_sentence_words"],
    }
