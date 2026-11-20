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
from schemas.models import ScenePlan

MANIM = "0.20.1"  # pinned in pyproject.toml
TOOLS = P.ROOT / "tools"
TOPICS_DIR = P.ROOT / ".claude" / "skills" / "manim-ce-0-20-1-reference" / "topics"
API_INDEX = P.ROOT / ".cache" / f"manim_api_{MANIM}.json"
ALWAYS_TOPICS = ["clip-structure", "timing-and-sync", "positioning-layout"]
WPM = {"slow": 130, "medium": 150, "fast": 170}
STYLE = {"background": "#0e2733", "text": "WHITE", "focus": "YELLOW", "given": "BLUE", "derived": "GREEN",
         "warning": "RED", "secondary": "GREY_B"}
LEAD_IN, HOLD = 0.3, 0.8  # seconds of picture before the voice starts / after it ends, in every clip

# Shared by the planner, the math verifier and the builder: written once into each static system prompt (prompt cache),
# so every scene and clip of every video follows the same rules without resending them per call.
VIDEO_STANDARDS = f"""
VIDEO STANDARDS — identical for every scene and clip
Frame: 16:9, 2560×1440 (Manim frame 14.2 × 8 units); keep 0.5 units clear of every edge. One background for the whole
video ({STYLE["background"]}, set by the harness — never set it in clip code).
Palette roles (Manim colour constants): text {STYLE["text"]} · current focus/highlight {STYLE["focus"]} ·
given quantities {STYLE["given"]} · derived results {STYLE["derived"]} · mistakes/warnings {STYLE["warning"]} ·
secondary/dimmed {STYLE["secondary"]}. Each math symbol keeps ONE colour for the whole video (SYMBOL COLORS).
Type scale (font_size): title 48 · body 34 · label 28 · caption 24, never smaller. MathTex: main formula 44, inline 34.
Zones: top_center = title or the running formula · center = main diagram · left_half/right_half = comparisons ·
bottom_center = one-line caption. At most 2 text blocks and 1 diagram on screen at once.
Timing: Write/Create 0.8–1.5 s · FadeIn/FadeOut 0.4–0.6 s · Transform 0.8–1.2 s · hold ≥ 0.8 s after a key result.
Nothing moves during a [pause]: that is when the viewer looks.
Clip rhythm: the picture starts {LEAD_IN} s before the voice; the final frame holds ≥ {HOLD} s after the voice ends.
Scenes: every scene starts on an empty frame and ends with its objects faded out (last beat of the last clip).
Narration text: plain spoken English for a voice. Write math symbols in backticks (`a`, `M`, `v_1`, `θ`) so the voice
says their names; write [pause] where the viewer needs a moment to look (after a key result, before a new step);
write units and abbreviations as words when in doubt ("meters per second", "astronomical units"). If one letter is used
in both cases (M and m), say the difference in words the first time ("big `M`, the Sun's mass").
""".strip()

EXPLANATION_STYLE = """
EXPLANATION STYLE — ELI5 / Feynman
- Start from something the viewer already knows (an everyday object or experience), then name the idea.
- One new idea per sentence; short sentences; every term gets a plain-words meaning where it first appears.
- Concrete before abstract: a picture or a worked number first, the general rule after.
- Show why it is true, not only that it is true: give the step the viewer would otherwise have to take on trust.
- After each key step, a one-line plain recap ("So: …").
- Talk to one curious person ("you"), warm and direct; no filler, no hype.
""".strip()
_lock = threading.Lock()

# ── Static prompts (identical for every call → prompt-cache hits; dynamic data only in the user message) ─────────

