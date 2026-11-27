"""Small helpers shared by every module: JSON files, hashing, timestamps, JSONL, ffprobe, a thread pool, and pydantic
error formatting."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from app.config import MAX_PARALLEL_RENDERS

log = logging.getLogger(__name__)


def read_json(path: Path):
    """The file's JSON, or None when it is missing or cannot be parsed (an agent mid-write, a trailing comma): every
    caller treats that as "not there yet", so one bad file never breaks a whole view."""
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, ValueError):
        return None


def write_atomic(path: Path, text: str) -> None:
    """Write through a temporary file beside it, then rename: a reader (the website polls) or a crash never sees a
    half-written file, and a failed write leaves the old one whole."""
    with tempfile.NamedTemporaryFile(
        "w", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as file:
        file.write(text)
    try:
        os.replace(file.name, path)
    except BaseException:
        Path(file.name).unlink(missing_ok=True)
        raise


def run_or_explain(argv: list, what: str, **options) -> subprocess.CompletedProcess:
    """Run a tool; if it fails, stop with what failed and the end of its stderr (never a bare CalledProcessError)."""
    done = subprocess.run(argv, capture_output=True, text=True, **options)
    if done.returncode != 0:
        tail = (done.stderr or "").strip()[-1500:]
        log.error("%s failed (exit %s): %s", what, done.returncode, tail)
        raise SystemExit(f"{what} failed (exit {done.returncode}):\n{tail}")
    return done


def write_json(path: Path, data) -> None:
    write_atomic(path, json.dumps(data, indent=2, ensure_ascii=False))


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
    """Every readable line; a torn line (an append cut off) is logged and skipped, never fatal."""
    entries = []
    for number, line in enumerate(path.read_text().splitlines() if path.exists() else [], 1):
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except ValueError:
            log.warning("%s line %d is not JSON, skipped: %.120s", path, number, line)
    return entries


def now_text() -> str:
    return datetime.now().isoformat(timespec="seconds")


def format_validation_errors(validation_error: ValidationError) -> list[str]:
    return [f"{'.'.join(map(str, error['loc']))}: {error['msg']}" for error in validation_error.errors()]


# One line for a person at the end of the human-facing commands (serve, new, final, --help). Never on a command
# whose output a test, script or Claude parses (approve, validate, hash, status, next).
CLI_QUOTES = {
    "serve": [
        "Curiosity, Illustrated.",
        '"I have arranged certain apparatus, the use of which you will see as I go on." — Michael Faraday',
        '"But first let us see that our instrument is in order." — Michael Faraday',
        '"Hello and, again, welcome to the Aperture Science computer-aided enrichment center." — Portal',
    ],
    "new": [
        '"Make it so!" — Star Trek: The Next Generation',
        '"let us make an experiment or two." — Michael Faraday',
    ],
    "final": [
        '"Work, Finish, Publish." — Michael Faraday',
        '"Yes! We have proved it by combustion" — Michael Faraday',
        '"We\'re made of star-stuff. We are a way for the cosmos to know itself." — Carl Sagan',
    ],
    "help": [
        "Curiosity, Illustrated.",
        '"What I cannot create, I do not understand." — Richard Feynman',
        '"I am no poet, but if you think for yourselves, as I proceed, the facts will form a poem in your minds." — Michael Faraday',
    ],
}


def cli_quote(moment: str) -> str:
    return random.choice(CLI_QUOTES[moment])
