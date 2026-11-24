"""Stage 3 contracts: the complete script (script.json)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator
from schemas.base import SceneId, Strict


class ScriptScene(Strict):
    scene_id: SceneId
    role: Literal["index", "content", "recap"] = Field(
        "content", description="s01 is the index scene: it tells the viewer what the video covers"
    )
    title: str = Field(..., min_length=1)
    objective: str = Field(..., min_length=1, description="what this scene teaches, in one sentence")
    key_concepts: list[str] = Field(..., min_length=1)
    covers: list[int] = Field(default_factory=list, description="1-based indexes into Script.objectives it teaches")
    previews: list[SceneId] = Field(default_factory=list, description="index scene only: every later scene, in order")
    outline_segment: int | None = Field(
        None, ge=1, description="the outline.json segment this scene narrates (empty for the index scene)"
    )
    duration_seconds: float = Field(..., gt=0)
    bridge_in: str = Field(
        "",
        description="spoken inter-scene transition at the start of this scene: what was just covered, what comes "
        "next, why it matters. Empty for the first scene.",
    )
    narration: str = Field(..., min_length=1, description="the complete spoken text of the scene after the bridge")
    visual_idea: str = Field("", description="one or two sentences; the scene's visual plan holds the detail")
    on_screen_text: list[str] = Field(
        default_factory=list, description="text or formulas that must appear on screen (the plan must show each)"
    )
    animations: list[str] = Field(default_factory=list, description="animations the scene requires")
    audio_requirements: str = Field("", description="voice, pause, music or sound needs of this scene")
    transition_requirements: str = Field("", description="how this scene must enter from the previous one")
    depends_on: list[SceneId] = Field(default_factory=list, description="earlier scenes this one builds on")


class Script(Strict):
    title: str = Field(..., min_length=1)
    structure: str = Field(..., min_length=1, description="narrative structure used, e.g. zoom, arc, linear, custom")
    objectives: list[str] = Field(..., min_length=1)
    target_wpm: int = Field(150, ge=90, le=220)
    scenes: list[ScriptScene] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _scenes_are_sequential_and_bridged(self):
        index_scene = self.scenes[0]
        if index_scene.role != "index":
            raise ValueError("s01 must be the index scene (role 'index'): say what the video covers")
        later = [scene.scene_id for scene in self.scenes[1:]]
        if index_scene.previews != later:
            raise ValueError(f"the index scene's previews must list every later scene in order: {later}")
        for number, scene in enumerate(self.scenes, 1):
            if later_dependencies := [d for d in scene.depends_on if int(d[1:]) >= number]:
                raise ValueError(f"{scene.scene_id}: depends_on lists only earlier scenes, not {later_dependencies}")
            if number > 1 and scene.role == "index":
                raise ValueError(f"{scene.scene_id}: only s01 is the index scene")
            if scene.role != "index" and not scene.covers:
                raise ValueError(f"{scene.scene_id} covers no objective: every teaching scene covers at least one")
            if scene.scene_id != f"s{number:02d}":
                raise ValueError(f"scene {scene.scene_id} is at position {number}: expected s{number:02d}")
            if bad := [index for index in scene.covers if not 1 <= index <= len(self.objectives)]:
                raise ValueError(f"{scene.scene_id} covers objectives {bad}, but there are {len(self.objectives)}")
            if number == 1 and scene.bridge_in.strip():
                raise ValueError("s01 bridge_in must be empty: the first scene has nothing to bridge from")
            if number > 1 and not scene.bridge_in.strip():
                raise ValueError(
                    f"{scene.scene_id} bridge_in is empty: say what was covered, what comes next and why it matters"
                )
        return self