CLIP_PLANNER_SYSTEM = """
You plan one scene of an animated math/science explainer (Manim, 2D, 16:9) as a sequence of CLIPS.
A clip is the unit that will be animated, rendered, reviewed and regenerated on its own.

CLIP RULES
1. One teaching purpose per clip. If the objective needs "and", split it.
2. 2–6 clips per scene; 4–20 s of narration per clip (hard max 30 s). The scene's clips together should match the
   scene's duration_seconds.
3. narration: the exact words the voice will say, following "Narration text" in VIDEO STANDARDS (symbols in
   backticks, [pause] markers, no markdown, numbers ≤ 2 decimals). Word budget per clip
   = est_seconds × target_wpm / 60 (±10%). Across the scene, cover the scene's talking_points in order.
4. beats: 1–8 visual events in narration order. Each beat names the narration phrase it starts on, in quotes,
   then what visibly changes. Example: "\\"the hypotenuse\\" → side c highlights in YELLOW".
   One visual event per phrase; never two unrelated events during one sentence.
5. on_screen_math: every LaTeX string that appears, exactly as it should render (raw LaTeX, no $).
   Keep a formula on screen while the narration discusses it.
6. Continuity contracts. entry = what is on screen when the clip starts; exit = what must remain at its end.
   Name objects with snake_case registry names (eq_main, axes, curve_f). Clip N+1's entry must equal clip N's exit.
   The FIRST clip's entry and the LAST clip's exit are always empty: each scene renders separately.
   Transitions between scenes are visual: the last clip's final beat leads into transition_to_next and fades the
   scene out; when the outline continues an idea, the first clip's first beat re-draws PREVIOUS SCENE FINAL IMAGE
   (same objects, colours and zones) before moving on, so the cut feels like one continuous video.
7. object_positions use semantic zones only: top_center, top_left, top_right, center, left_half, right_half,
   bottom_center, bottom_left, bottom_right.
8. manim_topics: choose from this closed list only: clip-structure, mathtex-indexing, text-and-latex,
   positioning-layout, timing-and-sync, transforms, axes-and-graphs, camera, updaters-and-trackers, emphasis.
9. Do not introduce facts, formulas or numbers that are not in the scene's talking points or derivable from them.
   If a talking point is ambiguous, keep the claim narrower rather than adding content.
10. Screen budget: at most 2 text blocks and 1 diagram visible at once; say in beats when things leave.
11. Ids: scene_id is given; clip_id = scene_id + "c" + two-digit index (s02c01, s02c02, …); index starts at 1.
12. color_roles: map every math symbol and recurring object of this scene to one palette constant. Reuse SYMBOL
   COLORS SO FAR exactly; add only symbols that are new in this scene.
13. Pacing: about one [pause] per clip, after the key result; beats never put motion inside a pause.
14. HUMAN FEEDBACK, when present, overrides everything above for what it mentions.
Return the ScenePlan as structured output.

""" + VIDEO_STANDARDS + "\n\n" + EXPLANATION_STYLE

MATH_VERIFIER_SYSTEM = """
You are a mathematics editor checking an explainer script before it is animated.
For every clip you receive its narration and the formulas shown on screen.
Report only real problems:
  FALSE        a statement or formula is wrong
  UNSTATED     a result is used outside its conditions (domain, convergence, non-zero divisor, ...) and the
               narration states it as unconditional
  NOTATION     a symbol changes meaning, or narration and formula disagree ("x squared" vs x^3)
  MISLEADING   a simplification will leave a wrong mental model for the stated audience
  SPOKEN       a formula will be read aloud ambiguously by TTS ("1/2x")
For each problem give clip_id, the quoted text, why it is wrong, and the minimal correction.
Severity: ERROR for FALSE, NOTATION and UNSTATED; WARN otherwise, and WARN whenever you are not sure.
Do not comment on style, pacing or visuals. No problems → empty findings list.
Narration convention (intended, not a problem): math symbols are written in backticks (`a`) and spoken by name;
[pause] marks a pause. Report SPOKEN when a symbol outside backticks would be read ambiguously.
""".strip()

