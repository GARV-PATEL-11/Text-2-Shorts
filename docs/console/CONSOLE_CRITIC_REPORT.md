# Console critic report

Three independent reviewers (Sonnet), each given the code and the documents, not the implementer's conclusions:
visual/UX (V), functional/interaction (F), architecture/quality/security (A). Severity: Critical, High, Medium, Low,
Enhancement. Every finding has a resolution: **fixed** (with the test that covers it), **deferred** (why), or
**rejected** (evidence). Full findings with each reviewer's cross-questions are kept with the session's scratch files;
this is the consolidated record.

## Round 1 (built Phases 1–5 in one pass, then reviewed)

Counts: Critical 1, High 10, Medium 24, Low 13, Enhancement 5.

### Critical and High

| ID | Finding | Resolution |
|---|---|---|
| A1 Critical | Session allowances lived in `state.json` inside the run folder, which the jail can write; Claude could grant itself `Bash(python3 *)` without a prompt. | **Fixed.** Allowances are held in server memory only (`console_permissions.ALLOWED`, cleared by `/clear` and restarts); the console's model and mode moved to `artifacts/console/<run>.json`, outside the run folder (read-only inside the jail). Tests: `test_session_allowances_and_console_settings_live_outside_the_run_folder`, `test_a_planted_allowance_in_the_run_folder_changes_nothing`. |
| A2 High | The turn token was on the command line (`--mcp-config` JSON), readable from `/proc` by any local process; held prompts each pin a server thread. | **Fixed.** The config is an owner-only (0600) file outside the run folder, deleted when the turn ends; at most 4 waiting prompts per turn, more are denied. Tests: `test_the_turn_token_is_never_on_a_command_line`, `test_too_many_waiting_prompts_are_denied_at_once`. |
| A3 High | With the token, forged prompts could trick the user into a broad allowance. | **Mitigated, residual accepted.** Forging needs a POST from inside the jail; Claude Code's Bash sandbox has no network (`allowedDomains: []`), WebFetch only GETs, and the token is no longer on argv. Allowances are now narrow (A4). |
| A4 High | "Allow for this session" by first word let `python3 -c`, `env`, `bash`, `find -exec`, `xargs` through; file tools were allowed for any path. | **Fixed.** Bash rules are command + first argument (`Bash(python3 tools/check.py *)`), never for wrappers, inline-code flags, `VAR=` prefixes or compound/substituted commands; file tools only inside the run folder; WebFetch by exact domain. Tests: `test_allow_for_this_session_is_narrow` (12 cases), `test_a_session_rule_matches_only_what_it_names`. |
| F1 High | Ctrl+R search had no exit; with no match, Enter sent the query to Claude; Esc while busy stopped the turn. | **Fixed.** In search, Enter only takes a match and Esc restores the draft. Tests: keys unit test, e2e step "Ctrl+R searches…". |
| F2 High | A permission prompt took focus; a keypress meant for the prompt box could approve a call never seen. | **Fixed.** Keys in the prompt's first 600 ms and key repeats are ignored. e2e: an early "1" leaves the prompt open. |
| F3 High | A dropped connection put the message back (a resend would duplicate the turn); quiet connections could time out. | **Fixed.** Only a refused request (an API error) restores the text; a lost connection re-follows the running turn; the follow stream is async with a heartbeat every 15 s. |
| F4 High | A permission entry of an ended turn stayed "open" and replaced the input for good. | **Fixed.** Ended turns write "Ended: the turn stopped before you answered." for open prompts; prompts are only open while a turn runs; an unfinished turn says so. Tests: `test_a_prompt_nobody_answers_is_denied_when_the_turn_stops`, unit test "stopped turn". |
| V1 High | Mode switching and help were keyboard-only (touch users stuck). | **Fixed.** The mode badge and "? for shortcuts" are buttons; key hints hide on small screens. |
| V2 High | Double border and inverted bar on the permission prompt. | **Fixed.** "❯" marker and bold, no programmatic focus ring. |
| V3 High | Menus' selected row was a full white inversion. | **Fixed.** "❯" marker, bold, subtle veil. |

