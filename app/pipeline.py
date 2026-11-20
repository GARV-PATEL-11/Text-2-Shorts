"""pipeline.py — the `t2s` CLI, the Claude runner (`claude()`: caching, retries, limit waits, logging) and the
brief/outline/TTS stages. The clip-level stages (clips, voice, build, final, approve, feedback, status) are in
app/clips.py. Driven by the /make-short skill, one step at a time:

    t2s new "<topic>" --approach zoom --minutes 2 --tts polly --voice Matthew [--font Roboto]
    t2s outline  runs/<id> [--feedback "..."]        CP1 → t2s approve runs/<id> outline
    t2s clips    runs/<id> [--scenes 2]              CP2 → t2s approve runs/<id> plan
    t2s voice    runs/<id>
    t2s build    runs/<id> [--clips s02c03 --feedback "..."]   CP3 → t2s approve runs/<id> s02
    t2s final    runs/<id>                           CP4 → t2s approve runs/<id> final
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from app import speech
from app.graph.models.classic_linear_narrative import ClassicLinearNarrativeOutline
from app.graph.models.conceptual_zoom import ConceptualZoomOutline
from app.graph.models.problem_solution_arc import ProblemSolutionArcOutline
from app.graph.prompts.outline_critic_prompt import (
    OUTLINE_CRITIC_SYSTEM, OUTLINE_REFACTOR_SYSTEM, OutlineCritiqueResult,
    build_outline_critic_prompt, build_outline_refactor_prompt,
    )
from app.graph.prompts.script_gen_prompt import (
    CLASSIC_LINEAR_NARRATIVE_SYSTEM, CONCEPTUAL_ZOOM_SYSTEM, PROBLEM_TO_SOLUTION_ARC_SYSTEM, REQ_MODIFIER_SYSTEM,
    )

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable  # the venv interpreter — manim is installed here
SANDBOX_SETTINGS = Path(__file__).with_name("sandbox.json")
FPS = int(os.environ.get("T2S_FPS", 60))  # final render is always 2560x1440 (-qp, 16:9); 60–120 fps
MAX_PARALLEL = int(os.environ.get("T2S_PARALLEL", 4))  # scenes at a time (user's call: 4)
CACHE_WARMUP_S = 20  # ponytail: fixed delay, not a signal that the cache is written; tune if logs show misses
CRITIC_ROUNDS = 2  # outline critic passes

# (model, effort) per stage. T2S_MODEL=<alias> forces one model everywhere (cheap smoke runs).
STAGES: dict[str, tuple[str, str]] = {
    "refine": ("haiku", "low"),
    "outline": ("sonnet", "high"),
    "outline_critic": ("sonnet", "high"),
    "outline_refactor": ("sonnet", "medium"),
    "clip_plan": ("sonnet", "high"),
    "math_verify": ("sonnet", "high"),
    "clip_build": ("sonnet", "high"),
    "clip_build_retry": ("sonnet", "xhigh"),
    }

APPROACHES: dict[str, tuple[str, type[BaseModel]]] = {
    "zoom": (CONCEPTUAL_ZOOM_SYSTEM, ConceptualZoomOutline),
    "arc": (PROBLEM_TO_SOLUTION_ARC_SYSTEM, ProblemSolutionArcOutline),
    "linear": (CLASSIC_LINEAR_NARRATIVE_SYSTEM, ClassicLinearNarrativeOutline),
    }

# bubblewrap jail for the final (unattended) render of LLM-written code: read-only host,
# no network, writable scene dir + ~/.cache only. Mirrors app/sandbox.json.
CACHE = Path.home() / ".cache"
LLM_CACHE = ROOT / ".cache" / "llm"  # non-agent results keyed by sha256 of every input
BWRAP = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp",
         "--bind", str(CACHE), str(CACHE), "--unshare-net", "--die-with-parent"]


# ── Schemas for new stages ────────────────────────────────────────────────────

def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


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
        schema: type[BaseModel] | None = None, scene: int | str | None = None,
        cwd: Path | None = None, agent: bool = False,
        ):
    """One `claude -p` call. Retries once; waits out rate/usage limits; non-agent results are cached by input hash.
    Raises RuntimeError if both attempts fail."""
    model, effort = STAGES[stage]
    model = os.environ.get("T2S_MODEL", model)
    tag = stage if scene is None else f"{stage}_{scene:03d}" if isinstance(scene, int) else f"{stage}_{scene}"
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
                "--permission-mode", "acceptEdits", "--permission-prompts", "none"]
    else:
        cmd += ["--system-prompt-file", str(sys_file), "--tools", ""]

    cached = None if agent else LLM_CACHE / (hashlib.sha256(json.dumps(
        [model, effort, system, user, schema and schema.model_json_schema()]).encode()).hexdigest() + ".json")
    if cached and cached.exists() and (out := parse_envelope(json.loads(cached.read_text()), schema)) is not None:
        log_row(run, {"run": run.name, "event": "end", "stage": stage, "type": "llm", "scene": scene, "model": model,
                      "effort": effort, "success": True, "cache_hit": True, "cost_usd": 0.0})
        return out
    env: dict = {}
    attempt = waits = 0
    while attempt < 2:
        attempt += 1
        t0 = time.monotonic()
        base = {"run": run.name, "call_id": uuid.uuid4().hex[:8], "stage_no": list(STAGES).index(stage) + 1,
                "stage": stage, "type": "agent" if agent else "llm", "scene": scene, "model": model,
                "effort": effort, "attempt": attempt}
        log_row(run, {**base, "event": "start"})  # a start row with no matching end row = running or killed
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
        usage = env.get("usage") or {}
        net_in, read, write = (usage.get(k) for k in
                               ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
        log_row(run, {
            **base, "event": "end", "success": out is not None,
            "outcome": getattr(out, "status", None),             # agent verdict, e.g. READY / FAILED
            "stop_reason": env.get("terminal_reason") or env.get("subtype"),
            "input_tokens": net_in, "output_tokens": usage.get("output_tokens"),
            "thinking_tokens": (usage.get("output_tokens_details") or {}).get("thinking_tokens"),
            "cache_read": read, "cache_write": write,
            "total_input_tokens": sum(x or 0 for x in (net_in, read, write)) if usage else None,
            "cost_usd": env.get("total_cost_usd"),
            "duration_ms": round((time.monotonic() - t0) * 1000), "api_ms": env.get("duration_api_ms"),
            "ttft_ms": env.get("ttft_ms"), "turns": env.get("num_turns"),
            "permission_denials": len(env.get("permission_denials") or []),
            "model_id": next(iter(env.get("modelUsage") or {}), None), "session_id": env.get("session_id"),
            "notes": (getattr(out, "notes", None) or None) and out.notes[:500],
            "error": None if out is not None else str(env.get("result") or env.get("subtype"))[:300],
            })
        if out is not None:
            if cached:
                cached.parent.mkdir(parents=True, exist_ok=True)
                cached.write_text(json.dumps(env))
            return out
        wait = transient_wait(str(env.get("result") or ""), waits)
        if wait is not None and waits < 6:  # rate limit / overload / usage limit: wait, then retry the same attempt
            waits += 1
            attempt -= 1
            print(f"{tag}: {str(env.get('result'))[:120]} — waiting {wait:.0f}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"{tag} failed twice: {str(env.get('result') or env.get('subtype'))[:300]}")


def transient_wait(error: str, n: int, now: datetime | None = None) -> float | None:
    """Seconds to wait before retrying a failed call, or None if the error is not transient."""
    m = re.search(r"limit\W+resets (\d{1,2})(?::(\d\d))?\s*([ap]m)\s*\(([^)]+)\)", error, re.I)
    if m:  # "You've hit your 5-hour limit · resets 1:30am (Asia/Kolkata)"
        hour, minute, ampm, tz = int(m[1]) % 12 + (12 if m[3].lower() == "pm" else 0), int(m[2] or 0), m[3], m[4]
        now = now or datetime.now(ZoneInfo(tz))
        reset = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        reset += timedelta(days=1) if reset <= now else timedelta()
        return min((reset - now).total_seconds() + 60, 6 * 3600)
    if re.search(r"rate.?limit|overloaded|\b(429|529)\b", error, re.I):
        return (10, 40, 120)[min(n, 2)]
    return None


def log_row(run: Path, row: dict) -> None:
    """One JSON object per line in runs/<id>/log.jsonl (start/end rows per Claude call, paired by call_id)."""
    with (run / "log.jsonl").open("a") as fh:
        fh.write(json.dumps({"ts": datetime.now().isoformat(timespec="milliseconds"), **row}) + "\n")


def run_cost(run: Path) -> float:
    log = run / "log.jsonl"
    return sum((json.loads(l).get("cost_usd") or 0) for l in log.read_text().splitlines()) if log.exists() else 0.0


def probe_seconds(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


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
    pf = subprocess.run([PYTHON, str(ROOT / "tools" / "preflight.py")], capture_output=True, text=True)
    if pf.returncode:  # fail before any paid call: missing LaTeX/ffmpeg/bwrap/… would only surface at render
        sys.exit(f"Preflight failed: {json.loads(pf.stdout)['problems']}")
    if a.tts == "polly":
        import boto3
        if boto3.Session().get_credentials() is None:
            sys.exit("AWS credentials not found for Polly — run `aws configure` or set AWS_PROFILE (or use --tts google)")
    else:
        import google.auth
        try:
            google.auth.default()
        except google.auth.exceptions.DefaultCredentialsError:
            sys.exit("Google credentials not found — run `gcloud auth application-default login` or set "
                     "GOOGLE_APPLICATION_CREDENTIALS (or use --tts polly)")
    families = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True).stdout
    if a.font and a.font.lower() not in {f.strip().lower() for line in families.splitlines() for f in line.split(",")}:
        sys.exit(f"Font not installed: {a.font!r} — pick one from `fc-list : family`")
    slug =re.sub(r"[^a-z0-9]+", "-", a.requirement.lower())[:40].strip("-")
    run = ROOT / "runs" / f"{datetime.now():%Y%m%d-%H%M%S}-{slug}"
    run.mkdir(parents=True)
    refined = claude(run, "refine", a.requirement, REQ_MODIFIER_SYSTEM)
    write_json(run / "brief.json", {
        "requirement": a.requirement, "approach": a.approach, "minutes": a.minutes, "pace": a.pace,
        "audience": a.audience, "notes": a.notes, "tts": a.tts, "voice": a.voice, "engine": a.engine, "font": a.font, "refined": refined.strip(),
        })
    print(run.relative_to(ROOT))
    print(refined.strip())


def _refactor_outline(run: Path, outline: dict, schema, critique: OutlineCritiqueResult, it: int) -> dict:
    user = build_outline_refactor_prompt(outline["meta"], outline["outline"], critique, it)
    return claude(run, "outline_refactor", user, OUTLINE_REFACTOR_SYSTEM, schema=schema).model_dump()


def cmd_outline(a) -> None:
    run = Path(a.run)
    brief = read_json(run / "brief.json")
    from app.clips import EXPLANATION_STYLE  # late import: clips imports pipeline
    system, schema = APPROACHES[brief["approach"]]
    system = f"{system}\n\n{EXPLANATION_STYLE}"  # static → still one cached prompt per approach

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
    target = brief["minutes"] * 60
    for it in (1, 2):  # length is arithmetic, so check it here rather than trusting an LLM critic
        total = sum(s.get("duration_seconds", 0) for s in outline["outline"])
        if abs(total - target) <= 0.2 * target:
            break
        print(f"outline is {total}s for a {target:.0f}s target — revising length")
        fix = OutlineCritiqueResult(approved=False, score=5, critique=f"Total duration {total}s; target {target:.0f}s.",
                                    improvements=[f"Rescale to {target:.0f}s total (±10%): set duration_seconds so they "
                                                  f"sum to about {target:.0f}; drop or merge the least essential scenes "
                                                  f"rather than squeezing every scene; update total_duration_seconds."])
        outline = _refactor_outline(run, outline, schema, fix, it)
    write_json(run / "outline.json", outline)

    meta = outline.get("meta", {})
    total = sum(s.get("duration_seconds", 0) for s in outline["outline"])
    print(f"\n# {meta.get('title')} — {total}s, {len(outline['outline'])} scenes\n")
    print("| # | title | sec | talking points |\n|---|---|---|---|")
    for i, s in enumerate(outline["outline"], 1):
        print(f"| s{i:02d} | {s.get('title')} | {s.get('duration_seconds')} | {'; '.join(s.get('talking_points', []))[:110]} |")
    print(f"\nFull outline: {run}/outline.json")


def tts_for(brief: dict):
    """The narration synthesiser the user chose for this video: AWS Polly or Google Cloud TTS."""
    return google_tts(brief["voice"]) if brief.get("tts") == "google" else polly_tts(brief["voice"], brief["engine"])


def polly_tts(voice: str, engine: str):
    """AWS Polly with SSML (pauses) and word speech marks (beat timing). Falls back to plain text when an engine
    rejects a tag, and to no marks when an engine has none."""
    import boto3

    polly = boto3.client("polly")

    def call(text: str, **kw):
        try:
            return polly.synthesize_speech(Text=speech.to_ssml(text), TextType="ssml", VoiceId=voice, Engine=engine, **kw)
        except polly.exceptions.InvalidSsmlException:
            return polly.synthesize_speech(Text=speech.to_plain(text), VoiceId=voice, Engine=engine, **kw)

    def synth(text: str) -> tuple[bytes, list[tuple[str, float]] | None]:
        # ponytail: one request per clip (clips are ≤ 30 s, far under Polly's 3000-char limit)
        audio = call(text, OutputFormat="mp3")["AudioStream"].read()
        try:
            raw = call(text, OutputFormat="json", SpeechMarkTypes=["word"])["AudioStream"].read().decode()
            marks = [(m["value"], m["time"] / 1000) for m in map(json.loads, raw.splitlines()) if m["type"] == "word"]
        except Exception:  # noqa: BLE001 — speech marks are a timing aid, never a reason to fail the voice step
            marks = None
        return audio, marks
    return synth


def google_tts(voice: str):
    """Google Cloud TTS (v1beta1 for timepoints): SSML with a <mark/> per word → word timings for beat sync.
    Voices without SSML support (e.g. Chirp 3 HD) fall back to plain text without timings."""
    from google.api_core.exceptions import InvalidArgument
    from google.cloud import texttospeech_v1beta1 as gtts

    client = gtts.TextToSpeechClient()
    voice_cfg = {"language_code": "-".join(voice.split("-")[:2]), "name": voice}
    mp3 = {"audio_encoding": gtts.AudioEncoding.MP3}

    def synth(text: str) -> tuple[bytes, list[tuple[str, float]] | None]:
        ssml, words = speech.to_ssml_marked(text)
        try:
            r = client.synthesize_speech(request={
                "input": {"ssml": ssml}, "voice": voice_cfg, "audio_config": mp3,
                "enable_time_pointing": [gtts.SynthesizeSpeechRequest.TimepointType.SSML_MARK]})
        except InvalidArgument:
            r = client.synthesize_speech(request={"input": {"text": speech.to_plain(text)}, "voice": voice_cfg,
                                                  "audio_config": mp3})
            return r.audio_content, None
        return r.audio_content, [(words[int(tp.mark_name)], tp.time_seconds) for tp in r.timepoints] or None
    return synth


def main() -> None:
    ap = argparse.ArgumentParser(prog="t2s")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new")
    p.add_argument("requirement")
    p.add_argument("--approach", choices=list(APPROACHES), default="zoom")
    p.add_argument("--minutes", type=float, default=2)
    p.add_argument("--pace", choices=["slow", "medium", "fast"], default="medium")
    p.add_argument("--audience", default="curious beginners")
    p.add_argument("--notes", default="")
    p.add_argument("--tts", choices=["polly", "google"], default=os.environ.get("T2S_TTS", "polly"),
                   help="narration provider: AWS Polly or Google Cloud Text-to-Speech")
    p.add_argument("--engine", choices=["neural", "generative", "standard"],
                   default=os.environ.get("POLLY_ENGINE", "neural"), help="Polly engine (ignored for Google)")
    p.add_argument("--font", help="font family for all Text (any name from `fc-list : family`); default: Manim's")
    p.add_argument("--voice", help="Polly: Matthew, Joanna, Ruth, Stephen … · Google: en-US-Neural2-D, en-US-Studio-O …")
    p.set_defaults(fn=cmd_new)

    p = sub.add_parser("outline")
    p.add_argument("run")
    p.add_argument("--feedback", help="human reviewer feedback to apply to the current outline")
    p.set_defaults(fn=cmd_outline)

    from app import clips  # clip-level commands (imports pipeline, so register late)
    clips.register(sub)
    a = ap.parse_args()
    if a.cmd == "new" and not a.voice:
        a.voice = (os.environ.get("GOOGLE_VOICE", "en-US-Neural2-D") if a.tts == "google"
                   else os.environ.get("POLLY_VOICE", "Matthew"))
    if getattr(a, "run", None):
        a.run = str(Path(a.run).resolve())  # child `claude -p` runs with cwd inside the run dir
    a.fn(a)


if __name__ == "__main__":
    main()
