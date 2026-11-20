"""Clip-level pipeline (Plan.md §5, §8, §12): outline scene → clips → voice per clip → one agent per clip → final.

Run layout (scene ids sNN, clip ids sNNcMM):
  runs/<id>/state.json              approvals + per-clip build state (the ledger)
  runs/<id>/feedback.jsonl          human feedback, scoped to outline | plan | sNN | sNNcMM
  runs/<id>/math.json               math verifier findings
  runs/<id>/scenes/sNN/plan.json    ScenePlan (plan.vN.json = earlier versions)
  runs/<id>/scenes/sNN/audio/       clip_MM.mp3 + index.json (spoken text hash → seconds, beat start times)
  runs/<id>/scenes/sNN/clips/       approved clip_MM.py files (the harness composes scene.py from them)
  runs/<id>/scenes/sNN/work/clip_MM agent sandbox: TASK.md/.json, API_CARDS.md, ./check, its own scene copy
Every stage skips work whose inputs are unchanged (content hashes), so re-running after feedback redoes only the
affected clips and the clips after them in that scene.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError

from app import pipeline as P
from app import speech
from app.graph.models.classic_linear_narrative import ClassicLinearNarrativeOutline
from app.graph.models.conceptual_zoom import ConceptualZoomOutline
from app.graph.models.problem_solution_arc import ProblemSolutionArcOutline
from schemas.models import ScenePlan

MANIM = "0.20.1"  # pinned in pyproject.toml
TOOLS = P.ROOT / "tools"
TOPICS_DIR = P.ROOT / "env" / "skills" / "manim-ce-0-20-1-reference" / "topics"
API_INDEX = P.ROOT / ".cache" / f"manim_api_{MANIM}.json"
ALWAYS_TOPICS = ["clip-structure", "timing-and-sync", "positioning-layout"]
STYLE = {"background": "#0e2733", "text": "WHITE", "focus": "YELLOW", "given": "BLUE", "derived": "GREEN",
         "warning": "RED", "secondary": "GREY_B"}
LEAD_IN, HOLD = 0.3, 0.8  # seconds of picture before the voice starts / after it ends, in every clip
_lock = threading.Lock()  # state.json / feedback.jsonl writers


class MathFinding(BaseModel):
    clip_id: str
    severity: Literal["ERROR", "WARN"]
    kind: Literal["FALSE", "UNSTATED", "NOTATION", "MISLEADING", "SPOKEN"]
    quote: str
    why: str
    fix: str


class MathReport(BaseModel):
    findings: list[MathFinding]


# ── Ledger: state.json + feedback.jsonl ─────────────────────────────────────────────────────────────────────────

def sha(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:16]


def load_state(run: Path) -> dict:
    f = run / "state.json"
    return json.loads(f.read_text()) if f.exists() else {"approved": {}, "clips": {}}


def update_state(run: Path, fn) -> dict:
    """Read-modify-write under a lock, written atomically (a crash never leaves a half-written state.json)."""
    with _lock:
        st = load_state(run)
        fn(st)
        tmp = run / "state.json.tmp"
        tmp.write_text(json.dumps(st, indent=1))
        os.replace(tmp, run / "state.json")
        return st


def feedback_for(run: Path, *targets: str) -> list[dict]:
    f = run / "feedback.jsonl"
    rows = [json.loads(l) for l in f.read_text().splitlines()] if f.exists() else []
    return [r for r in rows if r["target"] in targets]


def feedback_text(rows: list[dict]) -> str:
    return "\n".join(f"- [{r['target']} · {r['scope']}] {r['text']}" for r in rows) or "none"


def sid_of(n: int) -> str:
    return f"s{n:02d}"


def scene_plans(run: Path) -> list[ScenePlan]:
    return [ScenePlan.model_validate_json(p.read_text()) for p in sorted((run / "scenes").glob("s[0-9][0-9]/plan.json"))]


def save_versioned(path: Path, text: str) -> bool:
    """Write text; keep the old content as name.vN.ext. Returns True if the content changed."""
    if path.exists() and path.read_text() == text:
        return False
    if path.exists():
        n = len(list(path.parent.glob(f"{path.stem}.v*{path.suffix}"))) + 1
        shutil.copy(path, path.with_name(f"{path.stem}.v{n}{path.suffix}"))
    path.write_text(text)
    return True


# ── clips: plan every scene as clips, then verify the math ─────────────────────────────────────────────────────

def scene_end_problems(plan: ScenePlan) -> list[str]:
    """Each scene renders as its own Manim Scene, so no object can cross a scene boundary."""
    out = []
    if plan.clips[0].entry.persistent_objects:
        out.append(f"{plan.clips[0].clip_id} entry must be empty (scenes start on an empty frame)")
    if plan.clips[-1].exit.persistent_objects:
        out.append(f"{plan.clips[-1].clip_id} exit must be empty (scenes end with everything faded out)")
    return out


# ── voice: one narration file per clip (audio first: timings come from the real audio) ─────────────────────────

def cmd_voice(a) -> None:
    run = Path(a.run)
    brief = P.read_json(run / "brief.json")
    synth = None
    plans = scene_plans(run)
    pairs = speech.case_pairs([c.narration for p in plans for c in p.clips])  # letters used as both M and m
    for plan in plans:
        adir = run / "scenes" / plan.scene_id / "audio"
        adir.mkdir(exist_ok=True)
        idx = P.read_json(adir / "index.json") if (adir / "index.json").exists() else {}
        for c in plan.clips:
            text = speech.speakable(c.narration, pairs)
            key = sha(text, brief.get("tts", "polly"), brief["voice"], brief["engine"])
            mp3 = adir / f"clip_{c.index:02d}.mp3"
            if idx.get(c.clip_id, {}).get("hash") == key and mp3.exists():
                continue  # unchanged text → keep the audio
            synth = synth or P.tts_for(brief)
            audio, marks = synth(text)
            mp3.write_bytes(audio)
            idx[c.clip_id] = {"hash": key, "seconds": round(P.probe_seconds(mp3), 2), "spoken": text,
                              "beat_times": speech.phrase_times(marks, c.beats, pairs) if marks else None}
            print(f"{c.clip_id}: {idx[c.clip_id]['seconds']}s")
        P.write_json(adir / "index.json", idx)
    total = sum(v["seconds"] for p in scene_plans(run)
                for v in P.read_json(run / "scenes" / p.scene_id / "audio" / "index.json").values())
    print(f"total narration: {total:.1f}s")


# ── build: one sandboxed agent per clip, gated by ./check, re-checked in a jail ─────────────────────────────────

def ensure_api_index() -> None:
    if not API_INDEX.exists():
        API_INDEX.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([P.PYTHON, str(TOOLS / "build_manim_api_index.py"), "--out", str(API_INDEX)], check=True,
                       capture_output=True)


# ── deterministic stage commands for a Claude Code session: validate · task · accept · next steps ──────────────

OUTLINE_MODELS = {"zoom": ConceptualZoomOutline, "arc": ProblemSolutionArcOutline, "linear": ClassicLinearNarrativeOutline}
AGENT_FILE = P.ROOT / "env" / "agents" / "clip-builder.md"
STANDARDS = P.ROOT / "env" / "skills" / "t2s-produce" / "references" / "standards.md"


def _errors(exc: ValidationError) -> list[str]:
    return [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()]


def validate_outline(run: Path) -> list[str]:
    """outline.json against the brief's approach schema, plus the length rule (±20% of the requested minutes)."""
    brief = P.read_json(run / "brief.json")
    try:
        outline = OUTLINE_MODELS[brief.get("approach", "zoom")].model_validate_json((run / "outline.json").read_text())
    except FileNotFoundError:
        return ["outline.json does not exist"]
    except ValidationError as exc:
        return _errors(exc)
    total, target = sum(s.duration_seconds for s in outline.outline), brief["minutes"] * 60
    return [] if abs(total - target) <= 0.2 * target else [
        f"scenes total {total}s but the target is {target:.0f}s (±20%): rescale duration_seconds, drop or merge scenes"]


