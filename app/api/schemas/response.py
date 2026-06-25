from typing import Literal

from pydantic import BaseModel

from app.api.schemas.enums import NarrativeApproach


class GenerateResponse(BaseModel):
    """
    Response model
    """
    session_id: str
    workflow_id: str
    approach: NarrativeApproach
    status: Literal[
        "queued",
        "running",
        "completed",
        "failed",
    ]
