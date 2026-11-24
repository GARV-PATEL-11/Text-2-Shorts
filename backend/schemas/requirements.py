"""Stage 1 contracts: the brief, standing preferences, the video template, the environment report."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator
from schemas.base import Strict


class Brief(Strict):
    """Stage 1 — the user's requirements, written by `text-2-shorts new` and confirmed with the user."""

    requirement: str = Field(..., min_length=1, description="the topic and request in the user's words")
    objectives: list[str] = Field(default_factory=list, description="what the viewer should be able to do or explain")
    audience: str = "curious beginners"
    style: str = Field("ELI5 / Feynman", description="explanation style and tone")
    approach: Literal["zoom", "arc", "linear", "creative"] = Field(
        "zoom",
        description="narrative structure: three fixed ones, or 'creative' (designed for this topic, or the user's own)",
    )
    minutes: float = Field(2.0, gt=0, le=12)
    pace: Literal["slow", "medium", "fast"] = "medium"
    notes: str = Field("", description="constraints and anything else the user asked for")
    tts: Literal["polly", "google"] = "polly"
    voice: str | None = None
    engine: Literal["neural", "generative", "standard"] = "neural"
    font: str | None = None
    detail_level: Literal["overview", "standard", "detailed"] = "standard"
    explanation_depth: Literal["intuitive", "conceptual", "rigorous"] = "conceptual"
    technical_complexity: Literal["beginner", "intermediate", "advanced"] = "beginner"
    visual_expectations: str = Field("", description="what the user expects to see (style, diagrams, density)")
    audio_expectations: str = Field("", description="voice, music and sound the user expects")


class VideoTemplate(Strict):
    """The video's look and feel (template.json): a starter template from runtime-environment/templates/ with the
    user's overrides. Overrides preferences.json, which overrides the standard style."""

    name: str = Field(..., min_length=1)
    description: str = ""
    background: str = Field(..., pattern=r"^#[0-9a-fA-F]{6}$")
    palette: dict[Literal["text", "focus", "given", "derived", "warning", "secondary"], str] = Field(
        default_factory=dict, description="palette role → Manim colour constant"
    )
    font: str | None = None
    type_scale: dict[Literal["title", "body", "label", "caption"], int] = Field(
        {"title": 48, "body": 34, "label": 28, "caption": 24}, description="font_size per role (standards.md)"
    )
    animation_style: str = Field("smooth, unhurried moves; one motion at a time", min_length=1)
    scene_transition: Literal["cut", "fade", "crossfade"] = "fade"
    transition_seconds: float = Field(0.5, ge=0, le=2)
    density: Literal["sparse", "balanced", "dense"] = "balanced"
    composition: str = Field("one focal element, centred; supporting labels around it", min_length=1)
    pacing: Literal["slow", "medium", "fast"] = "medium"
    music: str | None = Field(None, description="path to the user's own background music file (none = silence)")
    music_volume_db: float = Field(-24, ge=-40, le=0, description="music level under the voice")

    @model_validator(mode="after")
    def _readable_type(self):
        if min(self.type_scale.values(), default=24) < 24:
            raise ValueError("type_scale: nothing smaller than 24 (standards.md)")
        return self


class EnvironmentReport(Strict):
    manim_version: str
    python_version: str
    claude_code_version: str | None = None
    latex: bool
    dvisvgm: bool
    ffmpeg: bool
    bwrap: bool
    socat: bool
    api_index_hash: str
    problems: list[str] = Field(default_factory=list, description="what blocks a run (empty = ready)")


class Preferences(Strict):
    """Standing preferences applied at every stage (preferences.json in the run; copied from the repo root's
    preferences.json, if any, by `text-2-shorts new`)."""

    tone: str = Field("", description="tone of voice for the script, e.g. 'warm, playful'")
    palette: dict[Literal["text", "focus", "given", "derived", "warning", "secondary"], str] = Field(
        default_factory=dict, description="palette role → Manim colour constant, overriding the standard palette"
    )
    background: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    font: str | None = Field(None, description="font family when brief.json names none")
    voice_rate_percent: int = Field(100, ge=80, le=120)
    pause_ms: int = Field(600, ge=200, le=2000, description="length of a [pause]")
    confirm_each_scene: bool = Field(False, description="ask the user before each scene's production starts")
    quality_threshold: int = Field(
        85, ge=50, le=100, description="the critique score (0–100) a scene plan or video must reach"
    )
