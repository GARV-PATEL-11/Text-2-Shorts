"""Fingerprints: what each approval and each clip build depends on, so a change marks exactly the affected
work stale."""

from __future__ import annotations

import hashlib
from pathlib import Path

from schemas.plans import ScenePlan

from app.config import SCENE_BUILDER_AGENT_PATH
from app.utilities import content_hash, read_json
from app.workflow.artifacts import load_scene_plans
from app.workflow.change_requests import requests_for
from app.workflow.templates import drawing, load_template, look


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
UPSTREAM = {
    "outline": ("requirements",),
    "script": ("requirements", "outline"),
    "plan": ("requirements", "outline", "script"),
}


def upstream_fingerprints(run: Path, stage: str) -> dict[str, str | None]:
    """The earlier stages a stage is built on, as they are now: an approval records them, and a change to any of
    them asks for the approval again (changed requirements → CP0, CP1 and CP2 again)."""
    return {earlier: STAGE_FINGERPRINTS[earlier](run) for earlier in UPSTREAM.get(stage, ())}


def scene_video_hash(run: Path, scene_id: str) -> str | None:
    """The scene's current video: its clips' keys and their audio (filled in by the preview step)."""
    plan = next((plan for plan in load_scene_plans(run) if plan.scene_id == scene_id), None)
    return scene_fingerprint(run, plan) if plan else None


def clip_key(run: Path, plan: ScenePlan, clip) -> str:
    """Everything a clip's code depends on. One file per scene (scene_code.py), so every clip of a scene shares the
    scene's key: the whole plan (execution plan included), its colour roles, the scene's change requests (not declined
    ones, nor audio-timing ones, which re-time the audio), the template and the scene-builder's instructions. Not the
    SSML or audio, which are re-timed to the built video."""
    del clip  # kept in the signature: callers ask per clip, the answer is the scene's
    return content_hash(
        plan.model_dump(exclude={"clips": {"__all__": {"ssml", "sound_effects"}}}),
        [
            (r.id, r.kind, r.text)
            for r in requests_for(run, plan.scene_id, *(scene_clip.clip_id for scene_clip in plan.clips))
            if r.status != "declined" and r.kind != "audio-timing"
        ],
        look(run),  # the template's background, colour roles, font, sizes and safe area
        SCENE_BUILDER_AGENT_PATH.read_text() if SCENE_BUILDER_AGENT_PATH.exists() else "",
    )


def file_hash(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16] if path.is_file() else None


def scene_fingerprint(run: Path, plan: ScenePlan) -> str:
    """A scene's video and audio as they are now: its clip keys, each clip's audio and sound effects (their files'
    content too), and what the renderer draws behind every clip (backdrop, grid, border, subtitles)."""
    audio_index_path = run / "scenes" / plan.scene_id / "audio" / "index.json"
    audio_index = read_json(audio_index_path) if audio_index_path.exists() else {}
    return content_hash(
        [clip_key(run, plan, clip) for clip in plan.clips],
        [audio_index.get(clip.clip_id) for clip in plan.clips],
        [[(effect.model_dump(), file_hash(run / effect.file)) for effect in clip.sound_effects] for clip in plan.clips],
        drawing(run),
    )


def fingerprint(run: Path, plans: list[ScenePlan]) -> str:
    """These scenes' videos and audio: changes whenever a clip would be rebuilt or its audio changes."""
    return content_hash([scene_fingerprint(run, plan) for plan in plans])


def final_fingerprint(run: Path, plans: list[ScenePlan]) -> str:
    """final.mp4 as it would be made now: the scenes plus how they are assembled (transition and its colour, the
    music file's content and level)."""
    template = load_template(run)
    assembly = (
        template.model_dump(include={"scene_transition", "transition_seconds", "music", "music_volume_db"})
        if template
        else None
    )
    music = file_hash(run / template.music) if template and template.music else None
    return content_hash(fingerprint(run, plans), assembly, music, look(run)["background"])
