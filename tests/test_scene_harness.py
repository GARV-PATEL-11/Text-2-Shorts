import shutil, sys
from conftest import FIX, TOOLS
sys.path.insert(0, str(TOOLS))
import scene_harness as h

def _scene(tmp_path):
    d = tmp_path / "s01"; shutil.copytree(FIX / "scene_s01", d); h.compose(d, "s01"); return d

def test_full_render_emits_one_section_per_clip(tmp_path):
    r = h.render(_scene(tmp_path), "s01", None, "l")
    assert r["ok"] and [s["name"] for s in r["sections"]] == ["clip_01", "clip_02", "clip_03"]
    assert abs(r["sections"][1]["duration"] - 2.5) < 0.15

def test_target_renders_only_that_clip_with_exact_entry_state(tmp_path):
    r = h.render(_scene(tmp_path), "s01", "clip_02", "l")
    assert r["ok"] and [s["name"] for s in r["sections"]] == ["clip_02"]  # clip_01 ran but was skipped, clip_03 never ran

def test_clip_file_must_hold_one_named_function(tmp_path):
    d = _scene(tmp_path); (d / "clips/clip_02.py").write_text("from manim import *\ndef helper(self): pass\n")
    import pytest
    with pytest.raises(SystemExit):
        h.compose(d, "s01")

def test_portrait_render_is_actually_portrait(tmp_path):
    import subprocess
    d = _scene(tmp_path); shutil.copy(FIX / "portrait" / "manim.cfg", d / "manim.cfg")
    r = h.render(d, "s01", "clip_01", "l", aspect="9:16"); assert r["ok"]
    sec = r["sections"][0]
    assert (sec["width"], sec["height"]) == (480, 854)
