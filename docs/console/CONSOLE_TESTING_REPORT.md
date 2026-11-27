# Console testing report

## How to run

| Suite | Command | What it covers |
|---|---|---|
| Backend | `uv run pytest -q tests/test_console.py` | events → entries (a real Claude Code turn as fixture), permission bridge (allow once, session, deny with note, timeouts, caps, ended turns, tokens), narrow allowances (wrappers, flags, paths, domains), stop (before and after the process starts), new session, @ files, settings outside the run folder, subagent events, batching, and the whole path over real HTTP with a fake Claude Code. |
| Frontend unit | `cd frontend && npm test` | `node --test` with TypeScript type stripping, no dependency: fold, diff, history, slash commands, keyboard map. |
| End to end | demo server + `RUN=<run> PLAYWRIGHT=<path> node frontend/e2e/console.e2e.mjs <out>` | Chrome against a demo server whose `claude` is `tests/fixtures/console/fake_claude.py` (real event shapes, real permission endpoint, no live turn): 18 states, each asserted and screenshotted. |
| Everything | `uv run ruff check && uv run ruff format --check && uv run pytest -q && (cd frontend && npx tsc --noEmit && npm test && npm run build)` | |

The e2e needs the Playwright package (any copy; this machine's npx cache has 1.63) and Chrome at `/usr/bin/google-chrome`
(`CHROME` to change it). No new dependency was added to the project.

## Results

| When | Backend | Frontend unit | E2E |
|---|---|---|---|
| Baseline (Phase 0) | 216 passed | none existed | none existed |
| Phases 1–5 built | 235 passed | 9 passed | 16 steps, 17 screenshots, passed |
| After round 1 fixes | 255 passed | 9 passed | 18 steps (+ Ctrl+R, prompt key guard), passed |
| After round 2 fixes (final) | **257 passed** | **9 passed** | **18 screenshots, passed**; ruff, format, tsc, build clean |

Tests were written before their code for the backend features and every security fix (each watched failing first:
the A1–A6 tests went red with 18 failures, R1/R2 with 4). Some frontend unit tests were written together with their
module; the e2e covers their behaviour in the browser.

## Regressions found and fixed during testing

- Enter on an unavailable command did nothing (e2e).
- A stop pressed before Claude Code had started was lost (pytest found it: `stop_turn` returned False).
- A test that rewrote `state.json` raced with the running turn (test bug, removed).
- After the field moved, demo runs written by the intermediate build kept a `console` key that the strict `RunState`
  rejected; only this session's demo runs had it (real runs checked: none).

## Not covered

- A live Claude Code turn: deliberately not run (no live runs during the build). The contract was probed once on
  Claude Code 2.1.332 (`CONSOLE_REFERENCE_AND_GAP_ANALYSIS.md` §2) and is replayed by the fixture and the fake.
- The bubblewrap jail itself with the permission endpoint (the probe used Claude Code outside the jail; the jail keeps
  the host network, so the endpoint is reachable). Verify on the first real turn (Phase 6 of the remediation plan).
- Visual comparison with Claude Code screenshots: it is a terminal program; compared with its documented behaviour.
