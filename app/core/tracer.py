"""tracer.py — Structured trace models and recorder for LLM calls."""

from __future__ import annotations

import dataclasses
import json
import logging
from dataclasses import dataclass


# ------------------------------------------------------------------ #
# Base trace                                                           #
# ------------------------------------------------------------------ #

@dataclass
class BaseTrace:
    """Fields shared by every LLM provider trace.

    Provider-specific subclasses extend this with any extra metadata
    their API surfaces (e.g. request IDs, cache tokens, safety ratings).
    Fields that contain free-form text are pre-truncated by the caller
    before being stored here.
    """

    timestamp: str
    session_id: str
    workflow_id: str
    node_name: str
    model_id: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    system_prompt: str  # pre-truncated to 500 chars by caller
    user_prompt: str  # pre-truncated to 500 chars by caller
    response_preview: str  # pre-truncated to 200 chars by caller
    is_structured: bool = False


# ------------------------------------------------------------------ #
# Provider-specific traces                                             #
# ------------------------------------------------------------------ #

@dataclass
class BedrockTrace(BaseTrace):
    """AWS Bedrock Converse API trace.

    Extra fields:
    - ``request_id``        — ``ResponseMetadata.RequestId`` for cross-referencing CloudWatch logs.
    - ``cache_read_tokens`` — tokens served from the prompt cache (saves cost).
    - ``cache_write_tokens``— tokens written into the prompt cache.
    """

    provider: str = "bedrock"
    request_id: str = ""
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


@dataclass
class GeminiTrace(BaseTrace):
    """Google Gemini GenerativeAI trace.

    Gemini does not surface a per-request ID or cache token counts in
    ``usage_metadata``, so those fields are intentionally absent.
    Reserved for future additions (grounding metadata, safety ratings, etc.).
    """

    provider: str = "gemini"


# ------------------------------------------------------------------ #
# Union alias                                                          #
# ------------------------------------------------------------------ #

AnyTrace = BedrockTrace | GeminiTrace

# ------------------------------------------------------------------ #
# Recorder                                                             #
# ------------------------------------------------------------------ #

_trace_logger = logging.getLogger("llm.trace")


def record_trace(trace: AnyTrace) -> None:
    """Serialise *trace* to one JSON line via the ``llm.trace`` logger.

    The logger is expected to be wired to ``logs/app.jsonl`` (or equivalent)
    by the application's logging configuration.  Each line is a flat dict
    produced by :func:`dataclasses.asdict`, so every field — including
    provider-specific ones — appears in the output automatically.
    """
    _trace_logger.info(json.dumps(dataclasses.asdict(trace)))
