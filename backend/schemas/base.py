"""Shared building blocks of every contract: the strict base model, id types, severity, hashing."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

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
    return datetime.now(UTC)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class Severity(str, Enum):
    info = "INFO"
    warn = "WARN"
    error = "ERROR"


TargetId = Annotated[str, Field(pattern=r"^(outline|script|plan|scenes|final|s\d{2}(c\d{2})?)$")]


RequestKind = Literal["wording", "visual", "audio-timing", "accuracy", "structure", "style", "other"]
