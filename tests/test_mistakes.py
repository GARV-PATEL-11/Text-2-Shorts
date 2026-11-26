"""The mistake log: every judgement of an agent's output, over every run, grouped so repeating mistakes stand out."""

import json
from pathlib import Path

from app.workflow import change_requests, critiques, mistakes
from conftest import critique_issue, write_brief, write_json_file
from schemas.reviews import MistakeIssue


def two_runs_with_the_same_plan_mistake(runs: Path) -> list[Path]:
    made = []
    for name in ("20261126-100000-a", "20261126-110000-b"):
        run = runs / name
        write_brief(run)
        issue = critique_issue("plan", "s01c01", "basic", "P-B2", "clarity")
        rounds = [
            {"reviewed": f"v{n}", "verdict": "revise", "score": 75, "summary": "s", "issues": [issue]} for n in (1, 2)
        ]  # the refactor between the rounds did not fix it
        write_json_file(run / "scenes" / "s01" / "plan_critique.json", {"rounds": rounds})
        made.append(run)
    return made


def test_the_report_finds_what_repeats_across_runs_and_survives_a_fix(tmp_path):
    first, second = two_runs_with_the_same_plan_mistake(tmp_path)
    issue = MistakeIssue(code="layout: OVERLAP", severity="ERROR", target="s01", problem="layout: OVERLAP")
    for attempt in (1, 2, 3):
        mistakes.record(first, "build", "scene-builder", "s01", [issue], attempt)
    mistakes.record_invalid(first, first / "outline.json", ["outline.json: segment 2 runs 12 s over its stage"])
    change_requests.add_request(second, "s01c01", "visual", "the arrow is too small")

    report = mistakes.build_report(tmp_path)
    by_code = {(p.agent, p.code): p for p in report.patterns}
    plan = by_code[("scene-planner", "P-B2 clarity")]
    assert (plan.count, plan.runs, plan.recurred) == (4, 2, 2)  # in both runs, and still there after each refactor
    build = by_code[("scene-builder", "layout: OVERLAP")]
    assert (build.count, build.recurred) == (3, 2)
    assert ("script-writer", "outline.json: segment N runs N s over its stage") in by_code  # numbers grouped away
    assert ("scene-builder", "user asked: visual") in by_code
    assert {p.code for p in report.prompt_candidates} == {"P-B2 clarity", "layout: OVERLAP"}
    assert report.gave_up == [f"{first.name} · build · s01"]

    json_path, markdown_path = mistakes.write_report(tmp_path, tmp_path / "reports")
    assert json.loads(json_path.read_text())["mistakes"] == report.mistakes
    text = markdown_path.read_text()
    assert "## Prompt candidates" in text and "### scene-planner" in text and "`P-B2 clarity`" in text


def test_a_video_round_is_linked_to_the_refactor_that_followed_it(tmp_path):
    run = tmp_path / "20261126-120000-c"
    write_brief(run)
    issue = critique_issue("video", "s01c01", "basic")
    rounds = [{"reviewed": "v1", "verdict": "revise", "score": 75, "summary": "s", "issues": [issue]}]
    write_json_file(run / "scenes" / "s01" / "video_critique.json", {"rounds": rounds})
    change = {"target": "s01c01", "iteration": 1, "issue": "i", "findings": ["f"], "modification": "named the object",
              "validation_results": "accept READY"}  # fmt: skip
    write_json_file(run / "scenes" / "s01" / "changes.json", {"entries": [change]})
    [event] = [event for event in mistakes.run_events(run) if event.loop == "critique:video"]
    assert (event.agent, event.refactor, event.outcome) == ("scene-builder", "named the object", "fail")
    assert critiques.CRITICS["video"] == "video-critic"  # the critic judges; the builder owns the fix