def validate_plan(run: Path, sid: str) -> list[str]:
    """scenes/sNN/plan.json: ScenePlan contracts, empty scene boundaries, symbol colours consistent with earlier scenes."""
    try:
        plan = ScenePlan.model_validate_json((run / "scenes" / sid / "plan.json").read_text())
    except FileNotFoundError:
        return [f"scenes/{sid}/plan.json does not exist"]
    except ValidationError as exc:
        return _errors(exc)
    errors = [] if plan.scene_id == sid else [f"scene_id is {plan.scene_id}, expected {sid}"]
    errors += scene_end_problems(plan)
    for earlier in (p for p in scene_plans(run) if p.scene_id < sid):
        errors += [f"`{sym}` is {col} here but {earlier.color_roles[sym]} in {earlier.scene_id}: one colour per symbol"
                   for sym, col in plan.color_roles.items() if earlier.color_roles.get(sym, col) != col]
    return errors


def validate_math(run: Path) -> list[str]:
    try:
        report = MathReport.model_validate_json((run / "math.json").read_text())
    except FileNotFoundError:
        return ["math.json does not exist"]
    except ValidationError as exc:
        return _errors(exc)
    known = {c.clip_id for p in scene_plans(run) for c in p.clips}
    return [f"unknown clip {f.clip_id}" for f in report.findings if f.clip_id not in known]


