"""The web API of `text-2-shorts serve`: run summaries, one run's full view, and the user's approvals and change
requests (inputs validated here, applied by the same workflow functions as the CLI)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from schemas.base import Strict
from schemas.interaction import CheckpointDecision, TrackedRequest
from schemas.media import MediaFinding
from schemas.outline_models.approaches import ApproachName
from schemas.run_state import Status
from schemas.session import ActionBatch

RunStatus = Literal["configuring", "in_progress", "awaiting_approval", "failed", "completed"]


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


class ProfileInput(Strict):
    """PUT /api/profile: the name Faraday calls you (kept on this machine)."""

    name: str = Field("", max_length=80)


class ProfileView(ProfileInput):
    """GET /api/profile: who is signed in, and what the runs on this machine have cost."""

    account: ClaudeAccount
    runs: int = Field(0, ge=0, description="runs on this machine (not drafts or the trash)")
    spend_usd: float = Field(0.0, ge=0, description="the cost Claude Code reported for every console turn, all runs")


class SessionView(Strict):
    """GET/POST/DELETE /api/session"""

    signed_in: bool
    account: ClaudeAccount | None = None
    claude_code_signed_in: bool = Field(True, description="False: run `claude auth login` first")


class RunSummary(Strict):
    """One row of the run list."""

    id: str = Field(..., description="the run folder name, e.g. 20261124-101500-keplers-laws")
    name: str = Field("", description="the user's name for it, or '<topic> — <date>' when they gave none")
    topic: str
    created: str = Field(..., description="YYYY-MM-DD HH:MM, from the folder name")
    updated: str = Field("", description="YYYY-MM-DD HH:MM: the last time any of its files changed")
    template: str = Field("", description="the starter template its look started from")
    status: RunStatus = "in_progress"
    stage: str = Field(..., description="the stage the next batch belongs to, or why the run cannot be read")
    stages_approved: int = Field(
        0, ge=0, le=7, description="of the 7 the website shows: the 6 checkpoints, and all scenes as one"
    )
    has_final: bool
    readable: bool = Field(True, description="False when an older version of the workflow made it")


class RenameInput(Strict):
    """PATCH /api/runs/<run>: a new name (the run's files and id do not change)."""

    name: str = Field(..., min_length=1, max_length=120)


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
    fingerprint: str | None = Field(None, description="the version shown; ApproveInput sends it back")


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

    checkpoint: str = Field(
        ..., pattern=r"^(requirements|template|outline|script|plan|scenes|final|s\d{2}|start:s\d{2})$"
    )
    notes: str = Field("", max_length=4000)
    force: bool = Field(False, description="approve although problems are open (the user accepts them)")
    fingerprint: str | None = Field(None, description="CheckpointView.fingerprint the page showed (409 if it moved on)")


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
    approach: ApproachName = "visual_intuition"
    name: str = Field("", max_length=120, description="optional: the run's name (default: its topic and date)")
    minutes: float = Field(4, ge=3, le=20, description="teaching narration; intro, bridges and closing are extra")
    notes: str = Field("", max_length=2000, description="for Custom: how the user wants it taught")
    audience: str = Field("curious beginners", max_length=300)
    tts: Literal["polly", "google"] = "polly"
    look: LookInput | None = Field(
        None, description="the template chosen in Start a Run's first step (saved and approved)"
    )


class BrowserLogEntry(Strict):
    """One thing the browser reports: an error, a failed request, an action."""

    level: Literal["debug", "info", "warn", "error"]
    message: str = Field(..., max_length=2000)
    at: str = Field("", max_length=40, description="the browser's time")
    page: str = Field("", max_length=300, description="the route it happened on")
    details: str = Field("", max_length=4000)


class BrowserLogBatch(Strict):
    """POST /api/logs: what the browser has to report, in batches (frontend.log)."""

    entries: list[BrowserLogEntry] = Field(..., min_length=1, max_length=50)


class ConsoleInput(Strict):
    """POST /api/runs/<run>/console: one message to the run's Claude Code session."""

    message: str = Field(..., min_length=1, max_length=8000)


class ConsoleEntry(Strict):
    """One line of the console (console.jsonl): what the user said, what Claude said or did, or what happened."""

    at: str
    role: Literal["you", "claude", "question", "tool", "system", "error"]
    text: str = Field(..., description="Markdown")
    options: list[str] = Field(default_factory=list, description="a question's choices, answered with one click")


class ConsoleView(Strict):
    busy: bool
    kickoff: str = Field("", description="the message that starts (or resumes) production")
    entries: list[ConsoleEntry] = Field(default_factory=list)


class LookOption(Strict):
    id: str
    label: str
    detail: str = Field("", description="what it means beyond its name (voice ids, rate, tone rules)")


class LookElement(Strict):
    """One element of the tree: a variant per option, maybe a custom value, maybe a gallery sheet of every option."""

    id: str
    label: str
    group: str
    kind: Literal["visual", "sound"]
    description: str = ""
    options: list[LookOption]
    custom: str | None = Field(None, description="what a custom value is (e.g. 'colour'); None = variants only")
    previewed: bool = Field(False, description="every option has a picture: /previews/<mode>/<id>/<option>.webp")


class LookTemplate(Strict):
    name: str
    description: str = ""
    elements: dict[str, str]


class LookCatalogue(Strict):
    """GET /api/look: the starter templates and every element the user can set."""

    templates: list[LookTemplate]
    elements: list[LookElement]


class LookInput(Strict):
    """POST /api/runs/<run>/look (and …/look/voice): a starter template, the elements changed, custom values."""

    template: str = Field(..., min_length=1)
    elements: dict[str, str] = Field(default_factory=dict, description="element → variant; others keep the default")
    custom: dict[str, str] = Field(default_factory=dict, description="element → the user's own value")


class ReshuffleInput(Strict):
    """POST /api/runs/<run>/reshuffle: which groups to reshuffle, with which seed; apply=False only shows it."""

    seed: int = Field(..., ge=0, le=2**31 - 1, description="the same seed always gives the same look")
    groups: list[Literal["colours", "fonts", "background", "grid", "border"]] = Field(..., min_length=1)
    apply: bool = False


class ReshuffleChange(Strict):
    element: str
    before: str
    after: str


class ReshuffleView(Strict):
    """The reshuffled look (as a LookInput, for the still preview) and what changed; applied when it was saved."""

    look: LookInput
    changes: list[ReshuffleChange]
    applied: bool


class LookView(Strict):
    """The run's look and sound as chosen so far (the default starter until one is saved)."""

    template: str
    elements: dict[str, str]
    custom: dict[str, str] = Field(default_factory=dict)
    saved: bool = Field(False, description="template.json exists")


class VoiceSample(Strict):
    url: str


class LookOptionsInput(Strict):
    """POST /api/look/options: every option of one element, drawn in the user's own look."""

    look: LookInput
    element: str = Field(..., min_length=1, max_length=40)


class LookOptionPicture(Strict):
    option: str = Field(..., description="a variant id, or __custom__ for the user's own value")
    url: str | None = Field(None, description="854×480, lossless; None when this option would make the text unreadable")
    full: str | None = Field(None, description="2560×1440, rendered when first opened")


class LookOptionPictures(Strict):
    pictures: list[LookOptionPicture]


class LookStill(Strict):
    """POST /api/runs/<run>/look/still: one frame in the chosen colours, font and sizes."""

    url: str
    note: str | None = Field(None, description="e.g. the font is not installed and a default is shown")


class UsageWindow(Strict):
    """One usage-limit window, as Claude Code's rate_limit_event reports it."""

    id: str = Field(..., description="five_hour (the current session) or a weekly window: seven_day, seven_day_opus, …")
    used_percent: float = Field(..., ge=0)
    resets_at: int = Field(..., ge=0, description="epoch seconds")
    status: str = Field("allowed", description="allowed, or why not (e.g. rejected)")


class UsageView(Strict):
    """GET/POST /api/usage: the Claude plan's usage limits, from the latest Claude Code turn on this computer."""

    plan: str = ""
    checked_at: str | None = Field(None, description="when Claude Code last reported them (local ISO time)")
    windows: list[UsageWindow] = Field(default_factory=list)


class DraftInput(Strict):
    """PUT /api/drafts/<id>: Start a Run as far as the user got, saved as they go (on this machine, in the runs
    folder). Lenient on purpose: a draft may be half filled; POST /api/runs checks it all."""

    name: str = Field("", max_length=120)
    step: int = Field(0, ge=0, le=20)
    look: LookInput | None = None
    requirement: str = Field("", max_length=2000)
    objectives: str = Field("", max_length=4000, description="as typed: one per line")
    approach: ApproachName = "visual_intuition"
    minutes: str = Field("4", max_length=8, description="as typed")
    audience: str = Field("curious beginners", max_length=300)
    tts: Literal["polly", "google"] = "polly"
    notes: str = Field("", max_length=2000)


class Draft(DraftInput):
    id: str = Field(..., pattern=r"^[0-9a-f-]{36}$")
    updated: str
