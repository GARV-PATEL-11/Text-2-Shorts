"""Views of runs for the frontend: a summary per run, one run's full view, and the checkpoints waiting for the user,
built from the run's files through their contracts. Nothing here writes to a run."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError
from schemas.api import CheckpointView, ClipView, RunDetail, RunSummary, SceneView
from schemas.session import ActionBatch

from app.workflow.approvals import approval_fingerprint, approval_problems, checkpoint_target
from app.workflow.artifacts import load_brief, load_final_report, load_scene_plans, load_sync_report
from app.workflow.change_requests import load_requests
from app.workflow.driver import next_actions
from app.workflow.ledger import load_decisions, load_state
from app.workflow.status import compute_statuses
from app.workflow.templates import load_template

CHECKPOINT_ORDER = ("requirements", "template", "outline", "script", "plan", "final")


def media_url(run: Path, path: Path) -> str | None:
    return f"/media/{run.name}/{path.relative_to(run).as_posix()}" if path.exists() else None


def created_text(run: Path) -> str:
    match = re.match(r"^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})", run.name)
    return f"{match[1]}-{match[2]}-{match[3]} {match[4]}:{match[5]}" if match else ""


def updated_text(run: Path) -> str:
    """When any of the run's own files last changed (its state, logs, decisions, outputs at the top level)."""
    times = [path.stat().st_mtime for path in run.iterdir() if path.is_file()] or [run.stat().st_mtime]
    return f"{datetime.fromtimestamp(max(times)):%Y-%m-%d %H:%M}"


def run_status(statuses: dict, batch: ActionBatch) -> str:
    """Where the run stands, in the run list's words (a run moves only when the user or Claude moves it)."""
    if statuses.get("final") == "approved":
        return "completed"
    if "failed" in statuses.values():
        return "failed"
    if statuses.get("requirements") != "approved":  # the look and the requirements are still being set
        return "configuring"
    return "awaiting_approval" if any(action.do == "ask_user" for action in batch.actions) else "in_progress"


def run_summary(run: Path) -> RunSummary:
    """One row of the run list; a run an older workflow version made is listed as not readable."""
    brief = load_brief(run)
    readable, stage, approved, status = brief is not None, "made by an older version", 0, "completed"
    if readable:
        try:
            batch = next_actions(run)
            stage = batch.stage
            statuses = compute_statuses(run)
            scenes = [status for key, status in statuses.items() if len(key) == 3 and key.startswith("s")]
            approved = sum(statuses.get(name) == "approved" for name in CHECKPOINT_ORDER)
            approved += bool(scenes) and all(status == "approved" for status in scenes)
            status = run_status(statuses, batch)
        except (ValidationError, ValueError, KeyError) as error:
            readable, stage, status = False, f"cannot be read: {type(error).__name__}", "failed"
    topic = brief.requirement if brief else run.name.split("-", 2)[-1].replace("-", " ")
    try:
        name = load_state(run).name
    except ValidationError:
        name = None
    template = load_template(run) if readable else None
    return RunSummary(
        id=run.name,
        name=name or default_name(topic, run),
        topic=topic,
        created=created_text(run),
        updated=updated_text(run),
        template=template.name if template else "",
        status=status if readable or not (run / "final.mp4").exists() else "completed",
        stage=stage,
        has_final=(run / "final.mp4").exists(),
        readable=readable,
        stages_approved=approved,
    )


def default_name(topic: str, run: Path) -> str:
    """'<topic> — Nov 26, 2026' from the run's topic and start date, when the user named it nothing."""
    words = re.sub(r"[*_`#>]", "", topic).strip().rstrip("?.!") or "Untitled Run"
    match = re.match(r"^(\d{4})(\d{2})(\d{2})", run.name)
    when = datetime(int(match[1]), int(match[2]), int(match[3])).strftime("%b %-d, %Y") if match else ""
    short = words if len(words) <= 60 else words[:57].rsplit(" ", 1)[0] + "…"
    short = short[0].upper() + short[1:]  # names from an old folder slug are all lower case
    return f"{short} — {when}" if when else short


LABELS = {
    "requirements": "Requirements",
    "template": "Template",
    "outline": "Outline",
    "script": "Script",
    "plan": "Scene Plans",
    "final": "Final Video",
}


def checkpoint_label(target: str) -> str:
    if target.startswith("start:"):
        return f"Start Scene {int(target.removeprefix('start:s'))}"
    if target == "scenes":
        return "All Scenes"
    return LABELS.get(target, f"Scene {int(target[1:])}" if re.fullmatch(r"s\d{2}", target) else target)


def awaiting_checkpoints(run: Path, statuses: dict, batch: ActionBatch) -> list[CheckpointView]:
    """The checkpoints the user can decide now: those waiting for approval, and the one the next batch asks about."""
    targets = [
        name
        for name, value in statuses.items()
        if value == "requires_user_approval" and not re.match(r"^s\d{2}(c\d{2})?$", name)  # scenes: one CP3, "scenes"
    ]
    targets += [action.checkpoint for action in batch.actions if action.checkpoint and action.checkpoint not in targets]
    return [
        CheckpointView(
            target=target,
            label=checkpoint_label(target),
            problems=approval_problems(run, checkpoint_target(target)),
            fingerprint=approval_fingerprint(run, checkpoint_target(target)),
        )
        for target in targets
    ]


def run_detail(run: Path) -> RunDetail:
    """Everything the run page shows. A run made by an older version still shows its final video."""
    summary = run_summary(run)
    detail = RunDetail(summary=summary, final_video=media_url(run, run / "final.mp4"))
    if not summary.readable:
        detail.problem = "Made by an older version of Faraday: only its final video can be shown."
        return detail
    brief = load_brief(run)
    assert brief is not None  # readable runs have a valid brief
    statuses = compute_statuses(run)
    detail.objectives, detail.approach, detail.minutes = brief.objectives, brief.approach, brief.minutes
    detail.stages = {stage: statuses[stage] for stage in CHECKPOINT_ORDER if stage in statuses}
    detail.next = next_actions(run)
    detail.awaiting = awaiting_checkpoints(run, statuses, detail.next)
    for plan in load_scene_plans(run):
        sync = load_sync_report(run, plan.scene_id)
        detail.scenes.append(
            SceneView(
                scene_id=plan.scene_id,
                title=plan.title,
                status=statuses.get(plan.scene_id, "pending"),
                clips=[
                    ClipView(
                        clip_id=clip.clip_id, objective=clip.objective, status=statuses.get(clip.clip_id, "pending")
                    )
                    for clip in plan.clips
                ],
                preview=media_url(run, run / "scenes" / plan.scene_id / "preview.mp4"),
                sync_problems=sync.problems if sync else [],
            )
        )
    report = load_final_report(run)
    detail.final_checks = report.checks if report else []
    detail.final_checked = report is not None and (run / "final.mp4").exists()
    detail.requests = load_requests(run)
    detail.decisions = load_decisions(run)
    return detail
