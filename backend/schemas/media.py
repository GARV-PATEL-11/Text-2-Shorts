"""Production contracts: narration audio, the clip-builder task, gate results, scene renders, the preview sync
report, the assembly manifest and the final report with its media checks."""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field, RootModel
from schemas.base import ClipId, SceneId, Strict
from schemas.plans import SoundEffect


class ClipAudio(Strict):
    """One clip's narration in scenes/sNN/audio/index.json."""

    hash: str = Field(..., description="voice key: spoken SSML + provider + voice + engine")
    seconds: float = Field(..., ge=0)
    spoken: str = ""
    beat_times: list[float | None] | None = Field(None, description="when the voice says each beat's phrase")


class AudioIndex(RootModel[dict[str, ClipAudio]]):
    """scenes/sNN/audio/index.json: clip id → its narration audio."""


class ClipTask(Strict):
    """TASK.json in a clip-builder folder: what ./check needs to judge the clip."""

    clip_name: str = Field(..., pattern=r"^clip_\d{2}$")
    clip_id: ClipId
    scene_id: SceneId
    scene_class_name: str
    clip_seconds: float = Field(..., gt=0, description="lead-in + narration + end hold")
    entry: list[str] = Field(default_factory=list)
    exit: list[str] = Field(default_factory=list)
    api_index: str
    beats: int = Field(..., ge=0)
    background: str = ""


class GateFinding(Strict):
    """A finding of the validator or the layout probe."""

    severity: Literal["ERROR", "WARN", "INFO"]
    code: str
    message: str = ""
    line: int | None = None
    t: float | None = Field(None, description="seconds into the scene")
    event: str | None = Field(None, description="the clip or animation it happened in")
    mobject: str | None = None
    mobjects: list[str] | None = None
    bbox: list[float] | None = None


class GateResult(Strict):
    """checks/<gate>.json written by ./check (compose, static, probe, render, frames)."""

    ok: bool
    findings: list[GateFinding] = Field(default_factory=list)
    error: str | None = None
    clip: dict[str, float | str | None] | None = Field(None, description="the clip's span in the probe")
    beats: dict[str, float] = Field(default_factory=dict, description="beat number → when self.beat(n) ran")
    video: str | None = None
    duration: float | None = None
    frames: list[str] = Field(default_factory=list)


class RenderedSection(Strict):
    """One clip section of a scene render (Manim's sections JSON; its extra fields are ignored)."""

    model_config = ConfigDict(extra="ignore")
    name: str
    path: str
    duration: float


class SceneRender(Strict):
    """What tools/scene_harness.py render reports."""

    model_config = ConfigDict(extra="ignore")
    ok: bool
    sections: list[RenderedSection] = Field(default_factory=list)
    stderr_tail: str | None = None


class SyncBeat(Strict):
    beat: int = Field(..., ge=1)
    plan: str
    spoken_at: float | None = None
    shown_at: float | None = None
    offset: float | None = Field(None, description="shown − spoken, seconds")


class SyncClip(Strict):
    clip_id: ClipId
    video_seconds: float | None = None
    audio_seconds: float | None = None
    audio_fits: bool | None = None
    beats: list[SyncBeat] = Field(default_factory=list)
    changes: str = Field("", description="the clip-builder's CHANGES.md")


class SyncReport(Strict):
    """scenes/sNN/sync.json: spoken vs shown time of every beat, and whether each clip's audio fits."""

    scene_id: SceneId
    tolerance: float
    clips: list[SyncClip]
    problems: list[str] = Field(default_factory=list)
    in_sync: bool
    scene_hash: str | None = Field(None, description="the scene video this report was made from")


class ManifestClip(Strict):
    clip_id: ClipId
    video: str
    audio: str
    lead_in: float = 0.0
    tail: float = 0.0
    sound_effects: list[SoundEffect] = Field(default_factory=list, description="files as absolute paths")


class ManifestScene(Strict):
    scene_id: SceneId
    clips: list[ManifestClip]


class SceneTransition(Strict):
    style: Literal["cut", "fade", "crossfade"] = "cut"
    seconds: float = Field(0.5, ge=0, le=2)
    color: str | None = None


class BackgroundMusic(Strict):
    file: str
    volume_db: float = Field(-24, ge=-40, le=0)


class AssemblyManifest(Strict):
    """assembly.json: what tools/assemble_clips.py joins into final.mp4."""

    scenes: list[ManifestScene]
    transition: SceneTransition | None = None
    music: BackgroundMusic | None = None


class ClipMux(Strict):
    video_s: float
    audio_s: float
    out_s: float
    video_padded_s: float
    audio_padded_s: float


class MediaFinding(Strict):
    severity: Literal["ERROR", "WARN"]
    code: str
    message: str


class FinalReport(Strict):
    """final_report.json: the assembly report, the media and delivery checks, and the fingerprint of the video."""

    clips: dict[str, ClipMux]
    sound_effects: int = 0
    transition: str = "cut"
    music: bool = False
    final_s: float
    sum_clips_s: float
    checks: list[MediaFinding] = Field(default_factory=list)
    fingerprint: str | None = None
