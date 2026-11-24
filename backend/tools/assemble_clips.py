#!/usr/bin/env python3
"""assemble_clips.py — clip-level audio/video assembly (deterministic, ffmpeg only).

For each clip: mux the clip's section video with the clip's narration audio. The shorter stream is
padded (video: freeze last frame; audio: silence) so A/V drift can never accumulate across clips —
drift is bounded per clip by the timing checker's tolerance, instead of per scene as today.
A clip's sound effects (the user's own files) are mixed into its audio. Every part must have the same stream
parameters before concatenation. Clips → scene by concat; scenes → video with the template's transition (cut, fade
through the background colour, or crossfade); the user's background music is looped under the voice; then EBU R128
loudness normalisation once.

Usage:
  python backend/tools/assemble_clips.py --manifest assembly.json --out final.mp4
  assembly.json = {"scenes": [{"scene_id": "s01", "clips": [{"clip_id": "s01c01",
                   "video": ".../Scene01_0000_clip_01.mp4", "audio": ".../s01c01.mp3",
                   "lead_in": 0.25, "tail": 0.35, "sound_effects": [{"file": "pop.mp3", "at": 1.2,
                   "volume_db": -6}]}]}], "transition": {"style": "fade", "seconds": 0.5, "color": "#0e2733"},
                   "music": {"file": "music.mp3", "volume_db": -24}}
Status: IMPLEMENTED in this package (tests/test_assemble_clips.py).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from schemas.media import AssemblyManifest


def probe_duration_seconds(path) -> float:
    return float(
        subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )


def mux_clip(
    video: Path, audio: Path, output_path: Path, lead_in: float = 0.0, tail: float = 0.0, sound_effects=()
) -> dict:
    video_seconds, audio_seconds = probe_duration_seconds(video), probe_duration_seconds(audio)
    audio_total_seconds = lead_in + audio_seconds + tail
    total_seconds = max(video_seconds, audio_total_seconds)
    effects = "".join(
        f"[{i}:a]adelay={int(effect['at'] * 1000)}:all=1,volume={effect.get('volume_db', 0)}dB[e{i}];"
        for i, effect in enumerate(sound_effects, 2)
    )
    mix = "".join(f"[e{i}]" for i in range(2, 2 + len(sound_effects)))
    filter_graph = (
        f"[0:v]tpad=stop_mode=clone:stop_duration={max(0.0, total_seconds - video_seconds):.3f}[v];"
        f"[1:a]adelay={int(lead_in * 1000)}:all=1,apad[voice];{effects}"
        + (
            f"[voice]{mix}amix=inputs={1 + len(sound_effects)}:duration=first:normalize=0[a]"
            if mix
            else "[voice]anull[a]"
        )
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
            *[argument for effect in sound_effects for argument in ("-i", str(effect["file"]))],
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


def stream_parameters(path: Path) -> str:
    """What concatenation needs to match: frame size, frame rate, pixel format, sample rate, channels."""
    streams = json.loads(
        subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )["streams"]
    video = next((stream for stream in streams if stream["codec_type"] == "video"), {})
    audio = next((stream for stream in streams if stream["codec_type"] == "audio"), {})
    return (
        f"{video.get('width')}x{video.get('height')} {video.get('r_frame_rate')} {video.get('pix_fmt')} "
        f"{audio.get('sample_rate')}Hz {audio.get('channels')}ch"
    )


def run_ffmpeg(*arguments: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *arguments], check=True)


def join_scenes(scene_files: list[Path], output_path: Path, transition: dict) -> None:
    """cut = plain concat; fade = each scene fades through the background colour (length kept); crossfade = the
    scenes overlap by `seconds` (video xfade, audio acrossfade)."""
    style, seconds, colour = transition.get("style", "cut"), transition.get("seconds", 0.5), transition.get("color")
    if style == "cut" or len(scene_files) < 2 or seconds <= 0:
        concatenate_videos(scene_files, output_path)
        return
    if style == "fade":
        faded = []
        for number, scene_file in enumerate(scene_files):
            fades = []
            if number > 0:
                fades.append(f"fade=t=in:st=0:d={seconds}:color={colour or 'black'}")
            if number < len(scene_files) - 1:
                start = probe_duration_seconds(scene_file) - seconds
                fades.append(f"fade=t=out:st={start:.3f}:d={seconds}:color={colour or 'black'}")
            faded.append(scene_file.with_name(scene_file.stem + "_faded.mp4"))
            run_ffmpeg(
                "-i",
                str(scene_file),
                "-vf",
                ",".join(fades),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "copy",
                str(faded[-1]),
            )
        concatenate_videos(faded, output_path)
        return
    graph, video_label, audio_label, offset = [], "0:v", "0:a", 0.0
    for number, scene_file in enumerate(scene_files[1:], 1):
        offset += probe_duration_seconds(scene_files[number - 1]) - seconds
        graph.append(
            f"[{video_label}][{number}:v]xfade=transition=fade:duration={seconds}:offset={offset:.3f}[v{number}]"
        )
        graph.append(f"[{audio_label}][{number}:a]acrossfade=d={seconds}[a{number}]")
        video_label, audio_label = f"v{number}", f"a{number}"
    run_ffmpeg(
        *[argument for scene_file in scene_files for argument in ("-i", str(scene_file))],
        "-filter_complex",
        ";".join(graph),
        "-map",
        f"[{video_label}]",
        "-map",
        f"[{audio_label}]",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-ar",
        "48000",
        str(output_path),
    )


def add_music(video: Path, music: dict, output_path: Path) -> None:
    """The user's music file, looped under the whole video at `volume_db`."""
    run_ffmpeg(
        "-i",
        str(video),
        "-stream_loop",
        "-1",
        "-i",
        str(music["file"]),
        "-filter_complex",
        f"[1:a]volume={music.get('volume_db', -24)}dB[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
        "-map",
        "0:v",
        "-map",
        "[a]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-ar",
        "48000",
        str(output_path),
    )


