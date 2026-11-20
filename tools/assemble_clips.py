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
import argparse, json, subprocess, tempfile
from pathlib import Path


def probe(path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(path)], capture_output=True, text=True, check=True).stdout.strip())


def mux_clip(video: Path, audio: Path, out: Path, lead_in: float = 0.0, tail: float = 0.0) -> dict:
    v, au = probe(video), probe(audio)
    a_total = lead_in + au + tail
    total = max(v, a_total)
    filt = (f"[0:v]tpad=stop_mode=clone:stop_duration={max(0.0, total - v):.3f}[v];"
            f"[1:a]adelay={int(lead_in * 1000)}:all=1,apad[a]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(audio), "-filter_complex", filt,
                    "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-r", "30", "-c:a", "aac", "-ar", "48000", "-ac", "2", str(out)], check=True)
    return {"video_s": round(v, 3), "audio_s": round(au, 3), "out_s": round(probe(out), 3),
            "video_padded_s": round(max(0.0, total - v), 3), "audio_padded_s": round(max(0.0, total - a_total), 3)}


def concat(parts: list[Path], out: Path) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("".join(f"file '{p.resolve()}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f.name, "-c", "copy",
                    str(out)], check=True)


def assemble(manifest: dict, out: Path, workdir: Path, loudnorm: bool = True) -> dict:
    workdir.mkdir(parents=True, exist_ok=True)
    report, scene_files = {"clips": {}}, []
    for sc in manifest["scenes"]:
        parts = []
        for c in sc["clips"]:
            part = workdir / f"{c['clip_id']}.mp4"
            report["clips"][c["clip_id"]] = mux_clip(Path(c["video"]), Path(c["audio"]), part,
                                                     c.get("lead_in", 0.0), c.get("tail", 0.0))
            parts.append(part)
        scene_out = workdir / f"{sc['scene_id']}.mp4"; concat(parts, scene_out); scene_files.append(scene_out)
    raw = workdir / "video_raw.mp4"; concat(scene_files, raw)
    if loudnorm:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-c:v", "copy", "-af",
                        "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-ar", "48000", str(out)], check=True)
    else:
        raw.replace(out)
    report["final_s"] = round(probe(out), 3)
    report["sum_clips_s"] = round(sum(c["out_s"] for c in report["clips"].values()), 3)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--workdir", default="assembly_work"); ap.add_argument("--no-loudnorm", action="store_true")
    a = ap.parse_args()
    r = assemble(json.loads(Path(a.manifest).read_text()), Path(a.out), Path(a.workdir), not a.no_loudnorm)
    print(json.dumps(r, indent=1))


if __name__ == "__main__":
    main()
