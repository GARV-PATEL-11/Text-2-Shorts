import shutil
import sys
from conftest import FIXTURES_DIRECTORY, TOOLS_DIRECTORY

sys.path.insert(0, str(TOOLS_DIRECTORY))
import scene_harness


def _scene(tmp_path):
    scene_directory = tmp_path / "s01"
    shutil.copytree(FIXTURES_DIRECTORY / "scene_s01", scene_directory)
    scene_harness.compose_scene(scene_directory, "s01")
    return scene_directory


def test_full_render_emits_one_section_per_clip(tmp_path):
    result = scene_harness.render_scene(_scene(tmp_path), "s01", None, "l")
    assert result["ok"] and [section["name"] for section in result["sections"]] == ["clip_01", "clip_02", "clip_03"]
    assert abs(result["sections"][1]["duration"] - 2.5) < 0.15


def test_target_renders_only_that_clip_with_exact_entry_state(tmp_path):
    result = scene_harness.render_scene(_scene(tmp_path), "s01", "clip_02", "l")
    assert result["ok"] and [section["name"] for section in result["sections"]] == [
        "clip_02"
    ]  # clip_01 ran but was skipped, clip_03 never ran


def test_clip_file_must_hold_one_named_function(tmp_path):
    scene_directory = _scene(tmp_path)
    (scene_directory / "clips/clip_02.py").write_text("from manim import *\ndef helper(self): pass\n")
    import pytest

    with pytest.raises(SystemExit):
        scene_harness.compose_scene(scene_directory, "s01")


def test_portrait_render_is_actually_portrait(tmp_path):
    scene_directory = _scene(tmp_path)
    shutil.copy(FIXTURES_DIRECTORY / "portrait" / "manim.cfg", scene_directory / "manim.cfg")
    result = scene_harness.render_scene(scene_directory, "s01", "clip_01", "l", aspect="9:16")
    assert result["ok"]
    first_section = result["sections"][0]
    assert (first_section["width"], first_section["height"]) == (480, 854)
