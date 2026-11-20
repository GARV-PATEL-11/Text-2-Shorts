"""models.py — core data contracts for the Text-to-Shorts generator (Pydantic v2).

Status: PROPOSED for app/, but IMPLEMENTED and tested in this package
(`python -m pytest tests/test_models.py`). `export_json_schemas.py` writes the JSON
Schemas in schemas/json/ from these classes, so the two can never drift.

Hierarchy:  VideoProject → VideoPlan → ScenePlan[] → ClipPlan[] → (beats / animation elements)
Identity:   scene_id "s03", clip_id "s03c02" (stable across regenerations; versions are separate)
Provenance: every generated artifact carries GenerationMetadata with the hashes of its inputs,
            which is what makes cache keys and dependency-aware invalidation deterministic.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SceneId = Annotated[str, Field(pattern=r"^s\d{2}$", examples=["s03"])]
ClipId = Annotated[str, Field(pattern=r"^s\d{2}c\d{2}$", examples=["s03c02"])]


def canonical_hash(obj) -> str:
    """sha256 over canonical JSON (sorted keys, no whitespace). Used for cache keys + staleness."""
    if isinstance(obj, BaseModel):
        obj = obj.model_dump(mode="json")
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def now() -> datetime:
    return datetime.now(timezone.utc)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


# ── States ──────────────────────────────────────────────────────────────────────


class ApprovalState(str, Enum):
    draft = "draft"  # generated, never shown to a human
    pending_review = "pending_review"  # waiting at a human checkpoint
    approved = "approved"  # human (or auto-policy) accepted this exact version
    revision_requested = "revision_requested"
    rejected = "rejected"  # do not use; regenerate from upstream
    stale = "stale"  # an upstream input changed after approval


class ValidationStatus(str, Enum):
    not_run = "not_run"
    passed = "passed"
    passed_with_warnings = "passed_with_warnings"
    failed = "failed"


class Severity(str, Enum):
    info = "INFO"
    warn = "WARN"
    error = "ERROR"


# ── Provenance ──────────────────────────────────────────────────────────────────


class GenerationMetadata(Strict):
    producer: str = Field(..., description="agent/tool name, e.g. 'clip_codegen' or 'validate_manim_code'")
    producer_kind: Literal["llm", "deterministic", "human"]
    prompt_id: str | None = Field(None, description="prompt template id + version, e.g. 'clip_codegen@3'")
    model: str | None = None
    effort: str | None = None
    input_hashes: dict[str, str] = Field(default_factory=dict, description="artifact key → content hash consumed")
    created_at: datetime = Field(default_factory=now)
    cost_usd: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_read_tokens: int | None = None
    cache_write_tokens: int | None = None
    duration_ms: int | None = None
    attempt: int = 1

    def cache_key(self, extra: dict | None = None) -> str:
        return canonical_hash(
            {
                "producer": self.producer,
                "prompt": self.prompt_id,
                "model": self.model,
                "effort": self.effort,
                "inputs": self.input_hashes,
                **(extra or {}),
            }
        )


class ArtifactRef(Strict):
    kind: str
    path: str = Field(..., description="path relative to the run directory")
    version: int = Field(..., ge=1)
    content_hash: str


# ── Project / brief ────────────────────────────────────────────────────────────


class Brief(Strict):
    requirement: str
    refined: str | None = None
    approach: Literal["zoom", "arc", "linear"] = "zoom"
    target_minutes: float = Field(2.0, gt=0, le=12)
    pace: Literal["slow", "medium", "fast"] = "medium"
    audience: str = "curious beginners"
    notes: str = ""
    aspect: Literal["16:9", "9:16", "1:1"] = "16:9"
    voice: str = "Matthew"
    tts: Literal["polly", "google"] = "polly"
    tts_engine: Literal["neural", "generative", "standard"] = "neural"


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


class VideoProject(Strict):
    project_id: str = Field(..., pattern=r"^\d{8}-\d{6}-[a-z0-9-]{1,40}$")
    brief: Brief
    environment: EnvironmentReport
    created_at: datetime = Field(default_factory=now)


# ── Planning ────────────────────────────────────────────────────────────────────


class ContinuityState(Strict):
    """What is on screen at a boundary. Used as exit contract of clip N and entry contract of clip N+1."""

    persistent_objects: list[str] = Field(default_factory=list, description="registry names that must be visible")
    object_positions: dict[str, str] = Field(
        default_factory=dict, description="name → semantic zone, e.g. 'eq_main': 'top_center'"
    )
    camera: str = "default_frame"
    notes: str = ""


class ClipPlan(Strict):
    clip_id: ClipId
    index: int = Field(..., ge=1)
    objective: str = Field(..., description="one teaching purpose; if you need 'and', split the clip")
    narration: str = Field(..., description="exact spoken text for this clip (TTS input)")
    on_screen_math: list[str] = Field(default_factory=list, description="LaTeX strings that must appear")
    visual_intent: str = Field(..., description="what the viewer sees, 2–6 sentences, no code")
    beats: list[str] = Field(
        ..., min_length=1, max_length=8, description="ordered visual events synced to narration phrases"
    )
    entry: ContinuityState
    exit: ContinuityState
    est_seconds: float = Field(..., gt=0, le=45)
    depends_on: list[ClipId] = Field(default_factory=list)
    manim_topics: list[str] = Field(
        default_factory=list, description="keys into the doc index, e.g. ['mathtex.indexing','axes.plot']"
    )


class ScenePlan(Strict):
    scene_id: SceneId
    index: int = Field(..., ge=1)
    title: str
    objective: str
    segment_type: str
    clips: list[ClipPlan] = Field(..., min_length=1, max_length=8)
    transition_to_next: str | None = None
    color_roles: dict[str, str] = Field(default_factory=dict, description="semantic role → Manim color constant")

    @model_validator(mode="after")
    def _clip_ids_belong_to_scene(self):
        for i, clip in enumerate(self.clips, 1):
            if not clip.clip_id.startswith(self.scene_id) or clip.index != i:
                raise ValueError(
                    f"clip {clip.clip_id} index {clip.index} does not match scene {self.scene_id} position {i}"
                )
        for previous, current in zip(self.clips, self.clips[1:]):
            missing = set(current.entry.persistent_objects) - set(previous.exit.persistent_objects)
            if missing:
                raise ValueError(
                    f"{current.clip_id} entry needs {sorted(missing)} which {previous.clip_id} exit does not provide"
                )
        return self


class VideoPlan(Strict):
    title: str
    learning_outcome: str
    audience: str
    target_wpm: int = Field(150, ge=90, le=220)
    style: dict[str, str] = Field(
        default_factory=dict, description="global visual tokens (background, palette roles, fonts)"
    )
    scenes: list[ScenePlan] = Field(..., min_length=1)

    @field_validator("scenes")
    @classmethod
    def _sequential(cls, scenes):
        for i, scene in enumerate(scenes, 1):
            if scene.index != i or scene.scene_id != f"s{i:02d}":
                raise ValueError(f"scene {scene.scene_id} out of sequence at position {i}")
        return scenes

    def all_clips(self) -> list[ClipPlan]:
        return [clip for scene in self.scenes for clip in scene.clips]


# ── Production artifacts ───────────────────────────────────────────────────────


class NarrationSegment(Strict):
    clip_id: ClipId
    text: str
    text_hash: str
    voice: str
    engine: str


class AudioArtifact(Strict):
    clip_id: ClipId
    path: str
    seconds: float = Field(..., gt=0)
    text_hash: str
    word_marks: list[tuple[str, float]] | None = Field(
        None, description="(word, start_s) when the engine provides it (Polly speech marks)"
    )
    meta: GenerationMetadata


class DocumentationReference(Strict):
    topic: str = Field(..., description="doc index key, e.g. 'mathtex.indexing'")
    manim_version: str
    source_url: str
    snippet_path: str
    snippet_hash: str
    tokens_est: int


class VisualSpecification(Strict):
    """Clip-level visual plan (replaces the scene-level XML DSL as the unit of planning)."""

    clip_id: ClipId
    objects: dict[str, str] = Field(
        ..., description="registry name → Manim class + style, e.g. 'eq_main': 'MathTex FORMULA WHITE'"
    )
    layout: dict[str, str] = Field(..., description="registry name → semantic zone")
    steps: list[dict] = Field(..., min_length=1, description="[{beat, call, run_time, rate_func, narration_anchor}]")
    exit_state: ContinuityState
    docs_used: list[str] = Field(default_factory=list)
    meta: GenerationMetadata


class Finding(Strict):
    severity: Severity
    code: str = Field(..., description="stable machine code used by the repair router, e.g. REMOVED_API, OVERLAP")
    message: str
    line: int | None = None
    t: float | None = None


class ValidationResult(Strict):
    clip_id: ClipId
    validator: Literal["static", "layout", "timing", "render", "media"]
    status: ValidationStatus
    findings: list[Finding] = Field(default_factory=list)
    input_hash: str = Field(..., description="hash of the code/artifact validated; result reusable while unchanged")
    meta: GenerationMetadata


class CriticResult(Strict):
    clip_id: ClipId | None = None
    scene_id: SceneId | None = None
    critic: Literal["outline", "clip_plan", "clip_render", "scene_continuity"]
    approved: bool
    score: int = Field(..., ge=1, le=10)
    defects: list[Finding] = Field(
        default_factory=list, description="every defect must name evidence (frame time, line, field)"
    )
    input_hash: str
    meta: GenerationMetadata


class ManimCodeArtifact(Strict):
    clip_id: ClipId
    path: str
    class_name: str
    method_name: str = Field(..., pattern=r"^clip_\d{2}$")
    version: int = Field(..., ge=1)
    content_hash: str
    spec_hash: str = Field(..., description="hash of the VisualSpecification it implements")
    meta: GenerationMetadata


class RenderArtifact(Strict):
    clip_id: ClipId | None = None
    scene_id: SceneId | None = None
    level: Literal["clip_draft", "clip_final", "scene", "video"]
    path: str
    seconds: float
    quality: Literal["l", "m", "h", "k"]
    code_hash: str
    manim_version: str
    meta: GenerationMetadata


class HumanFeedback(Strict):
    feedback_id: str
    target_kind: Literal["video_plan", "scene", "clip_plan", "clip_render", "final_video"]
    target_id: str
    target_version: int
    action: Literal["approve", "revise", "reject", "regenerate"]
    text: str = ""
    scope: Literal["visual", "narration", "math", "timing", "structure", "any"] = "any"
    created_at: datetime = Field(default_factory=now)
    resolved_by_version: int | None = None


class CacheEntry(Strict):
    key: str
    kind: str
    path: str
    created_at: datetime = Field(default_factory=now)
    hits: int = 0
    producer: str
    valid: bool = True


class ClipState(Strict):
    """Row in the run ledger (runs/<id>/state.json). The ledger, not chat history, is the source of truth."""

    clip_id: ClipId
    plan_version: int = 1
    plan_hash: str
    approval: ApprovalState = ApprovalState.draft
    audio: ArtifactRef | None = None
    spec: ArtifactRef | None = None
    code: ArtifactRef | None = None
    render: ArtifactRef | None = None
    validations: dict[str, ValidationStatus] = Field(default_factory=dict)
    attempts: int = 0
    last_error: str | None = None
