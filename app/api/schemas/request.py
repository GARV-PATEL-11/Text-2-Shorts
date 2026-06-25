from uuid import uuid4

from pydantic import BaseModel, Field

from app.api.schemas.enums import NarrativeApproach


class GenerateRequest(BaseModel):
    requirement: str
    approach: NarrativeApproach
    session_id: str = Field(default_factory=lambda: uuid4().hex)
