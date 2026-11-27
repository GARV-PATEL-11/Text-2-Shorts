"""Claude usage limits as Claude Code itself reports them. Every print-mode turn with stream-json output emits a
`rate_limit_event` whose `unifiedWindows` hold the current session (five_hour) and the weekly windows (seven_day, …):
utilization 0–1 and resetsAt in epoch seconds. The latest is kept in ~/.cache/text-2-shorts/usage.json. Console turns
keep it current; `check()` asks Claude Code once, with a one-line Haiku turn, when the website wants fresher numbers.
"""

from __future__ import annotations

import json
import logging
import subprocess
import threading
import time

from schemas.api import UsageView, UsageWindow

from app.config import USER_CACHE_DIRECTORY
from app.sandbox import usage_check_arguments
from app.utilities import now_text, write_atomic

USAGE_FILE = USER_CACHE_DIRECTORY / "text-2-shorts" / "usage.json"
checking = threading.Lock()  # one probe at a time
log = logging.getLogger(__name__)


def record(event: dict) -> bool:
    """Keeps the windows of a rate_limit_event; any other event is ignored."""
    windows = (
        (event.get("rate_limit_info") or {}).get("unifiedWindows") if event.get("type") == "rate_limit_event" else None
    )
    if not windows:
        return False
    try:  # a unique temporary file per write (two turns at once), and a failure never stops the turn (L6)
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        write_atomic(USAGE_FILE, json.dumps({"checked_at": now_text(), "windows": windows}))
    except OSError:
        log.exception("usage limits not kept")
        return False
    return True


def window_over(percent: float) -> tuple[UsageWindow, str | None] | None:
    """The fullest usage window at `percent` or more that has not reset since it was read (and when it was read)."""
    view = latest()
    full = [window for window in view.windows if window.used_percent >= percent and window.resets_at > time.time()]
    return (max(full, key=lambda window: window.used_percent), view.checked_at) if full else None


def latest(plan: str = "") -> UsageView:
    try:
        kept = json.loads(USAGE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return UsageView(plan=plan)
    windows = [
        UsageWindow(
            id=name,
            used_percent=round(float(window.get("utilization", 0)) * 100, 1),
            resets_at=int(window.get("resetsAt", 0)),
            status=str(window.get("status", "allowed")),
        )
        for name, window in kept.get("windows", {}).items()
    ]
    return UsageView(plan=plan, checked_at=kept.get("checked_at"), windows=windows)


def probe() -> str:
    """One tiny Claude Code turn, for its rate_limit_event (run outside any project, so no CLAUDE.md is loaded)."""
    USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    done = subprocess.run(usage_check_arguments(), cwd=USAGE_FILE.parent, capture_output=True, text=True, timeout=120)
    return done.stdout


def check() -> None:
    """Fresh numbers from Claude Code; a check already running is not repeated."""
    if not checking.acquire(blocking=False):
        return
    try:
        lines = probe().splitlines()
        if not any(record(json.loads(line)) for line in lines if line.startswith("{")):
            log.warning("usage check: Claude Code reported no rate_limit_event")
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as problem:
        log.warning("usage check failed: %s", problem)
    finally:
        checking.release()
