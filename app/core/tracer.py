"""tracer.py — Structured trace model and recorder for Bedrock calls."""

from __future__ import annotations

import dataclasses
import json
import logging
from dataclasses import dataclass


@dataclass
class BedrockTrace:
    timestamp: str
    session_id: str
    workflow_id: str
    node_name: str
    model_id: str
    request_id: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    system_prompt: str  # truncated to 500 chars
    user_prompt: str  # truncated to 500 chars
    response_preview: str  # first 200 chars
    is_structured: bool


_trace_logger = logging.getLogger("bedrock.trace")


def record_trace(trace: BedrockTrace) -> None:
    """Write one JSON line to the bedrock.trace logger (logs/app.jsonl)."""
    _trace_logger.info(json.dumps(dataclasses.asdict(trace)))
