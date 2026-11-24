"""Run status: remaining steps, the status of every stage, scene and clip, and token totals."""

from __future__ import annotations

import json
from pathlib import Path

from schemas.run_state import Status, TokenUsage

from app.workflow.approvals import approval_problems
from app.workflow.artifacts import load_final_report, load_scene_plans, load_script
from app.workflow.change_requests import open_requests, requests_text
from app.workflow.checkpoints import stage_approval_problem
from app.workflow.critiques import critique_problems, critique_state, review_problems
from app.workflow.fingerprints import clip_key, fingerprint
from app.workflow.ledger import is_approval_current, load_state, update_state
from app.workflow.production import preview_problems, stale_audio
from app.workflow.templates import validate_template
from app.workflow.validation import (
    validate_brief,
    validate_content,
    validate_outline,
    validate_plan,
    validate_script,
    validate_topics,
)


def next_steps(run: Path) -> list[str]:
    """What is left to do, in order — the resume point after any interruption. Approvals and the final render are
    compared with the current clip keys, so anything rebuilt since is asked again."""
    state = load_state(run)
    steps = [f"brief: {error}" for error in validate_brief(run)]
    for name, validate in (("topics", validate_topics), ("content", validate_content), ("outline", validate_outline)):
        if errors := validate(run):
            return steps + [f"{name}: {error}" for error in errors]
    if stage_approval_problem(run, "outline"):
        return steps + [
            (
                "CP0: show the user the outline (segments, timing, visual plans); approve with "
                "`text-2-shorts approve <run> outline`"
            )
        ]
    script_errors = validate_script(run)
    steps += [f"script: {error}" for error in script_errors]
    if not script_errors:
        steps += [f"script critique: {problem}" for problem in critique_problems(run, "script", "script")]
        steps += [f"script review: {problem}" for problem in review_problems(run, "script")]
    if stage_approval_problem(run, "script"):
        steps.append(
            "CP1: show the user the complete script and the accuracy findings; approve with "
            "`text-2-shorts approve <run> script`"
        )
        return steps  # no visual planning before the script is approved
    script = load_script(run)
    plan_errors = [
        f"{scene.scene_id} plan: {error}"
        for scene in (script.scenes if script else [])
        for error in validate_plan(run, scene.scene_id)
    ]
    steps += plan_errors
    steps += [
        f"plan critique: {problem}"
        for scene in (script.scenes if script else [])
        if not validate_plan(run, scene.scene_id)
        for problem in critique_problems(run, scene.scene_id, "plan")
    ]
    if not plan_errors:
        steps += [f"plan review: {problem}" for problem in review_problems(run, "plan")]
    if stage_approval_problem(run, "plan"):
        steps.append(
            "CP2: show the user every scene's visual plan and the accuracy findings; approve with "
            "`text-2-shorts approve <run> plan`"
        )
        return steps  # no voice or clip code before the visual plans are approved
    plans = load_scene_plans(run)
    if stale := stale_audio(run, plans):
        steps.append(f"narration audio missing or outdated for {', '.join(sorted(stale))} (text-2-shorts voice <run>)")
    for plan in plans:
        if any(clip.clip_id in stale for clip in plan.clips):
            continue
        next_clip_id = next(
            (
                clip.clip_id
                for clip in plan.clips
                if (build := state.clips.get(clip.clip_id)) is None or build.key != clip_key(run, plan, clip)
            ),
            None,
        )
        if next_clip_id:
            steps.append(
                f"build {next_clip_id} (text-2-shorts task → clip-builder → text-2-shorts accept), "
                f"then the rest of {plan.scene_id}"
            )
        else:
            steps += preview_problems(run, plan) or [
                f"video critique: {problem}" for problem in critique_problems(run, plan.scene_id, "video")
            ]
        if not is_approval_current(state, f"scene:{plan.scene_id}", fingerprint(run, [plan])):
            steps.append(f"CP3: preview and approve {plan.scene_id}")
            break  # scenes are produced in series: later scenes wait for this one
    if plans:
        current_fingerprint = fingerprint(run, plans)
        report = load_final_report(run)
        if not (run / "final.mp4").exists() or report is None or report.fingerprint != current_fingerprint:
            steps.append("text-2-shorts final <run>")
        elif not is_approval_current(state, "final", current_fingerprint):
            steps.append("CP4: approve the final video")
    return steps


STATUSES = (
    "pending",
    "in_progress",
    "completed",
    "failed",
    "requires_refactoring",
    "requires_user_approval",
    "approved",
)