def find_clip(run: Path, clip_id: str):
    plan = ScenePlan.model_validate_json((run / "scenes" / clip_id[:3] / "plan.json").read_text())
    return plan, next(c for c in plan.clips if c.clip_id == clip_id)


def clip_key(run: Path, plan: ScenePlan, c) -> str:
    """Everything a clip's code depends on; the previous clip's installed code makes changes cascade in order."""
    sd = run / "scenes" / plan.scene_id
    prev = sd / "clips" / f"clip_{c.index - 1:02d}.py"
    return sha(c.model_dump(), P.read_json(sd / "audio" / "index.json").get(c.clip_id), plan.color_roles,
               feedback_for(run, plan.scene_id, c.clip_id), prev.read_text() if c.index > 1 and prev.exists() else "",
               P.read_json(run / "brief.json").get("font"), AGENT_FILE.read_text() if AGENT_FILE.exists() else "")


def prepare_clip(run: Path, clip_id: str) -> Path:
    """Set up scenes/sNN/work/clip_MM/ for the clip-builder: TASK.md/.json, API_CARDS.md, ./check, earlier clips."""
    plan, c = find_clip(run, clip_id)
    sd, mm = run / "scenes" / plan.scene_id, f"clip_{c.index:02d}"
    st = load_state(run)["clips"]
    missing = [x.clip_id for x in plan.clips[: c.index - 1] if st.get(x.clip_id, {}).get("status") != "READY"]
    if missing:
        sys.exit(f"build {missing[0]} first: {clip_id} starts from its exit state")
    audio = P.read_json(sd / "audio" / "index.json")[clip_id]
    brief = P.read_json(run / "brief.json")
    math = P.read_json(run / "math.json")["findings"] if (run / "math.json").exists() else []
    math_notes = [f"{f['kind']}: \"{f['quote']}\" → {f['fix']}" for f in math if f["clip_id"] == clip_id]
    ensure_api_index()
    w = sd / "work" / mm
    w.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(w / "scene", ignore_errors=True)
    shutil.rmtree(w / "checks", ignore_errors=True)
    (w / "scene" / "clips").mkdir(parents=True)
    (sd / "clips").mkdir(exist_ok=True)
    for earlier in plan.clips[: c.index - 1]:  # snapshot of the approved clips before this one
        shutil.copy(sd / "clips" / f"clip_{earlier.index:02d}.py", w / "scene" / "clips")
    if (sd / "clips" / f"{mm}.py").exists() and not (w / f"{mm}.py").exists():
        shutil.copy(sd / "clips" / f"{mm}.py", w)  # a rebuild starts from the approved version
    task = {"clip": mm, "clip_id": clip_id, "scene_id": plan.scene_id, "class": "Scene" + plan.scene_id[1:],
            "seconds": round(LEAD_IN + audio["seconds"] + HOLD, 2), "entry": c.entry.persistent_objects,
            "exit": c.exit.persistent_objects, "api_index": str(API_INDEX), "background": STYLE["background"]}
    P.write_json(w / "TASK.json", task)
    times = audio.get("beat_times") or [None] * len(c.beats)  # word timings → when the voice says each phrase
    beats = "\n".join(f"  {i}. {'' if at is None else f'@ {LEAD_IN + at:.1f}s  '}{b}"
                      for i, (b, at) in enumerate(zip(c.beats, times), 1))
    (w / "TASK.md").write_text(
        f"READ FIRST: {STANDARDS}, " + ", ".join(str(TOPICS_DIR / f"{x}.md") for x in ALWAYS_TOPICS) + "\n"
        f"CLIP {clip_id}  (scene {plan.scene_id}, clip {c.index} of {len(plan.clips)})   FILE: {mm}.py   "
        f"NARRATION_SECONDS: {audio['seconds']}   CLIP_SECONDS: {task['seconds']} (voice from {LEAD_IN}s, hold {HOLD}s)\n"
        f"OBJECTIVE: {c.objective}\nNARRATION (exact):\n  {c.narration}\nVISUAL INTENT: {c.visual_intent}\n"
        f"BEATS:\n{beats}\nON-SCREEN MATH (exact LaTeX): {json.dumps(c.on_screen_math)}\n"
        f"ENTRY (already on screen, in self.reg): {json.dumps(c.entry.model_dump())}\n"
        f"EXIT (must be in self.reg and on screen at the end): {json.dumps(c.exit.model_dump())}\n"
        f"SYMBOL COLORS: {json.dumps(plan.color_roles)}   FONT: {brief.get('font') or 'Manim default'}\n"
        f"MATH NOTES (verified): {'; '.join(math_notes) or 'none'}\n"
        f"HUMAN_FEEDBACK:\n{feedback_text(feedback_for(run, plan.scene_id, clip_id))}\n"
        f"PREVIOUS ATTEMPT: {mm + '.py exists — start from it' if (w / f'{mm}.py').exists() else 'none'}\n")
    topics = [x for x in dict.fromkeys(c.manim_topics) if x not in ALWAYS_TOPICS]
    cards = subprocess.run([P.PYTHON, str(TOOLS / "doc_cards.py"), "--index", str(API_INDEX), "--topics",
                            ",".join(topics), "--topics-dir", str(TOPICS_DIR)], capture_output=True, text=True)
    (w / "API_CARDS.md").write_text(cards.stdout if topics else "No extra topic cards for this clip. "
                                    "Check any other name with ./check doc Name.\n")
    (w / "check").write_text(f'#!/bin/sh\nexec "{P.PYTHON}" "{P.ROOT / "app" / "check.py"}" "$@"\n')
    (w / "check").chmod(0o755)
    return w


