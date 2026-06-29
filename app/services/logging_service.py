"""logging_service.py — Re-export shim (LoggingService lives in app.core)."""
from app.core.logging_service import LoggingService  # noqa: F401


__all__ = ["LoggingService"]
