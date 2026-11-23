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


# ── Script (stage 2) ────────────────────────────────────────────────────────────


class ScriptScene(Strict):
    scene_id: SceneId
    role: Literal["index", "content", "recap"] = Field(
        "content", description="s01 is the index scene: it tells the viewer what the video covers"
    )
    title: str = Field(..., min_length=1)
    objective: str = Field(..., min_length=1, description="what this scene teaches, in one sentence")
    key_concepts: list[str] = Field(..., min_length=1)
    covers: list[int] = Field(default_factory=list, description="1-based indexes into Script.objectives it teaches")
    previews: list[SceneId] = Field(default_factory=list, description="index scene only: every later scene, in order")
    duration_seconds: float = Field(..., gt=0)
    bridge_in: str = Field(
        "",
        description="spoken inter-scene transition at the start of this scene: what was just covered, what comes "
        "next, why it matters. Empty for the first scene.",
    )
    narration: str = Field(..., min_length=1, description="the complete spoken text of the scene after the bridge")
    visual_idea: str = Field("", description="one or two sentences; the scene's visual plan holds the detail")


class Script(Strict):
    title: str = Field(..., min_length=1)
    structure: str = Field(..., min_length=1, description="narrative structure used, e.g. zoom, arc, linear, custom")
    objectives: list[str] = Field(..., min_length=1)
    target_wpm: int = Field(150, ge=90, le=220)
    scenes: list[ScriptScene] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _scenes_are_sequential_and_bridged(self):
        index_scene = self.scenes[0]
        if index_scene.role != "index":
            raise ValueError("s01 must be the index scene (role 'index'): say what the video covers")
        later = [scene.scene_id for scene in self.scenes[1:]]
        if index_scene.previews != later:
            raise ValueError(f"the index scene's previews must list every later scene in order: {later}")
        for number, scene in enumerate(self.scenes, 1):
            if number > 1 and scene.role == "index":
                raise ValueError(f"{scene.scene_id}: only s01 is the index scene")
            if scene.role != "index" and not scene.covers:
                raise ValueError(f"{scene.scene_id} covers no objective: every teaching scene covers at least one")
            if scene.scene_id != f"s{number:02d}":
                raise ValueError(f"scene {scene.scene_id} is at position {number}: expected s{number:02d}")
            if bad := [index for index in scene.covers if not 1 <= index <= len(self.objectives)]:
                raise ValueError(f"{scene.scene_id} covers objectives {bad}, but there are {len(self.objectives)}")
            if number == 1 and scene.bridge_in.strip():
                raise ValueError("s01 bridge_in must be empty: the first scene has nothing to bridge from")
            if number > 1 and not scene.bridge_in.strip():
                raise ValueError(
                    f"{scene.scene_id} bridge_in is empty: say what was covered, what comes next and why it matters"
                )
        return self


# ── Planning ────────────────────────────────────────────────────────────────────


class ContinuityState(Strict):
    """What is on screen at a boundary. Used as exit contract of clip N and entry contract of clip N+1."""

    persistent_objects: list[str] = Field(default_factory=list, description="registry names that must be visible")
    object_positions: dict[str, str] = Field(
        default_factory=dict, description="name → semantic zone, e.g. 'eq_main': 'top_center'"
    )
    descriptions: dict[str, str] = Field(
        default_factory=dict,
        description="name → what the object is (type, text or LaTeX, colour, size), so a clip built on its own can "
        "re-create the objects it takes over",
    )
    camera: str = "default_frame"
    notes: str = ""


class ClipPlan(Strict):
    clip_id: ClipId
    index: int = Field(..., ge=1)
    objective: str = Field(..., description="one teaching purpose; if you need 'and', split the clip")
    narration: str = Field(..., description="exact spoken text for this clip (TTS input)")
    ssml: str = Field(
        ...,
        description="the clip's audio plan: <speak> SSML over exactly the narration's words — <break> for waits, "
        "<prosody rate> for pace, <emphasis>, <s>/<p>, <sub>, <say-as>",
    )
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
        default_factory=list, description="topic card names, e.g. ['mathtex-indexing', 'axes-and-graphs']"
    )


class ScenePlan(Strict):
    scene_id: SceneId
    index: int = Field(..., ge=1)
    title: str
    objective: str
    composition: str = Field(
        ..., min_length=1, description="layout zones and the main visual elements of the scene, 2–4 sentences"
    )
    transition_in: str = Field(
        "", description="how the scene opens from the previous scene's final image; empty for the first scene"
    )
    clips: list[ClipPlan] = Field(..., min_length=1, max_length=8)
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


# ── Accuracy reviews (stage 2: script, stage 3: scene plans) ───────────────────


class ReviewFinding(Strict):
    target: str = Field(
        ..., pattern=r"^s\d{2}(c\d{2})?$", description="scene id (script review) or clip id (plan review)"
    )
    severity: Literal["ERROR", "WARN"]
    kind: Literal["FALSE", "UNSTATED", "NOTATION", "MISLEADING", "SPOKEN"]
    quote: str
    why: str
    fix: str


class ReviewReport(Strict):
    findings: list[ReviewFinding]


# ── Critic-refactor loops (plan before CP2, video before CP3): one critic, at most 3 rounds per scene ──────────


class CritiqueIssue(Strict):
    target: str = Field(..., pattern=r"^s\d{2}(c\d{2})?$", description="the scene or clip the issue is about")
    aspect: str = Field(
        ..., description="plan: clarity · sync · constructability · design; video: plan-match · sync · render · design"
    )
    problem: str
    fix: str


class CritiqueRound(Strict):
    reviewed: str = Field(..., description="`text-2-shorts hash <run> sNN plan|video` of the version reviewed")
    verdict: Literal["pass", "revise"]
    issues: list[CritiqueIssue] = Field(default_factory=list)

    @model_validator(mode="after")
    def _revise_names_issues(self):
        if self.verdict == "revise" and not self.issues:
            raise ValueError("a 'revise' verdict must list the issues to fix")
        if self.verdict == "pass" and self.issues:
            raise ValueError("a 'pass' verdict has no open issues")
        return self


class Critique(Strict):
    rounds: list[CritiqueRound] = Field(..., min_length=1)
