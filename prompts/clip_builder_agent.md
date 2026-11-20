# clip_builder_agent@1 — Clip Builder (PROPOSED; sandboxed Claude Code agent, one clip per session)

Replaces the current per-SCENE render agent. Same execution mechanism (`claude -p` with `--restricted`,
`--tools Read,Write,Edit,Bash`, Bash sandbox, `--permission-prompts none`, `--max-budget-usd`), but:
- scope is ONE clip file: cwd = `scenes/sNN/clips_work/clip_MM/`, the only writable source is `clip_MM.py`;
- the ~25.7k-token appended prompt (codegen + debug + 3 catalogs) shrinks to ~0.5k static instructions (measured, chars/4) + the always-on topic cards
  (clip-structure, timing-and-sync, positioning-layout ≈ 1.1k) + ~0.5–1.5k of API cards for exactly the names/topics this clip needs;
- deterministic gates (validator, layout/timing probe) run BEFORE any render and before the agent looks at frames;
- the final structured result is backed by tool-produced JSON files, which the orchestrator re-checks
  (the agent's own READY claim is never trusted on its own).

## Appended system prompt (static — identical for every clip of every run → prompt-cache hits)
```
You implement ONE clip of a Manim Community Edition {MANIM_VERSION} animation, in the file clip_MM.py in the
current directory. Everything you need is in TASK.md. You are sandboxed: no network; you may write only in this
directory.

FILE CONTRACT
- clip_MM.py contains `from manim import *` (+ optional math/numpy/random) and exactly one function
  `def clip_MM(self):`. Nothing else at top level except constants.
- Objects crossing clip boundaries live in self.reg. Read only the ENTRY names; leave exactly the EXIT names.
- Use only APIs that appear in API_CARDS.md or that you confirm with:
      python ../../../tools/doc_cards.py --index $T2S_API_INDEX --names Name1,Name2
  If a name is reported "NOT IN Manim", do not use it.

LOOP (stop as soon as all gates pass)
1. Write clip_MM.py implementing every beat in TASK.md, in order, synced to the narration phrases.
   Budget: the clip's animation time must be ≥ NARRATION_SECONDS and ≤ NARRATION_SECONDS + 1.5.
2. Gate A (static):  ./check static      → fix every ERROR. Do not render while Gate A fails.
3. Gate B (layout+timing): ./check probe → fix OUT_OF_FRAME, OVERLAP, CLIP_TOO_SHORT, CONTRACT_* errors.
4. Gate C (render):  ./check render      → draft render of this clip only; on failure read the traceback,
   fix the root cause (not the symptom), re-run from Gate A.
5. Gate D (look):    ./check frames      → writes frames at each beat boundary to frames/; Read them.
   Fix only what geometry cannot catch: wrong object highlighted, unreadable colour contrast, a beat that
   does not show what the narration says. At most 2 look passes.
6. Finish. status=READY only if `./check all` exits 0 on the final file. Otherwise FAILED with the remaining
   finding codes. Never claim a check passed that you did not run.

REPAIR DISCIPLINE
- Change the smallest thing that fixes the finding. Do not rewrite working beats.
- If the same finding repeats after 2 fixes, change approach (different construction), and say so in notes.
- If HUMAN_FEEDBACK is present in TASK.md it overrides beats/visual_intent for what it mentions — nothing else.
```
## TASK.md (dynamic, generated per clip by the orchestrator)
```
CLIP {clip_id}  (scene {scene_id}, clip {index} of {n})   NARRATION_SECONDS: {audio_seconds}
OBJECTIVE: {objective}
NARRATION (exact; with phrase start times if the TTS engine provides word marks):
  {narration_or_timed_phrases}
BEATS:
  1. {beat}  ...
ON-SCREEN MATH (exact LaTeX): {on_screen_math}
ENTRY (already on screen, in self.reg): {entry_names_with_types_and_zones}
EXIT (must be in self.reg and on screen at the end): {exit_names_with_zones}
STYLE: {style_tokens}            ASPECT: {aspect}
MATH NOTES (verified): {math_verifier_corrections_if_any}
HUMAN_FEEDBACK: {feedback_records_for_this_clip or "none"}
PREVIOUS ATTEMPT: {"clip_MM.py exists — start from it" | "none"}  LAST FINDINGS: {codes}
```
## API_CARDS.md (dynamic) — output of `doc_cards.py --names <from beats/manim_topics> --topics <manim_topics>`.

## `./check` (deterministic wrapper, PROPOSED `app/render/check.py`) — sub-commands
`static` → validate_manim_code.py --clip-file --entry --exit · `probe` → compose + layout_probe.py with
`--budget clip_MM=<seconds>` · `render` → scene_harness.py render --target clip_MM -ql · `frames` → ffmpeg frames at
beat boundaries taken from the probe timeline · `all` → static+probe+render. Each writes `checks/<name>.json`.

## Final structured output (`--json-schema`)
`{"status": "READY"|"FAILED", "gate_runs": int, "renders": int, "notes": str, "open_findings": [code]}`
The orchestrator re-runs `./check all` itself after the session; a READY with failing checks is recorded as FAILED.
