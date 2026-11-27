"""Command handlers for production: voice, accept, preview, final."""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path

from schemas.media import AssemblyManifest, BackgroundMusic, ClipAudio, FinalReport, SceneRender, SceneTransition
from schemas.plans import ScenePlan
from schemas.reviews import MistakeIssue

from app import narration
from app.config import DRAFT_QUALITY, FINAL_FRAME_RATE, TOOLS_DIRECTORY
from app.utilities import probe_duration_seconds, run_in_parallel, write_atomic
from app.workflow import mistakes
from app.workflow.artifacts import load_audio_index, load_brief, load_scene_plans, save_audio_index
from app.workflow.checkpoints import require_approval
from app.workflow.fingerprints import clip_key, final_fingerprint, fingerprint, scene_video_hash
from app.workflow.ledger import count_attempt, is_approval_current, load_state
from app.workflow.preferences import clip_speech
from app.workflow.production import (
    check_delivery,
    check_final_media,
    render_scene_sections,
    scene_manifest,
    stale_audio,
    sync_report,
    voice_key,
)
from app.workflow.scene_code import accept_scene
from app.workflow.templates import load_template, look, sound

log = logging.getLogger(__name__)


def handle_voice_command(arguments) -> None:
    run = Path(arguments.run)
    require_approval(run, "plan")
    if load_brief(run) is None:
        sys.exit("brief.json is missing or invalid: `text-2-shorts validate . brief`")
    synthesize_clip = None
    plans = load_scene_plans(run)
    pairs = narration.case_pairs(
        [clip.narration for scene_plan in plans for clip in scene_plan.clips]
    )  # letters used as both M and m
    for plan in plans:
        audio_directory = run / "scenes" / plan.scene_id / "audio"
        audio_directory.mkdir(exist_ok=True)
        audio_index = load_audio_index(run, plan.scene_id)
        for clip in plan.clips:
            text = clip_speech(run, clip.ssml, pairs)  # the planned SSML, symbols by name, preferred rate and pauses
            voice_hash = voice_key(run, text)
            audio_path = audio_directory / f"clip_{clip.index:02d}.mp3"
            if clip.clip_id in audio_index and audio_index[clip.clip_id].hash == voice_hash and audio_path.exists():
                continue  # unchanged SSML → keep the audio
            synthesize_clip = synthesize_clip or narration.create_speech_synthesizer(sound(run))
            try:
                audio, marks = synthesize_clip(text)
            except Exception as error:  # the voice provider: say which clip and why; the clips made so far are kept
                log.exception("%s: voice failed", clip.clip_id)
                sys.exit(f"{clip.clip_id}: the voice provider failed — {error}. Run voice again to go on from here.")
            audio_path.write_bytes(audio)
            audio_index[clip.clip_id] = ClipAudio(
                hash=voice_hash,
                seconds=round(probe_duration_seconds(audio_path), 2),
                spoken=narration.to_plain(text),
                beat_times=narration.phrase_times(marks, clip.beats, pairs) if marks else None,
            )
            save_audio_index(run, plan.scene_id, audio_index)  # after every clip: a later failure loses none (M30)
            print(f"{clip.clip_id}: {audio_index[clip.clip_id].seconds}s")
    total = sum(
        clip_audio.seconds
        for scene_plan in load_scene_plans(run)
        for clip_audio in load_audio_index(run, scene_plan.scene_id).values()
    )
    print(f"total narration: {total:.1f}s")


def handle_final_command(arguments) -> None:
    """The 1440p delivery render: only from clips built from the current plans, with current audio, and (unless
    --force) scenes approved as they are now. A failed render or assembly leaves the last final.mp4 in place."""
    run = Path(arguments.run)
    require_approval(run, "plan")
    state = load_state(run)
    plans = load_scene_plans(run)
    missing = [
        clip.clip_id
        for plan in plans
        for clip in plan.clips
        if (build := state.clips.get(clip.clip_id)) is None
        or build.status != "READY"
        or build.key != clip_key(run, plan, clip)
    ]
    if missing:
        sys.exit(f"Not built, or built from an older plan or request: {missing}. Build them first (task, accept).")
    if stale := stale_audio(run, plans):
        sys.exit(f"audio missing or outdated for {sorted(stale)}: text-2-shorts voice <run>")
    unapproved = [
        plan.scene_id
        for plan in plans
        if not is_approval_current(state, f"scene:{plan.scene_id}", fingerprint(run, [plan]))
    ]
    if unapproved and not arguments.force:
        sys.exit(f"Scene previews not approved (CP3): {unapproved} — `approve <run> scenes` (or --force).")
    if not 60 <= FINAL_FRAME_RATE <= 120:
        sys.exit(f"TEXT_2_SHORTS_FPS={FINAL_FRAME_RATE}: must be 60–120")

    rendered_from = final_fingerprint(run, plans)  # before the render: a change made during it leaves it stale
    (run / "final_report.json").unlink(missing_ok=True)

    def render_scene(plan: ScenePlan) -> SceneRender:
        return render_scene_sections(run, plan, "p", FINAL_FRAME_RATE, "media_final")

    scene_renders = dict(zip([plan.scene_id for plan in plans], run_in_parallel(render_scene, plans)))
    failed = {scene_id: render.stderr_tail for scene_id, render in scene_renders.items() if not render.ok}
    if failed:
        sys.exit(f"Final render failed: {json.dumps(failed, indent=1)[:3000]}")
    manifest = AssemblyManifest(scenes=[scene_manifest(run, plan, scene_renders[plan.scene_id]) for plan in plans])
    if template := load_template(run):  # scene transitions and the user's music, as the template specifies
        manifest.transition = SceneTransition(
            style=template.scene_transition, seconds=template.transition_seconds, color=look(run)["background"]
        )
        if template.music:
            manifest.music = BackgroundMusic(file=str(run / template.music), volume_db=template.music_volume_db)
    (run / "assembly.json").write_text(manifest.model_dump_json(indent=2))
    sys.path.insert(0, str(TOOLS_DIRECTORY))
    from assemble_clips import assemble  # backend/tools/ is a script folder, not a package

    partial = run / "final.partial.mp4"
    report = FinalReport.model_validate(assemble(manifest.model_dump(), partial, run / "assembly_work"))
    partial.replace(run / "final.mp4")  # only a finished assembly replaces the last good video
    report.checks = check_final_media(run / "final.mp4") + check_delivery(run, plans, report)
    report.fingerprint = rendered_from
    write_atomic(run / "final_report.json", report.model_dump_json(indent=2))
    print(f"{run / 'final.mp4'}\nduration: {report.final_s}s · clips: {len(report.clips)}")
    for finding in report.checks:
        print(f"{finding.severity} {finding.code}: {finding.message}")