### Medium (summary)

Fixed: F5 (subagent events kept out of the transcript), F7 (Esc returns queued messages to the prompt), F8 (/model
reports only real changes), F9 (bare local commands only on an exact match; "/plan add X" goes to Claude), F10 (the
footer says when a mode change applies to the next message; /plan returns to the previous mode), F11 (the console
drawer does not close on an outside click), F12 (IME composition), F13 (focus on open, transcript scrollable by
keyboard), F14 (@ debounced, hidden folders never walked), F16 (streamed text kept apart from stored entries: blocks no
longer remount when a turn ends; text streamed before a stop is kept), A5 (turn registered only after it can run),
A6 (answer check-and-set under one lock; prompts after a turn ends are denied), A7 (async follow), A8 (shallowest
`claude`; escalation even if it already exited), A9 (streamed text coalesced into ~80 ms batches), A11 (an odd event
no longer ends the turn), V4–V10, V12–V14.

Deferred: F6 incremental fold and `?since=` polling (the transcript renders its last 300 blocks and folds in
milliseconds at the sizes runs reach; revisit with a profile), F22–F24 enhancements, A12 generated TS types (no
generator in the repo; contract covered by pytest and the e2e), V11 empty-state wording (house Title Case).

Rejected: V15 per-turn cost line (the footer only shows the last turn; earlier turns' costs would be lost),
F13 Shift+Tab focus trap (Shift+Tab is Claude Code's mode key; Tab still moves focus forward, and the mode is also a
button).

## Round 2 (a fresh reviewer re-checked every fix and tried to break them)

Critical/High: A1, F1, F2, F3, V1, V2, V3 **resolved**; A2, A3, A4, F4 **partial** at the time, now:

| ID | Finding | Resolution |
|---|---|---|
| R1 High | Wrappers were matched on the raw first word: `/usr/bin/env bash` produced an allowance that later let `/usr/bin/env bash -c …` through. | **Fixed.** Wrappers are matched by program name (`Path(word).name`), and `VAR=` prefixes too. Test cases added to `test_allow_for_this_session_is_narrow`. |
| R2 Medium | A one-word allowance (`Bash(make *)`) covered `make -f`, `python3 -c`, `git -c`. | **Fixed.** One-word commands get an exact rule (`Bash(make)`). Tests in `test_a_session_rule_matches_only_what_it_names`. |
| F4 remainder | ClaudePanel still showed "waiting for your permission" after the turn ended. | **Fixed.** It shows an open prompt only while a turn runs. |
| R3 Medium | In a hidden tab, a frame-batched update could land after the reload and duplicate entries. | **Fixed.** The batch is dropped before the reload that replaces it. |
| R6 Medium | A message whose request never reached Faraday was dropped silently. | **Fixed.** Nothing received means nothing ran: the text is put back with a note. |
| R9 Low | The last streamed words waited for the next text. | **Fixed.** They are sent with the next event of any kind. |
| A2 residual | The token file is readable by the jailed Claude (same user). | **Accepted.** Using it needs a POST from inside the jail (no network for Bash), can only create prompts (never answer them), and is capped at 4 waiting prompts per turn. |
| A3 residual | `tool_use_id` is not verified against the transcript. | **Accepted (Low).** It only places a prompt on a line; the decision comes from the page. |
| R4 Medium | Shift+Tab is always taken for the mode. | **Rejected.** Claude Code's key; Tab moves forward, the mode is a button, the drawer has a close button: no keyboard trap. |
| R5 Medium | Esc from a non-composer focus closes the drawer mid-prompt. | **Accepted.** The turn and its prompt go on; reopening shows the prompt again (verified in the e2e). |
| R7 Low | A stale lock with no running turn makes the page retry following every 2 s. | **Deferred.** One cheap 409 per 2 s; only after a crash. |
| R10–R12 Low | Cosmetic. | **Deferred.** |

No Critical or High finding is open. The reviewers could still name improvements (F6 incremental fold, generated TS types),
recorded above as deferred with reasons.
