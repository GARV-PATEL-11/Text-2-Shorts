"""Stage 4 contracts: scene visual + audio plans and their clips (scenes/sNN/plan.json)."""

from __future__ import annotations

from pydantic import Field, model_validator
from schemas.base import ClipId, SceneId, Strict


class ContinuityState(Strict):
    """What is on screen at a boundary. Used as exit contract of clip N and entry contract of clip N+1."""

    persistent_objects: list[str] = Field(default_factory=list, description="registry names that must be visible")
    object_positions: dict[str, str] = Field(
        default_factory=dict, description="name → semantic zone, e.g. 'eq_main': 'top_center'"
    )
    descriptions: dict[str, str] = Field(
        default_factory=dict,
        description="name → what the object is (type, text or LaTeX, colour, size), so a clip built on its own can "
        "re-create the objects it takes over",
    )
    camera: str = "default_frame"
    notes: str = ""


class SoundEffect(Strict):
    file: str = Field(..., min_length=1, description="the user's own audio file, relative to the run folder")
    at: float = Field(..., ge=0, description="seconds from the clip's start")
    volume_db: float = Field(-6, ge=-40, le=6)


class ClipPlan(Strict):
    clip_id: ClipId
    index: int = Field(..., ge=1)
    objective: str = Field(..., description="one teaching purpose; if you need 'and', split the clip")
    narration: str = Field(..., description="exact spoken text for this clip (TTS input)")
    ssml: str = Field(
        ...,
        description="the clip's audio plan: <speak> SSML over exactly the narration's words — <break> for waits, "
        "<prosody rate> for pace, <emphasis>, <s>/<p>, <sub>, <say-as>",
    )
    on_screen_math: list[str] = Field(default_factory=list, description="LaTeX strings that must appear")
    visual_intent: str = Field(..., description="what the viewer sees, 2–6 sentences, no code")
    beats: list[str] = Field(
        ..., min_length=1, max_length=8, description="ordered visual events synced to narration phrases"
    )
    entry: ContinuityState
    exit: ContinuityState
    est_seconds: float = Field(..., gt=0, le=45)
    depends_on: list[ClipId] = Field(default_factory=list)
    sound_effects: list[SoundEffect] = Field(default_factory=list, description="mixed in at assembly")
    manim_topics: list[str] = Field(
        default_factory=list,
        description="extra Manim reference files to load; usually empty, since the three reference files "
        "(manim-construction-patterns, manim-vocabulary, manim-common-mistakes) are in every clip task",
    )


class ScenePlan(Strict):
    scene_id: SceneId
    index: int = Field(..., ge=1)
    title: str
    objective: str
    composition: str = Field(
        ..., min_length=1, description="layout zones and the main visual elements of the scene, 2–4 sentences"
    )
    transition_in: str = Field(
        "", description="how the scene opens from the previous scene's final image; empty for the first scene"
    )
    clips: list[ClipPlan] = Field(..., min_length=1, max_length=8)
    color_roles: dict[str, str] = Field(default_factory=dict, description="semantic role → Manim color constant")
    execution_plan: str = Field(
        "",
        description="the Visual Director's Scene Execution Plan: its tagged sections <SCENE_OVERVIEW> … "
        "<IMPLEMENTATION_NOTES> (visual-director-output-spec.md), what the code generator implements",
    )

    @model_validator(mode="after")
    def _clip_ids_belong_to_scene(self):
        for i, clip in enumerate(self.clips, 1):
            if not clip.clip_id.startswith(self.scene_id) or clip.index != i:
                raise ValueError(
                    f"clip {clip.clip_id} index {clip.index} does not match scene {self.scene_id} position {i}"
                )
        for previous, current in zip(self.clips, self.clips[1:]):
            missing = set(current.entry.persistent_objects) - set(previous.exit.persistent_objects)
            if missing:
                raise ValueError(
                    f"{current.clip_id} entry needs {sorted(missing)} which {previous.clip_id} exit does not provide"
                )
        return self
