"""context.py — ContextVars for LLM call tracing correlation."""

from contextvars import ContextVar


session_id_var: ContextVar[str] = ContextVar("session_id", default="")
workflow_id_var: ContextVar[str] = ContextVar("workflow_id", default="")
node_name_var: ContextVar[str] = ContextVar("node_name", default="")
