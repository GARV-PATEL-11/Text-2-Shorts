"""events.py — Typed log schemas for every event category.

Each class inherits BaseLogSchema and fixes its ``event`` discriminator so
the LoggingService can route and validate without isinstance chains.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from app.core.log_schemas.base import BaseLogSchema
from app.core.log_schemas.enums import EventType, LogLevel, LogStatus


# ── 1. SYSTEM_EVENT ───────────────────────────────────────────────────────────

class SystemEvent(BaseLogSchema):
    """Infrastructure, startup, shutdown, configuration, environment events."""

    event: Literal[EventType.SYSTEM_EVENT] = EventType.SYSTEM_EVENT

    # Component that emitted this event (e.g. "uvicorn", "LangGraph", "ffmpeg")
    component: str = ""
    # Human-readable action label (e.g. "startup", "shutdown", "config.load")
    action: str = ""
    environment: str = ""


# ── 2. API_EVENT ──────────────────────────────────────────────────────────────

class ApiEvent(BaseLogSchema):
    """Request reception, response delivery, validation, auth, endpoint exec."""

    event: Literal[EventType.API_EVENT] = EventType.API_EVENT

    method: str = ""  # HTTP verb
    path: str = ""  # URL path (no query string)
    status_code: int = 0
    client_ip: str = ""
    # Truncated previews — full payloads go in ``details``
    request_preview: str = ""
    response_preview: str = ""


# ── 3. WORKFLOW_EVENT ─────────────────────────────────────────────────────────

class WorkflowEvent(BaseLogSchema):
    """Workflow initialisation, progress, completion, cancellation, failures."""

    event: Literal[EventType.WORKFLOW_EVENT] = EventType.WORKFLOW_EVENT

    approach: str = ""
    total_scenes: int = 0
    completed_stages: list[str] = Field(default_factory=list)
    failed_stages: list[str] = Field(default_factory=list)
    resume_from: str = ""


# ── 4. STAGE_EVENT ────────────────────────────────────────────────────────────

class StageEvent(BaseLogSchema):
    """Stage entry, exit, completion, retries, stage-level metrics."""

    event: Literal[EventType.STAGE_EVENT] = EventType.STAGE_EVENT

    stage_name: str = ""
    attempt: int = 1
    # Summary of what the stage produced (schema-agnostic dict)
    output_summary: dict[str, Any] = Field(default_factory=dict)


# ── 5. NODE_EVENT ─────────────────────────────────────────────────────────────

class NodeEvent(BaseLogSchema):
    """Node execution lifecycle: start, success, retry, skip, failure."""

    event: Literal[EventType.NODE_EVENT] = EventType.NODE_EVENT

    node_name: str = ""
    attempt: int = 1
    next_node: str = ""


# ── 6. LLM_EVENT ─────────────────────────────────────────────────────────────

class LlmEvent(BaseLogSchema):
    """Model invocation, prompt execution, token usage, latency, retries."""

    event: Literal[EventType.LLM_EVENT] = EventType.LLM_EVENT
    level: LogLevel = LogLevel.INFO

    provider: str = ""  # "gemini" | "bedrock"
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    # prompt/response previews (already truncated by callers)
    prompt_preview: str = ""
    response_preview: str = ""
    attempt: int = 1
    is_structured: bool = False
    # Bedrock-specific extras — stored in details by record_trace()
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


# ── 7. TTS_EVENT ──────────────────────────────────────────────────────────────

class TtsEvent(BaseLogSchema):
    """Text-to-speech generation, synthesis progress, completion, failures."""

    event: Literal[EventType.TTS_EVENT] = EventType.TTS_EVENT

    voice_id: str = ""
    text_len: int = 0
    audio_format: str = ""  # e.g. "mp3", "wav"
    audio_size_bytes: int = 0
    provider: str = ""


# ── 8. RENDER_EVENT ───────────────────────────────────────────────────────────

class RenderEvent(BaseLogSchema):
    """Rendering pipeline execution, frame generation, video assembly, failures."""

    event: Literal[EventType.RENDER_EVENT] = EventType.RENDER_EVENT

    scene_index: int = -1
    attempt: int = 1
    renderer: str = "manim"  # "manim" | "ffmpeg"
    output_path: str = ""
    stderr_preview: str = ""  # first 500 chars of render stderr
    returncode: int | None = None


# ── 9. STORAGE_EVENT ──────────────────────────────────────────────────────────

class StorageEvent(BaseLogSchema):
    """File uploads, downloads, reads, writes, deletes, sync activities."""

    event: Literal[EventType.STORAGE_EVENT] = EventType.STORAGE_EVENT

    operation: str = ""  # "read" | "write" | "delete" | "upload" | "download"
    path: str = ""
    size_bytes: int = 0
    content_type: str = ""
    backend: str = "local"  # "local" | "s3"
    bucket: str = ""


# ── 10. ERROR_EVENT ───────────────────────────────────────────────────────────

class ErrorEvent(BaseLogSchema):
    """Exceptions, validation failures, dependency failures, critical errors."""

    event: Literal[EventType.ERROR_EVENT] = EventType.ERROR_EVENT
    level: LogLevel = LogLevel.ERROR
    status: LogStatus = LogStatus.FAILED

    error_type: str = ""  # exception class name
    message: str = ""
    traceback: str = ""  # last 2000 chars
    context: str = ""  # calling function / pipeline stage


# ── 11. METRIC_EVENT ──────────────────────────────────────────────────────────

class MetricEvent(BaseLogSchema):
    """Performance metrics, resource utilisation, throughput, token KPIs."""

    event: Literal[EventType.METRIC_EVENT] = EventType.METRIC_EVENT

    metric_name: str = ""
    value: float = 0.0
    unit: str = ""  # "ms" | "tokens" | "bytes" | "count" | "%"
    tags: dict[str, str] = Field(default_factory=dict)


# ── Union alias for type narrowing ────────────────────────────────────────────

AnyLogEvent = (
        SystemEvent
        | ApiEvent
        | WorkflowEvent
        | StageEvent
        | NodeEvent
        | LlmEvent
        | TtsEvent
        | RenderEvent
        | StorageEvent
        | ErrorEvent
        | MetricEvent
)
