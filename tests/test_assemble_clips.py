import shutil
import subprocess
import sys
from conftest import FIXTURES_DIRECTORY, TOOLS_DIRECTORY

sys.path.insert(0, str(TOOLS_DIRECTORY))
import assemble_clips
import scene_harness


def tone(path, seconds):
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={seconds}",
            "-c:a",
            "libmp3lame",
            str(path),
        ],
        check=True,
    )


def test_per_clip_sync_bounds_drift(tmp_path):
    scene_directory = tmp_path / "s01"
    shutil.copytree(FIXTURES_DIRECTORY / "scene_s01", scene_directory)
    scene_harness.compose_scene(scene_directory, "s01")
    render_result = scene_harness.render_scene(scene_directory, "s01", None, "l")
    assert render_result["ok"]
    section_videos = {section["name"]: scene_directory / section["path"] for section in render_result["sections"]}
    # clip_01 video ≈2.5s with 3.0s narration (video must be padded); clip_02 ≈2.5s with 1.5s narration (audio padded)
    tone(tmp_path / "a1.mp3", 3.0)
    tone(tmp_path / "a2.mp3", 1.5)
    tone(tmp_path / "a3.mp3", 0.4)
    manifest = {
        "scenes": [
            {
                "scene_id": "s01",
                "clips": [
                    {"clip_id": "s01c01", "video": section_videos["clip_01"], "audio": tmp_path / "a1.mp3"},
                    {
                        "clip_id": "s01c02",
                        "video": section_videos["clip_02"],
                        "audio": tmp_path / "a2.mp3",
                        "lead_in": 0.2,
                    },
                    {"clip_id": "s01c03", "video": section_videos["clip_03"], "audio": tmp_path / "a3.mp3"},
                ],
            }
        ]
    }
    report = assemble_clips.assemble(manifest, tmp_path / "final.mp4", tmp_path / "work", loudnorm=True)
    first_clip, second_clip = report["clips"]["s01c01"], report["clips"]["s01c02"]
    assert first_clip["video_padded_s"] > 0.3 and first_clip["out_s"] >= 3.0  # narration never cut off
    assert second_clip["audio_padded_s"] > 0.5 and abs(second_clip["out_s"] - second_clip["video_s"]) < 0.1
    assert abs(report["final_s"] - report["sum_clips_s"]) < 0.2  # no drift accumulated by concat
