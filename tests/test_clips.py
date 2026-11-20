"""Clip pipeline without LLM calls: a fake agent writes real clip files; ./check gates + the jailed re-check run."""

import json
from pathlib import Path
import shutil
import subprocess

import pytest

from app import cli
from app import run_steps
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
    return {
        "clip_id": f"s01c{i:02d}",
        "index": i,
        "objective": "o",
        "narration": "n",
        "visual_intent": "v",
        "beats": ["b"],
        "entry": {"persistent_objects": entry},
        "exit": {"persistent_objects": exit_},
        "est_seconds": 2,
    }


def bwrap_works() -> bool:  # some CI kernels block unprivileged user namespaces
    return bool(shutil.which("bwrap")) and subprocess.run(["bwrap", "--ro-bind", "/", "/", "true"]).returncode == 0


def outline_segment(i, seconds):
    return {
        "scene_id": i,
        "segment_type": "concept",
        "title": f"t{i}",
        "duration_seconds": seconds,
        "talking_points": ["p"],
        "visual_plan": "v",
        "narration_hint": "n",
        "transition_to_next": None,
    }


def outline(*scene_seconds):
    return {
        "meta": {
            "title": "T",
            "topic": "t",
            "total_duration_seconds": sum(scene_seconds),
            "pace": "medium",
            "target_wpm": 150,
            "approach_name": "zoom",
            "approach_style": "s",
        },
        "outline": [outline_segment(i, seconds) for i, seconds in enumerate(scene_seconds, 1)],
    }


def test_validate_outline_plan_and_math(tmp_path):
    run = tmp_path
    cli.write_json(run / "brief.json", {"approach": "zoom", "minutes": 1})
    cli.write_json(run / "outline.json", outline(30, 30))
    assert run_steps.validate_outline(run) == []
    cli.write_json(run / "outline.json", outline(60, 60))
    assert any("120s" in error for error in run_steps.validate_outline(run))  # 2x the 60 s target
    cli.write_json(run / "outline.json", {"meta": {}, "outline": []})
    assert run_steps.validate_outline(run)  # schema errors

    first_plan = {
        "scene_id": "s01",
        "index": 1,
        "title": "t",
        "objective": "o",
        "segment_type": "x",
        "color_roles": {"a": "BLUE"},
        "clips": [clip(1, [], [])],
    }
    (run / "scenes" / "s01").mkdir(parents=True)
    (run / "scenes" / "s01" / "plan.json").write_text(json.dumps(first_plan))
    assert run_steps.validate_plan(run, "s01") == []
    second_plan = {
        **first_plan,
        "scene_id": "s02",
        "index": 2,
        "color_roles": {"a": "RED"},
        "clips": [{**clip(1, ["x"], []), "clip_id": "s02c01"}],
    }
    (run / "scenes" / "s02").mkdir()
    (run / "scenes" / "s02" / "plan.json").write_text(json.dumps(second_plan))
    errors = run_steps.validate_plan(run, "s02")
    assert any("entry must be empty" in error for error in errors) and any(
        "`a`" in error and "BLUE" in error for error in errors
    )

    (run / "math.json").write_text('{"findings": [{"clip_id": "s09c01"}]}')
    assert run_steps.validate_math(run)
    (run / "math.json").write_text('{"findings": []}')
    assert run_steps.validate_math(run) == []


