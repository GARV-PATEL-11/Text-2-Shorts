from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.graph.models.enums import NarrativeApproach


class UserInputState(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    session_id: str
    workflow_id: str = Field(default_factory=lambda: uuid4().hex)
    approach: NarrativeApproach
    requirement: str
    status: Literal["ready", "routed", "failed"]
    error: str | None = None


class RefinedOutputState(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    session_id: str
    workflow_id: str
    system_prompt: str
    approach: NarrativeApproach
    refined_requirement: str
    status: Literal["ready", "routed", "failed"]
    error: str | None = None
