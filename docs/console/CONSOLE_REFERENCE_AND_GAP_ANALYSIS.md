# Console — Claude Code reference and gap analysis (Phase 0, 2026-11-27)

Faraday's run Console is rebuilt to work like Claude Code's terminal, in black and white. This document records what Claude
Code does, what our console does today, and what our backend can really support. Sources: the Claude Code docs
(interactive-mode, permission-modes, permissions, commands, headless, cli-reference, model-config, statusline,
agent-sdk/streaming-output), read 2026-11-27, and two probes run against Claude Code 2.1.332 (below).

## 1. How the console runs (constraint that shapes everything)

Each console message is one **headless** Claude Code turn: `claude -p --output-format stream-json --verbose` inside the
run's bubblewrap jail, resuming the run's session (`state.console_session`). The web server owns the turn in a thread
(`app/web/console.py`: `start_turn` / `follow`); the page only follows it. There is no terminal and no TTY. So every
interactive Claude Code feature has to be either (a) driven through a headless flag or event, (b) rebuilt by us from
data we really have, or (c) declared unavailable. Nothing is faked.

## 2. Probes (Claude Code 2.1.332, one Haiku turn each, `scratchpad/probe/`)

1. `--permission-prompt-tool mcp__perm__approve` with a stdio MCP stub. Claude Code calls `tools/call` with
   `arguments = {tool_name, input, tool_use_id}` and `_meta["claudecode/toolUseId"]`. Returning one text block
   `{"behavior":"allow","updatedInput":<input>}` ran the command. Deny is `{"behavior":"deny","message":…}` (docs).
2. The same with an **HTTP** MCP server (`{"type":"http","url":…,"headers":{…}}`): identical calls; custom headers arrive
   (used for a per-turn token). The jail keeps the host network, so Claude Code in the jail reaches 127.0.0.1.
3. `--include-partial-messages` adds `{"type":"stream_event","event":{…}}` lines: `content_block_start` (text,
   tool_use, thinking), `content_block_delta` (`text_delta`, `input_json_delta`, `thinking_delta`), `message_stop`.
4. Event fields confirmed (saved, scrubbed, as `tests/fixtures/console/turn-bash.jsonl`):
   - `system/init`: session_id, model, permissionMode, cwd, tools, slash_commands, skills, agents, mcp_servers.
   - `assistant`: message.content (text, tool_use {id,name,input}, thinking) and message.usage (input, cache read and
     creation, output tokens).
   - `user`: content[].tool_result {tool_use_id, content, is_error}, `tool_use_result` {stdout, stderr, interrupted},
     `tool_result_meta[].permission_decision` {decision, source}.
   - `result`: total_cost_usd, duration_ms, num_turns, usage, `modelUsage[model].contextWindow`, permission_denials,
     is_error, subtype.
   - Also `system/status`, `system/thinking_tokens`, `rate_limit_event`.

## 3. Claude Code reference (what we mirror)

