"""Clip pipeline without LLM calls: a fake agent writes real clip files; ./check gates + the jailed re-check run."""

import json
from pathlib import Path
import shutil
import subprocess

import pytest

from conftest import approve, make_plan, make_script, write_brief, write_critique, write_json_file

from app import narration, run_steps
from schemas.models import ScenePlan

CLIP_01 = '''from manim import *

def clip_01(self):
    self.beat(1)
    title = Text("Hello").to_edge(UP)
    self.play(Write(title), run_time=1)
    self.wait(2.2)
    self.reg["title"] = title
'''
CLIP_02 = '''from manim import *

def clip_02(self):
    title = self.entry("title", lambda: Text("Hello").to_edge(UP))
    self.beat(1)
    self.play(FadeOut(title), run_time=0.5)
    self.reg.pop("title")
    self.wait(2.7)
'''


def bwrap_works() -> bool:  # some CI kernels block unprivileged user namespaces
    return bool(shutil.which("bwrap")) and subprocess.run(["bwrap", "--ro-bind", "/", "/", "true"]).returncode == 0


def video_format(path):
    stream = json.loads(
        subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,avg_frame_rate",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )["streams"][0]
    return stream["width"], stream["height"], stream["avg_frame_rate"]


def run_with_approved_plans(run, clip_count=1, exits=None):
    """Brief → script (CP1) → one scene plan (CP2): the state in which voice and clip building may start."""
    write_brief(run, minutes=0.5, objectives=["understand the topic"])
    script = make_script(30)
    write_json_file(run / "script.json", script)
    write_json_file(run / "script_review.json", {"findings": []})
    approve(run, "script")
    plan = make_plan(script, 1, clip_count=clip_count, exits=exits)
    write_json_file(run / "scenes" / "s01" / "plan.json", plan)
    write_json_file(run / "plan_review.json", {"findings": []})
    write_critique(run, "s01", "plan", "pass")
    approve(run, "plan")
    return plan


def audio_index_for(run, plan, seconds=2.0):
    """The audio index `text-2-shorts voice` would write for this plan's current SSML."""
    return {
        clip["clip_id"]: {"hash": run_steps.voice_key(run, narration.speakable_ssml(clip["ssml"])), "seconds": seconds}
        for clip in plan["clips"]
    }


@pytest.mark.skipif(not bwrap_works(), reason="needs a working bubblewrap sandbox")
def test_task_accept_status_final(tmp_path, monkeypatch):
    run = tmp_path / "run"
    scene_directory = run / "scenes" / "s01"
    plan = run_with_approved_plans(run, clip_count=2, exits=[["title"], []])
    write_json_file(scene_directory / "audio" / "index.json", audio_index_for(run, plan))
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

    assert build_clip("s01c02", CLIP_02)["status"] == "READY"  # clips of a scene are built in parallel:
    assert build_clip("s01c01", CLIP_01)["status"] == "READY"  # clip_02 was built and checked before clip_01
    assert (scene_directory / "clips" / "clip_02.py").read_text() == CLIP_02
    checks = json.loads((scene_directory / "work" / "clip_02" / "checks" / "render.json").read_text())
    assert checks["ok"] and checks["duration"] >= 3.1  # lead-in + narration + hold
    assert video_format(scene_directory / "work" / "clip_02" / checks["video"]) == (1280, 720, "30/1")  # draft
    assert not [step for step in run_steps.next_steps(run) if "s01c0" in step]  # nothing stale
    unmarked = build_clip("s01c02", CLIP_02.replace("    self.beat(1)\n", ""))
    assert unmarked["status"] == "FAILED" and "probe: BEAT_MARKS_MISSING" in unmarked["open_findings"]
    assert build_clip("s01c02", "def clip_02(self):\n    pass\n")["status"] == "FAILED"  # too short → rejected
    assert (scene_directory / "clips" / "clip_02.py").read_text() == CLIP_02  # the approved clip stays installed
    assert any("s01c02" in step for step in run_steps.next_steps(run))
    build_clip("s01c02", CLIP_02)

    # CP3 → final: 720p30 scene preview + sync report + video critique, then the jailed 1440p render
    import argparse

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
    with pytest.raises(SystemExit, match="preview"):
        approve(run, "s01")  # CP3 needs the scene preview, the sync report and a video critique
    run_steps.handle_preview_command(argparse.Namespace(run=str(run), scene="s01"))
    preview = scene_directory / "preview.mp4"
    assert video_format(preview) == (1280, 720, "30/1")  # drafts: 720p30
    sync = json.loads((scene_directory / "sync.json").read_text())
    assert [clip["clip_id"] for clip in sync["clips"]] == ["s01c01", "s01c02"] and "in_sync" in sync
    with pytest.raises(SystemExit, match="video_critique"):
        approve(run, "s01")
    write_critique(run, "s01", "video", "pass")
    approve(run, "s01", force=not sync["in_sync"])  # the test audio is a tone: no word timings to sync
    run_steps.handle_final_command(argparse.Namespace(run=str(run), force=False))
    report = json.loads((run / "final_report.json").read_text())
    assert not [finding for finding in report["checks"] if finding["severity"] == "ERROR"], report["checks"]
    assert report["final_s"] >= 4.0
    assert {finding["code"] for finding in report["checks"]} <= {"LOUDNESS", "BLACK_FRAMES"}
    assert video_format(run / "final.mp4") == (2560, 1440, "120/1")  # delivery: 1440p at 120 fps


def test_next_steps_tracks_stale_audio_and_stale_approvals(tmp_path):
    plan = run_with_approved_plans(tmp_path)
    scene_directory = tmp_path / "scenes" / "s01"
    assert any("audio" in step for step in run_steps.next_steps(tmp_path))  # approved plan, no audio yet
    write_json_file(scene_directory / "audio" / "index.json", audio_index_for(tmp_path, plan))
    assert not any("audio" in step for step in run_steps.next_steps(tmp_path))

    scene_plan = ScenePlan.model_validate(plan)
    run_steps.update_state(
        tmp_path,
        lambda state: state["clips"].__setitem__(
            "s01c01", {"status": "READY", "key": run_steps.clip_key(tmp_path, scene_plan, scene_plan.clips[0])}
        ),
    )
    approve(tmp_path, "s01", force=True)  # (preview, sync and critique are covered elsewhere)
    assert not any("CP3" in step and "s01" in step for step in run_steps.next_steps(tmp_path))
    run_steps.add_feedback(tmp_path, "s01c01", "visual", "bigger")  # clip stale → approval stale
    steps = run_steps.next_steps(tmp_path)
    assert any("build s01c01" in step for step in steps) and any("CP3" in step and "s01" in step for step in steps)


def test_approve_refuses_unfinished_checkpoints(tmp_path):
    write_brief(tmp_path, objectives=["understand the topic"])
    with pytest.raises(SystemExit, match="script"):
        approve(tmp_path, "script")  # no script.json
    with pytest.raises(SystemExit, match="CP1"):
        approve(tmp_path, "plan")  # plans before the script is approved
    with pytest.raises(SystemExit, match="s01"):
        approve(tmp_path, "s01")  # clips not READY
    approve(tmp_path, "script", force=True)
    assert "script" in run_steps.load_state(tmp_path)["approved"]


def test_retiming_the_audio_keeps_the_clip_code_and_cp2_but_asks_cp3_again(tmp_path):
    plan = run_with_approved_plans(tmp_path)
    scene_directory = tmp_path / "scenes" / "s01"
    write_json_file(scene_directory / "audio" / "index.json", audio_index_for(tmp_path, plan))
    scene_plan = ScenePlan.model_validate(plan)
    key = run_steps.clip_key(tmp_path, scene_plan, scene_plan.clips[0])
    run_steps.update_state(
        tmp_path, lambda state: state["clips"].__setitem__("s01c01", {"status": "READY", "key": key})
    )
    approve(tmp_path, "s01", force=True)
    assert not any(step.startswith("CP3") for step in run_steps.next_steps(tmp_path))

    words = plan["clips"][0]["narration"].split()  # the audio-refactorer: same words, a new pause → new audio
    plan["clips"][0]["ssml"] = f'<speak>{words[0]} <break time="500ms"/> {" ".join(words[1:])}</speak>'
    write_json_file(scene_directory / "plan.json", plan)
    write_json_file(scene_directory / "audio" / "index.json", audio_index_for(tmp_path, plan, seconds=2.5))
    steps = run_steps.next_steps(tmp_path)
    assert not any(step.startswith(("CP1", "CP2", "build")) for step in steps)  # code and plan approvals still hold
    assert any(step.startswith("CP3") for step in steps)  # the scene's audio changed: preview again
