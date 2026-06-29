"""logger.py — Terminal output, JSONL tracing, and per-request audit logging.

All log entries are routed through LoggingService and validated against the
corresponding typed schema before being persisted.  The public API of
RequestLogger is preserved so existing call sites continue to work without
modification.
"""
from __future__ import annotations

import asyncio
import functools
import logging
import os
import sys
import time
import traceback as _traceback
from typing import Any, Callable

from app.core.log_schemas import (
    ApiEvent,
    ErrorEvent,
    LlmEvent,
    LogLevel,
    LogStatus,
    MetricEvent,
    NodeEvent,
    StageEvent,
    StorageEvent,
    SystemEvent,
    WorkflowEvent,
    )
from app.core.logging_service import LoggingService


# ── Standard LogRecord attribute names excluded from extras display ────────────

_STD_RECORD_ATTRS: frozenset[str] = frozenset({
    "args", "created", "exc_info", "exc_text", "filename", "funcName",
    "levelname", "levelno", "lineno", "message", "module", "msecs", "msg",
    "name", "pathname", "process", "processName", "relativeCreated",
    "stack_info", "taskName", "thread", "threadName",
    },
    )


# ── Terminal formatter ─────────────────────────────────────────────────────────

class _TerminalFormatter(logging.Formatter):
    """12:34:56 | INFO     | module.name | Message  key=val  key=val"""

    _COLOURS: dict[str, str] = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
        }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        colour = self._COLOURS.get(record.levelname, "")
        ts = self.formatTime(record, datefmt="%H:%M:%S")
        level = f"{colour}{record.levelname:<8}{self._RESET}"
        msg = record.getMessage()
        extras = {
            k: v for k, v in record.__dict__.items()
            if k not in _STD_RECORD_ATTRS and not k.startswith("_")
            }
        extra_str = (
                "  " + "  ".join(f"{k}={v}" for k, v in extras.items())
        ) if extras else ""
        line = f"{ts} | {level} | {record.name} | {msg}{extra_str}"
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


# ── Module-level structured logger factory ─────────────────────────────────────

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


# ── Root logging configuration ─────────────────────────────────────────────────

