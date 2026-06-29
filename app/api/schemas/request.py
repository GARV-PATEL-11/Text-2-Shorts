import re
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from app.api.schemas.enums import NarrativeApproach


_SESSION_ID_RE = re.compile(r"^[a-f0-9]{32}$")


class GenerateRequest(BaseModel):
    requirement: str = Field(min_length=10, max_length=4096)
    approach: NarrativeApproach
    session_id: str = Field(default_factory=lambda: uuid4().hex)

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        if not _SESSION_ID_RE.match(v):
            raise ValueError("session_id must be a 32-character lowercase hex string (UUID hex)")
        return v
