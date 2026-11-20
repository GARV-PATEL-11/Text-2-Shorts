"""pipeline.py — Text-2-Shorts stages. Every LLM step is a `claude -p` subprocess.

Driven by the /make-short skill (.claude/skills/make-short/SKILL.md), one step at a time:

    uv run python -m app.pipeline new "<topic>" --approach zoom --minutes 2 --voice af_heart
    uv run python -m app.pipeline outline  runs/<id> [--feedback "..."]
    uv run python -m app.pipeline tts      runs/<id>
    uv run python -m app.pipeline plan     runs/<id> [--scenes 2,3] [--feedback "..."]
    uv run python -m app.pipeline render   runs/<id> [--scenes 2]   [--feedback "..."]
    uv run python -m app.pipeline assemble runs/<id>

Each step reads/writes JSON + media under runs/<id>/ and prints a short summary for the orchestrator.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from app.graph.models.classic_linear_narrative import ClassicLinearNarrativeOutline
from app.graph.models.conceptual_zoom import ConceptualZoomOutline
from app.graph.models.problem_solution_arc import ProblemSolutionArcOutline
from app.graph.prompts.outline_critic_prompt import (
    OUTLINE_CRITIC_SYSTEM, OUTLINE_REFACTOR_SYSTEM, OutlineCritiqueResult,
    build_outline_critic_prompt, build_outline_refactor_prompt,
    )
from app.graph.prompts.render_debug_prompt import _DEBUG_IDENTITY_AND_PROTOCOL
from app.graph.prompts.script_gen_prompt import (
    CLASSIC_LINEAR_NARRATIVE_SYSTEM, CONCEPTUAL_ZOOM_SYSTEM, PROBLEM_TO_SOLUTION_ARC_SYSTEM, REQ_MODIFIER_SYSTEM,
    )
from app.graph.prompts.visual_code_gen_prompt import SYSTEM_PROMPT as CODE_GEN_SYSTEM
from app.graph.prompts.visual_code_gen_prompt import build_user_prompt as build_code_user_prompt
from app.graph.prompts.visual_plan_critic_prompt import (
    CRITIC_SYSTEM, REFACTOR_SYSTEM, CritiqueResult, build_critic_user_prompt, build_refactor_user_prompt,
    )
from app.graph.prompts.visual_plan_gen_prompt import SceneDirectorInput, generate_visual_plan_prompt


load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable  # the venv interpreter — manim is installed here
SANDBOX_SETTINGS = Path(__file__).with_name("sandbox.json")
FINAL_QUALITY = os.environ.get("T2S_QUALITY", "-qh")
MAX_PARALLEL = int(os.environ.get("T2S_PARALLEL", 4))  # scenes at a time (user's call: 4)
CACHE_WARMUP_S = 20  # ponytail: fixed delay, not a signal that the cache is written; tune if logs show misses
CRITIC_ROUNDS = 3  # critic passes; the last one always scores the final plan

# (model, effort) per stage. T2S_MODEL=<alias> forces one model everywhere (cheap smoke runs).
STAGES: dict[str, tuple[str, str]] = {
    "refine": ("haiku", "low"),
    "outline": ("sonnet", "high"),
    "outline_critic": ("sonnet", "high"),
    "outline_refactor": ("sonnet", "medium"),
    "narration": ("sonnet", "medium"),
    "plan": ("sonnet", "high"),
    "plan_critic": ("sonnet", "medium"),
    "plan_refactor": ("sonnet", "medium"),
    "scene": ("sonnet", "high"),
    "scene_retry": ("sonnet", "xhigh"),
    }

APPROACHES: dict[str, tuple[str, type[BaseModel]]] = {
    "zoom": (CONCEPTUAL_ZOOM_SYSTEM, ConceptualZoomOutline),
    "arc": (PROBLEM_TO_SOLUTION_ARC_SYSTEM, ProblemSolutionArcOutline),
    "linear": (CLASSIC_LINEAR_NARRATIVE_SYSTEM, ClassicLinearNarrativeOutline),
    }

# bubblewrap jail for the final (unattended) render of LLM-written code: read-only host,
# no network, writable scene dir + ~/.cache only. Mirrors app/sandbox.json.
CACHE = Path.home() / ".cache"
BWRAP = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp",
         "--bind", str(CACHE), str(CACHE), "--unshare-net", "--die-with-parent"]


# ── Schemas for new stages ────────────────────────────────────────────────────

class SceneNarration(BaseModel):
    scene_id: int
    narration: str


class Narration(BaseModel):
    scenes: list[SceneNarration]


class SceneResult(BaseModel):
    status: Literal["READY", "FAILED"]
    render_attempts: int = 0
    notes: str = ""


NARRATION_SYSTEM = """
You write the spoken voiceover script for an educational explainer video, one entry per scene.
Rules:
- Word count per scene ≈ duration_seconds / 60 × meta.target_wpm. Never exceed it by more than 10%.
- Cover that scene's talking_points in order; follow its narration_hint for tone and pacing.
- End each scene (except the last) with a natural bridge into the next one (see transition_to_next).
- Plain spoken English for a text-to-speech voice: no markdown, emojis, stage directions or brackets.
  Write symbols as spoken ("x squared", "theta", "greater than").
