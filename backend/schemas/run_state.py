"""The run ledger: state.json (approvals, clip builds, session transcripts, statuses) and log.jsonl rows."""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from schemas.base import Strict

Status = Literal[
    "pending",
    "in_progress",
    "completed",
    "failed",
    "requires_refactoring",
    "requires_user_approval",
    "approved",
]


class Approval(Strict):
    """A checkpoint approval, bound to the fingerprint of exactly what was approved."""

    at: str
    fingerprint: str | None = None
    upstream: dict[str, str | None] = Field(
        default_factory=dict, description="the earlier stages' fingerprints this approval was made on (M1)"
    )


class ClipBuild(Strict):
    """The last `accept` of a clip: READY with the key of the inputs it was built from, or FAILED."""

    status: Literal["READY", "FAILED"]
    open_findings: list[str] = Field(default_factory=list, description="gate: CODE for every ERROR still open")
    key: str | None = Field(None, description="clip_key of the inputs the accepted code was built from")
    at: str = ""


class RunState(Strict):
    """state.json — changed only by `approve`, `accept`, the hook and `status` (never by hand)."""

    approved: dict[str, Approval] = Field(
        default_factory=dict, description="requirements, template, outline, script, plan, scene:sNN, start:sNN, final"
    )
    clips: dict[str, ClipBuild] = Field(default_factory=dict, description="clip id → its last build")
    sessions: list[str] = Field(default_factory=list, description="Claude Code transcript paths of this run")
    status: dict[str, Status] = Field(default_factory=dict, description="every stage, scene and clip → its status")
    console_session: str | None = Field(None, description="the Claude Code session the website's console resumes")
    builder_prompt: str | None = Field(
        None, description="hash of the scene-builder prompt this run was made with: part of every clip key (D3)"
    )
    name: str | None = Field(
        None, max_length=120, description="the user's name for the run (None: named from its topic)"
    )
    spend_usd: float = Field(0.0, ge=0, description="what its console turns cost, as Claude Code reports each turn")
    attempts: dict[str, int] = Field(
        default_factory=dict,
        description="a loop's failed tries in a row (build:sNN:<key>, sync:sNN, review:script|plan); at MAX_ATTEMPTS "
        "the driver hands the loop to the user",
    )


class LogEntry(Strict):
    """One row of log.jsonl: a tool call of the session, as shown to the user."""

    ts: str
    event: Literal["tool"] = "tool"
    tool: str | None = None
    detail: str = ""
    agent: str | None = Field(None, description="the subagent, when the tool call dispatched one")
    shown: str = Field("", description="the line shown to the user")


class TokenUsage(Strict):
    """Token totals of a run's Claude Code sessions and subagents (`text-2-shorts report`)."""

    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0
    messages: int = Field(0, description="model responses, each counted once")
