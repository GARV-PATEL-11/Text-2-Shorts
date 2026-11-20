import json
from conftest import FIX, run

def codes(out):
    return {f["code"] for f in json.loads(out)}

def test_bad_scene_flags_every_planted_defect(api_index):
    rc, out = run("validate_manim_code.py", FIX / "bad_scene.py", "--index", api_index,
                  "--class-name", "Scene003", "--clips", "1,2", "--json")
    assert rc == 1
    assert {"FORBIDDEN_IMPORT", "REMOVED_API", "CLIP_METHODS"} <= codes(out)
    msgs = " ".join(f["message"] for f in json.loads(out))
    for planted in ["get_graph", "TextMobject", "ThoughtBubble", "ShowCreation", "make_it_shiny"]:
        assert planted in msgs, planted

def test_good_scene_passes(api_index):
    rc, out = run("validate_manim_code.py", FIX / "good_clips.py", "--index", api_index,
                  "--class-name", "Scene001", "--clips", "1,2", "--json")
    assert rc == 0, out

def test_wrong_class_name(api_index):
    rc, out = run("validate_manim_code.py", FIX / "good_clips.py", "--index", api_index, "--class-name", "Scene009", "--json")
    assert rc == 1 and "SCENE_CLASS" in codes(out)

CLIPS = FIX / "scene_s01" / "clips"

def test_clip_file_contracts_pass(api_index):
    rc, out = run("validate_manim_code.py", CLIPS / "clip_02.py", "--index", api_index, "--clip-file",
                  "--entry", "eq", "--exit", "eq", "--json")
    assert rc == 0, out

def test_clip_reading_name_outside_entry_contract_fails(api_index):
    rc, out = run("validate_manim_code.py", CLIPS / "clip_02.py", "--index", api_index, "--clip-file",
                  "--entry", "", "--json")
    assert rc == 1 and "CONTRACT_READ" in codes(out)

def test_clip_missing_exit_promise_fails(api_index):
    rc, out = run("validate_manim_code.py", CLIPS / "clip_01.py", "--index", api_index, "--clip-file",
                  "--entry", "", "--exit", "eq,axes", "--json")
    assert rc == 1 and any("axes" in f["message"] for f in json.loads(out) if f["code"] == "CONTRACT_EXIT")
