# Console implementation plan

Branch CCW-V02. Each phase: build → three independent reviews (visual/UX, functional/interaction,
architecture/quality, on Sonnet) → classify → fix → regression tests → re-review of the fixes, until no Critical or High
finding is open. Results go in CONSOLE_CRITIC_REPORT.md and CONSOLE_TESTING_REPORT.md; changes in CONSOLE_CHANGELOG.md.

## Architecture

**Backend (`backend/app/web/console.py`, `schemas/api.py`, `app/sandbox.py`, `app/web/app.py`)**
- `ConsoleEntry` gains optional fields: `id` (tool_use_id or permission id), `tool`, `input`, `is_error`, `stats`.
  New roles: `result` (a tool's output, matched by `id`), `permission` and `answer` (a prompt and its decision),
  `partial` (streamed text, never stored), `thinking`. Append-only: the page folds results into their tool calls.
- Per-run console settings in `state.json` (`console`): model, permission mode, session allowances.
- Each turn: `--model`, `--permission-mode`, `--include-partial-messages`, an HTTP MCP server pointing at
  `/api/console-permission/{run}` with a random per-turn token header, and `--permission-prompt-tool`.
- The permission endpoint (MCP JSON-RPC: initialize, tools/list, tools/call) checks the token, applies session
  allowances, otherwise records a `permission` entry in the running turn and waits (10 minutes, then deny) for the
  signed-in page's answer (`POST …/console/permissions/{id}`). It never trusts anything from inside the jail beyond
  the request itself; answers only come from the signed-in browser.
- `POST …/console/stop` sends SIGINT to the turn's Claude Code process (found under its bwrap parent), then SIGTERM
  after 5 s. `POST …/console/clear` drops `console_session`. `PUT …/console/settings`. `GET …/console/files`.
- `ConsoleView` adds the settings, the last `system/init` summary (model, cwd, slash commands, skills, agents) and
  the last turn's stats.

**Frontend (`frontend/src/pages/run/console/`)**
- `Console.tsx`: state and backend calls (the only component that talks to the server).
- `Transcript.tsx`: renders folded blocks (prompt, text, tool + result, permission, error, turn summary, divider).
- `Composer.tsx`: the prompt, keyboard map, history, slash and `@` menus.
- `StatusLine.tsx`, `PermissionPrompt.tsx`, `ShortcutHelp.tsx`.
- Pure, unit-tested logic (no React): `fold.ts` (entries → blocks), `diff.ts` (line diff), `history.ts`,
  `commands.ts` (parse and list slash commands), `keys.ts` (key → action).
- Tests: `*.test.ts` with `node --test` (type stripping, no dependency). End-to-end: Playwright from the local npx
  cache + installed Chrome, against a demo server whose `claude` is a fake that replays real event shapes and calls
  the real permission endpoint.

## Phases

| Phase | Scope | Exit |
|---|---|---|
| 0 | Reference, gap analysis, parity matrix, probes, plan | these documents |
| 1+2 | Monochrome terminal layout, transcript with folded blocks, prompt (Enter/newline/history), token streaming, stop | unit + pytest + e2e green, review clean |
| 3 | Tool blocks with output, status, duration, expand/collapse, Ctrl+O, diffs, errors, turn summary | same |
| 4 | Permission prompts (real bridge), modes + Shift+Tab, model, slash menu, `@` files, shortcuts help, queue, Ctrl+R | same |
| 5 | Status line (context, cost, cwd), `/context` `/cost` `/status` `/diff` `/permissions`, session restoration (reconnect to a running turn, pending prompt survives reload) | same |
| 6 | Long transcripts (windowed rendering past 400 blocks), stream back-pressure, accessibility pass, small screens, failure recovery | same + final review |

Phases 1 and 2 are merged: the design foundation is a stylesheet section and has no behaviour to review on its own.

## As built (deviations)

- Phases 1–5 were built in one pass (their pieces share one data model: entries → blocks), then reviewed together by the
  three critics; Phase 6 items (long transcripts: the last 300 blocks render; batching; async follow; small screens;
  failure recovery) were folded into the fixes. Recorded in CONSOLE_CRITIC_REPORT.md.
- Console settings are not in `state.json` (the jail can write the run folder): `artifacts/console/<run>.json`;
  session allowances are in server memory only.
- The MCP config with the turn token is an owner-only file in `artifacts/console/`, not a command-line argument.
