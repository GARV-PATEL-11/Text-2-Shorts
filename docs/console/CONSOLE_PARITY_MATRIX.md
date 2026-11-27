# Console parity matrix

Status: **done** (built and tested), **partial**, **unavailable** (no backend equivalent; the console says so).
Final state after Phases 1–6 and two review rounds (2026-11-27).

## Interaction

| Claude Code feature | Our equivalent | Backend | Status |
|---|---|---|---|
| Enter sends, Shift+Enter / `\`+Enter / Ctrl+J newline | same | — | done |
| Enter during a reply queues | held until the turn ends, then sent; Esc returns it to the prompt | turn lock | done |
| Up/Down history (after the first/last line) | same, over this run's prompts | console.jsonl | done |
| Ctrl+R history search | same | console.jsonl | done |
| Esc interrupts; Esc Esc clears the draft | same | `POST console/stop` (SIGINT) | done |
| Ctrl+C interrupt / clear input | same | same | done |
| Shift+Tab cycles modes | default → acceptEdits → plan | `--permission-mode` | done |
| Ctrl+O transcript detail | expand every tool block and show timestamps | entries carry `at` | done |
| `?` shortcuts help | same | — | done |
| `/` commands with autocomplete | menu from local commands + session skills/commands | init `slash_commands` | done |
| `@` file autocomplete | run files | `GET console/files` | done |
| `!` shell mode | — | none outside the session | unavailable |
| Ctrl+L redraw, Ctrl+Z, Ctrl+G editor, Ctrl+V image paste, Ctrl+S stash | — | terminal-only | unavailable |
| Alt+P model switch | `/model` | `--model` | done |

## Transcript

| Feature | Our equivalent | Backend | Status |
|---|---|---|---|
| User prompt | `›` line | entry `you` | done |
| Assistant text, streamed | Markdown, live text deltas | `stream_event` text_delta | done |
| Thinking indicator | "Thinking…" while thinking blocks stream (content is not shown: it arrives empty) | `thinking` block, `thinking_tokens` | done |
| Tool call | `⏺ Tool(detail)` | `tool_use` | done |
| Tool result | `⎿` output, collapsed to a few lines | `tool_result`, `tool_use_result` | done |
| Status per tool | running / done / failed / denied / awaiting approval | tool_result, is_error, permission | done |
| Duration | time between call and result | entry timestamps | done |
| Edits as diffs | `-`/`+` line diff | Edit/MultiEdit/Write input | done |
| Errors, warnings | `✗` lines, plain words | result is_error, process exit | done |
| End of turn summary | `✓ Done · 12 s · $0.004 · 3 tools` | result | done |
| Questions (AskUserQuestion) | question with one-click choices | tool_use AskUserQuestion | done (kept) |

## Permissions, modes, status

| Feature | Our equivalent | Backend | Status |
|---|---|---|---|
| Permission prompt: Yes | Allow once | MCP prompt tool → allow | done |
| "Don't ask again" | Allow for this session, narrow: Bash by command + first argument (exact for one word; never wrappers or inline-code flags), files inside the run, WebFetch by domain | server memory | done |
| No, with a note | Deny with an optional note to Claude | deny + message | done |
| Keyboard on the prompt | 1/2/3, Enter, Esc denies, Tab note | — | done |
| default / acceptEdits / plan modes | same, badge in the footer | `--permission-mode` | done |
| auto, dontAsk, bypassPermissions | — | would weaken the run's protections | unavailable (by decision) |
| Model display and choice | footer + `/model` | init.model, `--model` | done |
| Context usage | footer `ctx 31%` + `/context` | usage, contextWindow | done |
| Cost | footer last turn and run spend + `/cost` | total_cost_usd, state.spend_usd | done |
| Working directory | footer: the run folder | init.cwd | done |
| Session restoration | transcript and settings survive reload; a running turn is followed again | console.jsonl, server-owned turn | done (transcript, settings and a running turn with its open prompt survive a reload) |

## Slash commands

| Command | Our behaviour | Status |
|---|---|---|
| `/help` | commands and shortcuts | done |
| `/clear` | starts a new Claude Code session for this run (old transcript kept, a divider marks it) | done |
| `/compact` | sent to Claude Code (headless behaviour not documented; shown as is) | done |
| `/model [name]` | choose the console's model | done |
| `/plan`, `/mode` | switch permission mode | done |
| `/permissions` | the run's allow and deny rules, plus this session's allowances (revocable) | done |
| `/cost`, `/usage` | last turn and run spend | done |
| `/context` | tokens used of the model's window, from the last turn | done |
| `/status` | model, mode, session id, working directory, busy | done |
| `/diff` | files this session changed, with their diffs, from the transcript's edit calls | done |
| `/skills`, `/agents` | from the session's init event | done |
| `/stop` | interrupt | done |
| Skills and plugin commands (e.g. `/text-2-shorts-produce`) | sent to Claude Code, which expands them | done |
| `/resume`, `/rewind`, `/fork` | one session per run | unavailable |
| `/config`, `/hooks`, `/mcp`, `/memory`, `/init`, `/add-dir`, `/theme`… | run settings are fixed by Faraday | unavailable |
