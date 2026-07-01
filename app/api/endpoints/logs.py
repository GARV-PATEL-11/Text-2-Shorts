"""logs.py — Endpoints for reading session structured logs and computing analytics."""
from __future__ import annotations

import json
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query


router = APIRouter()

_SESSIONS_DIR = os.path.join("logs", "sessions")


def _load_entries(
        session_id: str,
        level: str = "",
        stage: str = "",
        node: str = "",
        search: str = "",
        limit: int = 500,
        offset: int = 0,
        ) -> tuple[list[dict], int]:
    """Read, filter, and paginate log entries for a session."""
    log_path = os.path.join(_SESSIONS_DIR, f"{session_id}.jsonl")
    if not os.path.exists(log_path):
        return [], 0

    entries: list[dict] = []
    try:
        with open(log_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if level and level != "ALL":
                    if entry.get("level", "").upper() != level.upper():
                        continue
                if stage:
                    if stage.lower() not in entry.get("stage", "").lower():
                        continue
                if node:
                    if node.lower() not in entry.get("node", "").lower():
                        continue
                if search:
                    if search.lower() not in json.dumps(entry).lower():
                        continue

                entries.append(entry)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Error reading logs: {exc}") from exc

    total = len(entries)
    return entries[offset: offset + limit], total


@router.get("/logs/{session_id}")
async def get_session_logs(
        session_id: str,
        level: Optional[str] = Query(None),
        stage: Optional[str] = Query(None),
        node: Optional[str] = Query(None),
        search: Optional[str] = Query(None),
        limit: int = Query(500, le=2000),
        offset: int = Query(0, ge=0),
        ) -> dict:
    """Return structured log entries for a session with optional filtering."""
    entries, total = _load_entries(
        session_id,
        level=level or "",
        stage=stage or "",
        node=node or "",
        search=search or "",
        limit=limit,
        offset=offset,
        )
    return {
        "session_id": session_id,
        "total": total,
        "entries": entries,
        "has_more": total > offset + limit,
        }


@router.get("/logs/{session_id}/analytics")
async def get_session_analytics(session_id: str) -> dict:
    """Compute per-session analytics from the structured log file."""
    entries, _ = _load_entries(session_id, limit=10000)

    llm_calls: list[dict] = []
    errors: list[dict] = []
    model_stats: dict[str, dict] = {}

    for entry in entries:
        event = entry.get("event", "")
        level = entry.get("level", "")
        details = entry.get("details", {}) or {}

        # LLM events
        if "llm" in str(event).lower():
            model = entry.get("model") or details.get("model") or "unknown"
            provider = entry.get("provider") or details.get("provider") or "unknown"
            input_tokens = int(entry.get("input_tokens") or details.get("input_tokens") or 0)
            output_tokens = int(entry.get("output_tokens") or details.get("output_tokens") or 0)
            duration_ms = float(entry.get("duration_ms") or 0)
            attempt = int(entry.get("attempt") or details.get("attempt") or 1)

            llm_calls.append({
                "model": model,
                "provider": provider,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "duration_ms": duration_ms,
                "attempt": attempt,
                },
                )

            if model and model != "unknown":
                if model not in model_stats:
                    model_stats[model] = {
                        "provider": provider,
                        "requests": 0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_latency_ms": 0.0,
                        "retries": 0,
                        }
                model_stats[model]["requests"] += 1
                model_stats[model]["input_tokens"] += input_tokens
                model_stats[model]["output_tokens"] += output_tokens
                model_stats[model]["total_latency_ms"] += duration_ms
                if attempt > 1:
                    model_stats[model]["retries"] += 1

        # Error events
        if str(level).upper() in ("ERROR", "CRITICAL"):
            errors.append({
                "timestamp": entry.get("timestamp", ""),
                "stage": entry.get("stage", ""),
                "node": entry.get("node", ""),
                "error_type": details.get("error_type", ""),
                "message": details.get("message", str(details)[:200]),
                },
                )

    total_input = sum(c["input_tokens"] for c in llm_calls)
    total_output = sum(c["output_tokens"] for c in llm_calls)
    latencies = [c["duration_ms"] for c in llm_calls if c["duration_ms"]]
    retries = sum(1 for c in llm_calls if c.get("attempt", 1) > 1)
    fallbacks = sum(1 for e in entries if "fallback" in str(e.get("event", "")).lower())

    model_summary = [
        {
            "model": model,
            "provider": stats["provider"],
            "requests": stats["requests"],
            "input_tokens": stats["input_tokens"],
            "output_tokens": stats["output_tokens"],
            "total_tokens": stats["input_tokens"] + stats["output_tokens"],
            "avg_latency_ms": round(
                stats["total_latency_ms"] / stats["requests"], 1,
                ) if stats["requests"] else 0.0,
            "retries": stats["retries"],
            }
        for model, stats in model_stats.items()
        ]

    return {
        "session_id": session_id,
        "analytics": {
            "total_llm_calls": len(llm_calls),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_errors": len(errors),
            "total_retries": retries,
            "total_fallbacks": fallbacks,
            "avg_llm_latency_ms": round(
                sum(latencies) / len(latencies), 1,
                ) if latencies else 0.0,
            "max_llm_latency_ms": round(max(latencies), 1) if latencies else 0.0,
            "min_llm_latency_ms": round(min(latencies), 1) if latencies else 0.0,
            "model_usage": model_summary,
            "errors": errors[:25],
            },
        }
