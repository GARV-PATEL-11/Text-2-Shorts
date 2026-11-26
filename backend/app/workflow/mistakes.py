"""The mistake log: every judgement of an agent's output, so repeating mistakes can be fixed in the agents' prompts.

Per run, mistakes.jsonl keeps the judgements that are otherwise overwritten: each accuracy review, each `accept` (the
build's gates), each preview's sync and each file that failed validation. Critique rounds (all kept in their files),
refactors (changes.json) and the user's change requests (requests.jsonl) are read where they live. `text-2-shorts
mistakes` reads every run and writes artifacts/reports/mistakes.json and mistakes.md: what each agent gets wrong, what
was still wrong after a refactor, which loops gave up, and the patterns worth fixing in a prompt."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from pydantic import ValidationError
from schemas.interaction import TrackedRequest
from schemas.reviews import ChangeLog, Critique, MistakeEvent, MistakeIssue, MistakePattern, MistakeReport

from app.config import MAX_ATTEMPTS, MAX_CRITIQUE_ROUNDS
from app.utilities import now_text, read_jsonl
from app.workflow.ledger import append_jsonl

LOG = "mistakes.jsonl"
CRITIC_OF = {"script": "script-writer", "plan": "scene-planner", "video": "scene-builder"}  # whose output each judges
WRITER_OF = {  # a file that failed validation → the agent that writes it
    "outline.json": "script-writer",
    "script.json": "script-writer",
    "plan.json": "scene-planner",
    "script_critique.json": "script-critic",
    "plan_critique.json": "plan-critic",
    "video_critique.json": "video-critic",
    "script_review.json": "accuracy-reviewer",
    "plan_review.json": "accuracy-reviewer",
}
REQUEST_OWNER = {"wording": "script-writer", "accuracy": "script-writer", "structure": "script-writer",
                 "audio-timing": "audio-refactorer"}  # fmt: skip


def record(run: Path, loop: str, agent: str, target: str, issues: list[MistakeIssue], attempt: int | None = None):
    """Append one judgement to the run's mistakes.jsonl (a pass when nothing was found)."""
    event = MistakeEvent(
        ts=now_text(), loop=loop, agent=agent, target=target, outcome="fail" if issues else "pass",
        attempt=attempt, issues=issues,
    )  # fmt: skip
    append_jsonl(run, LOG, event)


def record_invalid(run: Path, file: Path, errors: list[str]) -> None:
    """A file an agent (or the session) wrote that failed its validation."""
    agent = WRITER_OF.get(file.name, "session")
    issues = [MistakeIssue(code=validation_code(error), severity="ERROR", target=file.name, problem=error)
              for error in errors]  # fmt: skip
    record(run, "validation", agent, str(file.relative_to(run)) if file.is_relative_to(run) else file.name, issues)


def validation_code(error: str) -> str:
    """The rule an error broke, without the numbers and quoted values that differ every time."""
    rule = re.sub(r"'[^']*'|\"[^\"]*\"", "…", error.split(" — ")[0])
    return re.sub(r"\d+(\.\d+)?", "N", rule)[:90]


def sync_code(problem: str) -> str:
    if "runs past" in problem:
        return "sync: voice longer than its animation"
    return f"sync: beat shown {'after' if ' after ' in problem else 'before'} it is said"


# ── reading every judgement of a run ────────────────────────────────────────────────────────────────────────


def run_events(run: Path) -> list[MistakeEvent]:
    """The run's logged judgements, its critique rounds (each linked to the refactor that followed it) and its
    change requests, oldest first within each target."""
    events = []
    for row in read_jsonl(run / LOG):
        try:
            events.append(MistakeEvent.model_validate(row))
        except ValidationError:
            continue
    critique_files = [(run / "script_critique.json", "script", "script")] + [
        (path, path.parent.name, path.name.split("_")[0]) for path in sorted(run.glob("scenes/s*/*_critique.json"))
    ]
    for path, target, kind in critique_files:
        try:
            rounds = Critique.model_validate_json(path.read_text()).rounds if path.exists() else []
            changes = (
                ChangeLog.model_validate_json((path.parent / "changes.json").read_text()).entries
                if (kind == "video" and (path.parent / "changes.json").exists())
                else []
            )
        except ValidationError:
            continue
        for number, critique_round in enumerate(rounds, 1):
            refactor = "; ".join(change.modification for change in changes if change.iteration == number)
            events.append(MistakeEvent(
                ts="", loop=f"critique:{kind}", agent=CRITIC_OF[kind], target=target,
                outcome="pass" if critique_round.verdict == "pass" else "fail", attempt=number, refactor=refactor,
                issues=[MistakeIssue(code=f"{issue.criterion} {issue.aspect}", severity=issue.tier,
                                     target=issue.target, problem=issue.problem, fix=issue.fix)
                        for issue in critique_round.issues],
            ))  # fmt: skip
    for row in read_jsonl(run / "requests.jsonl"):
        if row.get("event") != "request":
            continue
        request = TrackedRequest.model_validate({key: value for key, value in row.items() if key != "event"})
        clip = re.fullmatch(r"s\d{2}c\d{2}", request.target)
        owner = REQUEST_OWNER.get(request.kind) or (
            ("scene-builder" if clip else "scene-planner") if request.kind == "visual" else "session"
        )
        events.append(MistakeEvent(
            ts=request.created_at, loop="request", agent=owner, target=request.target, outcome="fail",
            issues=[MistakeIssue(code=f"user asked: {request.kind}", severity=request.kind, target=request.target,
                                 problem=request.text)],
        ))  # fmt: skip
    return events


