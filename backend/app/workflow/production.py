"""Media production: stale audio, scene section renders, the preview sync report, final assembly manifests and the
delivery media checks."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from pydantic import ValidationError
from schemas.media import (
    FinalReport,
    ManifestClip,
    ManifestScene,
    MediaFinding,
    SceneRender,
    SyncBeat,
    SyncClip,
    SyncReport,
)
from schemas.plans import ScenePlan

from app import narration
from app.config import (
    FINAL_FRAME_RATE,
    PYTHON_EXECUTABLE,
    SYNC_TOLERANCE_SECONDS,
    TOOLS_DIRECTORY,
    VOICE_LEAD_IN_SECONDS,
)
from app.sandbox import render_jail_prefix
from app.utilities import content_hash
from app.workflow.artifacts import load_audio_index, load_brief, load_gate_result, load_script, load_sync_report
from app.workflow.fingerprints import scene_video_hash
from app.workflow.preferences import clip_speech
from app.workflow.templates import drawing, install_template, sound


def voice_key(run: Path, spoken: str) -> str:
    if load_brief(run) is None:
        raise SystemExit("brief.json is missing or invalid: `text-2-shorts validate . brief`")
    return content_hash(spoken, sound(run))


def stale_audio(run: Path, plans: list[ScenePlan]) -> set[str]:
    """Clips whose audio is missing or was made from different narration text/voice."""
    pairs = narration.case_pairs([clip.narration for plan in plans for clip in plan.clips])
    stale_clip_ids = set()
    for plan in plans:
        audio_index = load_audio_index(run, plan.scene_id)
        stale_clip_ids |= {
            clip.clip_id
            for clip in plan.clips
            if clip.clip_id not in audio_index
            or audio_index[clip.clip_id].hash != voice_key(run, clip_speech(run, clip.ssml, pairs))
        }
    return stale_clip_ids


def render_scene_sections(run: Path, plan: ScenePlan, quality: str, fps: int | None, media: str) -> SceneRender:
    """Wrap the scene's accepted code (scene_code.py) and render every clip as a section, in a network-less jail."""
    scene_directory = run / "scenes" / plan.scene_id
    install_template(run)  # the renderer the harness draws the backdrop with, in the run environment
    subprocess.run(
        [
            PYTHON_EXECUTABLE,
            str(TOOLS_DIRECTORY / "scene_harness.py"),
            "compose",
            str(scene_directory),
            "--scene-id",
            plan.scene_id,
        ],
        check=True,
        capture_output=True,
    )
    shutil.rmtree(scene_directory / media, ignore_errors=True)
    render_process = subprocess.run(
        render_jail_prefix()
        + [
            "--bind",
            str(scene_directory),
            str(scene_directory),
            "--setenv",
            "TEXT_2_SHORTS_LOOK",
            json.dumps(drawing(run)),
            PYTHON_EXECUTABLE,
            str(TOOLS_DIRECTORY / "scene_harness.py"),
            "render",
            str(scene_directory),
            "--scene-id",
            plan.scene_id,
            "--quality",
            quality,
            "--media",
            media,
        ]
        + (["--fps", str(fps)] if fps else []),
        capture_output=True,
        text=True,
        timeout=7200,
    )
    try:
        return SceneRender.model_validate_json(render_process.stdout)
    except ValidationError:
        return SceneRender(ok=False, stderr_tail=render_process.stderr[-2000:])


def scene_manifest(run: Path, plan: ScenePlan, render: SceneRender) -> ManifestScene:
    """One scene for backend/tools/assemble_clips.py: each clip's section video with its narration audio."""
    scene_directory = run / "scenes" / plan.scene_id
    sections = {section.name: section.path for section in render.sections}
    return ManifestScene(
        scene_id=plan.scene_id,
        clips=[
            ManifestClip(
                clip_id=clip.clip_id,
                video=str(scene_directory / sections[f"clip_{clip.index:02d}"]),
                audio=str(scene_directory / "audio" / f"clip_{clip.index:02d}.mp3"),
                lead_in=VOICE_LEAD_IN_SECONDS,
                sound_effects=[
                    effect.model_copy(update={"file": str(run / effect.file)}) for effect in clip.sound_effects
                ],
            )
            for clip in plan.clips
        ],
    )


def sync_report(run: Path, plan: ScenePlan, video_seconds: dict[str, float]) -> SyncReport:
    """Per clip and beat: when the voice says the beat's phrase vs when the animation marks it (optional self.beat),
    whether the audio fits the clip's video, and the scene-builder's notes on what it changed from the plan."""
    scene_directory = run / "scenes" / plan.scene_id
    audio_index = load_audio_index(run, plan.scene_id)
    probe = load_gate_result(scene_directory / "work" / "checks" / "probe.json")
    changes_path = scene_directory / "work" / "CHANGES.md"
    changes = changes_path.read_text().strip() if changes_path.exists() else ""
    clips, problems = [], []
    for clip in plan.clips:
        shown = probe.beats.get(f"clip_{clip.index:02d}", {}) if probe else {}
        audio = audio_index.get(clip.clip_id)
        beats = []
        for number, (beat, spoken) in enumerate(
            zip(clip.beats, (audio.beat_times if audio else None) or [None] * len(clip.beats)), 1
        ):
            spoken_at = None if spoken is None else round(VOICE_LEAD_IN_SECONDS + spoken, 2)
            shown_at = shown.get(str(number))
            offset = None if spoken_at is None or shown_at is None else round(shown_at - spoken_at, 2)
            beats.append(SyncBeat(beat=number, plan=beat, spoken_at=spoken_at, shown_at=shown_at, offset=offset))
            if offset is not None and abs(offset) > SYNC_TOLERANCE_SECONDS:
                when = "after" if offset > 0 else "before"
                problems.append(f"{clip.clip_id} beat {number}: shown {abs(offset):.2f}s {when} the voice says it")
        audio_seconds, video = (audio.seconds if audio else None), video_seconds.get(clip.clip_id)
        audio_fits = None
        if audio_seconds is not None and video is not None:
            audio_fits = VOICE_LEAD_IN_SECONDS + audio_seconds <= video + 0.2
            if not audio_fits:
                problems.append(
                    f"{clip.clip_id}: the voice ({VOICE_LEAD_IN_SECONDS + audio_seconds:.2f}s with lead-in) runs past "
                    f"its animation ({video:.2f}s)"
                )
        clips.append(
            SyncClip(
                clip_id=clip.clip_id,
                video_seconds=video,
                audio_seconds=audio_seconds,
                audio_fits=audio_fits,
                beats=beats,
                changes=changes if clip.index == 1 else "",  # the scene's one CHANGES.md, on its first clip
            )
        )
    return SyncReport(
        scene_id=plan.scene_id, tolerance=SYNC_TOLERANCE_SECONDS, clips=clips, problems=problems, in_sync=not problems
    )


