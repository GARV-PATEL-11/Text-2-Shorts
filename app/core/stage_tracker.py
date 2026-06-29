"""stage_tracker.py — In-memory per-session pipeline stage tracker."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


# ── Scene-level record ────────────────────────────────────────────────────────

@dataclass
class SceneRecord:
    scene_index: int
    title: str
    status: str = "pending"  # pending | running | completed | failed
    started_at_s: float = 0.0
    completed_at_s: float = 0.0
    duration_ms: float | None = None
    error: str | None = None


PIPELINE_STAGES: list[str] = [
    "validate_input",
    "generate_outline",
    "map_outline",
    "visual_planning",
    "manim_code_generation",
    "scene_rendering",
    "video_assembly",
    ]

NODE_TO_STAGE: dict[str, str] = {
    "validate_input": "validate_input",
    "conceptual_zoom": "generate_outline",
    "problem_solution_arc": "generate_outline",
    "classic_linear_narrative": "generate_outline",
    "map_outline_to_visual_plan": "map_outline",
    "visual_planning": "visual_planning",
    "manim_code_generation": "manim_code_generation",
    "scene_rendering": "scene_rendering",
    "video_assembly": "video_assembly",
    }

STAGE_LABELS: dict[str, str] = {
    "validate_input": "Validate & Refine Input",
    "generate_outline": "Generate Outline",
    "map_outline": "Map Outline to Scenes",
    "visual_planning": "Generate Visual Plans",
    "manim_code_generation": "Generate Manim Code",
    "scene_rendering": "Render Scenes",
    "video_assembly": "Assemble Video",
    }


@dataclass
class StageRecord:
    stage: str
    label: str
    status: str = "pending"  # pending | running | completed | failed | skipped
    node_name: str = ""
    started_at_s: float = 0.0
    completed_at_s: float = 0.0
    duration_ms: float | None = None
    output_summary: dict = field(default_factory=dict)
    error: str | None = None


class SessionTracker:
    """Tracks pipeline stage progress for a single session."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.pipeline_status: str = "pending"
        self.started_at_s: float = 0.0
        self.completed_at_s: float = 0.0
        self._stages: list[StageRecord] = [
            StageRecord(stage=name, label=STAGE_LABELS[name])
            for name in PIPELINE_STAGES
            ]
        self._stage_map: dict[str, StageRecord] = {r.stage: r for r in self._stages}
        self._node_outputs: dict[str, dict] = {}
        self._scenes: dict[int, SceneRecord] = {}

    # ── Pipeline lifecycle ────────────────────────────────────────────────────

    def mark_started(self) -> None:
        self.pipeline_status = "running"
        self.started_at_s = time.monotonic()
        self._mark_next_running()

    def mark_complete(self) -> None:
        self.pipeline_status = "completed"
        self.completed_at_s = time.monotonic()
        for r in self._stages:
            if r.status in ("pending", "running"):
                r.status = "skipped"

    def mark_failed(self, error: str) -> None:
        self.pipeline_status = "failed"
        self.completed_at_s = time.monotonic()
        for r in self._stages:
            if r.status == "running":
                r.status = "failed"
                r.error = error

    # ── Node completion ───────────────────────────────────────────────────────

    def complete_node(self, node_name: str, updates: dict[str, Any]) -> None:
        """Record that a LangGraph node finished."""
        stage_name = NODE_TO_STAGE.get(node_name)
        if not stage_name:
            return
        record = self._stage_map.get(stage_name)
        if not record:
            return

        now = time.monotonic()
        record.node_name = node_name
        is_failed = updates.get("status") == "failed"
        record.status = "failed" if is_failed else "completed"
        record.completed_at_s = now
        if record.started_at_s:
            record.duration_ms = round((now - record.started_at_s) * 1000, 1)
        if is_failed:
            record.error = str(updates.get("error") or "Stage failed")

        record.output_summary = _summarize_output(stage_name, updates)
        self._node_outputs[node_name] = _make_serializable(updates)

        if record.status == "completed":
            self._mark_next_running()

    def fail_node(self, node_name: str, error: str) -> None:
        stage_name = NODE_TO_STAGE.get(node_name)
        if not stage_name:
            return
        record = self._stage_map.get(stage_name)
        if not record:
            return
        now = time.monotonic()
        record.status = "failed"
        record.error = error
        record.completed_at_s = now
        if record.started_at_s:
            record.duration_ms = round((now - record.started_at_s) * 1000, 1)

    # ── Scene-level tracking ──────────────────────────────────────────────────

    def init_scenes(self, scenes: list) -> None:
        """Initialize per-scene records before the visual_planning loop begins."""
        self._scenes = {
            s.scene_index: SceneRecord(scene_index=s.scene_index, title=s.title)
            for s in scenes
            }

    def start_scene(self, scene_index: int) -> None:
        r = self._scenes.get(scene_index)
        if r:
            r.status = "running"
            r.started_at_s = time.monotonic()

    def complete_scene(self, scene_index: int) -> None:
        r = self._scenes.get(scene_index)
        if r:
            now = time.monotonic()
            r.status = "completed"
            r.completed_at_s = now
            if r.started_at_s:
                r.duration_ms = round((now - r.started_at_s) * 1000, 1)

    def fail_scene(self, scene_index: int, error: str) -> None:
        r = self._scenes.get(scene_index)
        if r:
            now = time.monotonic()
            r.status = "failed"
            r.error = error
            r.completed_at_s = now
            if r.started_at_s:
                r.duration_ms = round((now - r.started_at_s) * 1000, 1)

    def update_scene_render_status(self, scene_index: int, status: str, error: str | None = None) -> None:
        """Update a scene's status during code generation / rendering stages.

        Accepts the extended status set:
        GENERATING | RENDERING | DEBUGGING | REFACTORING | READY | FAILED
        """
        r = self._scenes.get(scene_index)
        if not r:
            return
        now = time.monotonic()
        if not r.started_at_s:
            r.started_at_s = now
        r.status = status.lower()  # normalise to lowercase for consistency
        if status in ("READY", "FAILED"):
            r.completed_at_s = now
            if r.started_at_s:
                r.duration_ms = round((now - r.started_at_s) * 1000, 1)
        if error:
            r.error = error

    def get_scene_progress(self) -> dict:
        scenes = list(self._scenes.values())
        return {
            "total": len(scenes),
            "completed": sum(1 for s in scenes if s.status == "completed"),
            "failed": sum(1 for s in scenes if s.status == "failed"),
            "running_index": next(
                (s.scene_index for s in scenes if s.status == "running"), None,
                ),
            "scenes": [
                {
                    "scene_index": s.scene_index,
                    "title": s.title,
                    "status": s.status,
                    "duration_ms": s.duration_ms,
                    "error": s.error,
                    }
                for s in scenes
                ],
            }

    # ── Accessors ─────────────────────────────────────────────────────────────

    def get_stages(self) -> list[dict]:
        return [
            {
                "stage": r.stage,
                "label": r.label,
                "status": r.status,
                "node_name": r.node_name,
                "duration_ms": r.duration_ms,
                "output_summary": r.output_summary,
                "error": r.error,
                }
            for r in self._stages
            ]

    def get_stage_output(self, stage: str) -> dict | None:
        record = self._stage_map.get(stage)
        if not record or not record.node_name:
            return None
        return self._node_outputs.get(record.node_name)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _mark_next_running(self) -> None:
        for record in self._stages:
            if record.status == "pending":
                record.status = "running"
                record.started_at_s = time.monotonic()
                return


