from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.graph.models.validate_input_state import RefinedOutputState


class OutlineOutputState(BaseModel):
    session_id: str
    workflow_id: str
    outline: dict
    outline_type: str | None = None
    status: Literal["completed", "failed"]
    error: str | None = None


OutlineInputState = RefinedOutputState