# ── the report over every run ───────────────────────────────────────────────────────────────────────────────


def build_report(runs_directory: Path) -> MistakeReport:
    runs = sorted(path for path in runs_directory.iterdir() if path.is_dir() and not path.name.startswith("."))
    counts: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"count": 0, "runs": set(), "recurred": 0, "loops": set(), "examples": []}
    )
    judgements = mistakes = 0
    gave_up = []
    for run in runs:
        history: dict[tuple[str, str], set[tuple[str, str]]] = {}  # (loop, target) → the last judgement's mistakes
        for event in run_events(run):
            judgements += 1
            if (
                event.loop.startswith("critique:")
                and event.outcome == "fail"
                and event.attempt == MAX_CRITIQUE_ROUNDS
                or event.outcome == "fail"
                and (event.attempt or 0) >= MAX_ATTEMPTS
            ):
                gave_up.append(f"{run.name} · {event.loop} · {event.target}")
            found = {(issue.code, issue.target) for issue in event.issues}
            before = history.get((event.loop, event.target), set())
            history[(event.loop, event.target)] = found
            for issue in event.issues:
                mistakes += 1
                pattern = counts[(event.agent, issue.code)]
                pattern["count"] += 1
                pattern["runs"].add(run.name)
                pattern["loops"].add(event.loop)
                pattern["recurred"] += (issue.code, issue.target) in before  # a refactor in between did not fix it
                if len(pattern["examples"]) < 3:
                    pattern["examples"].append(
                        f"{run.name} · {issue.target}: {issue.problem}" + (f" → {issue.fix}" if issue.fix else "")
                    )
    patterns = sorted(
        (
            MistakePattern(agent=agent, code=code, count=value["count"], runs=len(value["runs"]),
                           recurred=value["recurred"], loops=sorted(value["loops"]), examples=value["examples"])
            for (agent, code), value in counts.items()
        ),
        key=lambda pattern: (-pattern.runs, -pattern.recurred, -pattern.count, pattern.agent, pattern.code),
    )  # fmt: skip
    return MistakeReport(
        generated_at=now_text(), runs=len(runs), judgements=judgements, mistakes=mistakes,
        gave_up=sorted(set(gave_up)), patterns=patterns,
        prompt_candidates=[pattern for pattern in patterns if pattern.runs >= 2 or pattern.recurred >= 2],
    )  # fmt: skip


def report_markdown(report: MistakeReport) -> str:
    def table(patterns: list[MistakePattern]) -> list[str]:
        rows = ["| mistake | times | runs | still there after a fix | loops | example |", "|---|---|---|---|---|---|"]
        rows += [
            f"| `{p.code}` | {p.count} | {p.runs} | {p.recurred} | {', '.join(p.loops)} | "
            + (p.examples[0].replace("|", "\\|")[:160] if p.examples else "")
            + " |"
            for p in patterns
        ]
        return rows

    lines = [
        "# Agent mistakes",
        "",
        f"{report.generated_at} · {report.runs} runs · {report.judgements} judgements · {report.mistakes} mistakes",
        "",
        "Every judgement of an agent's output: critique rounds, accuracy reviews, build gates, sync checks, files",
        "that failed validation, and the user's change requests. \"Still there after a fix\" counts a mistake found",
        "again in the next judgement of the same target. Fix the prompt candidates in the agent's prompt",
        "(`runtime-environment/agents/<agent>.md`) or in the references it reads, then watch their counts fall.",
        "",
        "## Prompt candidates",
        "",
        "In 2+ runs, or still there after 2+ fixes.",
        "",
    ]
    if report.prompt_candidates:
        for agent in dict.fromkeys(p.agent for p in report.prompt_candidates):
            lines += [f"### {agent}", "", *table([p for p in report.prompt_candidates if p.agent == agent]), ""]
            for p in (p for p in report.prompt_candidates if p.agent == agent):
                lines += [f"- `{p.code}`:", *(f"  - {example}" for example in p.examples)]
            lines.append("")
    else:
        lines += ["None yet.", ""]
    lines += ["## Loops that gave up", ""]
    lines += [f"- {item}" for item in report.gave_up] or ["None."]
    lines += ["", "## Every mistake, by agent", ""]
    for agent in sorted({p.agent for p in report.patterns}):
        lines += [f"### {agent}", "", *table([p for p in report.patterns if p.agent == agent]), ""]
    return "\n".join(lines) + "\n"


def write_report(runs_directory: Path, out_directory: Path) -> tuple[Path, Path]:
    report = build_report(runs_directory)
    out_directory.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = out_directory / "mistakes.json", out_directory / "mistakes.md"
    json_path.write_text(report.model_dump_json(indent=2) + "\n")
    markdown_path.write_text(report_markdown(report))
    return json_path, markdown_path
