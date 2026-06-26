"""context.py — ContextVars for request correlation and per-request logging."""

from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app.core.logger import RequestLogger


session_id_var: ContextVar[str] = ContextVar("session_id", default="")
workflow_id_var: ContextVar[str] = ContextVar("workflow_id", default="")
node_name_var: ContextVar[str] = ContextVar("node_name", default="")

# Active per-request audit logger; None when no request is in flight.
# asyncio.create_task() copies the current context, so tasks created after
# this var is set automatically inherit the RequestLogger.
request_logger_var: ContextVar[RequestLogger | None] = ContextVar(
    "request_logger", default=None,
    )
