"""The user's interaction: change requests and their resolutions (requests.jsonl), checkpoint decisions
(decisions.jsonl)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from schemas.base import RequestKind, Strict, TargetId


class ChangeRequest(Strict):
    """One tweak the user asked for (`text-2-shorts feedback`), routed to the stage it belongs to."""

    id: str = Field(..., pattern=r"^r\d{3}$")
    target: TargetId
    kind: RequestKind
    text: str = Field(..., min_length=1, description="the user's words")
    checkpoint: str | None = Field(None, description="the checkpoint it was raised at, if any")
    created_at: str


class RequestEvent(ChangeRequest):
    """A request row of requests.jsonl."""

    event: Literal["request"] = "request"


class ResolutionEvent(Strict):
    """A resolution row of requests.jsonl."""

    event: Literal["resolution"] = "resolution"
    id: str = Field(..., pattern=r"^r\d{3}$")
    status: Literal["applied", "declined"]
    note: str = ""
    resolved_at: str


class TrackedRequest(ChangeRequest):
    """A change request with its current status, folded from its events in requests.jsonl."""

    status: Literal["open", "applied", "declined"] = "open"
    note: str = ""


class RequestResolution(Strict):
    id: str = Field(..., pattern=r"^r\d{3}$")
    status: Literal["applied", "declined"]
    note: str = ""
    resolved_at: str


class CheckpointDecision(Strict):
    """How the user decided at a checkpoint (CP0–CP4, or the start of a scene when they asked to confirm each)."""

    checkpoint: str = Field(
        ..., pattern=r"^(requirements|template|outline|script|plan|scenes|final|s\d{2}|start:s\d{2})$"
    )
    decision: Literal["approved", "approved_with_notes", "changes_requested"]
    notes: str = ""
    requests: list[str] = Field(default_factory=list, description="change request ids raised with this decision")
    forced: bool = False
    fingerprint: str | None = None
    decided_at: str
    by: str = Field("", description="who decided: the signed-in account on the website, 'session' from the CLI")
