# Faraday — remediation plan from the 2026-11-26 audits

*A plan only: nothing in the codebase has been changed for it. Finding ids (H1, M12, …) refer to
`docs/history/repo-audit-2026-11-26.txt` Part 3.*

## Decisions taken (2026-11-26)
- D1 bind approvals to upstream versions: **yes**.
- D2 sign-in token plus deny `approve` to subagents: **yes**.
- D3 pin the scene-builder prompt per run: **yes**.
- D4 a live 3-minute run in Phase 6: **yes, gated on a go-ahead right before it runs**.
- D5 delete the dead code: **yes**.
- D6 delete the duplicate `health-review-2026-11-26.txt`: **yes** (done in Phase 7, not now).
- D7 a local check script instead of CI: **yes**.
- D8 Sonnet instead of Opus for plan and scene *refactors* (Opus kept for the first plan and the first build):
  **pending**. Decide after the Phase 6 run measures cost and quality.

## Context
Three audits were written and committed today (`docs/history/flow-audit-2026-11-26.txt`, `repo-audit-2026-11-26.txt`
Parts 1–3, `health-review-2026-11-26.txt`). The workflow logic is sound: 17 mock runs pass, one of them through the
website API. But the review found 10 HIGH, 36 MEDIUM and 11 LOW issues, mostly at the edges:
- a run can show "done" with a video that no longer matches it;
- the run page never refreshes and its console is fragile;
- the local server trusts any process on the machine;
- errors in the media steps are swallowed;
- real agents and rendering have never been run end to end.

This plan orders all remaining work into phases, lists the decisions you need to make, and names the
structural changes. Finding ids (H1, M12, …) refer to repo-audit Part 3.

## Already carried out (committed on CCW-V02, not pushed)
- `5f45839`: the three audit docs.
- `18eff84`:
  - Loop limits: accuracy reviews, builds and sync previews stop after 3 failures in a row (`state.json` "attempts",
    `ledger.count_attempt`, `config.MAX_ATTEMPTS`), and the review loop respects a forced approval.
  - CP4 is blocked by media-check ERRORs.
  - A video critique runs only after the rebuild and new preview.
  - Declined and audio-timing requests no longer change the build key.
  - The mistake log (`workflow/mistakes.py`, `text-2-shorts mistakes`).
  - Website: older runs show their final video, the Start a Run sub-breadcrumb, and "Request a Change" hidden on
    Template, Requirements and Reshuffle.
  - Tests: `tests/test_flow.py`, `tests/test_mistakes.py`.
- `3731394`: the CI workflow removed.

## Decision details (the options weighed; the choices are above)
- **D1 Approval model (M1, M9).** Bind each approval to the upstream versions it was made against, so changed
  requirements re-ask CP0–CP2. The cost is more re-approvals after upstream edits. Alternative: keep the current
  model (accept the gap). *Rec: bind.*
- **D2 Sign-in (H6, M31).** A one-time token printed by `serve` (and put in the URL it opens), plus `approve` denied
  to subagents. Alternative: accept it as single-user and localhost only. *Rec: token + deny.*
- **D3 Agent prompt in the build key (M7).** Pin the scene-builder prompt's hash per run at creation. Alternative:
  drop the prompt from the key entirely. *Rec: pin per run.*
- **D4 Live verification run (M26, M27, the agent path).** It contradicts the "no live runs during build" memory
  note. *Rec: one 3-minute run in Phase 6, only with your go-ahead.*
- **D5 Over-engineering cuts (Part 2).** Delete the template_kit Python (keep `elements.json` and
  `templates/*.json`), `unused_contracts.py`, `cost_report.py`, `audit_prompt_catalog.py` and the ten small dead
  pieces. *Rec: yes.*
- **D6 Duplicate report.** Delete `health-review-2026-11-26.txt`, now that it is Part 3 of repo-audit.
  *Rec: yes.*
- **D7 CI.** It was removed on request. Plan: a local `make check`-style script instead (Phase 7). *Rec: one
  script, no CI.*

## Structural and architectural changes
- **A1 Upstream-bound approvals (D1).** `schemas/run_state.Approval` gains `upstream: dict[str, str]`;
  `approvals.approve_checkpoint` fills it from `fingerprints.STAGE_FINGERPRINTS`; `ledger.is_approval_current`
  checks it. The page sends the fingerprint it rendered (`ApproveInput.fingerprint`) and gets a 409 on mismatch.
