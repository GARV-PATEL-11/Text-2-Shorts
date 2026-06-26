"""logger.py — Application logger with human-readable terminal output."""

from __future__ import annotations

import logging
import os
import sys


# Standard LogRecord attribute names that should NOT be treated as extras
_STD_RECORD_ATTRS: frozenset[str] = frozenset({
    "args", "created", "exc_info", "exc_text", "filename", "funcName",
    "levelname", "levelno", "lineno", "message", "module", "msecs", "msg",
    "name", "pathname", "process", "processName", "relativeCreated",
    "stack_info", "taskName", "thread", "threadName",
    },
    )


# ── Formatter ─────────────────────────────────────────────────────────────────

class _TerminalFormatter(logging.Formatter):
    """
    Readable single-line format:

        12:34:56 | INFO     | app.graph.nodes | Outline generated  session_id=abc
    """

    _COLOURS: dict[str, str] = {
        "DEBUG": "\033[36m",  # cyan
        "INFO": "\033[32m",  # green
        "WARNING": "\033[33m",  # yellow
        "ERROR": "\033[31m",  # red
        "CRITICAL": "\033[35m",  # magenta
        }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        colour = self._COLOURS.get(record.levelname, "")
        reset = self._RESET

        ts = self.formatTime(record, datefmt="%H:%M:%S")
        level = f"{colour}{record.levelname:<8}{reset}"
        msg = record.getMessage()

        # Collect any extra fields the caller attached via extra={...}
        extras = {
            k: v for k, v in record.__dict__.items()
            if k not in _STD_RECORD_ATTRS and not k.startswith("_")
            }
        extra_str = ("  " + "  ".join(f"{k}={v}" for k, v in extras.items())) if extras else ""

        line = f"{ts} | {level} | {record.name} | {msg}{extra_str}"

        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)

        return line


# ── Logger factory ────────────────────────────────────────────────────────────

class StructuredLogger:
    """Returns a stdlib Logger configured with the readable terminal formatter."""

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        logger = logging.getLogger(name)
        if logger.handlers:
            return logger

        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_TerminalFormatter())
        logger.addHandler(handler)

        return logger


# ── Root logger configuration ─────────────────────────────────────────────────

def configure_root_logging(level: int = logging.INFO) -> None:
    """
    Call once at app startup so all loggers (uvicorn, fastapi, langgraph, etc.)
    emit to stdout with a readable format.
    """
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_TerminalFormatter())
    root.addHandler(handler)

    os.makedirs("logs", exist_ok=True)
    trace_logger = logging.getLogger("llm.trace")
    if not trace_logger.handlers:
        fh = logging.FileHandler("logs/app.jsonl", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(message)s"))
        trace_logger.addHandler(fh)
        trace_logger.propagate = False
        trace_logger.setLevel(logging.INFO)
