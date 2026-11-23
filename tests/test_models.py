import pytest
from pydantic import ValidationError
import models


def clip(clip_id, i, entry=(), exit_=()):
    return models.ClipPlan(
        clip_id=clip_id,
        index=i,
        objective="o",
        narration="n",
        ssml="<speak>n</speak>",
        visual_intent="v",
        beats=["b"],
        entry=models.ContinuityState(persistent_objects=list(entry)),
        exit=models.ContinuityState(persistent_objects=list(exit_)),
        est_seconds=5,
    )


def test_continuity_contract_enforced():
    with pytest.raises(ValidationError, match="entry needs"):
        models.ScenePlan(
            scene_id="s01",
            index=1,
            title="t",
            objective="o",
            composition="c",
            clips=[clip("s01c01", 1, exit_=["eq"]), clip("s01c02", 2, entry=["eq", "axes"])],
        )


def test_valid_scene():
    scene = models.ScenePlan(
        scene_id="s01",
        index=1,
        title="t",
        objective="o",
        composition="c",
        clips=[clip("s01c01", 1, exit_=["eq"]), clip("s01c02", 2, entry=["eq"])],
    )
    assert len(scene.clips) == 2


def test_clip_id_must_belong_to_scene():
    with pytest.raises(ValidationError, match="does not match scene s02"):
        models.ScenePlan(scene_id="s02", index=1, title="t", objective="o", composition="c", clips=[clip("s01c01", 1)])


def test_cache_key_is_stable_and_input_sensitive():
    metadata = models.GenerationMetadata(
        producer="clip_codegen",
        producer_kind="llm",
        prompt_id="clip_codegen@1",
        model="sonnet",
        effort="high",
        input_hashes={"spec": "abc"},
    )
    changed_metadata = metadata.model_copy(update={"input_hashes": {"spec": "abd"}})
    assert (
        metadata.cache_key() == metadata.model_copy().cache_key()
        and metadata.cache_key() != changed_metadata.cache_key()
    )


def test_extra_fields_rejected():
    with pytest.raises(ValidationError):
        models.Finding(severity="ERROR", code="X", message="m", surprise=1)
