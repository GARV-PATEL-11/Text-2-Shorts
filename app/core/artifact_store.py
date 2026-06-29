"""artifact_store.py — File-based persistence for pipeline artifacts and session index."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any


ARTIFACTS_ROOT = Path("artifacts")
_SESSIONS_FILE = ARTIFACTS_ROOT / "sessions.json"
_index_lock = threading.Lock()


# ── Serialization ──────────────────────────────────────────────────────────────

def _to_json(obj: Any) -> Any:
    """Recursively convert Pydantic models and non-JSON types to JSON-safe values."""
    if hasattr(obj, "model_dump"):
        return _to_json(obj.model_dump())
    if isinstance(obj, dict):
        return {k: _to_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json(item) for item in obj]
    return obj


# ── Per-session artifact I/O ───────────────────────────────────────────────────

class ArtifactStore:
    """Manages JSON artifacts on disk for one session.

    Layout::

        artifacts/{session_id}/refined_input.json
        artifacts/{session_id}/outline.json
        artifacts/{session_id}/scene_map.json
        artifacts/{session_id}/visual_plans.json
        artifacts/{session_id}/scenes/scene_001.json
        artifacts/{session_id}/scenes/scene_002.json
        ...
    """

    LABELS: dict[str, str] = {
        "refined_input": "Refined Input",
        "outline": "Video Outline",
        "scene_map": "Scene Map",
        "visual_plans": "All Visual Plans",
        }

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._dir = ARTIFACTS_ROOT / session_id
        self._scenes_dir = self._dir / "scenes"

    # ── Stage artifacts ───────────────────────────────────────────────────────

    def save(self, artifact_type: str, data: Any) -> str:
        """Write *data* as JSON. Returns the file path string."""
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._dir / f"{artifact_type}.json"
        path.write_text(json.dumps(_to_json(data), indent=2, ensure_ascii=False))
        return str(path)

    def load(self, artifact_type: str) -> dict | None:
        """Load an artifact. Returns None if missing or corrupt."""
        path = self._dir / f"{artifact_type}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except Exception:
            return None

    def exists(self, artifact_type: str) -> bool:
        return (self._dir / f"{artifact_type}.json").exists()

    # ── Per-scene artifacts ───────────────────────────────────────────────────

    def save_scene(self, scene_index: int, data: Any) -> str:
        self._scenes_dir.mkdir(parents=True, exist_ok=True)
        path = self._scenes_dir / f"scene_{scene_index:03d}.json"
        path.write_text(json.dumps(_to_json(data), indent=2, ensure_ascii=False))
        return str(path)

    def load_scene(self, scene_index: int) -> dict | None:
        path = self._scenes_dir / f"scene_{scene_index:03d}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except Exception:
            return None

    def list_completed_scene_indices(self) -> list[int]:
        """Sorted list of scene indices that have a persisted artifact."""
        if not self._scenes_dir.exists():
            return []
        indices: list[int] = []
        for p in self._scenes_dir.glob("scene_*.json"):
            try:
                indices.append(int(p.stem.split("_")[1]))
            except (IndexError, ValueError):
                pass
        return sorted(indices)

    # ── Metadata listing ──────────────────────────────────────────────────────

    def list_artifacts(self) -> list[dict]:
        """Return metadata dicts for all artifacts in this session."""
        result: list[dict] = []
        if self._dir.exists():
            for p in sorted(self._dir.glob("*.json")):
                atype = p.stem
                st = p.stat()
                result.append({
                    "artifact_type": atype,
                    "label": self.LABELS.get(atype, atype.replace("_", " ").title()),
                    "path": str(p),
                    "size_bytes": st.st_size,
                    "modified_at": st.st_mtime,
                    },
                    )
        if self._scenes_dir.exists():
            for p in sorted(self._scenes_dir.glob("scene_*.json")):
                try:
                    idx = int(p.stem.split("_")[1])
                except (IndexError, ValueError):
                    continue
                st = p.stat()
                result.append({
                    "artifact_type": f"scene_{idx:03d}",
                    "label": f"Scene {idx} Visual Plan",
                    "path": str(p),
                    "size_bytes": st.st_size,
                    "modified_at": st.st_mtime,
                    },
                    )
        return result


# ── Global session index ───────────────────────────────────────────────────────

class SessionIndex:
    """Tracks all sessions in a single JSON file (artifacts/sessions.json)."""

    @classmethod
    def _read(cls) -> list[dict]:
        if not _SESSIONS_FILE.exists():
            return []
        try:
            return json.loads(_SESSIONS_FILE.read_text())
        except Exception:
            return []

    @classmethod
    def _write(cls, sessions: list[dict]) -> None:
        ARTIFACTS_ROOT.mkdir(parents=True, exist_ok=True)
        _SESSIONS_FILE.write_text(json.dumps(sessions, indent=2, ensure_ascii=False))

    @classmethod
    def upsert(
            cls,
            session_id: str,
            *,
            approach: str = "",
            requirement_preview: str = "",
            pipeline_status: str = "running",
            completed_stages: list[str] | None = None,
            total_scenes: int = 0,
            ) -> None:
        with _index_lock:
            sessions = cls._read()
            now = time.time()
            for s in sessions:
                if s["session_id"] == session_id:
                    s["pipeline_status"] = pipeline_status
                    s["last_updated"] = now
                    if completed_stages is not None:
                        s["completed_stages"] = completed_stages
                    if total_scenes:
                        s["total_scenes"] = total_scenes
                    cls._write(sessions)
                    return
            sessions.insert(0, {
                "session_id": session_id,
                "approach": approach,
                "requirement_preview": requirement_preview[:200],
                "pipeline_status": pipeline_status,
                "completed_stages": completed_stages or [],
                "total_scenes": total_scenes,
                "created_at": now,
                "last_updated": now,
                },
                )
            cls._write(sessions)

    @classmethod
    def list_all(cls) -> list[dict]:
        return cls._read()

    @classmethod
    def get(cls, session_id: str) -> dict | None:
        for s in cls._read():
            if s["session_id"] == session_id:
                return s
        return None
