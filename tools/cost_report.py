#!/usr/bin/env python3
"""cost_report.py — baseline & regression report from runs/<id>/log.jsonl.

Works on the log format the EXISTING app already writes (pipeline.claude():
ts, stage, scene, model, effort, attempt, ok, cost_usd, duration_ms, cache_read, cache_write, error),
on the current format (start/end rows; end rows add success, input/output/thinking tokens, api_ms, turns, …),
and on the proposed format (adds clip, prompt_id, input_tokens, output_tokens, cache_hit).
Phase 0 of the roadmap runs this on existing runs to get the baseline that every PROVISIONAL target
in Plan.md is later replaced with.

Usage: python tools/cost_report.py runs/<id>/log.jsonl [more logs...] [--json]
Status: IMPLEMENTED.
"""
from __future__ import annotations
import argparse, json
from collections import defaultdict
from pathlib import Path


def summarize(paths: list[Path]) -> dict:
    rows = [json.loads(l) for p in paths for l in p.read_text().splitlines() if l.strip()]
    rows = [r for r in rows if r.get("event") != "start" and r.get("status") != "started"]  # start rows carry no result
    for r in rows:
        r.setdefault("ok", r.get("success"))  # pipeline now logs "success"; older logs used "ok"
    by = defaultdict(lambda: {"calls": 0, "failed": 0, "retries": 0, "cost_usd": 0.0, "ms": 0,
                              "cache_read": 0, "cache_write": 0, "input_tokens": 0, "output_tokens": 0,
                              "artifact_cache_hits": 0})
    for r in rows:
        s = by[r.get("stage", "?")]
        s["calls"] += 1
        s["failed"] += 0 if r.get("ok") else 1
        s["retries"] += 1 if (r.get("attempt") or 1) > 1 else 0
        s["cost_usd"] += r.get("cost_usd") or 0.0
        s["ms"] += r.get("duration_ms") or 0
        s["cache_read"] += r.get("cache_read") or 0
        s["cache_write"] += r.get("cache_write") or 0
        s["input_tokens"] += r.get("input_tokens") or 0
        s["output_tokens"] += r.get("output_tokens") or 0
        s["artifact_cache_hits"] += 1 if r.get("cache_hit") else 0
    for s in by.values():
        tot = s["cache_read"] + s["cache_write"]
        s["prompt_cache_read_ratio"] = round(s["cache_read"] / tot, 3) if tot else None
        s["cost_usd"] = round(s["cost_usd"], 4)
    total = round(sum(s["cost_usd"] for s in by.values()), 4)
    units = {r.get("clip") or r.get("scene") for r in rows if r.get("stage") in {"scene", "scene_retry", "clip_build"}}
    units.discard(None)
    return {"runs": len(paths), "calls": len(rows), "total_cost_usd": total,
            "first_attempt_success": round(sum(1 for r in rows if r.get("ok") and (r.get("attempt") or 1) == 1) / max(1, len(rows)), 3),
            "render_units": len(units),
            # all-in: every LLM call of the run divided by rendered units (scenes today, clips after refactor)
            "cost_per_render_unit": round(total / len(units), 4) if units else None,
            # render-only: just the render/build agent sessions per unit
            "render_cost_per_unit": round(sum(by[k]["cost_usd"] for k in ("scene", "scene_retry", "clip_build") if k in by)
                                          / len(units), 4) if units else None,
            "stages": dict(sorted(by.items(), key=lambda kv: -kv[1]["cost_usd"]))}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("logs", nargs="+", type=Path); ap.add_argument("--json", action="store_true")
    a = ap.parse_args(); r = summarize(a.logs)
    if a.json:
        print(json.dumps(r, indent=1)); return
    print(f"{r['runs']} run(s) · {r['calls']} calls · ${r['total_cost_usd']} · first-attempt success {r['first_attempt_success']}"
          f" · cost/render unit {r['cost_per_render_unit']}")
    print(f"{'stage':18}{'calls':>6}{'fail':>5}{'retry':>6}{'cost $':>9}{'sec':>8}{'in tok':>10}{'out tok':>9}{'cache rd':>10}{'cache wr':>10}{'read%':>7}")
    for k, s in r["stages"].items():
        cr = "-" if s["prompt_cache_read_ratio"] is None else f"{100 * s['prompt_cache_read_ratio']:.0f}%"
        print(f"{k:18}{s['calls']:>6}{s['failed']:>5}{s['retries']:>6}{s['cost_usd']:>9.3f}{s['ms'] / 1000:>8.0f}"
              f"{s['input_tokens']:>10}{s['output_tokens']:>9}{s['cache_read']:>10}{s['cache_write']:>10}{cr:>7}")


if __name__ == "__main__":
    main()