def accept_clip(run: Path, clip_id: str) -> dict:
    """Re-run every gate on the clip in a jail (it is LLM-written code); install it only if all pass."""
    plan, c = find_clip(run, clip_id)
    sd, mm = run / "scenes" / plan.scene_id, f"clip_{c.index:02d}"
    w = sd / "work" / mm
    ok = (w / f"{mm}.py").exists() and subprocess.run(
        P.BWRAP + ["--bind", str(w), str(w), P.PYTHON, str(P.ROOT / "app" / "check.py"), "all"],
        cwd=w, capture_output=True).returncode == 0
    findings = [f"{gate.stem}: {f['code']}" for gate in sorted((w / "checks").glob("*.json"))
                for f in P.read_json(gate).get("findings", []) if f.get("severity") == "ERROR"]
    if ok:
        shutil.copy(w / f"{mm}.py", sd / "clips" / f"{mm}.py")
    result = {"status": "READY" if ok else "FAILED", "open_findings": findings,
              "key": clip_key(run, plan, c) if ok else None, "at": datetime.now().isoformat(timespec="seconds")}
    update_state(run, lambda s: s["clips"].__setitem__(clip_id, result))
    return result


def next_steps(run: Path) -> list[str]:
    """What is left to do, in order — the resume point after any interruption."""
    st, steps = load_state(run), []
    if (run / "brief.json").exists() and P.read_json(run / "brief.json").get("approach"):
        steps += [f"outline: {e}" for e in validate_outline(run)]
        if "outline" not in st["approved"]:
            steps.append("CP1: approve the outline (t2s approve <run> outline)")
    plans = scene_plans(run)
    for p in plans:
        steps += [f"{p.scene_id} plan: {e}" for e in validate_plan(run, p.scene_id)]
    if plans and "plan" not in st["approved"]:
        steps.append("CP2: math review + approve the clip plan (t2s approve <run> plan)")
    for p in plans:
        idx = run / "scenes" / p.scene_id / "audio" / "index.json"
        if not idx.exists() or set(P.read_json(idx)) != {c.clip_id for c in p.clips}:
            steps.append(f"{p.scene_id}: narration audio missing (t2s voice <run>)")
            continue
        stale = next((c.clip_id for c in p.clips if st["clips"].get(c.clip_id, {}).get("key") != clip_key(run, p, c)), None)
        if stale:
            steps.append(f"build {stale} (t2s task → clip-builder → t2s accept), then the rest of {p.scene_id}")
        elif f"scene:{p.scene_id}" not in st["approved"]:
            steps.append(f"CP3: preview and approve {p.scene_id}")
    if plans and not (run / "final.mp4").exists():
        steps.append("t2s final <run>")
    elif plans and "final" not in st["approved"]:
        steps.append("CP4: approve the final video")
    return steps


# ── final: full-quality render per scene (sections → one file per clip), assembly, media checks ─────────────────