CLIP_BUILDER_SYSTEM = f"""
You implement ONE clip of a Manim Community Edition {MANIM} animation, in the file clip_MM.py in the current
directory (MM = the clip number in TASK.md). Everything you need is in TASK.md and API_CARDS.md.
You are sandboxed: no network; you may write only in this directory.

FILE CONTRACT
- clip_MM.py contains `from manim import *` (+ optional math/numpy/random) and exactly one function
  `def clip_MM(self):` (self is the Scene). Nothing else at top level except imports and constants.
- Objects crossing clip boundaries live in self.reg (a dict). Read only the ENTRY names; when the clip ends,
  self.reg must hold exactly the EXIT names and those objects must be on screen. Remove everything else.
- Never set the background or camera background: the harness sets one background for the whole video.
- Use the palette roles and SYMBOL COLORS from TASK.md; if TASK.md names a FONT, pass font=<FONT> to every
  Text/MarkupText.
- Use only APIs that appear in API_CARDS.md or that you confirm with `./check doc Name1,Name2`.
  If a name is reported as not in Manim, do not use it.

LOOP (stop as soon as all gates pass)
1. Write clip_MM.py implementing every beat in TASK.md, in order, synced to the narration phrases.
   The clip must run between CLIP_SECONDS and CLIP_SECONDS + 1.5 (TASK.md). The voice starts at t = {LEAD_IN} s;
   when BEATS carry times ("@ 2.4s"), start that beat's animation at that time (±0.2 s), using self.wait() to line up.
2. Gate A (static):  ./check static  → fix every ERROR. Do not render while Gate A fails.
3. Gate B (layout+timing): ./check probe → fix OUT_OF_FRAME, OVERLAP, CLIP_TOO_SHORT, CONTRACT_* errors.
4. Gate C (render):  ./check render  → draft render of this clip only; on failure read the error,
   fix the root cause (not the symptom), re-run from Gate A.
5. Gate D (look):    ./check frames  → writes frames/; Read them. Fix only what geometry cannot catch: wrong object
   highlighted, poor colour contrast, a beat that does not show what the narration says. At most 2 look passes.
6. Finish. status=READY only if `./check all` exits 0 on the final file. Otherwise FAILED with the remaining
   finding codes in open_findings. Never claim a check passed that you did not run.

REPAIR DISCIPLINE
- Change the smallest thing that fixes the finding. Do not rewrite working beats.
- If the same finding repeats after 2 fixes, change approach (different construction), and say so in notes.
- HUMAN_FEEDBACK in TASK.md overrides beats/visual intent for what it mentions — nothing else.
- Run only ./check, python, ffmpeg, ffprobe, ls.

""" + VIDEO_STANDARDS + f"\n\nALWAYS-ON TOPIC CARDS (Manim {MANIM})\n" + "\n".join(
    (TOPICS_DIR / f"{name}.md").read_text() for name in ALWAYS_TOPICS)


class MathFinding(BaseModel):
    clip_id: str
    severity: Literal["ERROR", "WARN"]
    kind: Literal["FALSE", "UNSTATED", "NOTATION", "MISLEADING", "SPOKEN"]
    quote: str
    why: str
    fix: str


class MathReport(BaseModel):
    findings: list[MathFinding]


class ClipResult(BaseModel):
    status: Literal["READY", "FAILED"]
    gate_runs: int = 0
    renders: int = 0
    notes: str = ""
    open_findings: list[str] = []


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

def cmd_clips(a) -> None:
    run = Path(a.run)
    brief = P.read_json(run / "brief.json")
    outline = P.read_json(run / "outline.json")
    meta, segs = outline.get("meta", {}), outline["outline"]
    targets = {int(x) for x in a.scenes.split(",")} if a.scenes else None
    if a.feedback:
        for n in targets or range(1, len(segs) + 1):
            add_feedback(run, sid_of(n), "plan", a.feedback)
    summaries = "\n".join(f"  {sid_of(i)} {s.get('title', '')}: {s.get('visual_plan', '')[:140]}"
                          for i, s in enumerate(segs, 1))
    prev_image, colors = "none — this is the first scene", {}
    for i, seg in enumerate(segs, 1):  # sequential: each scene builds on the previous scene's colours and final image
        sid, d = sid_of(i), run / "scenes" / sid_of(i)
        if targets is None or i in targets:
            d.mkdir(parents=True, exist_ok=True)
            fb = feedback_for(run, "outline", sid, *(f"{sid}c{k:02d}" for k in range(1, 9)))
            user = (f"VIDEO: {meta.get('title', '')} · audience: {brief['audience']} · "
                    f"target_wpm: {WPM.get(brief.get('pace'), 150)} · aspect: 16:9\n"
                    f"OTHER SCENES (one line each):\n{summaries}\n"
                    f"SYMBOL COLORS SO FAR: {json.dumps(colors)}\nPREVIOUS SCENE FINAL IMAGE: {prev_image}\n"
                    f"TARGET SCENE {sid} ({seg.get('duration_seconds', 30)}s, {seg.get('segment_type', '')}):\n"
                    f"  title: {seg.get('title', '')}\n  talking_points: {json.dumps(seg.get('talking_points', []))}\n"
                    f"  visual_plan: {seg.get('visual_plan', '')}\n  narration_hint: {seg.get('narration_hint', '')}\n"
                    f"  transition_to_next: {seg.get('transition_to_next', '')}\nHUMAN FEEDBACK:\n{feedback_text(fb)}")
            save_versioned(d / "plan.json", plan_scene(run, sid, i, user).model_dump_json(indent=1))
        if (d / "plan.json").exists():
            sp = ScenePlan.model_validate_json((d / "plan.json").read_text())
            prev_image = f"{sp.clips[-1].visual_intent} Final beat: {sp.clips[-1].beats[-1]}"
            colors.update(sp.color_roles)
    verify_math(run, brief)
    print_plan(run)


