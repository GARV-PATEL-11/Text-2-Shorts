import json

from conftest import FIXTURES_DIRECTORY, run_tool


def test_detects_offscreen_and_overlap():
    exit_code, output = run_tool("layout_probe.py", FIXTURES_DIRECTORY / "bad_layout.py", "L", "--json")
    assert exit_code == 1
    found = {finding["code"] for finding in json.loads(output)["findings"]}
    assert {"OUT_OF_FRAME", "OVERLAP"} <= found


def test_clip_timing_against_narration_budget():
    exit_code, output = run_tool(
        "layout_probe.py",
        FIXTURES_DIRECTORY / "good_clips.py",
        "Scene001",
        "--budget",
        "clip_01=3.2,clip_02=4.0",
        "--json",
    )
    report = json.loads(output)
    clips = {clip["clip"]: clip for clip in report["clips"]}
    assert clips["clip_01"]["duration"] == 3.0 and clips["clip_02"]["duration"] == 1.5
    assert any(finding["code"] == "CLIP_TOO_SHORT" and finding["event"] == "clip_02" for finding in report["findings"])
    assert not any(finding["event"] == "clip_01" for finding in report["findings"])  # within tolerance


def test_clean_scene_passes():
    exit_code, output = run_tool("layout_probe.py", FIXTURES_DIRECTORY / "good_clips.py", "Scene001", "--json")
    assert exit_code == 0, output