| Area | Claude Code behaviour (docs) |
|---|---|
| Layout | Transcript top, prompt at the bottom, a one-line footer with the permission mode; no chrome. |
| Prompt | Enter sends (queues during a reply); Shift+Enter, `\`+Enter or Ctrl+J newline; Up/Down move in multiline text first, then history; Ctrl+R history search; Esc Esc clears the draft; `?` on empty input shows help; `/` commands and skills; `@` file autocomplete; `!` shell mode. |
| Interrupt | Esc interrupts and keeps work done; Ctrl+C interrupts, idle Ctrl+C clears input. Headless: SIGINT ends the turn; the session resumes and leaves the interrupted turn as it is. |
| Modes | default (manual), acceptEdits, plan, auto, dontAsk, bypassPermissions. Shift+Tab cycles default → acceptEdits → plan. Footer: `⏸ manual mode on`, `⏵⏵ accept edits on`, `⏸ plan mode on`. All values work with `-p`; plan mode keeps its blocks headless. |
| Permission prompt | Describes the action and its command or path; Yes; "Yes, and don't ask again for: <rule>" (session for edits, per command for Bash); No (Esc). Tab adds a comment to Yes/No. |
| Transcript | Tool calls one line each, details hidden until expanded (Ctrl+O transcript view: tool detail, timestamps, model). MCP calls collapse. `/diff` shows edits. Exact glyphs (⏺ ⎿) are not documented. |
| Status | Footer mode badge; header shows effort and model source. Context and cost via `/context`, `/usage` (`/cost` alias); status-line data: model, context %, cost, duration, lines added/removed. |
| Slash commands | ~110 built-ins. In `-p`: skills and custom commands expand; `/model x`, `/effort x` take an argument; terminal-only commands are not available. |

## 4. Our console today (before this work)

- `Console.tsx` (104 lines): a drawer with a log of entries and a textarea. Enter sends, Shift+Enter newline.
- Roles shown: you, claude, question, tool, system, error. A tool is one summary line (`tool_line`); **its output,
  status and duration are dropped**; edits show no diff.
- No stop, no modes, no model choice, no slash commands, no `@`, no history, no shortcuts help, no context or cost.
- Permissions: `settings.json` `defaultMode: acceptEdits` plus an allow list; in `-p` anything else is **silently
  denied** (`result.permission_denials`), and the user never sees why.
- Streaming is per event (whole messages), not per token.

## 5. Gap analysis and decisions

| Gap | Real backend support | Decision |
|---|---|---|
| Tool output, status, duration, errors | `user.tool_result`, `tool_use_result`, timestamps | Show per tool; collapsed by default, expand per block or all (Ctrl+O). |
| Diffs | `Edit`/`MultiEdit`/`Write` inputs carry old/new text | Line diff rendered from the real input. |
| Token streaming | `--include-partial-messages` | Stream text deltas live (not stored); the final message replaces them. |
| Interrupt | SIGINT to the Claude Code process | `POST …/console/stop`; Esc / Ctrl+C. |
| Permission prompts | `--permission-prompt-tool` via an HTTP MCP endpoint on our server, per-turn token | Real Allow once / Allow for this session / Deny with a note; enforcement stays in Claude Code; times out to deny after 10 minutes. |
| Modes | `--permission-mode` per turn | default, acceptEdits, plan, cycled by Shift+Tab. `bypassPermissions`, `auto`, `dontAsk` not offered (security, and `auto` is documented as not guaranteeing safety). |
| Model | `--model` per turn | `/model` (haiku, sonnet, opus); default stays the run session's model. |
| Context, cost | `assistant.usage`, `result.modelUsage.contextWindow`, `total_cost_usd` | Footer: context %, last turn cost, run spend. |
| Slash commands | init `slash_commands` (skills, plugin commands) | Pass-through to Claude Code; local commands listed in the parity matrix; unsupported ones shown as unavailable with the reason. |
| `@` files | run folder on disk | Autocomplete from a run-files endpoint; inserted as `@path`. |
| History | console.jsonl "you" entries | Up/Down and Ctrl+R over previous prompts; draft kept per run. |
| `!` shell mode | none: the console has no shell outside Claude Code | Unavailable (it would bypass the session's permissions). |
| Rewind, fork, resume picker | one session per run | Unavailable; `/clear` starts a new session. |

## 6. Constraints carried into the build

- No live video runs; tests and screenshots use a fake `claude` that replays real event shapes.
- No new dependencies: unit tests use Node's built-in test runner (TypeScript type stripping), end-to-end tests the
  Playwright copy already on this machine with the installed Chrome.
- The palette is fixed by `test_the_frontend_is_black_with_white_and_grey_only`: neutrals only.
- Reference screenshots of Claude Code itself are not captured (it is a terminal program; a capture would need a live
  session). Visual comparison is against the documented behaviour above. Documented deviation.
