"""Logging for all three parts of Faraday, in one format:

- backend   — the web server (requests, problems, writes): artifacts/logs/backend.log
- frontend  — what the browser reports (errors, failed requests, actions), via POST /api/logs: artifacts/logs/frontend.log
- runtime   — the run environment: commands the run session calls, hooks, preview renders. With a run, in that run's
              own logs/runtime.log (the session's jail can write only there); without one, artifacts/logs/runtime.log

Each line: `2026-11-24 18:13:02.123 INFO    backend  app.web.app  message`. Files rotate at 5 MB, three kept.
TEXT_2_SHORTS_LOG_LEVEL sets the level (default INFO); TEXT_2_SHORTS_LOG_DIR moves artifacts/logs. A file that cannot
be opened (a read-only place) is skipped: logging never stops the work.
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIRECTORY = Path(
    os.environ.get("TEXT_2_SHORTS_LOG_DIR") or Path(__file__).resolve().parent.parent / "artifacts" / "logs"
)
FORMAT = "%(asctime)s.%(msecs)03d %(levelname)-7s %(component)-8s %(name)s  %(message)s"
DATE = "%Y-%m-%d %H:%M:%S"


class _Component(logging.Filter):
    def __init__(self, component: str):
        super().__init__()
        self.component = component

    def filter(self, record: logging.LogRecord) -> bool:
        record.component = getattr(record, "component", self.component)
        return True


def log_file(component: str, run: Path | None = None) -> Path:
    return (
        (run / "logs" / "runtime.log")
        if run is not None and component == "runtime"
        else LOG_DIRECTORY / f"{component}.log"
    )


def configure(component: str, run: Path | None = None, *, console: bool = True) -> Path | None:
    """Send every logger to stderr and to the component's file; returns the file, or None when it cannot be written.
    Calling it again replaces the earlier set-up (one process, one component)."""
    root = logging.getLogger()
    root.setLevel(os.environ.get("TEXT_2_SHORTS_LOG_LEVEL", "INFO").upper())
    for handler in list(root.handlers):
        if getattr(handler, "_faraday", False):
            root.removeHandler(handler)
            handler.close()
    formatter = logging.Formatter(FORMAT, DATE)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)] if console else []
    path: Path | None = log_file(component, run)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(RotatingFileHandler(path, maxBytes=5_000_000, backupCount=3, encoding="utf-8"))
    except OSError:
        path = None
    for handler in handlers:
        handler._faraday = True  # type: ignore[attr-defined]
        handler.setFormatter(formatter)
        handler.addFilter(_Component(component))
        root.addHandler(handler)
    for noisy in ("httpx", "httpcore", "PIL", "matplotlib", "multipart", "manim"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return path


def channel(component: str) -> logging.Logger:
    """A logger of its own file, beside the process's own (the server writes what the browser reports to
    frontend.log, not backend.log)."""
    logger = logging.getLogger(f"faraday.{component}")
    if not logger.handlers:
        logger.propagate = False
        logger.setLevel(logging.DEBUG)
        try:
            LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
            handler: logging.Handler = RotatingFileHandler(
                LOG_DIRECTORY / f"{component}.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"
            )
        except OSError:
            handler = logging.NullHandler()
        handler.setFormatter(logging.Formatter(FORMAT, DATE))
        handler.addFilter(_Component(component))
        logger.addHandler(handler)
    return logger
