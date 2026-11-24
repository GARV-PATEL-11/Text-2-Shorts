"""Review contracts: accuracy reviews, critique rounds, and the refactor log (changes.json)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator
from schemas.base import Strict


class ReviewFinding(Strict):
    target: str = Field(
        ..., pattern=r"^s\d{2}(c\d{2})?$", description="scene id (script review) or clip id (plan review)"
    )
    severity: Literal["ERROR", "WARN"]
    kind: Literal["FALSE", "UNSTATED", "NOTATION", "MISLEADING", "SPOKEN"]
    quote: str
    why: str
    fix: str


class ReviewReport(Strict):
    findings: list[ReviewFinding]


class CritiqueIssue(Strict):
    target: str = Field(
        ..., pattern=r"^(script|s\d{2}(c\d{2})?)$", description="the whole script, or the scene or clip it is about"
    )
    aspect: str = Field(
        ...,
        description="script: outline-fit · clarity · flow · pacing · speakability · tone; plan: clarity · sync · "
        "constructability · design; video: plan-match · sync · render · design",
    )
    problem: str
    fix: str


class CritiqueRound(Strict):
    reviewed: str = Field(
        ..., description="`text-2-shorts hash <run> script` or `… sNN plan|video`: the version reviewed"
    )
    verdict: Literal["pass", "revise"]
    score: int | None = Field(
        None, ge=0, le=100, description="plan and video rounds: the rubric score; pass = score ≥ quality_threshold"
    )
    issues: list[CritiqueIssue] = Field(default_factory=list)

    @model_validator(mode="after")
    def _revise_names_issues(self):
        if self.verdict == "revise" and not self.issues:
            raise ValueError("a 'revise' verdict must list the issues to fix")
        if self.verdict == "pass" and self.issues:
            raise ValueError("a 'pass' verdict has no open issues")
        return self


class Critique(Strict):
    rounds: list[CritiqueRound] = Field(..., min_length=1)


class ChangeRecord(Strict):
    """What one refactor iteration of a scene's video changed (scenes/sNN/changes.json → the run's changes.txt)."""

    target: str = Field(..., pattern=r"^s\d{2}(c\d{2})?$", description="the scene or clip changed")
    iteration: int = Field(..., ge=1, le=3, description="the video critique round whose issues this fixes")
    issue: str = Field(..., min_length=1, description="the original issue")
    findings: list[str] = Field(..., min_length=1, description="the critique findings addressed")
    modification: str = Field(..., min_length=1)
    files_changed: list[str] = Field(default_factory=list)
    rendering_changes: str = "none"
    audio_timing_changes: str = "none"
    sync_adjustments: str = "none"
    validation_results: str = Field(..., min_length=1, description="e.g. `accept` READY, preview in sync")
    final_score: int | None = Field(None, ge=0, le=100, description="the next round's score, once known")


class ChangeLog(Strict):
    entries: list[ChangeRecord] = Field(..., min_length=1)
