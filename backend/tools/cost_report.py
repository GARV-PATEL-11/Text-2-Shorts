#!/usr/bin/env python3
"""cost_report.py — baseline & regression report from artifacts/runs/<id>/log.jsonl.

Works on the log format the EXISTING app already writes (pipeline.claude():
ts, stage, scene, model, effort, attempt, ok, cost_usd, duration_ms, cache_read, cache_write, error),
on the current format (start/end rows; end rows add success, input/output/thinking tokens, api_ms, turns, …),
and on the proposed format (adds clip, prompt_id, input_tokens, output_tokens, cache_hit).
Phase 0 of the roadmap runs this on existing runs to get the baseline that every PROVISIONAL target
in docs/history/architecture-plan.md is later replaced with.

Usage: python backend/tools/cost_report.py artifacts/runs/<id>/log.jsonl [more logs...] [--json]
Status: IMPLEMENTED.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def summarize(paths: list[Path]) -> dict:
    rows = [json.loads(line) for path in paths for line in path.read_text().splitlines() if line.strip()]
    rows = [
        row for row in rows if row.get("event") != "start" and row.get("status") != "started"
    ]  # start rows carry no result
    for row in rows:
        row.setdefault("ok", row.get("success"))  # pipeline now logs "success"; older logs used "ok"
    stages = defaultdict(
        lambda: {
            "calls": 0,
            "failed": 0,
            "retries": 0,
            "cost_usd": 0.0,
            "ms": 0,
            "cache_read": 0,
            "cache_write": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "artifact_cache_hits": 0,
        }
    )
    for row in rows:
        stage_totals = stages[row.get("stage", "?")]
        stage_totals["calls"] += 1
        stage_totals["failed"] += 0 if row.get("ok") else 1
        stage_totals["retries"] += 1 if (row.get("attempt") or 1) > 1 else 0
        stage_totals["cost_usd"] += row.get("cost_usd") or 0.0
        stage_totals["ms"] += row.get("duration_ms") or 0
        stage_totals["cache_read"] += row.get("cache_read") or 0
        stage_totals["cache_write"] += row.get("cache_write") or 0
        stage_totals["input_tokens"] += row.get("input_tokens") or 0
        stage_totals["output_tokens"] += row.get("output_tokens") or 0
        stage_totals["artifact_cache_hits"] += 1 if row.get("cache_hit") else 0
    for stage_totals in stages.values():
        cache_total = stage_totals["cache_read"] + stage_totals["cache_write"]
        stage_totals["prompt_cache_read_ratio"] = (
            round(stage_totals["cache_read"] / cache_total, 3) if cache_total else None
        )
        stage_totals["cost_usd"] = round(stage_totals["cost_usd"], 4)
    total = round(sum(stage_totals["cost_usd"] for stage_totals in stages.values()), 4)
    units = {
        row.get("clip") or row.get("scene")
        for row in rows
        if row.get("stage") in {"scene", "scene_retry", "clip_build"}
    }
    units.discard(None)
    return {
        "runs": len(paths),
        "calls": len(rows),
        "total_cost_usd": total,
        "first_attempt_success": round(
            sum(1 for row in rows if row.get("ok") and (row.get("attempt") or 1) == 1) / max(1, len(rows)), 3
        ),
        "render_units": len(units),
        # all-in: every LLM call of the run divided by rendered units (scenes today, clips after refactor)
        "cost_per_render_unit": round(total / len(units), 4) if units else None,
        # render-only: just the render/build agent sessions per unit
        "render_cost_per_unit": round(
            sum(
                stages[stage_name]["cost_usd"]
                for stage_name in ("scene", "scene_retry", "clip_build")
                if stage_name in stages
            )
            / len(units),
            4,
        )
        if units
        else None,
        "stages": dict(sorted(stages.items(), key=lambda item: -item[1]["cost_usd"])),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("logs", nargs="+", type=Path)
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args()
    report = summarize(arguments.logs)
    if arguments.json:
        print(json.dumps(report, indent=1))
        return
    print(
        f"{report['runs']} run(s) · {report['calls']} calls · ${report['total_cost_usd']} "
        f"· first-attempt success {report['first_attempt_success']}"
        f" · cost/render unit {report['cost_per_render_unit']}"
    )
    print(
        f"{'stage':18}{'calls':>6}{'fail':>5}{'retry':>6}{'cost $':>9}{'sec':>8}"
        f"{'in tok':>10}{'out tok':>9}{'cache rd':>10}{'cache wr':>10}{'read%':>7}"
    )
    for stage_name, stage_totals in report["stages"].items():
        cache_read_share = (
            "-"
            if stage_totals["prompt_cache_read_ratio"] is None
            else f"{100 * stage_totals['prompt_cache_read_ratio']:.0f}%"
        )
        print(
            f"{stage_name:18}{stage_totals['calls']:>6}{stage_totals['failed']:>5}{stage_totals['retries']:>6}"
            f"{stage_totals['cost_usd']:>9.3f}{stage_totals['ms'] / 1000:>8.0f}"
            f"{stage_totals['input_tokens']:>10}{stage_totals['output_tokens']:>9}{stage_totals['cache_read']:>10}{stage_totals['cache_write']:>10}{cache_read_share:>7}"
        )


if __name__ == "__main__":
    main()
