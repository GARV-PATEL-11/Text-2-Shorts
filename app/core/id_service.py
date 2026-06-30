"""id_service.py — Sequential human-readable ID generation for sessions and workflows.

All IDs are issued by this service so no other code generates UUIDs for
pipeline sessions or workflows.

Formats
-------
Session  : T2S_VG_00001, T2S_VG_00002, …
Workflow : T2S_VG_00001_W01, T2S_VG_00001_W02, …

Counter state is persisted to ``artifacts/id_counter.json`` so numbering
survives server restarts.  Writes are atomic (temp-file + os.replace) and
protected by a threading lock for single-process safety.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path


_COUNTER_FILE = Path(__file__).parent.parent.parent / "artifacts" / "id_counter.json"
_lock = threading.Lock()

_PREFIX = "T2S_VG"


class IDService:
    """Thread-safe sequential ID generator backed by a JSON counter file."""

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    @classmethod
    def _read(cls) -> dict:
        if _COUNTER_FILE.exists():
            try:
                return json.loads(_COUNTER_FILE.read_text())
            except Exception:
                pass
        return {"sessions": 0, "workflows": {}}

    @classmethod
    def _write(cls, data: dict) -> None:
        _COUNTER_FILE.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=_COUNTER_FILE.parent,
            prefix=".id_counter_",
            suffix=".tmp",
            )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, _COUNTER_FILE)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    # ------------------------------------------------------------------ #
    # Public                                                               #
    # ------------------------------------------------------------------ #

    @classmethod
    def next_session_id(cls) -> str:
        """Return the next session ID and persist the incremented counter.

        Example: ``T2S_VG_00001``
        """
        with _lock:
            data = cls._read()
            data["sessions"] = data.get("sessions", 0) + 1
            cls._write(data)
            return f"{_PREFIX}_{data['sessions']:05d}"

    @classmethod
    def next_workflow_id(cls, session_id: str) -> str:
        """Return the next workflow ID for *session_id* and persist the counter.

        Example: ``T2S_VG_00001_W01``
        """
        with _lock:
            data = cls._read()
            workflows: dict[str, int] = data.setdefault("workflows", {})
            workflows[session_id] = workflows.get(session_id, 0) + 1
            cls._write(data)
            return f"{session_id}_W{workflows[session_id]:02d}"

    @classmethod
    def peek_session_count(cls) -> int:
        """Return the current session counter without incrementing."""
        return cls._read().get("sessions", 0)
