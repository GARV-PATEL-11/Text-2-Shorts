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


Tier = Literal["basic", "good", "great"]
TIER_OF_LETTER: dict[str, Tier] = {"B": "basic", "G": "good", "X": "great"}
TIER_PENALTY: dict[str, int] = {"basic": 25, "good": 10, "great": 3}  # critique-protocol.md explains the tiers


class CritiqueIssue(Strict):
    """One defect, written so a refactorer can fix it without re-reviewing: which rule, where, what was seen, why it
    matters, and the smallest fix."""

    target: str = Field(
        ..., pattern=r"^(script|s\d{2}(c\d{2})?)$", description="the whole script, or the scene or clip it is about"
    )
    criterion: str = Field(
        ...,
        pattern=r"^[SPV]-[BGX]\d{1,2}$",
        description="the rubric line it breaks: S script · P plan · V video critic; B basic need · G good to have · "
        "X great if followed; then its number (P-B3)",
    )
    tier: Tier = Field(
        ..., description="basic: must always hold (blocks a pass) · good: expected quality · great: polish"
    )
    aspect: str = Field(
        ...,
        description="script: outline-fit · clarity · flow · pacing · speakability · tone; plan: clarity · sync · "
        "constructability · design; video: plan-match · sync · render · design",
    )
    evidence: str = Field(
        ..., min_length=1, description="what was seen and where: a quote, a beat, a frame time, a sync offset"
    )
    problem: str = Field(..., min_length=1, description="what is wrong, in one or two sentences")
    impact: str = Field(..., min_length=1, description="what it does to the viewer, the build or the sync")
    fix: str = Field(..., min_length=1, description="the smallest change that solves it")

    @model_validator(mode="after")
    def _criterion_names_its_tier(self):
        if (named := TIER_OF_LETTER[self.criterion[2]]) != self.tier:
            raise ValueError(f"{self.criterion} is a {named} criterion, not {self.tier}")
        return self


class CritiqueRound(Strict):
    reviewed: str = Field(
        ..., description="`text-2-shorts hash <run> script` or `… sNN plan|video`: the version reviewed"
    )
    verdict: Literal["pass", "revise"]
    score: int = Field(
        ...,
        ge=0,
        le=100,
        description="100 − 25 per basic − 10 per good − 3 per great issue (floor 0); pass = no basic issue and "
        "score ≥ quality_threshold",
    )
    summary: str = Field(
        ..., min_length=1, description="2–4 sentences: the verdict and why, the biggest risk, what already works"
    )
    strengths: list[str] = Field(default_factory=list, description="what works and must survive the refactor")
    issues: list[CritiqueIssue] = Field(default_factory=list, description="most important first")

    @model_validator(mode="after")
    def _score_and_verdict_follow_the_issues(self):
        expected = max(0, 100 - sum(TIER_PENALTY[issue.tier] for issue in self.issues))
        if self.score != expected:
            raise ValueError(
                f"score {self.score} does not follow from the issues: 100 − 25 per basic − 10 per good − 3 per "
                f"great = {expected}"
            )
        if self.verdict == "revise" and not self.issues:
            raise ValueError("a 'revise' verdict must list the issues to fix")
        if self.verdict == "pass" and (open_basic := [i.criterion for i in self.issues if i.tier == "basic"]):
            raise ValueError(f"basic needs are open ({', '.join(open_basic)}): the verdict is 'revise'")
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