- **A2 One source of truth for the scene set (H1).** A `current_plans(run)` helper in `workflow/artifacts.py` (the
  script's scene ids ∩ plans). The driver, `final`, fingerprints and `status` use it. The driver asks to delete
  orphaned `scenes/sNN`.
- **A3 Complete render fingerprint (H2, M2).** The scene fingerprint adds `templates.drawing(run)`. The final
  fingerprint adds the assembly settings (transition, seconds, music, volume) and the music and sound-effect file
  hashes. `final` fingerprints before rendering and compares after.
- **A4 Versioned accuracy reviews (H10).** `ReviewReport.reviewed`; a stale review counts as missing; the hash
  command and `accuracy-reviewer.md` are updated. The same pattern as `CritiqueRound.reviewed`.
- **A5 Atomic writes, tolerant reads (H3, M10, M12).**
  - `utilities.write_json`/`write_text` become temp file + `os.replace` (pattern: `ledger.update_state`).
  - `read_jsonl` skips and logs bad lines.
  - The fingerprint helpers return None on bad JSON.
  - `run_detail` shows the real error, not "older version".
  - `final.mp4` is written to a temp file and renamed.
- **A6 Build inputs pinned at `task` (M5, D3).** `work/TASK.json` records the clip key and request ids; `accept`
  uses those. The prompt hash is pinned per run.
- **A7 Console turn owned by the server (H7, M14, M25).** A background thread owns the lock, the `claude` process
  (terminated in `finally`) and the `console.jsonl` writes. The HTTP stream only tails. The prompt is passed on
  stdin or after `--` (H8). Stderr is merged.
- **A8 Narrower jail (M15).** Bind `~/.claude` subpaths (projects, sessions, credentials) read-write, the rest
  read-only, and add `--new-session`.
- **A9 Execution plan as its own file (O2).** Move the Visual Director execution plan from the `execution_plan`
  string inside `scenes/sNN/plan.json` (`schemas/plans.py`) into `scenes/sNN/execution_plan.md`. Today every line
  break and quote in it is escaped, so agents can't patch it with `Edit` and rewrite the whole file instead.
  Touches the plan schema, `validation.validate_plan`, `visual_director.py`, `fingerprints` (both files in the plan
  and build keys), `scene_code.prepare_scene`, the hook (validate on writes to either file) and the test fixtures
  (`tests/conftest.make_plan`).
- **A10 Fixed, cacheable opening for the scene-planner (O1).** Today every planner call reads ~8,000 words of the
  same references (`visual-director-system.md`, `visual-director-output-spec.md`, `scene-visual-planning.md`,
  `audio-ssml.md`, `transitions.md`) *after* a task text that differs per scene. So nothing after the task can be
  served from cache: in V01 the plan refactors had 0 cache reads. Generate the agent file's body with those
  references inlined (a build step beside `runtime-environment/prompts/export_references.py`), so they sit in the
  fixed system prompt before anything scene-specific. The scene-specific task stays last. The same check applies
  to the scene-builder's task (`ALWAYS_LOADED_TOPICS`, `config.py`), whose fixed block must stay first and
  unchanged.

## Execution order

### Phase 0 — Quick, independent fixes (low risk)
- The test-hygiene bug: exclude `runtime-environment/template/` in `test_run_environment_is_not_gitignored`.
- M11: `runs_directory.mkdir(parents=True, exist_ok=True)` in `web/app.create_app`.
- M8: narration ranges ("10-20" → "10 to 20") in `narration.py`.
- M17: "scenes" maps to an "All Scenes" target in `ChangeModal.tsx`; M18: `waitingTab` handles "scenes" in
  `RunPage.tsx`.
- M32: `task` without audio exits with "run voice first" (reuse `production.stale_audio`).
- H8: "--" before the console message (`sandbox.console_claude_arguments`).
- M6: exclude SSML from `critiques.critique_subject_hash("plan")` (like `fingerprints.plans_fingerprint`).
- M24: reset the "Approve with Open Problems" tick when the problems change (`CheckpointPanel.tsx`).

### Phase 1 — Wrong-video risks (A2, A3, A4, A1)
- H1 (A2), H2 + M2 (A3), H10 (A4).
- H9: `final` reuses preview's build-key check, `is_approval_current` and `require_approval("plan")`.
- M3: refuse force when the video is missing or stale.
- M1 + M9 (A1, if D1 = bind).
- Files: `artifacts.py`, `fingerprints.py`, `driver.py`, `approvals.py`, `production_commands.py`,
  `schemas/reviews.py`, `schemas/run_state.py`, `schemas/api.py`, `agents/accuracy-reviewer.md`,
  `CheckpointPanel.tsx`.

### Phase 2 — State and file robustness (A5)
- H3, M12, M10 (per-run try/except in `run_views.runs`, `os.scandir` in `updated_text`).
- M4: request id from max+1 inside `run_lock`.
- L4: approve takes its fingerprint once, under the lock.
- M13: clean up a half-made run on start or duplicate failure.
- M5 + M7 (A6, D3): `scene_code.prepare_scene` writes the clip key and request ids into `work/TASK.json`;
  `accept_scene` uses them and resolves only those requests. The scene-builder prompt hash is pinned in `state.json`
  at run creation (`run_workspace`), and `fingerprints.clip_key` reads the pinned hash instead of the live file.

### Phase 3 — Run page and console (A7)
- H4: `usePolling` on `RunPage`, `ClaudePanel` and `Console` while busy or in progress (`hooks/usePolling.ts`
  exists).
- H5: restore input and live state on failure.
- H7, M14, M25: A7, plus an AbortController in `services/http.streamTurn`.
- M19: modal reset keyed on `ask` only.
- M20: after a change request, offer or send a console message.
- M21–M23: Start a Run restore, expiry and limits.
- L8: deep links, bad id, double approve, unsaved Template edits, draft errors.

### Phase 4 — Security (A8, D2)
- H6 token sign-in; M31 deny `Bash(text-2-shorts approve:*)` to subagents (`runtime-environment/settings.json` or
  agent tools); M15 (A8).
- L5: cap and strip `/api/logs`, cache `claude auth status`, sweep expired sessions.
- L2: test compound commands against `excludedCommands`.
- L6: unique usage temp file; L7: lock and suffix on trash moves.

### Phase 5 — Silent failures and logging
- M28: log missing beat marks; sync reports "no beat timings".
- M29: keep the subprocess stderr tail in `open_findings` and the logs (accept, compose, index build).
- M30: save the audio index per clip, with a friendly TTS error.
- M16: `exc_info` logging plus a catch-all 500 handler.
- L1: the hook logs crashes and treats them as exit 2.
- L3: catch the render timeout and name the scene.
- M33: reshuffle also rewrites `work/scene_code.py` and marks the clips for the gates.
- C2: no re-dispatch when the refactorer changed nothing.
- C3: `status.next_steps` reuses `driver.next_actions`.

### Phase 5b — Runtime cost optimisation (before the live run, so it measures the optimised workflow)
Ranked by expected saving per video of the Kepler size (11 scenes, ~8 minutes). The figures are estimates from
V01's real per-call costs (see "Runtime cost: V01 vs V02" below).
- **O1 Cache the planner's fixed references (A10):** about −$8–12. This is the biggest lever.
- **O2 Patch, don't rewrite:**
  - the scene-planner and script-writer get the rule "in refactor mode, `Edit` only the sections the critique
    names; never rewrite the whole file" (the scene-builder already has "smallest change… never rewrite working
    clips");
  - the execution plan moves to its own Markdown file (A9);
  - critics append a round with `Edit` instead of rewriting their file.
  Direct saving about −$1–3: a 5–8k-token plan rewrite is ~$0.10–0.16 of Opus output, ×11–22 refactors. The larger
  value is that O3 depends on it, fixes after a rejected write get cheaper, and untouched parts can't be silently
  broken.
- **O3 Critic rounds 2–3 check only the change:** a later round checks whether the previous issues are fixed,
  plus the sections that changed (from the patch), instead of re-reviewing the whole plan or scene. About −$2–4.
  Files: `agents/plan-critic.md`, `agents/video-critic.md`, `references/critique-protocol.md`; the driver passes the
  previous round and the changed sections in the critic's `read`.
- **O4 Only basic issues trigger a refactor:** "good" and "great" issues become suggestions in the round, not
  refactors. About −$3–6. Files: `critiques.validate_critique` / `critique_state` (verdict rule), the critic
  agents, `critique-protocol.md`. The per-run `quality_threshold` preference stays.
- **O5 State the validator's rules up front:** put the rules the plan and script validators enforce (required
  fields, clip and beat constraints) at the top of the scene-planner and script-writer tasks, so fewer writes are
  rejected by the hook and regenerated. V01 had 16 planning and 14 scene retries. About −$2–5. Use the mistake log
  (`text-2-shorts mistakes`) after Phase 6 to pick the rules that break most.