def plan_scene(run: Path, sid: str, index: int, user: str) -> ScenePlan:
    """Clip-plan one scene; a plan that breaks the scene-boundary rule is sent back once with the exact problem."""
    problems: list[str] = []
    for _ in (1, 2):
        plan = P.claude(run, "clip_plan", user, CLIP_PLANNER_SYSTEM, schema=ScenePlan, scene=sid)
        plan = ScenePlan.model_validate({**plan.model_dump(), "scene_id": sid, "index": index})  # re-run validators
        problems = scene_end_problems(plan)
        if not problems:
            return plan
        user += "\n\nYOUR PREVIOUS PLAN WAS REJECTED: " + "; ".join(problems) + ". Fix exactly that."
    raise RuntimeError(f"{sid}: clip plan still breaks the scene-boundary rule: {problems}")


def scene_end_problems(plan: ScenePlan) -> list[str]:
    """Each scene renders as its own Manim Scene, so no object can cross a scene boundary."""
    out = []
    if plan.clips[0].entry.persistent_objects:
        out.append(f"{plan.clips[0].clip_id} entry must be empty (scenes start on an empty frame)")
    if plan.clips[-1].exit.persistent_objects:
        out.append(f"{plan.clips[-1].clip_id} exit must be empty (scenes end with everything faded out)")
    return out


def verify_math(run: Path, brief: dict) -> None:
    clips = [c for s in scene_plans(run) for c in s.clips]
    user = (f"AUDIENCE: {brief['audience']}\nCLIPS:\n" +
            "\n".join(f"- {c.clip_id}: narration: \"{c.narration}\" | math: {json.dumps(c.on_screen_math)}" for c in clips))
    report = P.claude(run, "math_verify", user, MATH_VERIFIER_SYSTEM, schema=MathReport)
    P.write_json(run / "math.json", report.model_dump())


def print_plan(run: Path) -> None:
    math = P.read_json(run / "math.json")["findings"] if (run / "math.json").exists() else []
    print("| clip | sec | objective | narration |\n|---|---|---|---|")
    for s in scene_plans(run):
        for c in s.clips:
            print(f"| {c.clip_id} | {c.est_seconds:.0f} | {c.objective} | {c.narration[:90]}… |")
    print(f"\nMath findings ({sum(f['severity'] == 'ERROR' for f in math)} ERROR):" if math else "\nMath: no findings.")
    for f in math:
        print(f"- {f['severity']} {f['kind']} {f['clip_id']}: \"{f['quote']}\" — {f['why']} → {f['fix']}")


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


def cmd_build(a) -> None:
    run = Path(a.run)
    st = load_state(run)
    if "plan" not in st["approved"] and not a.force:
        sys.exit("The clip plan (CP2) is not approved yet: `approve <run> plan` (or --force).")
    if a.feedback and a.clips:
        for cid in a.clips.split(","):
            add_feedback(run, cid, "visual", a.feedback)
    ensure_api_index()
    plans = [p for p in scene_plans(run) if not a.scenes or int(p.scene_id[1:]) in {int(x) for x in a.scenes.split(",")}]
    redo = set(a.clips.split(",")) if a.clips else set()
    rows = P.parallel(lambda p: build_scene(run, p, redo), plans)  # scenes in parallel, clips in order
    print("| clip | status | attempts | notes |\n|---|---|---|---|")
    print("\n".join(r for scene_rows in rows for r in scene_rows))