def contact_sheet_filter(seconds: float) -> str:
    """One frame every 2 s, 12 to a sheet, but at most 3 sheets (36 frames): what the video critic looks at stays
    bounded however long the scene is (O7)."""
    return f"fps=1/{max(2.0, seconds / 36):.2f},scale=480:-1,tile=4x3"


def handle_preview_command(arguments) -> None:
    """The whole scene (with its transitions) at 720p30 with its audio, the sync report and contact sheets."""
    run, scene_id = Path(arguments.run), arguments.scene
    require_approval(run, "plan")
    plan = next((plan for plan in load_scene_plans(run) if plan.scene_id == scene_id), None)
    if plan is None:
        sys.exit(f"{scene_id}: no valid plan")
    clip_states = load_state(run).clips
    if unbuilt := [
        c.clip_id
        for c in plan.clips
        if (build := clip_states.get(c.clip_id)) is None or build.key != clip_key(run, plan, c)
    ]:
        sys.exit(f"build the scene first (text-2-shorts task . {scene_id}): {unbuilt} not built")
    if stale := stale_audio(run, [plan]):
        sys.exit(f"audio missing or outdated for {sorted(stale)}: text-2-shorts voice <run>")
    render = render_scene_sections(run, plan, DRAFT_QUALITY, None, "media_preview")
    if not render.ok:
        sys.exit(f"preview render failed: {render.stderr_tail}")
    scene_directory = run / "scenes" / plan.scene_id
    sys.path.insert(0, str(TOOLS_DIRECTORY))
    from assemble_clips import assemble  # backend/tools/ is a script folder, not a package

    assemble(
        AssemblyManifest(scenes=[scene_manifest(run, plan, render)]).model_dump(),
        scene_directory / "preview.mp4",
        scene_directory / "preview_work",
    )
    for sheet in scene_directory.glob("preview_sheet_*.png"):
        sheet.unlink()
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(scene_directory / "preview.mp4"),
            "-vf",
            contact_sheet_filter(probe_duration_seconds(scene_directory / "preview.mp4")),
            str(scene_directory / "preview_sheet_%02d.png"),
        ],
        check=False,
    )
    sections = {section.name: section.duration for section in render.sections}
    report = sync_report(run, plan, {clip.clip_id: sections[f"clip_{clip.index:02d}"] for clip in plan.clips})
    report.scene_hash = scene_video_hash(run, scene_id)
    write_atomic(scene_directory / "sync.json", report.model_dump_json(indent=2))
    attempt = count_attempt(run, f"sync:{scene_id}", failed=not report.in_sync)
    count_attempt(run, "sync:refactors", failed=False)  # a new preview: the last re-timing changed something (C2)
    issues = [MistakeIssue(code=mistakes.sync_code(problem), severity="ERROR", target=problem.split(" ")[0].rstrip(":"),
                           problem=problem) for problem in report.problems]  # fmt: skip
    mistakes.record(run, "sync", "audio-refactorer", scene_id, issues, attempt or None)
    print(
        f"{scene_directory / 'preview.mp4'} (720p30) · sync: "
        + ("in sync" if report.in_sync else "\n  " + "\n  ".join(report.problems))
        + "".join(f"\n  not checked — {note}" for note in report.unchecked)
    )


def handle_accept_command(arguments) -> None:
    result = accept_scene(Path(arguments.run), arguments.scene)
    print(
        f"{arguments.scene}: {result.status}"
        + (f" — {', '.join(result.open_findings)}" if result.open_findings else "")
    )
    sys.exit(0 if result.status == "READY" else 1)
