"""enums.py — Standardised enumerations shared across all log schemas."""
from __future__ import annotations

from enum import Enum


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogStatus(str, Enum):
    """Standardised status values used across every event type."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    RETRYING = "RETRYING"


class EventType(str, Enum):
    """Top-level event classification for routing, filtering, and querying."""
    SYSTEM_EVENT = "SYSTEM_EVENT"
    API_EVENT = "API_EVENT"
    WORKFLOW_EVENT = "WORKFLOW_EVENT"
    STAGE_EVENT = "STAGE_EVENT"
    NODE_EVENT = "NODE_EVENT"
    LLM_EVENT = "LLM_EVENT"
    TTS_EVENT = "TTS_EVENT"
    RENDER_EVENT = "RENDER_EVENT"
    STORAGE_EVENT = "STORAGE_EVENT"
    ERROR_EVENT = "ERROR_EVENT"
    METRIC_EVENT = "METRIC_EVENT"
