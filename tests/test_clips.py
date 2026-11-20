"""Clip pipeline without LLM calls: a fake agent writes real clip files; ./check gates + the jailed re-check run."""
import json
import shutil
import subprocess

import pytest

from app import clips as C
from app import pipeline as P
from schemas.models import ScenePlan

CLIP_01 = '''from manim import *

def clip_01(self):
    title = Text("Hello").to_edge(UP)
    self.play(Write(title), run_time=1)
    self.wait(2.2)
    self.reg["title"] = title
'''
CLIP_02 = '''from manim import *

def clip_02(self):
    self.play(FadeOut(self.reg.pop("title")), run_time=0.5)
    self.wait(2.7)
'''


def clip(i, entry, exit_):
    return {"clip_id": f"s01c{i:02d}", "index": i, "objective": "o", "narration": "n", "visual_intent": "v",
            "beats": ["b"], "entry": {"persistent_objects": entry}, "exit": {"persistent_objects": exit_},
            "est_seconds": 2}


def bwrap_works() -> bool:  # some CI kernels block unprivileged user namespaces
    return bool(shutil.which("bwrap")) and subprocess.run(["bwrap", "--ro-bind", "/", "/", "true"]).returncode == 0


def seg(i, secs):
    return {"scene_id": i, "segment_type": "concept", "title": f"t{i}", "duration_seconds": secs,
            "talking_points": ["p"], "visual_plan": "v", "narration_hint": "n", "transition_to_next": None}


def outline(*secs):
    return {"meta": {"title": "T", "topic": "t", "total_duration_seconds": sum(secs), "pace": "medium", "target_wpm": 150,
                     "approach_name": "zoom", "approach_style": "s"}, "outline": [seg(i, s) for i, s in enumerate(secs, 1)]}


def test_validate_outline_plan_and_math(tmp_path):
    run = tmp_path
    P.write_json(run / "brief.json", {"approach": "zoom", "minutes": 1})
    P.write_json(run / "outline.json", outline(30, 30))
    assert C.validate_outline(run) == []
    P.write_json(run / "outline.json", outline(60, 60))
    assert any("120s" in e for e in C.validate_outline(run))           # 2x the 60 s target
    P.write_json(run / "outline.json", {"meta": {}, "outline": []})
    assert C.validate_outline(run)                                    # schema errors

    s1 = {"scene_id": "s01", "index": 1, "title": "t", "objective": "o", "segment_type": "x",
          "color_roles": {"a": "BLUE"}, "clips": [clip(1, [], [])]}
    (run / "scenes" / "s01").mkdir(parents=True)
    (run / "scenes" / "s01" / "plan.json").write_text(json.dumps(s1))
    assert C.validate_plan(run, "s01") == []
    s2 = {**s1, "scene_id": "s02", "index": 2, "color_roles": {"a": "RED"},
          "clips": [{**clip(1, ["x"], []), "clip_id": "s02c01"}]}
    (run / "scenes" / "s02").mkdir()
    (run / "scenes" / "s02" / "plan.json").write_text(json.dumps(s2))
    errors = C.validate_plan(run, "s02")
    assert any("entry must be empty" in e for e in errors) and any("`a`" in e and "BLUE" in e for e in errors)

    (run / "math.json").write_text('{"findings": [{"clip_id": "s09c01"}]}')
    assert C.validate_math(run)
    (run / "math.json").write_text('{"findings": []}')
    assert C.validate_math(run) == []


@pytest.mark.skipif(not bwrap_works(), reason="needs a working bubblewrap sandbox")
def test_task_accept_status_final(tmp_path, monkeypatch):
    run = tmp_path / "run"
    sd = run / "scenes" / "s01"
    (sd / "audio").mkdir(parents=True)
    plan = ScenePlan.model_validate({"scene_id": "s01", "index": 1, "title": "t", "objective": "o", "segment_type": "x",
                                     "clips": [clip(1, [], ["title"]), clip(2, ["title"], [])]})
    (sd / "plan.json").write_text(plan.model_dump_json())
    P.write_json(sd / "audio" / "index.json", {"s01c01": {"hash": "h", "seconds": 2.0}, "s01c02": {"hash": "h", "seconds": 2.0}})
    P.write_json(run / "brief.json", {"font": None})
    C.ensure_api_index()

    def build(clip_id, code):  # what the clip-builder subagent does: write the file in the prepared work dir
        w = C.prepare_clip(run, clip_id)
        assert "CLIP_SECONDS: 3.1" in (w / "TASK.md").read_text() and (w / "check").exists()
        (w / f"clip_{clip_id[-2:]}.py").write_text(code)
        return C.accept_clip(run, clip_id)

    with pytest.raises(SystemExit, match="s01c01"):
        C.prepare_clip(run, "s01c02")                                 # clips are built in order
    assert build("s01c01", CLIP_01)["status"] == "READY"
    assert build("s01c02", CLIP_02)["status"] == "READY"
    assert (sd / "clips" / "clip_02.py").read_text() == CLIP_02
    checks = json.loads((sd / "work" / "clip_02" / "checks" / "render.json").read_text())
    assert checks["ok"] and checks["duration"] >= 3.1   # lead-in + narration + hold
    assert not [s for s in C.next_steps(run) if "s01c0" in s]      # nothing stale
    assert build("s01c02", "def clip_02(self):\n    pass\n")["status"] == "FAILED"   # too short → rejected
    assert (sd / "clips" / "clip_02.py").read_text() == CLIP_02    # the approved clip stays installed
    assert any("s01c02" in s for s in C.next_steps(run))
    build("s01c02", CLIP_02)

    # CP3 → final: jailed 1440p section render, per-clip A/V mux, loudnorm, media checks
    import argparse, subprocess
    for i in (1, 2):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                        str(sd / "audio" / f"clip_{i:02d}.mp3")], check=True)
    with pytest.raises(SystemExit, match="not approved"):
        C.cmd_final(argparse.Namespace(run=str(run), force=False))
    C.cmd_approve(argparse.Namespace(run=str(run), target="s01", force=False))
    C.cmd_final(argparse.Namespace(run=str(run), force=False))
    report = json.loads((run / "final_report.json").read_text())
    assert not [f for f in report["checks"] if f["severity"] == "ERROR"], report["checks"]
    assert report["final_s"] >= 4.0