def cmd_final(a) -> None:
    run = Path(a.run)
    st = load_state(run)
    plans = scene_plans(run)
    missing = [c.clip_id for p in plans for c in p.clips if st["clips"].get(c.clip_id, {}).get("status") != "READY"]
    if missing:
        sys.exit(f"Not built yet: {missing}. Run build first.")
    unapproved = [p.scene_id for p in plans if f"scene:{p.scene_id}" not in st["approved"]]
    if unapproved and not a.force:
        sys.exit(f"Scene previews not approved (CP3): {unapproved} — `approve <run> sNN` (or --force).")
    if not 60 <= P.FPS <= 120:
        sys.exit(f"T2S_FPS={P.FPS}: must be 60–120")

    def render_scene(p: ScenePlan) -> dict:
        sd = run / "scenes" / p.scene_id
        subprocess.run([P.PYTHON, str(TOOLS / "scene_harness.py"), "compose", str(sd), "--scene-id", p.scene_id],
                       check=True, capture_output=True)
        shutil.rmtree(sd / "media_final", ignore_errors=True)
        r = subprocess.run(P.BWRAP + ["--bind", str(sd), str(sd), "--setenv", "T2S_BACKGROUND", STYLE["background"],
                                      P.PYTHON, str(TOOLS / "scene_harness.py"), "render", str(sd), "--scene-id",
                                      p.scene_id, "--quality", "p", "--fps", str(P.FPS), "--media", "media_final"],
                           capture_output=True, text=True, timeout=7200)
        try:
            return json.loads(r.stdout)
        except json.JSONDecodeError:
            return {"ok": False, "stderr_tail": r.stderr[-2000:]}

    renders = dict(zip([p.scene_id for p in plans], P.parallel(render_scene, plans)))
    failed = {k: v.get("stderr_tail") for k, v in renders.items() if not v.get("ok")}
    if failed:
        sys.exit(f"Final render failed: {json.dumps(failed, indent=1)[:3000]}")
    manifest = {"scenes": [{"scene_id": p.scene_id, "clips": [
        {"clip_id": c.clip_id,
         "video": str(run / "scenes" / p.scene_id / next(s["path"] for s in renders[p.scene_id]["sections"]
                                                         if s["name"] == f"clip_{c.index:02d}")),
         "audio": str(run / "scenes" / p.scene_id / "audio" / f"clip_{c.index:02d}.mp3"),
         "lead_in": LEAD_IN} for c in p.clips]}
        for p in plans]}
    P.write_json(run / "assembly.json", manifest)
    sys.path.insert(0, str(TOOLS))
    from assemble_clips import assemble  # noqa: E402  (tools/ is a script folder, not a package)
    report = assemble(manifest, run / "final.mp4", run / "assembly_work")
    report["checks"] = media_checks(run / "final.mp4")
    P.write_json(run / "final_report.json", report)
    print(f"{run / 'final.mp4'}\nduration: {report['final_s']}s · clips: {len(report['clips'])}")
    for f in report["checks"]:
        print(f"{f['severity']} {f['code']}: {f['message']}")


def media_checks(path: Path) -> list[dict]:
    """ffprobe streams + EBU R128 loudness + black frames (Plan.md §16.6)."""
    out = []
    streams = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)],
                                        capture_output=True, text=True).stdout)["streams"]
    v = next((s for s in streams if s["codec_type"] == "video"), {})
    if (v.get("width"), v.get("height")) != (2560, 1440):
        out.append({"severity": "ERROR", "code": "RESOLUTION", "message": f"{v.get('width')}x{v.get('height')}"})
    num, _, den = (v.get("avg_frame_rate") or "0/1").partition("/")
    if float(num) / float(den or 1) < 59.5:
        out.append({"severity": "ERROR", "code": "FRAME_RATE", "message": f"{v.get('avg_frame_rate')} fps (minimum 60)"})
    if not any(s["codec_type"] == "audio" for s in streams):
        out.append({"severity": "ERROR", "code": "NO_AUDIO", "message": "no audio stream"})
    log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-vf",
                          "blackdetect=d=1.0:pix_th=0.05", "-f", "null", "-"], capture_output=True, text=True).stderr
    lufs = [float(x.split("I:")[1].split("LUFS")[0]) for x in log.splitlines() if " I:" in x and "LUFS" in x]
    if lufs and abs(lufs[-1] + 16) > 1.5:
        out.append({"severity": "WARN", "code": "LOUDNESS", "message": f"{lufs[-1]} LUFS (target -16)"})
    blacks = [x for x in log.splitlines() if "black_start" in x]
    if blacks:
        out.append({"severity": "WARN", "code": "BLACK_FRAMES", "message": f"{len(blacks)} black stretch(es) ≥ 1 s"})
    return out