Return one entry per scene_id in the outline.
""".strip()

SCENE_AGENT_PROTOCOL = """
════════════════════════════════════════════════════════════════
OPERATING MODE — AUTONOMOUS SANDBOXED AGENT (overrides the OUTPUT FORMAT sections above)

You are not answering in chat. You work in the current directory with Read/Write/Edit/Bash, sandboxed:
no network, writes only inside this directory. The protocols above (code generation, then render
debugging) are your knowledge; this is your workflow:

1. Read plan.md (the scene DSL) and narration.txt (the voiceover this scene must play under).
2. Write scene.py containing exactly one Scene subclass named {class_name}. If scene.py already exists,
   start from it (a previous attempt) and apply any human feedback given in the task.
3. Render:  {render_cmd}
4. On failure, read the error, apply the RENDER DEBUG protocol, fix scene.py, re-render. At most 6 renders.
5. On success (the draft video is media/videos/scene/480p15/{class_name}.mp4; run these commands verbatim):
   a. Check duration: ffprobe -v error -show_entries format=duration -of csv=p=0 media/videos/scene/480p15/{class_name}.mp4
      It must be at least {target:.1f}s (the narration length). If shorter, extend waits/animations
      in narration-sync order; if more than 3s longer, tighten.
   b. Look at it: ffmpeg -y -loglevel error -i media/videos/scene/480p15/{class_name}.mp4 -vf fps=1/3 frames/f_%02d.png
      then Read the PNGs.
      Fix overlapping elements, text cut off at frame edges, unreadable text, empty frames. Re-render.
      At most 2 visual passes.
6. Finish with status READY only if the last render succeeded and passed checks; otherwise FAILED
   with notes saying what is still wrong. Never run anything except python/manim/ffmpeg/ffprobe/ls/mkdir.
