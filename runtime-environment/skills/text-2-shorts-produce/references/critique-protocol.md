# Critique protocol — how critics judge and how refactorers act on it

Shared by the critics (**script-critic**, **plan-critic**, **video-critic**) and everyone who refactors after them:
the session for the script, the **scene-planner** for plans, and, for a video, a clip rebuild through
`text-2-shorts feedback` plus the **audio-refactorer** for sync. Each critic's own agent file holds its rubric
(criteria S-…, P-…, V-…); this file holds what they share. The schema is `CritiqueRound` / `CritiqueIssue`
(`backend/schemas/reviews.py`); `text-2-shorts validate` rejects a round that breaks any rule below.

## 1. Tiers

| Tier | Id letter | Meaning | Penalty | Effect |
|---|---|---|---|---|
| **basic** need | B | Must always hold. Broken = the video is wrong, unclear, unbuildable, out of sync, or ignores the brief or the user. | −25 | Any open basic issue makes the verdict `revise`, whatever the score. |
| **good** to have | G | Expected professional quality. Broken = a viewer notices something off. | −10 | Counts against the threshold. |
| **great** if followed | X | Polish that lifts a good video. Missing = a missed opportunity, not a defect. | −3 | Counts lightly; a refactorer applies it only when it is cheap and safe. |

A criterion id is `<critic>-<tier letter><number>`: `S-B2` (script, basic, 2), `P-G4`, `V-X1`. Cite only ids from
your own rubric; the letter must match the issue's `tier`.

## 2. Score and verdict

- `score = max(0, 100 − 25 × basic − 10 × good − 3 × great)`, counted over this round's issues. Compute it; never
  estimate it. The validator recomputes it.
- `verdict = "pass"` when **no basic issue is open**, and, only if the user set `quality_threshold` in
  `preferences.json`, `score ≥ quality_threshold`. Otherwise `"revise"`.
- Good and great issues are suggestions: recorded in the round, never a reason for a refactor on their own.
- Rounds: plans and videos have at most 3 rounds per scene. After round 3 below the threshold, the scene
  **REQUIRES ATTENTION** and its open issues go to the user. The script gets exactly one round per change request
  the user raised at CP1.

## 3. Writing an issue (what a refactorer needs, nothing more)

| Field | Write | Example |
|---|---|---|
| `target` | the narrowest scope: a clip (`s03c02`) before a scene (`s03`) before `script` | `s03c02` |
| `criterion` | the one rubric line it breaks | `P-B3` |
| `tier` | the tier of that line | `basic` |
| `aspect` | the rubric column it falls under | `sync` |
| `evidence` | what you saw and exactly where: a quote in quotation marks, a beat number, a frame time from the sheet, a sync offset | `beat 2 "notice this angle" — the highlight comes at beat 3, 1.4 s later` |
| `problem` | what is wrong, in one or two plain sentences | `The voice points at the angle before anything is highlighted.` |
| `impact` | what it does to the viewer, the build or the sync | `The viewer looks for "this angle" on a static frame and loses the thread.` |
| `fix` | the smallest concrete change that solves it: what to change, where, to what | `Move the YELLOW Indicate of angle_a to beat 2; beat 3 keeps only the label.` |

Rules for issues
- **Evidence or nothing.** No quote, beat, frame or offset, no issue. "Feels slow" is not evidence; "5.8 s of
  static frame after beat 4 (sheet 1, frames 3–5)" is.
- **One root cause, one issue.** Merge symptoms of the same cause; list the cause, not each symptom.
- **Most important first**: basic before good before great, and within a tier the one that hurts the viewer most.
  The user's own change request, when there is one, comes first among the issues it touches.
- **Actionable fixes.** Name objects, beats, words, colours and seconds. Never "improve", "consider" or "make
  clearer" on its own.
- **Your lane only.** Each critic checks its own rubric. Facts belong to the accuracy-reviewer, the structure the
  validators already enforce (ids, schema, word-for-word narration) to the validators, and taste to no one.
- **Do not re-raise what was fixed.** Read `changes.json` (video) or the earlier rounds first. Raise an issue again
  only when it is still visible now, and say so in `evidence` ("still: …").

## 4. Writing the round

- **Append, never rewrite.** The first round writes the file. A later round is added at the end of `rounds` with
  `Edit`; the earlier rounds stay exactly as they are.
