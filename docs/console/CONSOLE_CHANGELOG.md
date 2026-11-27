# Console changelog

## Phase 0 (2026-11-27)

- Reference and gap analysis, parity matrix, implementation plan.
- Probed Claude Code 2.1.332 headless: permission-prompt tool over stdio and HTTP MCP, partial messages, event fields.
- Fixture `tests/fixtures/console/turn-bash.jsonl`: one real turn (Bash call, result, text), scrubbed.

## Phases 1–5 (2026-11-27), built in one pass

- Backend: `EventReader` (tool calls with input, results with output and duration, streamed text, thinking, turn
  stats, session info, compaction, command output); per-turn model and permission mode; permission prompts through
  Claude Code's `--permission-prompt-tool` served by Faraday (`console_permissions.py`, MCP over HTTP, per-turn token);
  stop (SIGINT to Claude Code); `/clear`; @ files; follow a running turn; `ConsoleView` with settings, session, rules.
- Frontend: `pages/run/console/` (Console, Transcript, Composer, parts, and pure fold/diff/history/commands/keys);
  terminal drawer; monochrome `.con` styles; ClaudePanel shows open prompts.
- Tests: `tests/test_console.py`, `console.test.ts`, `e2e/console.e2e.mjs`, `fixtures/console/fake_claude.py`.

## Round 1 fixes

- Security: allowances in server memory; console settings outside the run folder; token in an owner-only file; narrow
  allowance rules; prompt cap; prompts of ended turns denied and marked.
- Behaviour: Ctrl+R exit; prompt key guard; reconnect after a lost connection; subagent events hidden; Esc returns the
  queue; exact-match local commands; IME; focus; @ debounce; streamed text apart from stored entries; text kept on stop;
  async follow with heartbeat; partial batching; non-dismissable terminal drawer.
- Look: ❯ markers instead of inverted bars; one working line; echoed commands; quiet status tags; diff weight; detail
  indicator; grouped shortcut help; tappable mode and help; hover states; 120ch measure; mobile footer.

## Round 2 fixes

- Wrappers matched by program name; one-word allowances exact; ClaudePanel prompt liveness; no double-applied batch;
  unsent messages restored; last streamed words flushed with the next event.
