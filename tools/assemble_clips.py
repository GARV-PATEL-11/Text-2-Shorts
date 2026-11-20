#!/usr/bin/env python3
"""assemble_clips.py — clip-level audio/video assembly (deterministic, ffmpeg only).

For each clip: mux the clip's section video with the clip's narration audio. The shorter stream is
padded (video: freeze last frame; audio: silence) so A/V drift can never accumulate across clips —
drift is bounded per clip by the timing checker's tolerance, instead of per scene as today.
Then concatenates clips → scene, scenes → video, and applies EBU R128 loudness normalisation once.

Usage:
  python tools/assemble_clips.py --manifest assembly.json --out final.mp4
  assembly.json = {"scenes": [{"scene_id": "s01", "clips": [{"clip_id": "s01c01",
                   "video": ".../Scene01_0000_clip_01.mp4", "audio": ".../s01c01.mp3",
                   "lead_in": 0.25, "tail": 0.35}]}]}
Status: IMPLEMENTED in this package (tests/test_assemble_clips.py).
"""

from __future__ import annotations
import argparse
import json
import subprocess
import tempfile
from pathlib import Path


def probe_duration_seconds(path) -> float:
    return float(
        subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )


def mux_clip(video: Path, audio: Path, output_path: Path, lead_in: float = 0.0, tail: float = 0.0) -> dict:
    video_seconds, audio_seconds = probe_duration_seconds(video), probe_duration_seconds(audio)
    audio_total_seconds = lead_in + audio_seconds + tail
    total_seconds = max(video_seconds, audio_total_seconds)
    filter_graph = (
        f"[0:v]tpad=stop_mode=clone:stop_duration={max(0.0, total_seconds - video_seconds):.3f}[v];"
        f"[1:a]adelay={int(lead_in * 1000)}:all=1,apad[a]"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(video),
            "-i",
            str(audio),
            "-filter_complex",
            filter_graph,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-t",
            f"{total_seconds:.3f}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(output_path),
        ],
        check=True,
    )
    return {
        "video_s": round(video_seconds, 3),
        "audio_s": round(audio_seconds, 3),
        "out_s": round(probe_duration_seconds(output_path), 3),
        "video_padded_s": round(max(0.0, total_seconds - video_seconds), 3),
        "audio_padded_s": round(max(0.0, total_seconds - audio_total_seconds), 3),
    }


def concatenate_videos(parts: list[Path], output_path: Path) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as list_file:
        list_file.write("".join(f"file '{part.resolve()}'\n" for part in parts))
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            list_file.name,
            "-c",
            "copy",
            str(output_path),
        ],
        check=True,
    )


def assemble(manifest: dict, output_path: Path, work_directory: Path, loudnorm: bool = True) -> dict:
    work_directory.mkdir(parents=True, exist_ok=True)
    report, scene_files = {"clips": {}}, []
    for scene in manifest["scenes"]:
        parts = []
        for clip in scene["clips"]:
            part = work_directory / f"{clip['clip_id']}.mp4"
            report["clips"][clip["clip_id"]] = mux_clip(
                Path(clip["video"]), Path(clip["audio"]), part, clip.get("lead_in", 0.0), clip.get("tail", 0.0)
            )
            parts.append(part)
        scene_out = work_directory / f"{scene['scene_id']}.mp4"
        concatenate_videos(parts, scene_out)
        scene_files.append(scene_out)
    raw_video = work_directory / "video_raw.mp4"
    concatenate_videos(scene_files, raw_video)
    if loudnorm:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(raw_video),
                "-c:v",
                "copy",
                "-af",
                "loudnorm=I=-16:TP=-1.5:LRA=11",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                str(output_path),
            ],
            check=True,
        )
    else:
        raw_video.replace(output_path)
    report["final_s"] = round(probe_duration_seconds(output_path), 3)
    report["sum_clips_s"] = round(sum(clip["out_s"] for clip in report["clips"].values()), 3)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--workdir", default="assembly_work")
    parser.add_argument("--no-loudnorm", action="store_true")
    arguments = parser.parse_args()
    report = assemble(
        json.loads(Path(arguments.manifest).read_text()),
        Path(arguments.out),
        Path(arguments.workdir),
        not arguments.no_loudnorm,
    )
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