# ── checkpoints: approve / feedback / status ────────────────────────────────────────────────────────────────────

def add_feedback(run: Path, target: str, scope: str, text: str) -> None:
    with _lock, (run / "feedback.jsonl").open("a") as fh:
        fh.write(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"), "target": target, "scope": scope,
                             "text": text}) + "\n")


def cmd_feedback(a) -> None:
    add_feedback(Path(a.run), a.target, a.scope, a.text)
    print(f"feedback recorded for {a.target} ({a.scope}). Re-run "
          f"{'clips' if a.scope in ('narration', 'math', 'plan') else 'build'} to apply it.")


def cmd_approve(a) -> None:
    run = Path(a.run)
    target = a.target if a.target in ("outline", "plan", "final") else f"scene:{a.target}"
    if target == "plan" and not a.force:
        errors = [f for f in P.read_json(run / "math.json")["findings"] if f["severity"] == "ERROR"] \
            if (run / "math.json").exists() else []
        if errors:
            sys.exit(f"{len(errors)} math ERROR finding(s) open — fix via `feedback <run> sNNcMM --scope math` "
                     f"and re-run clips, or approve with --force to accept them.")
    update_state(run, lambda s: s["approved"].__setitem__(target, datetime.now().isoformat(timespec="seconds")))
    print(f"approved {target}")


def cmd_status(a) -> None:
    run = Path(a.run)
    st = load_state(run)
    print(f"approved: {', '.join(st['approved']) or 'nothing yet'}")
    print("| clip | status | notes |\n|---|---|---|")
    for p in scene_plans(run):
        for c in p.clips:
            s = st["clips"].get(c.clip_id, {})
            print(f"| {c.clip_id} | {s.get('status', 'not built')} | {s.get('notes', '')[:100]} |")
    print("next:" if (steps := next_steps(run)) else "next: nothing — the video is done.")
    print("\n".join(f"  - {s}" for s in steps))


def cmd_validate(a) -> None:
    run = Path(a.run)
    if a.what == "plan":
        sids = [a.scene] if a.scene else [p.parent.name for p in sorted((run / "scenes").glob("s[0-9][0-9]/plan.json"))]
        errors = [f"{s}: {e}" for s in sids for e in validate_plan(run, s)]
    else:
        errors = validate_outline(run) if a.what == "outline" else validate_math(run)
    print("\n".join(errors) or f"{a.what}: OK")
    sys.exit(1 if errors else 0)


def cmd_accept(a) -> None:
    r = accept_clip(Path(a.run), a.clip)
    print(f"{a.clip}: {r['status']}" + (f" — {', '.join(r['open_findings'])}" if r["open_findings"] else ""))
    sys.exit(0 if r["status"] == "READY" else 1)


def register(sub) -> None:
    def add(name, fn, *, scenes=False, clips=False, feedback=False, force=False):
        p = sub.add_parser(name)
        p.add_argument("run")
        if scenes:
            p.add_argument("--scenes", help="comma-separated scene numbers")
        if clips:
            p.add_argument("--clips", help="comma-separated clip ids to rebuild, e.g. s01c02")
        if feedback:
            p.add_argument("--feedback")
        if force:
            p.add_argument("--force", action="store_true")
        p.set_defaults(fn=lambda a: fn(_abs(a)))
        return p

    add("voice", cmd_voice)
    add("final", cmd_final, force=True)
    add("status", cmd_status)
    p = add("validate", cmd_validate)
    p.add_argument("what", choices=["outline", "plan", "math"])
    p.add_argument("--scene", help="sNN (plan only; default: every scene plan)")
    p = add("task", lambda a: print(prepare_clip(Path(a.run), a.clip)))
    p.add_argument("clip", help="sNNcMM")
    p = add("accept", cmd_accept)
    p.add_argument("clip", help="sNNcMM")
    p = add("approve", cmd_approve, force=True)
    p.add_argument("target", help="outline | plan | sNN | final")
    p = add("feedback", cmd_feedback)
    p.add_argument("target", help="outline | sNN | sNNcMM")
    p.add_argument("--scope", default="visual", choices=["narration", "math", "visual", "plan"])
    p.add_argument("--text", required=True)


def _abs(a):
    a.run = str(Path(a.run).resolve())
    return a
