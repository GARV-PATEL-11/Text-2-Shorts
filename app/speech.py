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
import re

LETTERS = dict(zip("abcdefghijklmnopqrstuvwxyz",
                   "ay bee see dee ee ef gee aitch eye jay kay el em en oh pee cue ar ess tee you vee "
                   "double-you ex why zee".split()))
GREEK = {"α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "Δ": "capital delta", "ε": "epsilon",
         "θ": "theta", "λ": "lambda", "μ": "mu", "π": "pi", "ρ": "rho", "σ": "sigma", "Σ": "capital sigma",
         "τ": "tau", "φ": "phi", "ω": "omega", "Ω": "capital omega"}
SYMBOLS = {"≈": " approximately ", "≠": " is not equal to ", "≤": " is less than or equal to ",
           "≥": " is greater than or equal to ", "×": " times ", "÷": " divided by ", "±": " plus or minus ",
           "√": " the square root of ", "∞": " infinity ", "→": " goes to ", "²": " squared", "³": " cubed",
           "%": " percent", "=": " equals ", "<": " is less than ", ">": " is greater than ", "+": " plus ",
           "−": " minus ", "∝": " is proportional to "}
UNITS = {"km/h": "kilometers per hour", "m/s²": "meters per second squared", "m/s": "meters per second",
         "km": "kilometers", "cm": "centimeters", "mm": "millimeters", "m": "meters", "kg": "kilograms",
         "g": "grams", "ms": "milliseconds", "s": "seconds", "min": "minutes", "h": "hours", "Hz": "hertz",
         "kHz": "kilohertz", "N": "newtons", "J": "joules", "W": "watts", "kW": "kilowatts", "V": "volts",
         "A": "amperes", "°C": "degrees Celsius", "°F": "degrees Fahrenheit", "°": "degrees", "K": "kelvin",
         "AU": "astronomical units", "ly": "light years", "L": "liters", "mL": "milliliters", "nm": "nanometers"}
ABBREVIATIONS = {"e.g.": "for example", "i.e.": "that is", "etc.": "et cetera", "vs.": "versus", "approx.": "approximately",
                 "AU": "A U", "Fig.": "figure", "Eq.": "equation", "No.": "number"}
PAUSE = "[pause]"


def symbol_name(tok: str, both_cases: set[str]) -> str:
    """`M` → "capital em" when m and M both occur in the video, else "em"; `r_1` → "ar one"; `θ` → "theta"."""
    base, _, sub = tok.partition("_")
    if base in GREEK:
        name = GREEK[base]
    elif len(base) == 1 and base.lower() in LETTERS:
        name = LETTERS[base.lower()]
        if base.lower() in both_cases:
            name = ("capital " if base.isupper() else "small ") + name
    else:
        name = " ".join(LETTERS.get(ch.lower(), ch) for ch in base)  # `AB` → "ay bee"
    return f"{name} {' '.join(LETTERS.get(ch, ch) if ch.isalpha() else ch for ch in sub)}".strip() if sub else name


def case_pairs(texts: list[str]) -> set[str]:
    """Letters used in backticks in BOTH cases anywhere in the video (e.g. M and m)."""
    seen = {t.partition("_")[0] for text in texts for t in re.findall(r"`([^`]+)`", text)}
    return {c.lower() for c in seen if len(c) == 1 and c.isalpha() and c.swapcase() in seen}


def speakable(text: str, both_cases: set[str] = frozenset()) -> str:
    """Plain text any TTS engine reads correctly; [pause] stays as a marker for to_ssml/to_plain."""
    text = re.sub(r"`([^`]+)`", lambda m: symbol_name(m[1], both_cases), text)
    for k, v in ABBREVIATIONS.items():
        if k != "AU":
            text = text.replace(k, v)
    units = "|".join(re.escape(u) for u in sorted(UNITS, key=len, reverse=True))
    text = re.sub(rf"(\d(?:[\d,.]*\d)?)\s?({units})(?![A-Za-z])", lambda m: f"{m[1]} {UNITS[m[2]]}", text)
    text = re.sub(r"(\d)\s*-\s*(\d)", r"\1 minus \2", text)
    for k, v in {**GREEK, **SYMBOLS}.items():
        text = text.replace(k, v if k in SYMBOLS else f" {v} ")
    text = re.sub(r"\bAU\b", "A U", text)
    return re.sub(r"\s+", " ", re.sub(r"\s+([,.!?;:])", r"\1", text)).strip()


def to_ssml(text: str, pause_ms: int = 600) -> str:
    parts = [html.escape(p.strip(), quote=False) for p in text.split(PAUSE)]
    return "<speak>" + f' <break time="{pause_ms}ms"/> '.join(p for p in parts if p) + "</speak>"


def to_ssml_marked(text: str, pause_ms: int = 600) -> tuple[str, list[str]]:
    """SSML with <mark name="i"/> before every word (Google TTS returns a time per mark) + the word list."""
    words, out = [], []
    for k, part in enumerate(text.split(PAUSE)):
        if k:
            out.append(f'<break time="{pause_ms}ms"/>')
        for w in part.split():
            out.append(f'<mark name="{len(words)}"/>{html.escape(w, quote=False)}')
            words.append(w)
    return "<speak>" + " ".join(out) + "</speak>", words


def to_plain(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace(PAUSE, " … ")).strip()


def phrase_times(marks: list[tuple[str, float]], beats: list[str], both_cases: set[str] = frozenset()) -> list[float | None]:
    """Start time (s) of each beat's quoted narration phrase, from word marks [(word, start_s)], in order."""
    norm = lambda s: re.sub(r"[^a-z0-9 ]", "", s.lower()).split()  # noqa: E731
    words = [norm(w)[0] if norm(w) else "" for w, _ in marks]
    out, i = [], 0
    for beat in beats:
        m = re.search(r"[\"“]([^\"”]+)[\"”]", beat)
        phrase = norm(speakable(m[1], both_cases).replace(PAUSE, "")) if m else []
        hit = next((j for j in range(i, len(words) - len(phrase) + 1) if phrase and words[j:j + len(phrase)] == phrase), None)
        out.append(round(marks[hit][1], 2) if hit is not None else None)
        i = hit + 1 if hit is not None else i
    return out
