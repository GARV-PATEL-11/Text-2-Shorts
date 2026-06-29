"""artifact_store.py — File-based persistence for pipeline artifacts and session index."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any


ARTIFACTS_ROOT = Path(__file__).parent.parent.parent / "artifacts"
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
        artifacts/{session_id}/render_results.json
        artifacts/{session_id}/video_stats.json
        artifacts/{session_id}/final_video.mp4
        artifacts/{session_id}/concat.txt
        artifacts/{session_id}/scenes/scene_001.json
        artifacts/{session_id}/scenes/scene_001_code.py
        artifacts/{session_id}/scenes/scene_001_code_meta.json
        artifacts/{session_id}/scenes/scene_001_render/
            attempt_1/{code.py, stdout.txt, stderr.txt, debug_analysis.json}
            scene_001.mp4
            thumbnail.jpg
        ...
    """

    LABELS: dict[str, str] = {
        "refined_input": "Refined Input",
        "outline": "Video Outline",
        "scene_map": "Scene Map",
        "visual_plans": "All Visual Plans",
        "render_results": "Render Results",
        "video_stats": "Video Stats",
        }

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._dir = ARTIFACTS_ROOT / session_id
        self._scenes_dir = self._dir / "scenes"

    @property
    def session_dir(self) -> Path:
        self._dir.mkdir(parents=True, exist_ok=True)
        return self._dir

    # ── Stage artifacts ───────────────────────────────────────────────────────

    def save(self, artifact_type: str, data: Any) -> str:
        """Write *data* as JSON atomically. Returns the file path string.

        Writes to a sibling `.tmp` file first, then renames into place so that
        readers never observe a partially-written file.
        """
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._dir / f"{artifact_type}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(_to_json(data), indent=2, ensure_ascii=False))
        tmp.replace(path)  # atomic on POSIX; best-effort on Windows
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
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(_to_json(data), indent=2, ensure_ascii=False))
        tmp.replace(path)
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
        for p in self._scenes_dir.glob("scene_???.json"):
            try:
                indices.append(int(p.stem.split("_")[1]))
            except (IndexError, ValueError):
                pass
        return sorted(indices)

    # ── Manim code artifacts ──────────────────────────────────────────────────

    def save_scene_code(self, scene_index: int, python_code: str) -> str:
        """Write generated Manim Python source. Returns the file path string."""
        self._scenes_dir.mkdir(parents=True, exist_ok=True)
        path = self._scenes_dir / f"scene_{scene_index:03d}_code.py"
        path.write_text(python_code)
        return str(path)

    def save_scene_code_meta(self, scene_index: int, metadata: dict) -> str:
        self._scenes_dir.mkdir(parents=True, exist_ok=True)
        path = self._scenes_dir / f"scene_{scene_index:03d}_code_meta.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(_to_json(metadata), indent=2, ensure_ascii=False))
        tmp.replace(path)
        return str(path)

    def load_scene_code_meta(self, scene_index: int) -> dict | None:
        path = self._scenes_dir / f"scene_{scene_index:03d}_code_meta.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except Exception:
            return None

    # ── Render artifacts ──────────────────────────────────────────────────────

    def get_render_attempt_dir(self, scene_index: int, attempt: int) -> Path:
        """Return (and create) the directory for one render attempt."""
        d = self._scenes_dir / f"scene_{scene_index:03d}_render" / f"attempt_{attempt}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_scene_clip(self, scene_index: int, src_path: "Path | str") -> str:
        """Copy rendered MP4 to canonical location. Returns stored path string."""
        from pathlib import Path as _Path

        src = _Path(src_path)
        render_dir = self._scenes_dir / f"scene_{scene_index:03d}_render"
        render_dir.mkdir(parents=True, exist_ok=True)
        dst = render_dir / f"scene_{scene_index:03d}.mp4"
        import shutil as _shutil

        _shutil.copy2(src, dst)
        return str(dst)

    def get_scene_clip_path(self, scene_index: int) -> str | None:
        path = self._scenes_dir / f"scene_{scene_index:03d}_render" / f"scene_{scene_index:03d}.mp4"
        return str(path) if path.exists() else None

    def get_scene_thumbnail_path(self, scene_index: int, create: bool = False) -> str | None:
        render_dir = self._scenes_dir / f"scene_{scene_index:03d}_render"
        if create:
            render_dir.mkdir(parents=True, exist_ok=True)
        path = render_dir / "thumbnail.jpg"
        if create:
            return str(path)
        return str(path) if path.exists() else None

    def list_ready_clips(self) -> list[tuple[int, str]]:
        """Return sorted list of (scene_index, clip_path) for all rendered clips."""
        if not self._scenes_dir.exists():
            return []
        clips: list[tuple[int, str]] = []
        for d in self._scenes_dir.glob("scene_???_render"):
            try:
                idx = int(d.name.split("_")[1])
            except (IndexError, ValueError):
                continue
            clip = d / f"scene_{idx:03d}.mp4"
            if clip.exists():
                clips.append((idx, str(clip)))
        return sorted(clips)

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
        tmp = _SESSIONS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(sessions, indent=2, ensure_ascii=False))
        tmp.replace(_SESSIONS_FILE)  # atomic rename

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
