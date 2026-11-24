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
                    {"clip_id": "s01c01", "video": str(section_videos["clip_01"]), "audio": str(tmp_path / "a1.mp3")},
                    {
                        "clip_id": "s01c02",
                        "video": str(section_videos["clip_02"]),
                        "audio": str(tmp_path / "a2.mp3"),
                        "lead_in": 0.2,
                    },
                    {"clip_id": "s01c03", "video": str(section_videos["clip_03"]), "audio": str(tmp_path / "a3.mp3")},
                ],
            }
        ]
    }
    report = assemble_clips.assemble(manifest, tmp_path / "final.mp4", tmp_path / "work", loudnorm=True)
    first_clip, second_clip = report["clips"]["s01c01"], report["clips"]["s01c02"]
    assert first_clip["video_padded_s"] > 0.3 and first_clip["out_s"] >= 3.0  # narration never cut off
    assert second_clip["audio_padded_s"] > 0.5 and abs(second_clip["out_s"] - second_clip["video_s"]) < 0.1
    assert abs(report["final_s"] - report["sum_clips_s"]) < 0.2  # no drift accumulated by concat


def colour_video(path, seconds, size="320x180"):
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=navy:s={size}:r=30:d={seconds}"]
        + ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)],
        check=True,
    )


def two_scene_manifest(tmp_path, **extra):
    for name in ("v1", "v2"):
        colour_video(tmp_path / f"{name}.mp4", 2)
    tone(tmp_path / "a.mp3", 1.5)
    tone(tmp_path / "pop.mp3", 0.3)
    return {
        "scenes": [
            {
                "scene_id": "s01",
                "clips": [
                    {
                        "clip_id": "s01c01",
                        "video": str(tmp_path / "v1.mp4"),
                        "audio": str(tmp_path / "a.mp3"),
                        "sound_effects": [{"file": str(tmp_path / "pop.mp3"), "at": 0.5, "volume_db": -6}],
                    }
                ],
            },
            {
                "scene_id": "s02",
                "clips": [{"clip_id": "s02c01", "video": str(tmp_path / "v2.mp4"), "audio": str(tmp_path / "a.mp3")}],
            },
        ],
        **extra,
    }


def test_scene_transitions_music_and_sound_effects_are_composed_at_assembly(tmp_path):
    tone(tmp_path / "music.mp3", 1.0)  # shorter than the video: it loops
    manifest = two_scene_manifest(
        tmp_path,
        transition={"style": "crossfade", "seconds": 0.5, "color": "#0e2733"},
        music={"file": str(tmp_path / "music.mp3"), "volume_db": -20},
    )
    report = assemble_clips.assemble(manifest, tmp_path / "final.mp4", tmp_path / "work", loudnorm=False)
    assert abs(report["final_s"] - (report["sum_clips_s"] - 0.5)) < 0.15  # the scenes overlap by the crossfade
    assert (report["transition"], report["music"], report["sound_effects"]) == ("crossfade", True, 1)

    manifest["transition"] = {"style": "fade", "seconds": 0.4, "color": "#0e2733"}
    report = assemble_clips.assemble(manifest, tmp_path / "faded.mp4", tmp_path / "work2", loudnorm=False)
    assert abs(report["final_s"] - report["sum_clips_s"]) < 0.15  # a fade through the background keeps the length


def test_mismatched_streams_are_refused_before_concatenation(tmp_path):
    manifest = two_scene_manifest(tmp_path)
    colour_video(tmp_path / "v2.mp4", 2, size="640x360")
    try:
        assemble_clips.assemble(manifest, tmp_path / "final.mp4", tmp_path / "work", loudnorm=False)
    except ValueError as error:
        assert "640x360" in str(error)
    else:
        raise AssertionError("a part with other stream parameters was concatenated")
