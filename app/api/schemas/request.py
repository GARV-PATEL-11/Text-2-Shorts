from __future__ import annotations

from pydantic import BaseModel, Field

from app.api.schemas.enums import NarrativeApproach


class GenerateRequest(BaseModel):
    requirement: str = Field(min_length=10, max_length=4096)
    approach: NarrativeApproach
