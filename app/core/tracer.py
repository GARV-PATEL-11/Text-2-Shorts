"""tracer.py — Structured trace models and recorder for LLM calls."""
from __future__ import annotations

import dataclasses
import json
import logging
from dataclasses import dataclass

from app.core.log_schemas import LlmEvent, LogStatus
from app.core.logging_service import LoggingService


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
    """AWS Bedrock Converse API trace."""

    provider: str = "bedrock"
    request_id: str = ""
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


@dataclass
class GeminiTrace(BaseTrace):
    """Google Gemini GenerativeAI trace."""

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
    """Serialise *trace* to logs/app.jsonl and emit a typed LlmEvent."""
    _trace_logger.info(json.dumps(dataclasses.asdict(trace)))

    svc = LoggingService.get()
    extra_details: dict = {}
    if isinstance(trace, BedrockTrace):
        extra_details = {
            "bedrock_request_id": trace.request_id,
            "cache_read_tokens": trace.cache_read_tokens,
            "cache_write_tokens": trace.cache_write_tokens,
            }

    svc.emit(
        LlmEvent(
            session_id=trace.session_id,
            workflow_id=trace.workflow_id,
            node=trace.node_name,
            provider=trace.provider,
            model=trace.model_id,
            input_tokens=trace.input_tokens,
            output_tokens=trace.output_tokens,
            total_tokens=trace.total_tokens,
            is_structured=trace.is_structured,
            prompt_preview=trace.user_prompt[:300],
            response_preview=trace.response_preview,
            duration_ms=trace.latency_ms,
            status=LogStatus.SUCCESS,
            details=extra_details,
            ),
        )

    try:
        from app.core.context import request_logger_var

        rl = request_logger_var.get()
        if rl is not None:
            rl.llm_call(
                provider=trace.provider,
                model=trace.model_id,
                node=trace.node_name,
                latency_ms=trace.latency_ms,
                input_tokens=trace.input_tokens,
                output_tokens=trace.output_tokens,
                total_tokens=trace.total_tokens,
                is_structured=trace.is_structured,
                system_prompt=trace.system_prompt,
                user_prompt=trace.user_prompt,
                response=trace.response_preview,
                )
    except Exception:
        pass