def configure_root_logging(level: int = logging.INFO) -> None:
    """Call once at app startup. Configures root + LLM trace loggers."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_TerminalFormatter())
    root.addHandler(handler)

    os.makedirs("logs", exist_ok=True)
    os.makedirs(os.path.join("logs", "requests"), exist_ok=True)
    os.makedirs(os.path.join("logs", "sessions"), exist_ok=True)

    trace_logger = logging.getLogger("llm.trace")
    if not trace_logger.handlers:
        fh = logging.FileHandler(os.path.join("logs", "app.jsonl"), encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(message)s"))
        trace_logger.addHandler(fh)
        trace_logger.propagate = False
        trace_logger.setLevel(logging.INFO)

    LoggingService.get().emit(
        SystemEvent(
            action="startup",
            component="app",
            environment=os.getenv("ENV", "development"),
            status=LogStatus.SUCCESS,
            level=LogLevel.INFO,
            ),
        )


# ══════════════════════════════════════════════════════════════════════════════
# Per-request JSONL audit logger
# ══════════════════════════════════════════════════════════════════════════════

class RequestLogger:
    """Per-pipeline-request structured logger backed by LoggingService.

    Every public method emits a typed schema validated through the centralized
    LoggingService.  The public API is preserved for backward compatibility.
    """

    def __init__(
            self,
            session_id: str,
            endpoint: str,
            payload: dict[str, Any],
            config: dict[str, Any] | None = None,
            ) -> None:
        from uuid import uuid4

        self.session_id = session_id
        self.request_id: str = uuid4().hex
        self._start = time.perf_counter()
        self._svc = LoggingService.get()

        # Aggregated for final summary
        self._nodes_executed: list[str] = []
        self._errors: list[dict] = []
        self._warnings: list[dict] = []
        self._llm_calls: list[dict] = []
        self._artifacts: list[str] = []
        self._retry_count = 0
        self._fallback_count = 0

        self._svc.emit(
            ApiEvent(
                request_id=self.request_id,
                session_id=session_id,
                method="POST",
                path=endpoint,
                status=LogStatus.RUNNING,
                level=LogLevel.INFO,
                details={"payload": payload, "config": config or {}},
                ),
            )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _elapsed_ms(self) -> float:
        return round((time.perf_counter() - self._start) * 1000, 2)

    def _base(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "session_id": self.session_id,
            "duration_ms": self._elapsed_ms(),
            }

    # ── Typed emit shortcut ───────────────────────────────────────────────────

    def emit(self, log: Any) -> None:
        """Emit a pre-constructed typed schema instance directly."""
        self._svc.emit(log)

    # ── Function lifecycle ────────────────────────────────────────────────────

    def function_entry(self, func: str, module: str, args: dict | None = None) -> None:
        if func.startswith("node:") and func[5:] not in self._nodes_executed:
            self._nodes_executed.append(func[5:])
        self._svc.emit(
            NodeEvent(
                **self._base(),
                node_name=func,
                status=LogStatus.RUNNING,
                details={"args": args or {}},
                ),
            )

    def function_exit(
            self,
            func: str,
            duration_ms: float,
            status: str,
            result: str | None = None,
            ) -> None:
        log_status = LogStatus.SUCCESS if status == "success" else LogStatus.FAILED
        self._svc.emit(
            NodeEvent(
                **self._base(),
                node_name=func,
                status=log_status,
                details={"result": result},
                ),
            )

    # ── Pipeline stage events ─────────────────────────────────────────────────

    def pipeline_step(self, step: str, details: dict | None = None) -> None:
        self._svc.emit(
            StageEvent(
                **self._base(),
                stage_name=step,
                status=LogStatus.RUNNING,
                level=LogLevel.INFO,
                details=details or {},
                ),
            )

    def routing_decision(
            self, *, from_node: str, to_node: str, reason: str = "",
            ) -> None:
        self._svc.emit(
            NodeEvent(
                **self._base(),
                node_name=from_node,
                next_node=to_node,
                status=LogStatus.SUCCESS,
                details={"reason": reason},
                ),
            )

    # ── LLM events ───────────────────────────────────────────────────────────

    def llm_call(
            self,
            *,
            provider: str,
            model: str,
            node: str,
            latency_ms: float,
            input_tokens: int,
            output_tokens: int,
            total_tokens: int,
            is_structured: bool,
            attempt: int = 1,
            system_prompt: str = "",
            user_prompt: str = "",
            response: str = "",
            ) -> None:
        record = {
            "provider": provider, "model": model, "node": node,
            "latency_ms": latency_ms, "input_tokens": input_tokens,
            "output_tokens": output_tokens, "total_tokens": total_tokens,
            "is_structured": is_structured, "attempt": attempt,
            }
        self._llm_calls.append(record)
        self._svc.emit(
            LlmEvent(
                **self._base(),
                node=node,
                provider=provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                is_structured=is_structured,
                attempt=attempt,
                prompt_preview=user_prompt[:300],
                response_preview=response[:300],
                duration_ms=latency_ms,
                status=LogStatus.SUCCESS,
                ),
            )

    def llm_retry(
            self,
            *,
            model: str,
            attempt: int,
            max_attempts: int,
            wait_s: float,
            error: str,
            ) -> None:
        self._retry_count += 1
        self._svc.emit(
            LlmEvent(
                **self._base(),
                model=model,
                attempt=attempt,
                status=LogStatus.RETRYING,
                level=LogLevel.WARNING,
                details={
                    "max_attempts": max_attempts,
                    "wait_s": wait_s,
                    "error": str(error)[:300],
                    },
                ),
            )

    def llm_fallback(
            self,
            *,
            from_model: str,
            to_model: str,
            after_attempts: int,
            reason: str = "",
            ) -> None:
        self._fallback_count += 1
        self._svc.emit(
            LlmEvent(
                **self._base(),
                model=to_model,
                status=LogStatus.RETRYING,
                level=LogLevel.WARNING,
                details={
                    "from_model": from_model,
                    "to_model": to_model,
                    "after_attempts": after_attempts,
                    "reason": str(reason)[:300],
                    },
                ),
            )

    # ── I/O events ───────────────────────────────────────────────────────────

    def file_written(
            self, *, path: str, size_bytes: int = 0, content_type: str = "",
            ) -> None:
        self._artifacts.append(path)
        self._svc.emit(
            StorageEvent(
                **self._base(),
                operation="write",
                path=path,
                size_bytes=size_bytes,
                content_type=content_type,
                status=LogStatus.SUCCESS,
                ),
            )

    # ── Error and warning events ──────────────────────────────────────────────

    def error(
            self,
            *,
            exc: Exception,
            context: str,
            func: str | None = None,
            extra: dict | None = None,
            ) -> None:
        record = {
            "error_type": type(exc).__name__,
            "message": str(exc)[:500],
            "context": context,
            "func": func,
            }
        self._errors.append(record)
        self._svc.emit(
            ErrorEvent(
                **self._base(),
                error_type=type(exc).__name__,
                message=str(exc)[:500],
                traceback=_traceback.format_exc()[-2000:],
                context=context,
                level=LogLevel.ERROR,
                details=extra or {},
                ),
            )

    def warning(
            self, *, message: str, context: str, extra: dict | None = None,
            ) -> None:
        record = {"message": message[:300], "context": context}
        self._warnings.append(record)
        self._svc.emit(
            ErrorEvent(
                **self._base(),
                error_type="Warning",
                message=message[:300],
                context=context,
                level=LogLevel.WARNING,
                status=LogStatus.RUNNING,
                details=extra or {},
                ),
            )

    # ── Final summary ─────────────────────────────────────────────────────────

    def summary(
            self,
            *,
            status: str,
            final_stage: str | None = None,
            outline_type: str | None = None,
            total_scenes: int = 0,
            error: str | None = None,
            ) -> None:
        total_ms = round((time.perf_counter() - self._start) * 1000, 2)
        total_in = sum(c.get("input_tokens", 0) for c in self._llm_calls)
        total_out = sum(c.get("output_tokens", 0) for c in self._llm_calls)
        total_llm_ms = round(
            sum(c.get("latency_ms", 0) for c in self._llm_calls), 2,
            )

        log_status = (
            LogStatus.SUCCESS if status == "completed"
            else LogStatus.FAILED if status == "failed"
            else LogStatus.RUNNING
        )

        self._svc.emit(
            WorkflowEvent(
                request_id=self.request_id,
                session_id=self.session_id,
                total_scenes=total_scenes,
                status=log_status,
                duration_ms=total_ms,
                level=LogLevel.ERROR if status == "failed" else LogLevel.INFO,
                details={
                    "final_stage": final_stage,
                    "outline_type": outline_type,
                    "error": error,
                    "nodes_executed": self._nodes_executed,
                    "llm_calls_total": len(self._llm_calls),
                    "total_input_tokens": total_in,
                    "total_output_tokens": total_out,
                    "total_llm_latency_ms": total_llm_ms,
                    "retries_total": self._retry_count,
                    "fallbacks_total": self._fallback_count,
                    "errors_total": len(self._errors),
                    "warnings_total": len(self._warnings),
                    "artifacts_saved": self._artifacts,
                    },
                ),
            )

        self._svc.emit(
            MetricEvent(
                request_id=self.request_id,
                session_id=self.session_id,
                metric_name="pipeline.total_tokens",
                value=float(total_in + total_out),
                unit="tokens",
                status=log_status,
                tags={"session_id": self.session_id},
                ),
            )
        self._svc.emit(
            MetricEvent(
                request_id=self.request_id,
                session_id=self.session_id,
                metric_name="pipeline.duration_ms",
                value=total_ms,
                unit="ms",
                status=log_status,
                tags={"session_id": self.session_id},
                ),
            )


# ══════════════════════════════════════════════════════════════════════════════
# @log_call decorator
# ══════════════════════════════════════════════════════════════════════════════

def _state_summary(arg: Any) -> dict[str, Any]:
    """Extract minimal identifying fields from a Pydantic state object."""
    if arg is None or not hasattr(arg, "model_dump"):
        return {}
    try:
        d = arg.model_dump()
        return {
            k: (str(v)[:150] if isinstance(v, str) else v)
            for k, v in d.items()
            if k in (
                "session_id", "workflow_id", "status", "approach",
                "outline_type", "total_scenes", "error",
                )
               and v is not None
            }
    except Exception:
        return {}


def log_call(
        _fn: Callable | None = None,
        *,
        stage: str | None = None,
        ) -> Callable:
    """Decorator: logs function entry, exit, timing, and errors to RequestLogger.

    Usage::

        @log_call
        async def my_node(state: GraphState) -> dict: ...

        @log_call(stage="node:validate_input")
        async def validate_input(state: GraphState) -> dict: ...
    """

    def decorator(fn: Callable) -> Callable:
        _name = stage or f"{fn.__module__}.{fn.__qualname__}"

        @functools.wraps(fn)
        async def _async(*args: Any, **kwargs: Any) -> Any:
            from app.core.context import request_logger_var

            rl: RequestLogger | None = request_logger_var.get()
            t0 = time.perf_counter()
            if rl:
                rl.function_entry(
                    _name, fn.__module__, _state_summary(args[0]) if args else {},
                    )
            try:
                result = await fn(*args, **kwargs)
                if rl:
                    rl.function_exit(
                        _name,
                        round((time.perf_counter() - t0) * 1000, 2),
                        "success",
                        type(result).__name__,
                        )
                return result
            except Exception as exc:
                dur = round((time.perf_counter() - t0) * 1000, 2)
                if rl:
                    rl.error(exc=exc, context=_name, func=fn.__qualname__)
                    rl.function_exit(_name, dur, "error", str(exc)[:200])
                raise

        @functools.wraps(fn)
        def _sync(*args: Any, **kwargs: Any) -> Any:
            from app.core.context import request_logger_var

            rl: RequestLogger | None = request_logger_var.get()
            t0 = time.perf_counter()
            if rl:
                rl.function_entry(
                    _name, fn.__module__, _state_summary(args[0]) if args else {},
                    )
            try:
                result = fn(*args, **kwargs)
                if rl:
                    rl.function_exit(
                        _name,
                        round((time.perf_counter() - t0) * 1000, 2),
                        "success",
                        type(result).__name__,
                        )
                return result
            except Exception as exc:
                dur = round((time.perf_counter() - t0) * 1000, 2)
                if rl:
                    rl.error(exc=exc, context=_name, func=fn.__qualname__)
                    rl.function_exit(_name, dur, "error", str(exc)[:200])
                raise

        return _async if asyncio.iscoroutinefunction(fn) else _sync

    if _fn is not None:
        return decorator(_fn)
    return decorator