def assemble(manifest: dict, output_path: Path, work_directory: Path, loudnorm: bool = True) -> dict:
    manifest = AssemblyManifest.model_validate(manifest).model_dump()  # the contract, with every default filled in
    work_directory.mkdir(parents=True, exist_ok=True)
    report: dict = {"clips": {}, "sound_effects": 0}
    scene_parts = []
    for scene in manifest["scenes"]:
        parts = []
        for clip in scene["clips"]:
            part = work_directory / f"{clip['clip_id']}.mp4"
            effects = clip.get("sound_effects", [])
            report["clips"][clip["clip_id"]] = mux_clip(
                Path(clip["video"]),
                Path(clip["audio"]),
                part,
                clip.get("lead_in", 0.0),
                clip.get("tail", 0.0),
                effects,
            )
            report["sound_effects"] += len(effects)
            parts.append(part)
        scene_parts.append((scene["scene_id"], parts))
    parameters = {part.stem: stream_parameters(part) for _, parts in scene_parts for part in parts}
    if len(set(parameters.values())) > 1:
        raise ValueError(
            "parts differ in stream parameters (size, rate, pixel format, audio): "
            + "; ".join(f"{name} {value}" for name, value in parameters.items())
        )
    scene_files = []
    for scene_id, parts in scene_parts:
        scene_files.append(work_directory / f"{scene_id}.mp4")
        concatenate_videos(parts, scene_files[-1])
    raw_video = work_directory / "video_raw.mp4"
    transition = manifest.get("transition") or {"style": "cut"}
    join_scenes(scene_files, raw_video, transition)
    report["transition"], report["music"] = transition.get("style", "cut"), bool(manifest.get("music"))
    if manifest.get("music"):
        mixed = work_directory / "video_music.mp4"
        add_music(raw_video, manifest["music"], mixed)
        raw_video = mixed
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
