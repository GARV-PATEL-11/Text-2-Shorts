import json
from conftest import FIX, run

def test_detects_offscreen_and_overlap():
    rc, out = run("layout_probe.py", FIX / "bad_layout.py", "L", "--json")
    assert rc == 1
    found = {f["code"] for f in json.loads(out)["findings"]}
    assert {"OUT_OF_FRAME", "OVERLAP"} <= found

def test_clip_timing_against_narration_budget():
    rc, out = run("layout_probe.py", FIX / "good_clips.py", "Scene001", "--budget", "clip_01=3.2,clip_02=4.0", "--json")
    r = json.loads(out)
    clips = {c["clip"]: c for c in r["clips"]}
    assert clips["clip_01"]["duration"] == 3.0 and clips["clip_02"]["duration"] == 1.5
    assert any(f["code"] == "CLIP_TOO_SHORT" and f["event"] == "clip_02" for f in r["findings"])
    assert not any(f["event"] == "clip_01" for f in r["findings"])  # within tolerance

def test_clean_scene_passes():
    rc, out = run("layout_probe.py", FIX / "good_clips.py", "Scene001", "--json")
    assert rc == 0, out