- **O6 Already in this plan, and it also saves tokens:**
  - M6 (Phase 0): SSML edits stop forcing extra plan-critic rounds.
  - M7 (Phase 2): editing the scene-builder prompt no longer re-keys every scene of every run at Opus cost.
- **O7 Bound critic images:** cap the preview contact sheets the video critic receives per scene
  (`production_commands` preview: `tile=4x3` at 480 px). A guard for long scenes, not a big saving.
- **O8 (D8, after Phase 6) Sonnet for refactors:** Opus only for the first plan and first build, Sonnet for
  refactors (`driver.py` picks the agent; a Sonnet variant of the scene-planner and scene-builder). About −$5–10.
  Decide only after the Phase 6 run shows refactor quality.
- **O9 Long console sessions:** each console turn resumes one growing session (`console.run_turn`, `--resume`).
  Start a fresh session, or compact, between major stages if Phase 6 shows the Haiku session's cost rising per
  turn.

### Phase 6 — Live verification (gated by D4)
- One 3-minute run (Sonnet/Haiku). It settles M26 (`preview` in `excludedCommands`?) and M27 (build the API index
  in `new`, or allowWrite it), and checks the real agents, TTS, preview and final.
- Inspect `mistakes.jsonl` and `text-2-shorts mistakes`.
- Cost check:
  - `text-2-shorts report <run>` per agent;
  - confirm the scene-planner calls now show cache reads (O1);
  - compare per-minute cost with V01's Kepler run ($82.24 for 8.3 minutes, ≈ $9.9 per minute);
  - then decide D8.

