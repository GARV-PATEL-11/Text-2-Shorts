"""Typed loaders for the run's files: brief, topics, outline, script, scene plans, clip plans, narration audio, gate
results, the preview sync report and the final report. Each returns its Pydantic contract."""

from __future__ import annotations

import shutil
from pathlib import Path

from pydantic import ValidationError
from schemas.media import AudioIndex, ClipAudio, FinalReport, GateResult, SyncReport
from schemas.outline_models.base_outline import VideoOutline
from schemas.plans import ScenePlan
from schemas.requirements import Brief
from schemas.script import Script


def load_scene_plans(run: Path) -> list[ScenePlan]:
    """The valid scene plans, in order. An invalid plan.json is skipped here; next_steps reports it."""
    plans = []
    for plan_path in sorted((run / "scenes").glob("s[0-9][0-9]/plan.json")):
        try:
            plans.append(ScenePlan.model_validate_json(plan_path.read_text()))
        except ValueError:
            continue
    return plans


def save_versioned(path: Path, text: str) -> bool:
    """Write text; keep the old content as name.vN.ext. Returns True if the content changed."""
    if path.exists() and path.read_text() == text:
        return False
    if path.exists():
        version = len(list(path.parent.glob(f"{path.stem}.v*{path.suffix}"))) + 1
        shutil.copy(path, path.with_name(f"{path.stem}.v{version}{path.suffix}"))
    path.write_text(text)
    return True


def read_topics(run: Path) -> list[str]:
    path = run / "topics.md"
    return (
        [line.split(".", 1)[1].strip() for line in path.read_text().splitlines() if line.strip()]
        if path.exists()
        else []
    )


def load_outline(run: Path) -> VideoOutline | None:
    try:
        return VideoOutline.model_validate_json((run / "outline.json").read_text())
    except (FileNotFoundError, ValueError):
        return None


def load_script(run: Path) -> Script | None:
    try:
        return Script.model_validate_json((run / "script.json").read_text())
    except (FileNotFoundError, ValueError):
        return None


def spoken_text(scene) -> str:
    """What the voice says in one script scene: the bridge, then the narration (whitespace-normalised)."""
    return " ".join(f"{scene.bridge_in} {scene.narration}".split())


def load_clip_plan(run: Path, clip_id: str):
    plan = ScenePlan.model_validate_json((run / "scenes" / clip_id[:3] / "plan.json").read_text())
    return plan, next(clip for clip in plan.clips if clip.clip_id == clip_id)


def load_brief(run: Path) -> Brief | None:
    """brief.json, or None when it is missing or invalid (validate_brief reports why)."""
    try:
        return Brief.model_validate_json((run / "brief.json").read_text())
    except (FileNotFoundError, ValidationError):
        return None


def audio_index_path(run: Path, scene_id: str) -> Path:
    return run / "scenes" / scene_id / "audio" / "index.json"


def load_audio_index(run: Path, scene_id: str) -> dict[str, ClipAudio]:
    """scenes/sNN/audio/index.json: clip id → its narration audio (empty before `voice`)."""
    path = audio_index_path(run, scene_id)
    return AudioIndex.model_validate_json(path.read_text()).root if path.exists() else {}


def save_audio_index(run: Path, scene_id: str, audio: dict[str, ClipAudio]) -> None:
    audio_index_path(run, scene_id).write_text(AudioIndex(audio).model_dump_json(indent=2))


def load_gate_result(path: Path) -> GateResult | None:
    """A ./check gate result (checks/<gate>.json), or None before the gate ran."""
    return GateResult.model_validate_json(path.read_text()) if path.exists() else None


def load_sync_report(run: Path, scene_id: str) -> SyncReport | None:
    path = run / "scenes" / scene_id / "sync.json"
    return SyncReport.model_validate_json(path.read_text()) if path.exists() else None


def load_final_report(run: Path) -> FinalReport | None:
    path = run / "final_report.json"
    return FinalReport.model_validate_json(path.read_text()) if path.exists() else None