""".strip()


# ── Helpers ───────────────────────────────────────────────────────────────────

def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def scene_dir(run: Path, scene_id: int) -> Path:
    d = run / "scenes" / f"{scene_id:03d}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def feedback_block(feedback: str | None) -> str:
    return f"\n\n## HUMAN REVIEWER FEEDBACK (highest priority — apply it)\n{feedback}" if feedback else ""


def parse_envelope(env: dict, schema: type[BaseModel] | None) -> BaseModel | str | None:
    """Extract the payload from `claude -p --output-format json` stdout. None = failed call."""
    if env.get("is_error") or env.get("subtype") != "success":
        return None
    if schema is None:
        return env.get("result") or None
    try:
        return schema.model_validate(env.get("structured_output"))
    except ValidationError:
        return None


def claude(
        run: Path, stage: str, user: str, system: str, *,
        schema: type[BaseModel] | None = None, scene: int | None = None,
        cwd: Path | None = None, agent: bool = False,
        ):
    """One `claude -p` call. Retries once; raises RuntimeError if both attempts fail."""
    model, effort = STAGES[stage]
    model = os.environ.get("T2S_MODEL", model)
    tag = f"{stage}_{scene:03d}" if scene is not None else stage
    prompts = run / ".prompts"
    prompts.mkdir(exist_ok=True)
    sys_file = prompts / f"{tag}.md"
    sys_file.write_text(system)  # prompts exceed Linux's 128 KB argv limit — always pass via file

    cmd = ["claude", "-p", "--model", model, "--effort", effort, "--output-format", "json",
           "--safe-mode", "--no-session-persistence"]
    if schema is not None:
        cmd += ["--json-schema", json.dumps(schema.model_json_schema(by_alias=False))]
    if agent:
        # Sandboxed Bash is auto-allowed, but some commands (ffmpeg/ffprobe) still hit "requires approval",
        # which --permission-prompts none turns into a denial — allow them explicitly (still sandboxed).
        cmd += ["--append-system-prompt-file", str(sys_file), "--restricted",
                "--tools", "Read,Write,Edit,Bash",
                "--allowedTools", "Bash(ffmpeg:*)", "Bash(ffprobe:*)", "Bash(python3:*)",
                "--settings", str(SANDBOX_SETTINGS),
                "--permission-mode", "acceptEdits", "--permission-prompts", "none", "--max-budget-usd", "3"]
    else:
        cmd += ["--system-prompt-file", str(sys_file), "--tools", ""]

    env: dict = {}
    for attempt in (1, 2):
        t0 = time.monotonic()
        with (run / "log.jsonl").open("a") as fh:  # a "started" line with no matching "ok" line = running or killed
            fh.write(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"), "stage": stage, "scene": scene,
                                 "model": model, "effort": effort, "attempt": attempt, "status": "started"}) + "\n")
        try:
            p = subprocess.run(cmd, input=user, capture_output=True, text=True,
                               cwd=cwd or run, timeout=3600 if agent else 1800)
            try:
                env = json.loads(p.stdout)
            except json.JSONDecodeError:
                env = {"is_error": True, "result": f"exit {p.returncode}: {(p.stderr or p.stdout)[-500:]}"}
        except subprocess.TimeoutExpired:
            env = {"is_error": True, "result": "timed out"}
        out = parse_envelope(env, schema)
        with (run / "log.jsonl").open("a") as fh:
            fh.write(json.dumps({
                "ts": datetime.now().isoformat(timespec="seconds"), "stage": stage, "scene": scene,
                "model": model, "effort": effort, "attempt": attempt, "ok": out is not None,
                "cost_usd": env.get("total_cost_usd"), "duration_ms": round((time.monotonic() - t0) * 1000),
                "cache_read": (env.get("usage") or {}).get("cache_read_input_tokens"),
                "cache_write": (env.get("usage") or {}).get("cache_creation_input_tokens"),
                "error": None if out is not None else str(env.get("result") or env.get("subtype"))[:300],
                }) + "\n")
        if out is not None:
            return out
    raise RuntimeError(f"{tag} failed twice: {str(env.get('result') or env.get('subtype'))[:300]}")


def probe_seconds(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def map_outline(outline: dict) -> tuple[dict, list[dict]]:
    """outline.json → (meta, scenes) where each scene is the dict the visual director needs."""
    scenes = [{
        "scene_id": seg.get("scene_id", i + 1),
        "title": seg.get("title", ""),
        "description": "\n".join(filter(None, [seg.get("visual_plan", ""), *seg.get("talking_points", [])])),
        "duration_seconds": seg.get("duration_seconds", 30),
        } for i, seg in enumerate(outline.get("outline", []))]
    return outline.get("meta", {}), scenes


def mux_args(clip: Path, audio: Path, out: Path, video_s: float, audio_s: float) -> list[str]:
    """ffmpeg args: pad the shorter of video (freeze last frame) / audio (silence) to the longer."""
    total = max(video_s, audio_s)
    return ["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip), "-i", str(audio),
            "-filter_complex",
            f"[0:v]tpad=stop_mode=clone:stop_duration={max(0.0, audio_s - video_s):.3f}[v];[1:a]apad[a]",
            "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", "-ac", "2", str(out)]


def selected(run: Path, scenes_arg: str | None) -> list[int]:
    ids = [s["scene_id"] for s in read_json(run / "narration.json")["scenes"]]
    return [int(x) for x in scenes_arg.split(",")] if scenes_arg else ids


def parallel(fn, items):
    # Run the first item alone for a moment so it writes the prompt cache; the rest then read it
    # instead of all paying a cache write at once (scenes share one large system prompt).
    items = list(items)
    with ThreadPoolExecutor(MAX_PARALLEL) as ex:
        futures = [ex.submit(fn, items[0])] if items else []
        if len(items) > 1 and MAX_PARALLEL > 1:
            time.sleep(CACHE_WARMUP_S)
        futures += [ex.submit(fn, it) for it in items[1:]]
        return [f.result() for f in futures]


# ── Steps ─────────────────────────────────────────────────────────────────────

def cmd_new(a) -> None:
    slug = re.sub(r"[^a-z0-9]+", "-", a.requirement.lower())[:40].strip("-")
    run = ROOT / "runs" / f"{datetime.now():%Y%m%d-%H%M%S}-{slug}"
    run.mkdir(parents=True)
    refined = claude(run, "refine", a.requirement, REQ_MODIFIER_SYSTEM)
    write_json(run / "brief.json", {
        "requirement": a.requirement, "approach": a.approach, "minutes": a.minutes, "pace": a.pace,
        "audience": a.audience, "notes": a.notes, "voice": a.voice, "engine": a.engine, "refined": refined.strip(),
        })
    print(run.relative_to(ROOT))
    print(refined.strip())


def _refactor_outline(run: Path, outline: dict, schema, critique: OutlineCritiqueResult, it: int) -> dict:
    user = build_outline_refactor_prompt(outline["meta"], outline["outline"], critique, it)
    return claude(run, "outline_refactor", user, OUTLINE_REFACTOR_SYSTEM, schema=schema).model_dump()


def cmd_outline(a) -> None:
    run = Path(a.run)
    brief = read_json(run / "brief.json")
    system, schema = APPROACHES[brief["approach"]]

    if a.feedback and (run / "outline.json").exists():
        human = OutlineCritiqueResult(approved=False, score=5, critique="Human reviewer requested changes.",
                                      improvements=[a.feedback])
        outline = _refactor_outline(run, read_json(run / "outline.json"), schema, human, 1)
    else:
        user = (f"raw_content: {brief['refined']}\ntopic: {brief['requirement']}\n"
                f"duration_minutes: {brief['minutes']}\npace: {brief['pace']}\n"
                f"audience: {brief['audience']}\nnotes: {brief['notes']}")
        outline = claude(run, "outline", user, system, schema=schema).model_dump()
        for it in range(1, CRITIC_ROUNDS + 1):
            crit = claude(run, "outline_critic", build_outline_critic_prompt(outline["meta"], outline["outline"], it),
                          OUTLINE_CRITIC_SYSTEM, schema=OutlineCritiqueResult)
            print(f"critic round {it}: score {crit.score}/10 — {crit.critique}")
            if crit.approved:
                break
            outline = _refactor_outline(run, outline, schema, crit, it)
    write_json(run / "outline.json", outline)

    narration = claude(run, "narration", json.dumps(outline, indent=2), NARRATION_SYSTEM, schema=Narration)
    write_json(run / "narration.json", narration.model_dump())

    meta, scenes = map_outline(outline)
    by_id = {s.scene_id: s.narration for s in narration.scenes}
    print(f"\n# {meta.get('title')} — {meta.get('total_duration_seconds')}s, {len(scenes)} scenes\n")
    print("| # | title | sec | words | narration |\n|---|---|---|---|---|")
    for s in scenes:
        text = by_id.get(s["scene_id"], "")
        print(f"| {s['scene_id']} | {s['title']} | {s['duration_seconds']} | {len(text.split())} | {text[:90]}… |")
    print(f"\nFull files: {run}/outline.json, {run}/narration.json")


KOKORO_DIR = Path(os.environ.get("KOKORO_DIR", Path.home() / ".cache" / "kokoro"))
KOKORO_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"


def kokoro_tts(voice: str):
    """Local Kokoro (ONNX). Downloads the ~350MB model to KOKORO_DIR on first use."""
    import urllib.request
    from kokoro_onnx import Kokoro

    for f in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
        if not (KOKORO_DIR / f).exists():
            KOKORO_DIR.mkdir(parents=True, exist_ok=True)
            print(f"downloading {f} → {KOKORO_DIR}")
            urllib.request.urlretrieve(KOKORO_URL + f, KOKORO_DIR / f)
    kokoro = Kokoro(str(KOKORO_DIR / "kokoro-v1.0.onnx"), str(KOKORO_DIR / "voices-v1.0.bin"))

    def synth(text: str) -> bytes:
        samples, rate = kokoro.create(text, voice=voice, lang="en-us")
        return subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "f32le", "-ar", str(rate), "-ac", "1",
                               "-i", "-", "-f", "mp3", "-"],
                              input=samples.astype("float32").tobytes(), capture_output=True, check=True).stdout
    return synth


def polly_tts(voice: str, engine: str):
    import boto3

    polly = boto3.client("polly")

    def synth(text: str) -> bytes:
        # Polly caps one request at 3000 chars; split on sentences and join the MP3 frames.
        chunks, cur = [], ""
        for sent in re.split(r"(?<=[.!?])\s+", text):
            if cur and len(cur) + len(sent) > 2800:
                chunks.append(cur)
                cur = ""
            cur = f"{cur} {sent}".strip()
        chunks.append(cur)
        return b"".join(polly.synthesize_speech(Text=c, OutputFormat="mp3", VoiceId=voice, Engine=engine)
                        ["AudioStream"].read() for c in chunks)
    return synth


def cmd_tts(a) -> None:
    run = Path(a.run)
    brief = read_json(run / "brief.json")
    narration = read_json(run / "narration.json")
    synth = (kokoro_tts(brief["voice"]) if brief["engine"] == "kokoro"
             else polly_tts(brief["voice"], brief["engine"]))
    for s in narration["scenes"]:
        d = scene_dir(run, s["scene_id"])
        (d / "narration.txt").write_text(s["narration"])
        (d / "narration.mp3").write_bytes(synth(s["narration"]))
        s["audio_seconds"] = round(probe_seconds(d / "narration.mp3"), 2)
        print(f"scene {s['scene_id']}: {s['audio_seconds']}s")
    write_json(run / "narration.json", narration)


def cmd_plan(a) -> None:
    run = Path(a.run)
    meta, scenes = map_outline(read_json(run / "outline.json"))
    narr = {s["scene_id"]: s for s in read_json(run / "narration.json")["scenes"]}
    keep_format = ("\n\nNOTE: the current plan is XML-style tagged text, not JSON. Return the complete revised "
                   "plan in exactly the same tagged format, and nothing else.")
    targets = set(selected(run, a.scenes))

    def one(scene: dict) -> str:
        sid = scene["scene_id"]
        d = scene_dir(run, sid)
        seconds = math.ceil(narr[sid].get("audio_seconds") or scene["duration_seconds"])
        scene_json = json.dumps({**scene, "duration_seconds": seconds, "narration_text": narr[sid]["narration"]},
                                indent=2)
        def snapshot(text: str) -> str:  # revision history: plan.v1.md, plan.v2.md, …
            n = len(list(d.glob("plan.v*.md")))
            if n and (d / f"plan.v{n}.md").read_text() == text:  # resuming: same text, same version
                return f"plan.v{n}.md"
            (d / f"plan.v{n + 1}.md").write_text(text)
            return f"plan.v{n + 1}.md"

        old_review = read_json(d / "plan_review.json") if (d / "plan_review.json").exists() else None
        plan, history = None, []
        try:
            if a.feedback and (d / "plan.md").exists():
                snapshot((d / "plan.md").read_text())
                human = CritiqueResult(approved=False, score=5, critique="Human reviewer requested changes.",
                                       improvements=[a.feedback])
                plan = claude(run, "plan_refactor",
                              build_refactor_user_prompt(scene_json, (d / "plan.md").read_text(), human, 1) + keep_format,
                              REFACTOR_SYSTEM, scene=sid)
                snapshot(plan)
                review = {"score": None, "critique": "revised from human feedback"}
            else:
                if a.refine and (d / "plan.md").exists():  # critique the existing plan instead of regenerating
                    plan = (d / "plan.md").read_text()
                else:
                    prompts = generate_visual_plan_prompt(SceneDirectorInput(
                        video_metadata=json.dumps(meta, indent=2), target_scene_id=f"scene_{sid:03d}",
                        target_scene=scene_json, target_duration=seconds))
                    plan = claude(run, "plan", prompts["user"] + feedback_block(a.feedback), prompts["system"], scene=sid)
                version = snapshot(plan)
                # Always end on a critic pass, so the saved score belongs to the saved plan.
                for it in range(1, a.rounds + 1):
                    crit = claude(run, "plan_critic", build_critic_user_prompt(scene_json, plan, it),
                                  CRITIC_SYSTEM, schema=CritiqueResult, scene=sid)
                    history.append({"version": version, **crit.model_dump()})
                    if crit.approved or crit.score >= 8 or it == a.rounds:
                        break
                    plan = claude(run, "plan_refactor",
                                  build_refactor_user_prompt(scene_json, plan, crit, it) + keep_format,
                                  REFACTOR_SYSTEM, scene=sid)
                    version = snapshot(plan)
                review = {"score": history[-1]["score"], "critique": history[-1]["critique"],
                          "improvements": history[-1]["improvements"], "history": history,
                          "previous_review": old_review}
        except RuntimeError as exc:
            if history:  # keep progress: plan.md = latest rewrite (unscored), so the next --refine resumes from it
                (d / "plan.md").write_text(plan)
                write_json(d / "plan_review.json", {"score": None, "critique": f"FAILED: {exc}",
                                                    "history": history, "previous_review": old_review})
            return f"| {sid} | {scene['title']} | FAILED | {exc} |"
        (d / "plan.md").write_text(plan)
        write_json(d / "plan_review.json", review)
        trail = " → ".join(str(h["score"]) for h in review.get("history", []))
        return f"| {sid} | {scene['title']} | {review.get('score')} ({trail}) | {review.get('critique')} |"

    rows = parallel(one, [s for s in scenes if s["scene_id"] in targets])
    print("| # | title | critic score | critic note |\n|---|---|---|---|")
    print("\n".join(rows))
    print(f"\nPlans: {run}/scenes/NNN/plan.md")


def cmd_render(a) -> None:
    run = Path(a.run)
    missing = [b for b in ("bwrap", "socat") if not shutil.which(b)]
    if missing:  # without these Claude Code silently runs Bash unsandboxed — refuse instead
        sys.exit(f"Sandbox dependencies missing: {missing}. Run: sudo apt install bubblewrap socat")
    narr = {s["scene_id"]: s for s in read_json(run / "narration.json")["scenes"]}
    for p in (CACHE / "manim", CACHE / "fontconfig"):
        p.mkdir(parents=True, exist_ok=True)  # sandbox allowWrite ignores paths that don't exist yet

    def one(sid: int) -> str:
        d = scene_dir(run, sid)
        name = f"Scene{sid:03d}"
        (d / "frames").mkdir(exist_ok=True)
        render_cmd = f'"{PYTHON}" -m manim render scene.py {name} -ql --media_dir media --disable_caching'
        system = "\n\n".join([CODE_GEN_SYSTEM, _DEBUG_IDENTITY_AND_PROTOCOL,
                              SCENE_AGENT_PROTOCOL.format(class_name=name, render_cmd=render_cmd,
                                                          target=narr[sid]["audio_seconds"])])
        user = build_code_user_prompt((d / "plan.md").read_text()) + feedback_block(a.feedback)

        result = SceneResult(status="FAILED", notes="not run")
        for stage in ("scene", "scene_retry"):
            try:
                result = claude(run, stage, user, system, schema=SceneResult, scene=sid, cwd=d, agent=True)
            except RuntimeError as exc:
                result = SceneResult(status="FAILED", notes=str(exc))
            if result.status == "READY" and (d / "scene.py").exists():
                break

        if result.status == "READY":
            # Final-quality render of the approved code, jailed (no network, writes to scene dir + ~/.cache).
            shutil.rmtree(d / "media_final", ignore_errors=True)
            p = subprocess.run(BWRAP + ["--bind", str(d), str(d), PYTHON, "-m", "manim", "render", "scene.py", name,
                                        FINAL_QUALITY, "--media_dir", "media_final", "--disable_caching"],
                               cwd=d, capture_output=True, text=True, timeout=3600)
            mp4s = sorted((d / "media_final").rglob(f"{name}.mp4")) or sorted((d / "media").rglob(f"{name}.mp4"))
            if p.returncode != 0:
                result.notes += f" | final render failed, using draft quality: {p.stderr[-300:]}"
            if mp4s:
                shutil.copy(mp4s[0], d / "clip.mp4")
                # last frame = the scene's settled state (a mid-point grab often lands mid-animation)
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-sseof", "-0.1", "-i", str(d / "clip.mp4"),
                                "-frames:v", "1", "-update", "1", str(d / "thumb.png")], check=False)
            else:
                result = SceneResult(status="FAILED", render_attempts=result.render_attempts, notes="no mp4 produced")
        if result.status == "FAILED":
            (d / "clip.mp4").unlink(missing_ok=True)
        write_json(d / "result.json", result.model_dump())
        return f"| {sid} | {result.status} | {result.render_attempts} | {result.notes[:200]} |"

    rows = parallel(one, selected(run, a.scenes))
    print("| # | status | renders | notes |\n|---|---|---|---|")
    print("\n".join(rows))


def cmd_assemble(a) -> None:
    run = Path(a.run)
    parts, skipped = [], []
    for s in read_json(run / "narration.json")["scenes"]:
        d = scene_dir(run, s["scene_id"])
        clip, audio = d / "clip.mp4", d / "narration.mp3"
        if not clip.exists():
            skipped.append(s["scene_id"])
            continue
        out = d / "part.mp4"
        subprocess.run(mux_args(clip, audio, out, probe_seconds(clip), probe_seconds(audio)), check=True)
        parts.append(out)
    if not parts:
        sys.exit("No rendered scenes to assemble.")
    (run / "concat.txt").write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    final = run / "final.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(run / "concat.txt"), "-c", "copy", str(final)], check=True)
    cost = sum((json.loads(l).get("cost_usd") or 0) for l in (run / "log.jsonl").read_text().splitlines())
    print(f"{final}\nduration: {probe_seconds(final):.1f}s · scenes: {len(parts)}"
          f"{f' · skipped (not rendered): {skipped}' if skipped else ''} · Claude cost: ${cost:.2f}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m app.pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new")
    p.add_argument("requirement")
    p.add_argument("--approach", choices=list(APPROACHES), default="zoom")
    p.add_argument("--minutes", type=float, default=2)
    p.add_argument("--pace", choices=["slow", "medium", "fast"], default="medium")
    p.add_argument("--audience", default="curious beginners")
    p.add_argument("--notes", default="")
    p.add_argument("--engine", default=os.environ.get("TTS_ENGINE", "kokoro"),
                   help="kokoro (local, free) or a Polly engine: neural | generative | standard")
    p.add_argument("--voice", help="Kokoro: af_heart, am_michael, … · Polly: Matthew, Joanna, …")
    p.set_defaults(fn=cmd_new)

    for name, fn in (("outline", cmd_outline), ("tts", cmd_tts), ("plan", cmd_plan),
                     ("render", cmd_render), ("assemble", cmd_assemble)):
        p = sub.add_parser(name)
        p.add_argument("run")
        p.add_argument("--scenes", help="comma-separated scene ids (plan/render only)")
        p.add_argument("--feedback", help="human reviewer feedback to apply")
        p.add_argument("--refine", action="store_true", help="plan: critique/refactor existing plan.md, don't regenerate")
        p.add_argument("--rounds", type=int, default=CRITIC_ROUNDS, help="plan: max critic passes per scene")
        p.set_defaults(fn=fn)

    a = ap.parse_args()
    if a.cmd == "new" and not a.voice:
        a.voice = (os.environ.get("KOKORO_VOICE", "af_heart") if a.engine == "kokoro"
                   else os.environ.get("POLLY_VOICE", "Matthew"))
    if getattr(a, "run", None):
        a.run = str(Path(a.run).resolve())  # child `claude -p` runs with cwd inside the run dir
    a.fn(a)


if __name__ == "__main__":
    main()