def build_scene(run: Path, plan: ScenePlan, redo: set[str]) -> list[str]:
    sd = run / "scenes" / plan.scene_id
    (sd / "clips").mkdir(exist_ok=True)
    audio = P.read_json(sd / "audio" / "index.json")
    brief = P.read_json(run / "brief.json")
    math = [f for f in (P.read_json(run / "math.json")["findings"] if (run / "math.json").exists() else [])]
    rows, prev = [], ""
    for c in plan.clips:
        mm = f"clip_{c.index:02d}"
        fb = feedback_for(run, plan.scene_id, c.clip_id)
        key = sha(c.model_dump(), audio[c.clip_id], plan.color_roles, fb, prev, brief.get("font"), CLIP_BUILDER_SYSTEM)
        done = load_state(run)["clips"].get(c.clip_id, {})
        final = sd / "clips" / f"{mm}.py"
        if done.get("status") == "READY" and done.get("key") == key and final.exists() and c.clip_id not in redo:
            rows.append(f"| {c.clip_id} | READY (unchanged) | 0 | |")
        else:
            notes_math = [f"{f['kind']}: \"{f['quote']}\" → {f['fix']}" for f in math if f["clip_id"] == c.clip_id]
            result = build_clip(run, plan, c, mm, audio[c.clip_id], fb, notes_math, brief.get("font"))
            update_state(run, lambda s: s["clips"].__setitem__(c.clip_id, {
                "status": result.status, "key": key if result.status == "READY" else None,
                "notes": result.notes[:500], "open_findings": result.open_findings, "at": datetime.now().isoformat()}))
            rows.append(f"| {c.clip_id} | {result.status} | {result.gate_runs} | {result.notes[:160]} |")
            if result.status != "READY":
                rows += [f"| {x.clip_id} | SKIPPED (needs {c.clip_id}) | 0 | |" for x in plan.clips[c.index:]]
                break  # later clips start from this clip's exit state
        prev = sha(final.read_text())
    return rows