@pytest.mark.skipif(not bwrap_works(), reason="needs a working bubblewrap sandbox")
def test_task_accept_status_final(tmp_path, monkeypatch):
    run = tmp_path / "run"
    scene_directory = run / "scenes" / "s01"
    (scene_directory / "audio").mkdir(parents=True)
    plan = ScenePlan.model_validate(
        {
            "scene_id": "s01",
            "index": 1,
            "title": "t",
            "objective": "o",
            "segment_type": "x",
            "clips": [clip(1, [], ["title"]), clip(2, ["title"], [])],
        }
    )
    (scene_directory / "plan.json").write_text(plan.model_dump_json())
    cli.write_json(run / "brief.json", {"font": None})
    voice_hash = run_steps.voice_key(run, "n")  # audio made from the current narration ("n")
    cli.write_json(
        scene_directory / "audio" / "index.json",
        {"s01c01": {"hash": voice_hash, "seconds": 2.0}, "s01c02": {"hash": voice_hash, "seconds": 2.0}},
    )
    run_steps.ensure_api_index()

    def build_clip(clip_id, code):  # what the clip-builder subagent does: write the file in the prepared work dir
        work_directory = run_steps.prepare_clip(run, clip_id)
        task = (work_directory / "TASK.md").read_text()
        assert "CLIP_SECONDS: 3.1" in task and (work_directory / "check").exists()
        read_first = [
            Path(entry_text.strip()) for entry_text in task.split("READ FIRST:")[1].splitlines()[0].split(",")
        ]
        assert len(read_first) == 4 and all(path.exists() for path in read_first)  # standards + 3 always-on cards
        (work_directory / f"clip_{clip_id[-2:]}.py").write_text(code)
        return run_steps.accept_clip(run, clip_id)

    with pytest.raises(SystemExit, match="s01c01"):
        run_steps.prepare_clip(run, "s01c02")  # clips are built in order
    assert build_clip("s01c01", CLIP_01)["status"] == "READY"
    assert build_clip("s01c02", CLIP_02)["status"] == "READY"
    assert (scene_directory / "clips" / "clip_02.py").read_text() == CLIP_02
    checks = json.loads((scene_directory / "work" / "clip_02" / "checks" / "render.json").read_text())
    assert checks["ok"] and checks["duration"] >= 3.1  # lead-in + narration + hold
    assert not [step for step in run_steps.next_steps(run) if "s01c0" in step]  # nothing stale
    assert build_clip("s01c02", "def clip_02(self):\n    pass\n")["status"] == "FAILED"  # too short → rejected
    assert (scene_directory / "clips" / "clip_02.py").read_text() == CLIP_02  # the approved clip stays installed
    assert any("s01c02" in step for step in run_steps.next_steps(run))
    build_clip("s01c02", CLIP_02)

    # CP3 → final: jailed 1440p section render, per-clip A/V mux, loudnorm, media checks
    import argparse
    import subprocess

    for i in (1, 2):
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=2",
                str(scene_directory / "audio" / f"clip_{i:02d}.mp3"),
            ],
            check=True,
        )
    with pytest.raises(SystemExit, match="not approved"):
        run_steps.handle_final_command(argparse.Namespace(run=str(run), force=False))
    run_steps.handle_approve_command(argparse.Namespace(run=str(run), target="s01", force=False))
    run_steps.handle_final_command(argparse.Namespace(run=str(run), force=False))
    report = json.loads((run / "final_report.json").read_text())
    assert not [finding for finding in report["checks"] if finding["severity"] == "ERROR"], report["checks"]
    assert report["final_s"] >= 4.0


def test_next_steps_tracks_missing_plans_stale_audio_and_stale_approvals(tmp_path):
    import argparse

    run = tmp_path
    cli.write_json(
        run / "brief.json",
        {"approach": "zoom", "minutes": 1, "tts": "polly", "voice": "Matthew", "engine": "neural", "font": None},
    )
    cli.write_json(run / "outline.json", outline(30, 30))
    scene_directory = run / "scenes" / "s01"
    (scene_directory / "audio").mkdir(parents=True)
    plan = {
        "scene_id": "s01",
        "index": 1,
        "title": "t",
        "objective": "o",
        "segment_type": "x",
        "clips": [clip(1, [], [])],
    }
    (scene_directory / "plan.json").write_text(json.dumps(plan))
    assert any(step.startswith("s02") for step in run_steps.next_steps(run))  # outline has 2 scenes, 1 plan

    cli.write_json(
        scene_directory / "audio" / "index.json", {"s01c01": {"hash": run_steps.voice_key(run, "n"), "seconds": 2.0}}
    )
    assert not any("audio" in step for step in run_steps.next_steps(run))
    (scene_directory / "plan.json").write_text(
        json.dumps({**plan, "clips": [{**clip(1, [], []), "narration": "new words"}]})
    )
    assert any("s01" in step and "audio" in step for step in run_steps.next_steps(run))  # narration edited → voice

    (scene_directory / "plan.json").write_text(json.dumps(plan))
    run_steps.update_state(
        run,
        lambda state: state["clips"].__setitem__(
            "s01c01",
            {
                "status": "READY",
                "key": run_steps.clip_key(
                    run, run_steps.ScenePlan.model_validate(plan), run_steps.ScenePlan.model_validate(plan).clips[0]
                ),
            },
        ),
    )
    run_steps.handle_approve_command(argparse.Namespace(run=str(run), target="s01", force=False))
    assert not any("CP3" in step and "s01" in step for step in run_steps.next_steps(run))
    run_steps.add_feedback(run, "s01c01", "visual", "bigger")  # clip stale → approval stale
    steps = run_steps.next_steps(run)
    assert any("build s01c01" in step for step in steps) and any("CP3" in step and "s01" in step for step in steps)


def test_approve_refuses_unfinished_checkpoints(tmp_path):
    import argparse

    run = tmp_path
    cli.write_json(run / "brief.json", {"approach": "zoom", "minutes": 1})

    def approve(target, force=False):
        run_steps.handle_approve_command(argparse.Namespace(run=str(run), target=target, force=force))

    with pytest.raises(SystemExit, match="outline"):
        approve("outline")  # no outline.json
    with pytest.raises(SystemExit, match="math"):
        approve("plan")  # no plans / math review
    with pytest.raises(SystemExit, match="s01"):
        approve("s01")  # clips not READY
    approve("outline", force=True)
    assert "outline" in run_steps.load_state(run)["approved"]