# ── Serialization helpers ─────────────────────────────────────────────────────

def _make_serializable(obj: Any) -> Any:
    """Recursively convert Pydantic models and other types to JSON-safe values."""
    if hasattr(obj, "model_dump"):
        return _make_serializable(obj.model_dump())
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serializable(item) for item in obj]
    return obj


def _summarize_output(stage: str, updates: dict[str, Any]) -> dict:
    s: dict[str, Any] = {}
    if stage == "validate_input":
        rr = updates.get("refined_requirement") or ""
        s["refined_len"] = len(rr) if isinstance(rr, str) else 0
    elif stage == "generate_outline":
        outline = updates.get("outline") or {}
        if isinstance(outline, dict):
            segments = outline.get("outline", [])
            s["segment_count"] = len(segments) if isinstance(segments, list) else 0
        s["outline_type"] = updates.get("outline_type")
    elif stage == "map_outline":
        s["total_scenes"] = updates.get("total_scenes", 0)
    elif stage == "visual_planning":
        plans = updates.get("scene_visual_plans") or []
        s["total_scenes"] = len(plans)
        failed = sum(
            1 for p in plans
                if (isinstance(p, dict) and p.get("error"))
                   or (hasattr(p, "error") and p.error)
            )
        s["failed_scenes"] = failed
    elif stage == "manim_code_generation":
        codes = updates.get("scene_manim_codes") or []
        s["total_scenes"] = len(codes)
        s["ready_scenes"] = sum(
            1 for c in codes
                if (isinstance(c, dict) and c.get("status") == "READY")
                   or (hasattr(c, "status") and c.status == "READY"),
            )
        s["failed_scenes"] = len(codes) - s["ready_scenes"]
    elif stage == "scene_rendering":
        results = updates.get("scene_render_results") or []
        s["total_scenes"] = len(results)
        s["ready_scenes"] = sum(
            1 for r in results
                if (isinstance(r, dict) and r.get("status") == "READY")
                   or (hasattr(r, "status") and r.status == "READY"),
            )
        s["failed_scenes"] = len(results) - s["ready_scenes"]
    elif stage == "video_assembly":
        s["final_video_path"] = updates.get("final_video_path")
        stats = updates.get("render_stats") or {}
        s["assembly_duration_ms"] = stats.get("assembly_duration_ms")
    return s


# ── Global registry ───────────────────────────────────────────────────────────

class StageTracker:
    _registry: dict[str, SessionTracker] = {}

    @classmethod
    def for_session(cls, session_id: str) -> SessionTracker:
        if session_id not in cls._registry:
            cls._registry[session_id] = SessionTracker(session_id)
        return cls._registry[session_id]

    @classmethod
    def remove(cls, session_id: str) -> None:
        cls._registry.pop(session_id, None)