def preview_problems(run: Path, plan: ScenePlan) -> list[str]:
    report = load_sync_report(run, plan.scene_id)
    if report is None or report.scene_hash != scene_video_hash(run, plan.scene_id):
        return [f"{plan.scene_id}: preview missing or out of date (text-2-shorts preview <run> {plan.scene_id})"]
    return [f"{plan.scene_id} out of sync — {problem} (audio-refactorer)" for problem in report.problems]


def check_delivery(run: Path, plans: list[ScenePlan], report: FinalReport) -> list[MediaFinding]:
    """Everything planned is in the video, and its length matches the script (±20 %)."""
    findings = []
    if missing := [clip.clip_id for plan in plans for clip in plan.clips if clip.clip_id not in report.clips]:
        findings.append({"severity": "ERROR", "code": "MISSING_CLIPS", "message": ", ".join(missing)})
    script = load_script(run)
    planned = sum(scene.duration_seconds for scene in script.scenes) if script else 0
    if planned and abs(report.final_s - planned) > 0.2 * planned:
        findings.append(
            {"severity": "WARN", "code": "DURATION", "message": f"{report.final_s}s against {planned}s scripted"}
        )
    return [MediaFinding.model_validate(finding) for finding in findings]


def check_final_media(path: Path) -> list[MediaFinding]:
    """ffprobe streams + EBU R128 loudness + black frames (docs/history/architecture-plan.md §16.6)."""
    findings = []
    streams = json.loads(
        subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)], capture_output=True, text=True
        ).stdout
    )["streams"]
    video_stream = next((stream for stream in streams if stream["codec_type"] == "video"), {})
    if (video_stream.get("width"), video_stream.get("height")) != (2560, 1440):
        findings.append(
            {
                "severity": "ERROR",
                "code": "RESOLUTION",
                "message": f"{video_stream.get('width')}x{video_stream.get('height')}",
            }
        )
    numerator, _, denominator = (video_stream.get("avg_frame_rate") or "0/1").partition("/")
    if float(numerator) / float(denominator or 1) < FINAL_FRAME_RATE - 0.5:
        findings.append(
            {
                "severity": "ERROR",
                "code": "FRAME_RATE",
                "message": f"{video_stream.get('avg_frame_rate')} fps (expected {FINAL_FRAME_RATE})",
            }
        )
    width, height = video_stream.get("width") or 0, video_stream.get("height") or 0
    if not height or abs(width / height - 16 / 9) > 0.01:
        findings.append({"severity": "ERROR", "code": "ASPECT_RATIO", "message": f"{width}x{height} is not 16:9"})
    if not any(stream["codec_type"] == "audio" for stream in streams):
        findings.append({"severity": "ERROR", "code": "NO_AUDIO", "message": "no audio stream"})
    ffmpeg_log = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-af",
            "ebur128=peak=true,silencedetect=n=-50dB:d=2.5",
            "-vf",
            "blackdetect=d=1.0:pix_th=0.05",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    ).stderr
    lufs = [
        float(line.split("I:")[1].split("LUFS")[0])
        for line in ffmpeg_log.splitlines()
        if " I:" in line and "LUFS" in line
    ]
    if lufs and abs(lufs[-1] + 16) > 1.5:
        findings.append({"severity": "WARN", "code": "LOUDNESS", "message": f"{lufs[-1]} LUFS (target -16)"})
    peaks = [float(line.split("Peak:")[1].split("dB")[0]) for line in ffmpeg_log.splitlines() if "Peak:" in line]
    if peaks and peaks[-1] > -1.0:
        findings.append({"severity": "WARN", "code": "TRUE_PEAK", "message": f"{peaks[-1]} dBTP (clipping risk > -1)"})
    silences = [line for line in ffmpeg_log.splitlines() if "silence_duration" in line]
    if silences:
        findings.append({"severity": "WARN", "code": "SILENCE", "message": f"{len(silences)} silence(s) ≥ 2.5 s"})
    decode_errors = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"], capture_output=True, text=True
    ).stderr.strip()
    if decode_errors:
        findings.append({"severity": "ERROR", "code": "DECODE_ERRORS", "message": decode_errors.splitlines()[0]})
    blacks = [line for line in ffmpeg_log.splitlines() if "black_start" in line]
    if blacks:
        findings.append(
            {"severity": "WARN", "code": "BLACK_FRAMES", "message": f"{len(blacks)} black stretch(es) ≥ 1 s"}
        )
    return [MediaFinding.model_validate(finding) for finding in findings]
