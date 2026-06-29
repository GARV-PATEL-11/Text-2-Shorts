"""logging_service.py — Centralized logging service.

All structured logs are funnelled through LoggingService.emit(), which:
  1. Validates the entry against its schema (Pydantic guarantees this at
     construction time; emit() just serialises and routes).
  2. Writes to  logs/structured.jsonl  — the global append-only event log.
  3. Writes to  logs/sessions/{session_id}.jsonl  when session_id is set.
  4. Forwards to the stdlib logging layer for terminal output.

The service is a process-level singleton. Thread safety is guaranteed by a
single reentrant lock around file writes.
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Any

from app.core.log_schemas.base import BaseLogSchema
from app.core.log_schemas.enums import LogLevel


_GLOBAL_LOG = os.path.join("logs", "structured.jsonl")
_SESSIONS_DIR = os.path.join("logs", "sessions")

_LEVEL_MAP: dict[str, int] = {
    LogLevel.DEBUG: logging.DEBUG,
    LogLevel.INFO: logging.INFO,
    LogLevel.WARNING: logging.WARNING,
    LogLevel.ERROR: logging.ERROR,
    LogLevel.CRITICAL: logging.CRITICAL,
    }

_service_logger = logging.getLogger("log_service")


class LoggingService:
    """Singleton that validates, routes, and persists structured log entries."""

    _instance: "LoggingService | None" = None
    _class_lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "LoggingService":
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._init()
                    cls._instance = instance
        return cls._instance

    def _init(self) -> None:
        self._write_lock = threading.RLock()
        os.makedirs("logs", exist_ok=True)
        os.makedirs(_SESSIONS_DIR, exist_ok=True)
        self._session_paths: dict[str, str] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def emit(self, log: BaseLogSchema) -> None:
        """Validate (implicitly via Pydantic) and route a structured log entry."""
        try:
            line = log.model_dump_json()
            self._write_global(line)
            if log.session_id:
                self._write_session(log.session_id, line)
            self._write_terminal(log)
        except Exception:
            pass  # logging must never disrupt the pipeline

    def emit_many(self, logs: list[BaseLogSchema]) -> None:
        for log in logs:
            self.emit(log)

    def session_log_path(self, session_id: str) -> str:
        """Return the path of the per-session structured log file."""
        if session_id not in self._session_paths:
            self._session_paths[session_id] = os.path.join(
                _SESSIONS_DIR, f"{session_id}.jsonl",
                )
        return self._session_paths[session_id]

    # ── Internal writers ──────────────────────────────────────────────────────

    def _write_global(self, line: str) -> None:
        with self._write_lock:
            try:
                with open(_GLOBAL_LOG, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except Exception:
                pass

    def _write_session(self, session_id: str, line: str) -> None:
        path = self.session_log_path(session_id)
        with self._write_lock:
            try:
                with open(path, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except Exception:
                pass

    def _write_terminal(self, log: BaseLogSchema) -> None:
        stdlib_level = _LEVEL_MAP.get(log.level, logging.INFO)  # type: ignore[arg-type]
        if stdlib_level < logging.INFO:
            return  # suppress DEBUG events from terminal output
        parts: list[str] = [f"[{log.event}]"]
        if log.stage:
            parts.append(f"stage={log.stage}")
        if log.node:
            parts.append(f"node={log.node}")
        parts.append(f"status={log.status}")
        if log.duration_ms is not None:
            parts.append(f"duration_ms={log.duration_ms}")
        msg = " ".join(parts)
        extra: dict[str, Any] = {}
        if log.session_id:
            extra["session_id"] = log.session_id
        _service_logger.log(stdlib_level, msg, extra=extra)

    # ── Factory helpers ───────────────────────────────────────────────────────

    @classmethod
    def get(cls) -> "LoggingService":
        """Return the singleton instance, creating it if needed."""
        return cls()
