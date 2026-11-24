"""Contracts of the module design that was planned but never built. Nothing in the workflow uses them; they are kept
only until their removal is approved (artifacts/reports/unused-files-inventory.md, row 5)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import Field, field_validator
from schemas.base import ClipId, SceneId, Severity, Strict, canonical_hash, now
from schemas.plans import ClipPlan, ContinuityState, ScenePlan
from schemas.requirements import Brief, EnvironmentReport


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


class VideoProject(Strict):
    project_id: str = Field(..., pattern=r"^\d{8}-\d{6}-[a-z0-9-]{1,40}$")
    brief: Brief
    environment: EnvironmentReport
    created_at: datetime = Field(default_factory=now)


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
    """Row in the run ledger (artifacts/runs/<id>/state.json). The ledger, not chat history, is the source of truth."""

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
