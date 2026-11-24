"""Fingerprints: what each approval and each clip build depends on, so a change marks exactly the affected
work stale."""

from __future__ import annotations

from pathlib import Path

from schemas.plans import ScenePlan

from app.config import CLIP_BUILDER_AGENT_PATH
from app.utilities import content_hash, read_json
from app.workflow.artifacts import load_scene_plans
from app.workflow.change_requests import requests_for
from app.workflow.templates import look


def requirements_fingerprint(run: Path) -> str | None:
    files = [run / name for name in ("brief.json", "topics.md", "content.md")]
    return content_hash([path.read_text() for path in files]) if all(path.exists() for path in files) else None


def template_fingerprint(run: Path) -> str | None:
    return content_hash(read_json(run / "template.json")) if (run / "template.json").exists() else None


def outline_fingerprint(run: Path) -> str | None:
    return content_hash(read_json(run / "outline.json")) if (run / "outline.json").exists() else None


def script_fingerprint(run: Path) -> str | None:
    return content_hash(read_json(run / "script.json")) if (run / "script.json").exists() else None


def plans_fingerprint(run: Path) -> str:
    """CP2 approves the visual plans; SSML is excluded because the audio is re-timed to the built video later."""
    return content_hash(
        [
            plan.model_dump(exclude={"clips": {index: {"ssml"} for index in range(len(plan.clips))}})
            for plan in load_scene_plans(run)
        ]
    )


STAGE_FINGERPRINTS = {
    "requirements": requirements_fingerprint,
    "template": template_fingerprint,
    "outline": outline_fingerprint,
    "script": script_fingerprint,
    "plan": plans_fingerprint,
}


def scene_video_hash(run: Path, scene_id: str) -> str | None:
    """The scene's current video: its clips' keys and their audio (filled in by the preview step)."""
    plan = next((plan for plan in load_scene_plans(run) if plan.scene_id == scene_id), None)
    return scene_fingerprint(run, plan) if plan else None


def clip_key(run: Path, plan: ScenePlan, clip) -> str:
    """Everything a clip's code depends on. The entry contract is its interface to the clips before it, so their code
    is not part of it (a rebuilt clip does not cascade); nor are its SSML and audio, which are re-timed to the
    built video."""
    return content_hash(
        clip.model_dump(exclude={"ssml", "sound_effects"}),
        plan.color_roles,
        [(r.id, r.kind, r.text) for r in requests_for(run, plan.scene_id, clip.clip_id)],
        look(run),  # the template's background, colour roles, font, sizes and safe area
        CLIP_BUILDER_AGENT_PATH.read_text() if CLIP_BUILDER_AGENT_PATH.exists() else "",
    )


def scene_fingerprint(run: Path, plan: ScenePlan) -> str:
    """A scene's video and audio as they are now: its clip keys plus each clip's audio."""
    audio_index_path = run / "scenes" / plan.scene_id / "audio" / "index.json"
    audio_index = read_json(audio_index_path) if audio_index_path.exists() else {}
    return content_hash(
        [clip_key(run, plan, clip) for clip in plan.clips],
        [audio_index.get(clip.clip_id) for clip in plan.clips],
        [[effect.model_dump() for effect in clip.sound_effects] for clip in plan.clips],
    )


def fingerprint(run: Path, plans: list[ScenePlan]) -> str:
    """These scenes' videos and audio: changes whenever a clip would be rebuilt or its audio changes."""
    return content_hash([scene_fingerprint(run, plan) for plan in plans])
