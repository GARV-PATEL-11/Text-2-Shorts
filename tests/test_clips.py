"""Scene code pipeline without LLM calls: a fake agent writes a real scene_code.py; ./check gates + the jailed re-check run."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from app import narration
from app.commands import production_commands
from app.workflow import change_requests, fingerprints, ledger, production, scene_code, status
from conftest import approve, approved_outline, make_plan, make_script, write_brief, write_critique, write_json_file
from schemas.plans import ScenePlan
from schemas.run_state import ClipBuild

SCENE_CODE = '''from manim import *

CLIP_1_SECONDS = 3.2
CLIP_2_SECONDS = 3.2


class Scene01(Scene):
    def _build_objects(self):
        self.title = Text("Hello").to_edge(UP)

    def _clip_1(self):
        self.beat(1)
        self.play(Write(self.title), run_time=1)
        self.wait(CLIP_1_SECONDS - 1)

    def _clip_2(self):
        self.beat(1)
        self.play(FadeOut(self.title), run_time=0.5)
        self.wait(CLIP_2_SECONDS - 0.5)

    def construct(self):
        self._build_objects()
        self._clip_1()
        self._clip_2()
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
    approved_outline(run, (30,))
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
        clip["clip_id"]: {"hash": production.voice_key(run, narration.speakable_ssml(clip["ssml"])), "seconds": seconds}
        for clip in plan["clips"]
    }


@pytest.mark.skipif(not bwrap_works(), reason="needs a working bubblewrap sandbox")
def test_task_accept_status_final(tmp_path, monkeypatch):
    run = tmp_path / "run"
    scene_directory = run / "scenes" / "s01"
    plan = run_with_approved_plans(run, clip_count=2, exits=[["title"], []])
    write_json_file(scene_directory / "audio" / "index.json", audio_index_for(run, plan))
    scene_code.ensure_api_index()
    work = scene_directory / "work"

    def build_scene(code):  # what the scene-builder subagent does: write scene_code.py in the prepared work folder
        task = scene_code.prepare_scene(run, "s01")
        assert "exactly 3.1s" in task and "Scene01" in task and (work / "check").exists()
        read_first = [
            Path(entry.strip()) for entry in task.split("READ FIRST, in this order:")[1].splitlines()[0].split(",")
        ]
        assert len(read_first) == 4 and all(path.exists() for path in read_first)  # codegen-system + 3 Manim references
        (work / "scene_code.py").write_text(code)
        return scene_code.accept_scene(run, "s01")

    assert build_scene(SCENE_CODE).status == "READY"
    assert (scene_directory / "scene_code.py").read_text() == SCENE_CODE
    checks = json.loads((work / "checks" / "render.json").read_text())
    assert checks["ok"] and checks["durations"]["clip_02"] >= 3.1  # lead-in + narration + hold
    assert video_format(work / checks["videos"]["clip_02"]) == (1280, 720, "30/1")  # draft
    assert not [step for step in status.next_steps(run) if "build" in step]  # nothing stale
    too_short = SCENE_CODE.replace("        self.wait(CLIP_2_SECONDS - 0.5)\n", "")
    failed = build_scene(too_short)
    assert failed.status == "FAILED" and "probe: CLIP_TOO_SHORT" in failed.open_findings
    missing = SCENE_CODE.replace("        self._clip_2()\n", "")
    assert build_scene(missing).status == "FAILED"  # a planned clip that never runs → rejected
    assert (scene_directory / "scene_code.py").read_text() == SCENE_CODE  # the accepted file stays installed
    assert any("build s01" in step for step in status.next_steps(run))
    build_scene(SCENE_CODE)

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
        production_commands.handle_final_command(argparse.Namespace(run=str(run), force=False))
    with pytest.raises(SystemExit, match="preview"):
        approve(run, "scenes")  # CP3 needs the scene preview, the sync report and a video critique
    production_commands.handle_preview_command(argparse.Namespace(run=str(run), scene="s01"))
    preview = scene_directory / "preview.mp4"
    assert video_format(preview) == (1280, 720, "30/1")  # drafts: 720p30
    sync = json.loads((scene_directory / "sync.json").read_text())
    assert [clip["clip_id"] for clip in sync["clips"]] == ["s01c01", "s01c02"] and "in_sync" in sync
    with pytest.raises(SystemExit, match="video_critique"):
        approve(run, "scenes")
    write_critique(run, "s01", "video", "pass")
    approve(run, "scenes", force=not sync["in_sync"])  # the test audio is a tone: no word timings to sync
    production_commands.handle_final_command(argparse.Namespace(run=str(run), force=False))
    report = json.loads((run / "final_report.json").read_text())
    assert not [finding for finding in report["checks"] if finding["severity"] == "ERROR"], report["checks"]
    assert report["final_s"] >= 4.0
    allowed = {"LOUDNESS", "BLACK_FRAMES", "DURATION"}  # the test narration is a short tone, not the scripted length
    assert {finding["code"] for finding in report["checks"]} <= allowed
    assert video_format(run / "final.mp4") == (2560, 1440, "120/1")  # delivery: 1440p at 120 fps


def test_next_steps_tracks_stale_audio_and_stale_approvals(tmp_path):
    plan = run_with_approved_plans(tmp_path)
    scene_directory = tmp_path / "scenes" / "s01"
    assert any("audio" in step for step in status.next_steps(tmp_path))  # approved plan, no audio yet
    write_json_file(scene_directory / "audio" / "index.json", audio_index_for(tmp_path, plan))
    assert not any("audio" in step for step in status.next_steps(tmp_path))

    scene_plan = ScenePlan.model_validate(plan)
    ledger.update_state(
        tmp_path,
        lambda state: state.clips.__setitem__(
            "s01c01", ClipBuild(status="READY", key=fingerprints.clip_key(tmp_path, scene_plan, scene_plan.clips[0]))
        ),
    )
    approve(tmp_path, "scenes", force=True)  # CP3: all scenes at once (preview, sync and critique: covered elsewhere)
    assert not any("CP3" in step for step in status.next_steps(tmp_path))
    change_requests.add_request(tmp_path, "s01c01", "visual", "bigger")  # clip stale → approval stale
    steps = status.next_steps(tmp_path)
    assert any("build s01" in step for step in steps) and any("CP3" in step for step in steps)


def test_approve_refuses_unfinished_checkpoints(tmp_path):
    write_brief(tmp_path, objectives=["understand the topic"])
    with pytest.raises(SystemExit, match="outline"):
        approve(tmp_path, "outline")  # no topics, content or outline yet
    with pytest.raises(SystemExit, match="script"):
        approve(tmp_path, "script")  # no script.json
    with pytest.raises(SystemExit, match="CP1"):
        approve(tmp_path, "plan")  # plans before the script is approved
    with pytest.raises(SystemExit, match="no scene plans"):
        approve(tmp_path, "scenes")  # clips not READY
    approve(tmp_path, "script", force=True)
    assert "script" in ledger.load_state(tmp_path).approved


def test_retiming_the_audio_keeps_the_clip_code_and_cp2_but_asks_cp3_again(tmp_path):
    plan = run_with_approved_plans(tmp_path)
    scene_directory = tmp_path / "scenes" / "s01"
    write_json_file(scene_directory / "audio" / "index.json", audio_index_for(tmp_path, plan))
    scene_plan = ScenePlan.model_validate(plan)
    key = fingerprints.clip_key(tmp_path, scene_plan, scene_plan.clips[0])
    ledger.update_state(tmp_path, lambda state: state.clips.__setitem__("s01c01", ClipBuild(status="READY", key=key)))
    approve(tmp_path, "scenes", force=True)
    assert not any(step.startswith("CP3") for step in status.next_steps(tmp_path))

    words = plan["clips"][0]["narration"].split()  # the audio-refactorer: same words, a new pause → new audio
    plan["clips"][0]["ssml"] = f'<speak>{words[0]} <break time="500ms"/> {" ".join(words[1:])}</speak>'
    write_json_file(scene_directory / "plan.json", plan)
    write_json_file(scene_directory / "audio" / "index.json", audio_index_for(tmp_path, plan, seconds=2.5))
    steps = status.next_steps(tmp_path)
    assert not any(step.startswith(("CP1", "CP2", "build")) for step in steps)  # code and plan approvals still hold
    assert any(step.startswith("CP3") for step in steps)  # the scene's audio changed: preview again
