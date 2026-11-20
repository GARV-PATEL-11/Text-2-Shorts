import pytest
from pydantic import ValidationError
import models as m

def clip(cid, i, entry=(), exit_=()):
    return m.ClipPlan(clip_id=cid, index=i, objective="o", narration="n", visual_intent="v", beats=["b"],
                      entry=m.ContinuityState(persistent_objects=list(entry)),
                      exit=m.ContinuityState(persistent_objects=list(exit_)), est_seconds=5)

def test_continuity_contract_enforced():
    with pytest.raises(ValidationError, match="entry needs"):
        m.ScenePlan(scene_id="s01", index=1, title="t", objective="o", segment_type="concept",
                    clips=[clip("s01c01", 1, exit_=["eq"]), clip("s01c02", 2, entry=["eq", "axes"])])

def test_valid_scene():
    s = m.ScenePlan(scene_id="s01", index=1, title="t", objective="o", segment_type="concept",
                    clips=[clip("s01c01", 1, exit_=["eq"]), clip("s01c02", 2, entry=["eq"])])
    assert len(s.clips) == 2

def test_clip_id_must_belong_to_scene():
    with pytest.raises(ValidationError):
        m.ScenePlan(scene_id="s02", index=1, title="t", objective="o", segment_type="concept", clips=[clip("s01c01", 1)])

def test_cache_key_is_stable_and_input_sensitive():
    a = m.GenerationMetadata(producer="clip_codegen", producer_kind="llm", prompt_id="clip_codegen@1",
                             model="sonnet", effort="high", input_hashes={"spec": "abc"})
    b = a.model_copy(update={"input_hashes": {"spec": "abd"}})
    assert a.cache_key() == a.model_copy().cache_key() and a.cache_key() != b.cache_key()

def test_extra_fields_rejected():
    with pytest.raises(ValidationError):
        m.Finding(severity="ERROR", code="X", message="m", surprise=1)
