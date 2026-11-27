"""Stage 1 contracts: the brief, standing preferences, the video template, the environment report."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator
from schemas.base import Strict
from schemas.outline_models.approaches import LEGACY, ApproachName


class Brief(Strict):
    """Stage 1 — the user's requirements, written by `text-2-shorts new` and confirmed with the user."""

    @model_validator(mode="before")
    @classmethod
    def _drop_settings_the_template_owns_now(cls, data):
        """Briefs written before 0.20 carried the voice and font (the template owns them now); before 0.34 the
        approach was zoom, arc, linear or creative. Old runs stay readable."""
        if not isinstance(data, dict):
            return data
        data = {key: value for key, value in data.items() if key not in ("voice", "engine", "font")}
        if data.get("approach") in LEGACY:
            data["approach"] = LEGACY[data["approach"]]
        return data

    requirement: str = Field(..., min_length=1, description="the topic and request in the user's words")
    objectives: list[str] = Field(default_factory=list, description="what the viewer should be able to do or explain")
    audience: str = "curious beginners"
    style: str = Field("ELI5 / Feynman", description="explanation style and tone")
    approach: ApproachName = Field(
        "visual_intuition",
        description="how the topic is taught: one of seven presets, or 'custom' (outline_models/approaches.py)",
    )
    minutes: float = Field(2.0, gt=0, le=20)
    pace: Literal["slow", "medium", "fast"] = "medium"
    notes: str = Field("", description="constraints and anything else the user asked for")
    tts: Literal["polly", "google"] = "polly"
    detail_level: Literal["overview", "standard", "detailed"] = "standard"
    explanation_depth: Literal["intuitive", "conceptual", "rigorous"] = "conceptual"
    technical_complexity: Literal["beginner", "intermediate", "advanced"] = "beginner"
    visual_expectations: str = Field("", description="what the user expects to see (style, diagrams, density)")
    audio_expectations: str = Field("", description="voice, music and sound the user expects")


class VideoTemplate(Strict):
    """The video's look and sound (template.json): one variant per element of
    backend/templates/template_kit/elements.json, from a starter template plus the user's choices; resolved by
    backend/templates/video_settings.py and audio_settings.py. The assembly fields are ours."""

    name: str = Field(..., min_length=1, description="the starter template it started from")
    description: str = ""
    elements: dict[str, str] = Field(..., description="element → variant id (template_kit/elements.json)")
    overrides: dict[str, dict] = Field(
        default_factory=dict, description="custom values merged into a variant (video_settings.CUSTOM)"
    )
    scene_transition: Literal["cut", "fade", "crossfade"] = "fade"
    transition_seconds: float = Field(0.5, ge=0, le=2)
    music: str | None = Field(None, description="path to the user's own background music file (none = silence)")
    music_volume_db: float = Field(-24, ge=-40, le=0, description="music level under the voice")


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
    pause_ms: int = Field(600, ge=200, le=2000, description="length of a [pause]")
    confirm_each_scene: bool = Field(False, description="ask the user before each scene's production starts")
    quality_threshold: int | None = Field(
        None,
        ge=50,
        le=100,
        description="unset: only basic issues send a plan or video back (good and great are suggestions); a number: "
        "the critique score (0–100) must reach it too",
    )
