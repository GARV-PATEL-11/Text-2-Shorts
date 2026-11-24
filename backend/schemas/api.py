"""The web API of `text-2-shorts serve`: run summaries, one run's full view, and the user's approvals and change
requests (inputs validated here, applied by the same workflow functions as the CLI)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from schemas.base import Strict
from schemas.interaction import CheckpointDecision, TrackedRequest
from schemas.media import MediaFinding
from schemas.run_state import Status
from schemas.session import ActionBatch


class ClaudeAuthStatus(BaseModel):
    """What `claude auth status --json` reports (Claude Code's format: only the fields used here are read)."""

    model_config = ConfigDict(extra="ignore")
    loggedIn: bool = False
    email: str | None = None
    orgName: str | None = None
    subscriptionType: str | None = None
    authMethod: str | None = None


class ClaudeAccount(Strict):
    """The Claude account Claude Code is signed in to on this machine: who the web view's user is."""

    email: str
    organization: str = ""
    plan: str = ""
    method: str = Field("", description="claude.ai (subscription) or console (API billing)")


class SessionView(Strict):
    """GET/POST/DELETE /api/session"""

    signed_in: bool
    account: ClaudeAccount | None = None
    claude_code_signed_in: bool = Field(True, description="False: run `claude auth login` first")


class RunSummary(Strict):
    """One row of the run list."""

    id: str = Field(..., description="the run folder name, e.g. 20261124-101500-keplers-laws")
    topic: str
    created: str = Field(..., description="YYYY-MM-DD HH:MM, from the folder name")
    stage: str = Field(..., description="the stage the next batch belongs to, or why the run cannot be read")
    has_final: bool
    readable: bool = Field(True, description="False when an older version of the workflow made it")


class ClipView(Strict):
    clip_id: str
    objective: str
    status: Status


class SceneView(Strict):
    scene_id: str
    title: str
    status: Status
    clips: list[ClipView] = Field(default_factory=list)
    preview: str | None = Field(None, description="URL of the 720p30 scene preview")
    sync_problems: list[str] = Field(default_factory=list)


class CheckpointView(Strict):
    """A checkpoint waiting for the user, with what would block approving it now."""

    target: str = Field(..., description="what `approve` takes: a stage, sNN, start:sNN or final")
    label: str
    problems: list[str] = Field(default_factory=list, description="open problems (approving anyway records it)")


class RunDetail(Strict):
    """Everything the run page shows."""

    summary: RunSummary
    objectives: list[str] = Field(default_factory=list)
    approach: str | None = None
    minutes: float | None = None
    stages: dict[str, Status] = Field(default_factory=dict, description="requirements … final")
    next: ActionBatch | None = None
    awaiting: list[CheckpointView] = Field(default_factory=list, description="checkpoints the user can decide now")
    scenes: list[SceneView] = Field(default_factory=list)
    final_video: str | None = Field(None, description="URL of final.mp4")
    final_checks: list[MediaFinding] = Field(default_factory=list)
    final_checked: bool = Field(False, description="the media checks ran on this final video (a report exists)")
    requests: list[TrackedRequest] = Field(default_factory=list)
    decisions: list[CheckpointDecision] = Field(default_factory=list)
    problem: str | None = Field(None, description="why the run could not be read fully")


class ApproveInput(Strict):
    """POST /api/runs/<run>/approve"""

    checkpoint: str = Field(..., pattern=r"^(requirements|template|outline|script|plan|final|s\d{2}|start:s\d{2})$")
    notes: str = Field("", max_length=4000)
    force: bool = Field(False, description="approve although problems are open (the user accepts them)")


class ChangeRequestInput(Strict):
    """POST /api/runs/<run>/requests"""

    target: str
    kind: str
    text: str = Field(..., min_length=1, max_length=4000)
    checkpoint: str | None = None


class ResolveInput(Strict):
    """POST /api/runs/<run>/requests/<id>"""

    status: Literal["applied", "declined"]
    note: str = Field("", max_length=4000)


class ApiError(Strict):
    error: str
    problems: list[str] = Field(default_factory=list)


class NewRunInput(Strict):
    """POST /api/runs: a run started from the website (what `text-2-shorts new` asks)."""

    requirement: str = Field(..., min_length=3, max_length=2000, description="the topic, in the user's words")
    objectives: list[str] = Field(default_factory=list, max_length=8)
    approach: Literal["zoom", "arc", "linear", "creative"] = "zoom"
    minutes: float = Field(2, gt=0, le=12)
    audience: str = Field("curious beginners", max_length=300)
    tts: Literal["polly", "google"] = "polly"


class ConsoleInput(Strict):
    """POST /api/runs/<run>/console: one message to the run's Claude Code session."""

    message: str = Field(..., min_length=1, max_length=8000)


class ConsoleEntry(Strict):
    """One line of the console (console.jsonl): what the user said, what Claude said or did, or what happened."""

    at: str
    role: Literal["you", "claude", "tool", "system", "error"]
    text: str


class ConsoleView(Strict):
    busy: bool
    kickoff: str = Field("", description="the message that starts (or resumes) production")
    entries: list[ConsoleEntry] = Field(default_factory=list)
