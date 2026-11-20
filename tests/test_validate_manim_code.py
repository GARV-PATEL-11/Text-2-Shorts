import json
from conftest import FIXTURES_DIRECTORY, run_tool


def codes(output):
    return {finding["code"] for finding in json.loads(output)}


def test_bad_scene_flags_every_planted_defect(api_index):
    exit_code, output = run_tool(
        "validate_manim_code.py",
        FIXTURES_DIRECTORY / "bad_scene.py",
        "--index",
        api_index,
        "--class-name",
        "Scene003",
        "--clips",
        "1,2",
        "--json",
    )
    assert exit_code == 1
    assert {"FORBIDDEN_IMPORT", "REMOVED_API", "CLIP_METHODS"} <= codes(output)
    messages = " ".join(finding["message"] for finding in json.loads(output))
    for planted in ["get_graph", "TextMobject", "ThoughtBubble", "ShowCreation", "make_it_shiny"]:
        assert planted in messages, planted


def test_good_scene_passes(api_index):
    exit_code, output = run_tool(
        "validate_manim_code.py",
        FIXTURES_DIRECTORY / "good_clips.py",
        "--index",
        api_index,
        "--class-name",
        "Scene001",
        "--clips",
        "1,2",
        "--json",
    )
    assert exit_code == 0, output


def test_wrong_class_name(api_index):
    exit_code, output = run_tool(
        "validate_manim_code.py",
        FIXTURES_DIRECTORY / "good_clips.py",
        "--index",
        api_index,
        "--class-name",
        "Scene009",
        "--json",
    )
    assert exit_code == 1 and "SCENE_CLASS" in codes(output)


CLIPS = FIXTURES_DIRECTORY / "scene_s01" / "clips"


def test_clip_file_contracts_pass(api_index):
    exit_code, output = run_tool(
        "validate_manim_code.py",
        CLIPS / "clip_02.py",
        "--index",
        api_index,
        "--clip-file",
        "--entry",
        "eq",
        "--exit",
        "eq",
        "--json",
    )
    assert exit_code == 0, output


def test_clip_reading_name_outside_entry_contract_fails(api_index):
    exit_code, output = run_tool(
        "validate_manim_code.py", CLIPS / "clip_02.py", "--index", api_index, "--clip-file", "--entry", "", "--json"
    )
    assert exit_code == 1 and "CONTRACT_READ" in codes(output)


def test_clip_missing_exit_promise_fails(api_index):
    exit_code, output = run_tool(
        "validate_manim_code.py",
        CLIPS / "clip_01.py",
        "--index",
        api_index,
        "--clip-file",
        "--entry",
        "",
        "--exit",
        "eq,axes",
        "--json",
    )
    assert exit_code == 1 and any(
        "axes" in finding["message"] for finding in json.loads(output) if finding["code"] == "CONTRACT_EXIT"
    )