### Phase 7 — Clean-up
- The Part 2 cuts (D5), net ≈ −1,900 lines.
- D6.
- M34: a schema-drift test.
- M35: stale docs (naming-conventions, PROJECT_STRUCTURE, the check_diagrams line).
- M36: hook, run and serve command tests.
- L9: declare numpy, pillow and starlette.
- L10: state "Linux/macOS only".
- D7: a local check script (ruff, format, npm build, pytest).

## Runtime cost: V01 (pipeline) vs V02 (Claude workflow), same Kepler video
**V01, actual:** CCW-V01 `app/pipeline.py`, one `claude -p` per stage, mostly Sonnet. The run's log:
`artifacts/runs/20261119-110104-kepler-s-laws-of-planetary-motion-why-or/log.jsonl`. It recorded cost and cache
reads and writes, but not input and output token counts, so the comparison is in dollars.

**V02, estimate:** no V02 run of this video exists. Per-call costs come from V01's log; call counts come from the
driver's flow and loop limits. Prices from the `claude-api` reference: Opus 5.5 $4 / $20 per million tokens in /
out, Sonnet 5.5 $2 / $10, Haiku 5.5 $0.10 / $0.50, cache reads ≈ 0.1× input.

| Stage | V01 actual | V02 now (estimate) | Why |
|---|---|---|---|
| Orchestration | ~$0 (Python) | $1–3 | Haiku session turns |
| Outline + script | $3.70 | $3–4 | Opus script-writer |
| Accuracy reviews | — | ~$1 | New in V02 |
| Scene planning | $44.82 (98 calls) | $20–30 | Opus at 2× the price, but ~22 calls instead of 98 |
| Plan critic | $10.50 (56 calls) | $5–7 | ~25–33 rounds |
| Scene code | $23.42 | $22–30 | Opus at 2× the price, ~15 builds |
| Video critic + rebuilds | — | $8–15 | New in V02 |
| Audio re-timing | — | $1–2 | New in V02 |
| **Total** | **$82.24** | **≈ $60–90 (likely ~$75)** | |

**What it means:**
- **V02 as it is now is roughly break-even with V01 (−25% to +10%).** Its savings come from structure: no
  re-planning after outline changes (V01 re-planned through outline v2–v4), only changed scenes rebuilt, and every
  loop capped at 3.
- **Those savings are eaten by the new costs:** the planner and builder moved to Opus at twice the price, and the
  new quality steps (video critic, accuracy reviews, audio re-timing) add calls.
- **With Phase 5b (O1–O5, plus O8 if approved), the same video is estimated at $40–50, about 40–50% below V01.**
- **Caveats:** the Kepler run includes your own revision rounds. The only real proof is the Phase 6 run plus
  `text-2-shorts report`.

## Verification (when the phases are executed)
- After each phase: `uv run ruff check && uv run ruff format --check`, `cd frontend && npm run build`,
  `uv run pytest -q`.
- Each fix gets one regression test that fails without it (the same pattern as today's three tests).
- Extend `tests/test_flow.py` with scenarios for:
  - H1: a scene dropped after CP2 is not in the final;
  - H2: a template transition change → re-render;
  - H3: a malformed script.json keeps the run page readable;
  - M1: changed requirements → CP0 again.
- Website changes: check them in Chrome on the running server (`text-2-shorts serve`): the run page updates
  without a reload, the Scenes request target, and the Approve All bar.
- Phase 5b, without spending money:
  - a test that the generated scene-planner agent file starts with the fixed references and contains no
    run-specific text (O1);
  - a `test_flow.py` scenario where a refactor patches `execution_plan.md` and the plan and build keys change only
    for that scene (O2, A9);
  - a test that "good"-only issues give verdict "pass" (O4).
- Phase 6 is the only end-to-end proof for the agents and media.
- Commit per phase on CCW-V02; push only when asked.