def build_clip(run, plan, c, mm, audio: dict, fb, math_notes, font) -> ClipResult:
    sd = run / "scenes" / plan.scene_id
    w = sd / "work" / mm
    w.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(w / "scene", ignore_errors=True)
    shutil.rmtree(w / "checks", ignore_errors=True)
    (w / "scene" / "clips").mkdir(parents=True)
    for earlier in plan.clips[: c.index - 1]:  # read-only snapshot of the approved clips before this one
        shutil.copy(sd / "clips" / f"clip_{earlier.index:02d}.py", w / "scene" / "clips")
    if (sd / "clips" / f"{mm}.py").exists() and not (w / f"{mm}.py").exists():
        shutil.copy(sd / "clips" / f"{mm}.py", w)  # rebuild starts from the approved version
    task = {"clip": mm, "clip_id": c.clip_id, "scene_id": plan.scene_id, "class": "Scene" + plan.scene_id[1:],
            "seconds": round(LEAD_IN + audio["seconds"] + HOLD, 2), "entry": c.entry.persistent_objects, "exit": c.exit.persistent_objects,
            "api_index": str(API_INDEX), "background": STYLE["background"]}
    P.write_json(w / "TASK.json", task)
    times = audio.get("beat_times") or [None] * len(c.beats)  # Polly word marks → when the voice says each phrase
    beats = "\n".join(f"  {i}. {'' if at is None else f'@ {LEAD_IN + at:.1f}s  '}{b}"
                      for i, (b, at) in enumerate(zip(c.beats, times), 1))
    md = (f"CLIP {c.clip_id}  (scene {plan.scene_id}, clip {c.index} of {len(plan.clips)})   "
          f"FILE: {mm}.py   NARRATION_SECONDS: {audio['seconds']}   CLIP_SECONDS: {task['seconds']} "
          f"(voice from {LEAD_IN}s, hold {HOLD}s)\nOBJECTIVE: {c.objective}\n"
          f"NARRATION (exact):\n  {c.narration}\nVISUAL INTENT: {c.visual_intent}\nBEATS:\n{beats}\n"
          f"ON-SCREEN MATH (exact LaTeX): {json.dumps(c.on_screen_math)}\n"
          f"ENTRY (already on screen, in self.reg): {json.dumps(c.entry.model_dump())}\n"
          f"EXIT (must be in self.reg and on screen at the end): {json.dumps(c.exit.model_dump())}\n"
          f"SYMBOL COLORS: {json.dumps(plan.color_roles)}   FONT: {font or 'Manim default'}\n"
          f"MATH NOTES (verified): {'; '.join(math_notes) or 'none'}\nHUMAN_FEEDBACK:\n{feedback_text(fb)}\n"
          f"PREVIOUS ATTEMPT: {mm + '.py exists — start from it' if (w / f'{mm}.py').exists() else 'none'}\n")
    (w / "TASK.md").write_text(md)
    topics = [x for x in dict.fromkeys(c.manim_topics) if x not in ALWAYS_TOPICS]  # always-on cards are in the system prompt
    cards = subprocess.run([P.PYTHON, str(TOOLS / "doc_cards.py"), "--index", str(API_INDEX), "--topics",
                            ",".join(topics), "--topics-dir", str(TOPICS_DIR)], capture_output=True, text=True)
    (w / "API_CARDS.md").write_text(cards.stdout if topics else "No extra topic cards for this clip — the always-on "
                                    "cards are in your instructions. Check any other name with ./check doc Name.\n")
    (w / "check").write_text(f'#!/bin/sh\nexec "{P.PYTHON}" "{P.ROOT / "app" / "check.py"}" "$@"\n')
    (w / "check").chmod(0o755)

    result = ClipResult(status="FAILED", notes="not run")
    for stage in ("clip_build", "clip_build_retry"):
        try:
            result = P.claude(run, stage, md + "\nRead TASK.md and API_CARDS.md, then follow the LOOP.",
                              CLIP_BUILDER_SYSTEM, schema=ClipResult, scene=c.clip_id, cwd=w, agent=True)
        except RuntimeError as exc:
            result = ClipResult(status="FAILED", notes=str(exc))
        # never trust the agent's READY: re-run every gate ourselves, jailed (the clip is LLM-written code)
        ok = (w / f"{mm}.py").exists() and subprocess.run(
            P.BWRAP + ["--bind", str(w), str(w), P.PYTHON, str(P.ROOT / "app" / "check.py"), "all"],
            cwd=w, capture_output=True).returncode == 0
        if result.status == "READY" and ok:
            shutil.copy(w / f"{mm}.py", sd / "clips" / f"{mm}.py")
            return result
        if result.status == "READY":
            result = result.model_copy(update={"status": "FAILED", "notes": "agent said READY but ./check all fails. "
                                                                             + result.notes})
    return result


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
    print(f"{run / 'final.mp4'}\nduration: {report['final_s']}s · clips: {len(report['clips'])} · "
          f"Claude cost: ${P.run_cost(run):.2f}")
    for f in report["checks"]:
        print(f"{f['severity']} {f['code']}: {f['message']}")
    subprocess.run([P.PYTHON, str(TOOLS / "cost_report.py"), str(run / "log.jsonl")])


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
    print(f"spend so far: ${P.run_cost(run):.2f}")


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

    add("clips", cmd_clips, scenes=True, feedback=True)
    add("voice", cmd_voice)
    add("build", cmd_build, scenes=True, clips=True, feedback=True, force=True)
    add("final", cmd_final, force=True)
    add("status", cmd_status)
    p = add("approve", cmd_approve, force=True)
    p.add_argument("target", help="outline | plan | sNN | final")
    p = add("feedback", cmd_feedback)
    p.add_argument("target", help="outline | sNN | sNNcMM")
    p.add_argument("--scope", default="visual", choices=["narration", "math", "visual", "plan"])
    p.add_argument("--text", required=True)


def _abs(a):
    a.run = str(Path(a.run).resolve())
    return a
