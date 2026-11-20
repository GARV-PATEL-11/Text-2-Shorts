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
    self.wait(1.2)
    self.reg["title"] = title
'''
CLIP_02 = '''from manim import *

def clip_02(self):
    self.play(FadeOut(self.reg.pop("title")), run_time=0.5)
    self.wait(1.7)
'''


def clip(i, entry, exit_):
    return {"clip_id": f"s01c{i:02d}", "index": i, "objective": "o", "narration": "n", "visual_intent": "v",
            "beats": ["b"], "entry": {"persistent_objects": entry}, "exit": {"persistent_objects": exit_},
            "est_seconds": 2}


def bwrap_works() -> bool:  # some CI kernels block unprivileged user namespaces
    return bool(shutil.which("bwrap")) and subprocess.run(["bwrap", "--ro-bind", "/", "/", "true"]).returncode == 0


@pytest.mark.skipif(not bwrap_works(), reason="needs a working bubblewrap sandbox")
def test_build_runs_gates_and_installs_clips(tmp_path, monkeypatch):
    run = tmp_path / "run"
    sd = run / "scenes" / "s01"
    (sd / "audio").mkdir(parents=True)
    plan = ScenePlan.model_validate({"scene_id": "s01", "index": 1, "title": "t", "objective": "o", "segment_type": "x",
                                     "clips": [clip(1, [], ["title"]), clip(2, ["title"], [])]})
    (sd / "plan.json").write_text(plan.model_dump_json())
    P.write_json(sd / "audio" / "index.json", {"s01c01": {"hash": "h", "seconds": 2.0}, "s01c02": {"hash": "h", "seconds": 2.0}})
    P.write_json(run / "brief.json", {"font": None})
    C.ensure_api_index()

    def fake_agent(run_, stage, user, system, *, cwd, scene, **kw):
        assert system == C.CLIP_BUILDER_SYSTEM and "NARRATION_SECONDS: 2.0" in user
        (cwd / f"clip_{scene[-2:]}.py").write_text({"01": CLIP_01, "02": CLIP_02}[scene[-2:]])
        return C.ClipResult(status="READY", gate_runs=1)

    monkeypatch.setattr(P, "claude", fake_agent)
    rows = C.build_scene(run, plan, set())
    assert all("| READY |" in r for r in rows), rows
    assert (sd / "clips" / "clip_02.py").read_text() == CLIP_02
    checks = json.loads((sd / "work" / "clip_02" / "checks" / "render.json").read_text())
    assert checks["ok"] and checks["duration"] >= 2.0
    # unchanged inputs → nothing rebuilt
    monkeypatch.setattr(P, "claude", lambda *a, **k: pytest.fail("rebuilt an unchanged clip"))
    assert all("unchanged" in r for r in C.build_scene(run, plan, set()))

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