def compute_statuses(run: Path) -> dict[str, Status]:
    """Every stage, scene and clip as one of STATUSES (PRD §state management), derived from the gates (no writes)."""
    state = load_state(run)
    statuses: dict[str, Status] = {}
    previous_approved = True
    for stage, artifact, validate in (
        ("requirements", "content.md", lambda run: validate_brief(run) + validate_topics(run) + validate_content(run)),
        ("template", "template.json", validate_template),
        ("outline", "outline.json", validate_outline),
        ("script", "script.json", validate_script),
        ("plan", "scenes/s01/plan.json", lambda run: validate_plan(run, "s01")),
    ):
        if not stage_approval_problem(run, stage):
            statuses[stage] = "approved"
        elif not previous_approved or not (run / artifact).exists():
            statuses[stage] = "pending"
        elif validate(run):
            statuses[stage] = "in_progress"
        else:
            statuses[stage] = "requires_refactoring" if approval_problems(run, stage) else "requires_user_approval"
        previous_approved = statuses[stage] == "approved"
    plans = load_scene_plans(run) if previous_approved else []
    for plan in plans:
        clips: list[Status] = []
        for clip in plan.clips:
            build = state.clips.get(clip.clip_id)
            if build is not None and build.status == "FAILED":
                clips.append("failed")
            elif build is None:
                work = run / "scenes" / plan.scene_id / "work" / f"clip_{clip.index:02d}"
                clips.append("in_progress" if work.exists() else "pending")
            else:
                clips.append("completed" if build.key == clip_key(run, plan, clip) else "requires_refactoring")
            statuses[clip.clip_id] = clips[-1]
        if is_approval_current(state, f"scene:{plan.scene_id}", fingerprint(run, [plan])):
            statuses[plan.scene_id] = "approved"
        elif "failed" in clips:
            statuses[plan.scene_id] = "failed"
        elif not approval_problems(run, f"scene:{plan.scene_id}"):
            statuses[plan.scene_id] = "requires_user_approval"
        elif critique_state(run, plan.scene_id, "video") in ("revise", "exhausted"):
            statuses[plan.scene_id] = "requires_refactoring"
        else:
            statuses[plan.scene_id] = "pending" if set(clips) == {"pending"} else "in_progress"
    report = load_final_report(run)
    if plans and is_approval_current(state, "final", fingerprint(run, plans)):
        statuses["final"] = "approved"
    elif plans and report is not None and report.fingerprint == fingerprint(run, plans):
        failed = any(finding.severity == "ERROR" for finding in report.checks)
        statuses["final"] = "failed" if failed else "requires_user_approval"
    else:
        statuses["final"] = "pending"
    return statuses


def update_statuses(run: Path) -> dict[str, Status]:
    """compute_statuses(), saved in state.json under "status"."""
    statuses = compute_statuses(run)
    update_state(run, lambda saved: setattr(saved, "status", statuses))
    return statuses


def status_text(run: Path) -> str:
    state = load_state(run)
    lines = [f"approved: {', '.join(state.approved) or 'nothing yet'}"]
    statuses = update_statuses(run)
    lines.append("status: " + " · ".join(f"{name}: {value}" for name, value in statuses.items()))
    if pending := open_requests(run):
        lines.append("open change requests:\n" + requests_text(pending))
    clips = [(clip.clip_id, state.clips.get(clip.clip_id)) for plan in load_scene_plans(run) for clip in plan.clips]
    if clips:
        lines += ["| clip | status | open findings |", "|---|---|---|"]
        lines += [
            f"| {clip_id} | {build.status if build else 'not built'} | "
            f"{', '.join(build.open_findings if build else [])[:100]} |"
            for clip_id, build in clips
        ]
    steps = next_steps(run)
    lines += (["next:"] + [f"  - {step}" for step in steps]) if steps else ["next: nothing — the video is done."]
    return "\n".join(lines)


def sum_session_tokens(run: Path) -> TokenUsage:
    """Token totals from this run's Claude Code transcripts (recorded by the SessionStart hook), subagents included.
    Streaming writes one transcript line per content block with the same message id — count each message once."""
    totals, seen = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "messages": 0}, set()
    for transcript in load_state(run).sessions:
        transcript_path = Path(transcript)
        for transcript_file in (
            ([transcript_path] + sorted(transcript_path.with_suffix("").glob("**/*.jsonl")))
            if transcript_path.exists()
            else []
        ):
            for line in transcript_file.read_text().splitlines():
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                message = entry.get("message") or {}
                usage = message.get("usage")
                if entry.get("type") != "assistant" or not usage or message.get("id") in seen:
                    continue
                seen.add(message.get("id"))
                totals["input"] += usage.get("input_tokens", 0)
                totals["output"] += usage.get("output_tokens", 0)
                totals["cache_read"] += usage.get("cache_read_input_tokens", 0)
                totals["cache_write"] += usage.get("cache_creation_input_tokens", 0)
                totals["messages"] += 1
    return TokenUsage(**totals)
