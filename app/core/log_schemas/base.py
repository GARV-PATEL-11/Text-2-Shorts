"""base.py — BaseLogSchema: mandatory fields every log entry must carry."""
from __future__ import annotations

import inspect
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.core.log_schemas.enums import EventType, LogLevel, LogStatus


SCHEMA_VERSION = "1.0"


class BaseLogSchema(BaseModel):
    """Root schema. Every log type must inherit from this class.

    Mandatory fields guarantee a consistent structure across all event types,
    enabling uniform querying, tracing, and observability pipeline ingestion.
    """

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    # ── Schema identity ───────────────────────────────────────────────────────
    schema_version: str = SCHEMA_VERSION

    # ── When ──────────────────────────────────────────────────────────────────
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        )

    # ── Severity ──────────────────────────────────────────────────────────────
    level: LogLevel = LogLevel.INFO

    # ── Where (code location) ─────────────────────────────────────────────────
    logger: str = ""
    module: str = ""
    func: str = ""
    line: int = 0

    # ── What (event classification) ───────────────────────────────────────────
    event: EventType

    # ── Traceability ──────────────────────────────────────────────────────────
    request_id: str = Field(default_factory=lambda: uuid4().hex)
    session_id: str = ""
    workflow_id: str = ""

    # ── Pipeline context ──────────────────────────────────────────────────────
    stage: str = ""
    node: str = ""

    # ── Outcome ───────────────────────────────────────────────────────────────
    status: LogStatus = LogStatus.PENDING

    # ── Timing ───────────────────────────────────────────────────────────────
    duration_ms: float | None = None

    # ── Extensible payload ────────────────────────────────────────────────────
    details: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_caller(
            cls,
            *,
            event: EventType,
            depth: int = 2,
            **kwargs: Any,
            ) -> "BaseLogSchema":
        """Construct with automatic code-location capture.

        ``depth`` controls how many frames to walk up the call stack so that
        ``module``, ``func``, and ``line`` point at the *caller's* site, not
        this factory method.
        """
        frame = inspect.stack()[depth]
        return cls(
            event=event,
            module=frame.filename.rsplit("/", 1)[-1].removesuffix(".py"),
            func=frame.function,
            line=frame.lineno,
            **kwargs,
            )
