"""Small helpers shared by every module: JSON files, hashing, timestamps, JSONL, ffprobe, a thread pool, and pydantic
error formatting."""

from __future__ import annotations

import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from app.config import MAX_PARALLEL_RENDERS


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def probe_duration_seconds(path: Path) -> float:
    ffprobe_output = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return float(ffprobe_output.strip())


def run_in_parallel(function, items):
    with ThreadPoolExecutor(MAX_PARALLEL_RENDERS) as executor:
        return list(executor.map(function, items))


def content_hash(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:16]


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def now_text() -> str:
    return datetime.now().isoformat(timespec="seconds")


def format_validation_errors(validation_error: ValidationError) -> list[str]:
    return [f"{'.'.join(map(str, error['loc']))}: {error['msg']}" for error in validation_error.errors()]