- **Rounds 2 and 3 check the change, not everything again.** Start from the previous round: for each of its issues,
  check whether it is fixed (raise it again as "still: …" only if it is still there). Then review what the refactor
  changed (the refactorer's reply; `changes.json` for a video) and what that change can break: the entries and exits
  it touches, its beats' sync. Leave untouched clips alone; the earlier round's view of them stands.

```json
{
  "reviewed": "<text-2-shorts hash output for this version>",
  "verdict": "revise",
  "score": 65,
  "summary": "Revise: beat 2 of s03c02 points at an angle nobody has highlighted yet (basic sync). The composition and the colour roles are clean and should stay. One label sits at caption size where the template asks for label size.",
  "strengths": [
    "s03c01 builds the triangle in narration order, one side per phrase",
    "colour roles match SYMBOL COLORS SO FAR exactly"
  ],
  "issues": [
    {"target": "s03c02", "criterion": "P-B3", "tier": "basic", "aspect": "sync",
     "evidence": "beat 2 \"notice this angle\": the highlight is in beat 3",
     "problem": "The voice points at the angle before it is highlighted.",
     "impact": "The viewer searches a static frame and loses the thread.",
     "fix": "Move the YELLOW Indicate of angle_a to beat 2; beat 3 keeps only the label."},
    {"target": "s03c02", "criterion": "P-G2", "tier": "good", "aspect": "design",
     "evidence": "beat 4: label_c at font_size 24",
     "problem": "A label uses the caption size.", "impact": "Hard to read at phone size.",
     "fix": "font_size 28 for label_c (template label size)."}
  ]
}
```
Here the score is 100 − 25 − 10 = 65, and the verdict is revise (a basic need is open).

- `summary` is 2–4 sentences: the verdict and the main reason, the biggest risk, and what already works. Someone who
  reads only the summary should know whether the work is close.
- `strengths` lists 0–5 concrete things that work and that a refactor must not break. Generic praise doesn't count.
- A pass with no issues is a valid, good result: `"score": 100, "issues": []`.

## 5. Refactoring from a round

1. Read the last round in full, including the summary and strengths.
2. Fix **every basic issue**, then **every good issue**. Fix a **great** issue only when it is a small change that
   cannot break anything that already passes.
3. Make the smallest change that satisfies each `fix`. You may solve the same `problem` in a better way than the
   proposed fix; say so in your reply.
4. Keep everything listed in `strengths`, and everything no issue names. Change something else only when an issue
   forces it, for example an entry/exit contract that must follow a changed object, and say so.
5. Never change narration words outside the script. A plan or a video speaks the approved script word for word;
   wording issues go back to the script and CP1.
6. You can decline an issue only when fixing it would break a basic need or contradict the user or the brief.
7. Patch, never rewrite: change the file with `Edit`, only where an issue points. A rewrite costs the whole file again
   and can silently change what already passed.
   Say which issue and why in your reply (and in `changes.json` for a video). Never decline silently.
7. Validate (`text-2-shorts validate …`), then hand back to the critic for the next round. For a video, the session
   appends a `ChangeRecord` to `scenes/sNN/changes.json`: `issue` = the criterion and problem, `findings` = one
   line per issue fixed (`"V-B2 s03c02: voice ran 0.9 s past beat 3"`), and the rest as the schema asks.

Who fixes what in a video round: `sync` issues go to the audio-refactorer (SSML timing only). `plan-match`,
`render` and `design` issues go through `text-2-shorts feedback . sNNcMM --text "<criterion>: <fix> (evidence:
<evidence>)"` and a rebuild of that clip. Issues that need a different plan go back to the scene-planner, which
means CP2 again for that scene.

## 6. Every critic: procedure, output and reply

1. Read the earlier rounds (and `changes.json` for a video). Then review against your rubric, basic needs first,
   then good, then great.
2. Write each issue as §3 describes, compute the score, set the verdict, and write the summary and strengths (§2, §4).
3. **Append one round** to your critique file and keep the earlier rounds. `reviewed` is the output of the hash
   command your agent file names. Run your validate command and fix the file until it passes. Write one round per
   call: never a 4th plan or video round, and never more script rounds than change requests.
4. **Reply**: `<target> round N — <verdict>, score S/100` (and `threshold T` if the user set one). Then the summary, the issues grouped
   by tier (B, G, X), each as `criterion target: problem → fix`, then the strengths to keep.
