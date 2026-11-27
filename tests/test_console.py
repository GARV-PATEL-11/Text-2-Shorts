"""The website's console as a Claude Code terminal: events → entries, permission prompts answered from the page,
stop, modes and model, new session, @ files. Claude Code is replaced by small scripts; event shapes come from a real
turn (fixtures/console/turn-bash.jsonl, Claude Code 2.1.332)."""

import json
import os
import sys
import threading
import time
from pathlib import Path

import pytest
from app import sandbox
from app.web import console, console_permissions
from conftest import REPOSITORY_ROOT
from test_web import ORIGIN, run_at_cp1, signed_in, web  # noqa: F401  (fixture)

FIXTURE = REPOSITORY_ROOT / "tests" / "fixtures" / "console" / "turn-bash.jsonl"
EVENTS = [json.loads(line) for line in FIXTURE.read_text().splitlines()]


def read_all(run):
    reader = console.EventReader(run)
    return [entry for event in EVENTS for entry in reader.read(event)]


# ── events → entries ─────────────────────────────────────────────────────────────────────────────────────


def test_a_real_turn_becomes_a_tool_call_its_result_streamed_text_and_a_summary(tmp_path):
    entries = read_all(tmp_path)
    roles = [entry.role for entry in entries]
    tool = next(entry for entry in entries if entry.role == "tool")
    assert tool.tool == "Bash" and tool.input["command"] == "date +%Y > year.txt" and tool.id.startswith("toolu_")
    result = next(entry for entry in entries if entry.role == "result")
    assert result.id == tool.id and result.tool == "Bash" and not result.is_error
    assert result.text == "(Bash completed with no output)" and result.duration_ms is not None
    assert "thinking" in roles and "partial" in roles  # live indicators, never stored
    assert roles.index("result") > roles.index("tool")
    done = entries[-1]
    assert done.role == "system" and done.stats is not None
    assert done.stats.model == "claude-haiku-5-5" and done.stats.context_window == 1_000_000
    assert done.stats.context_tokens == 2 + 1001 + 30594  # the last request's input: the context in use
    assert done.stats.cost_usd == pytest.approx(0.0040609) and done.stats.tools == 1


def test_the_init_event_describes_the_session(tmp_path):
    read_all(tmp_path)
    session = console.session_info(tmp_path)
    assert session.model == "claude-haiku-5-5" and session.permission_mode == "default"
    assert "text-2-shorts-produce" in session.slash_commands and "script-writer" in session.agents


def test_long_tool_output_and_inputs_are_cut_but_say_so(tmp_path):
    reader = console.EventReader(tmp_path)
    call = {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": "t1",
                    "name": "Write",
                    "input": {"file_path": "a.md", "content": "x" * 50_000},
                }
            ]
        },
    }
    (tool,) = reader.read(call)
    assert len(tool.input["content"]) < 21_000 and tool.input["content"].endswith("characters cut]")
    output = {
        "type": "user",
        "message": {
            "content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": [{"type": "text", "text": "y" * 50_000}]}
            ]
        },
    }
    (result,) = reader.read(output)
    assert result.text.endswith("characters cut]") and result.tool == "Write"


def test_compact_and_built_in_command_output_are_shown_but_the_summary_claude_reads_is_not(tmp_path):
    reader = console.EventReader(tmp_path)
    assert reader.read({"type": "system", "subtype": "status", "status": "compacting"})[0].role == "thinking"
    (boundary,) = reader.read(
        {
            "type": "system",
            "subtype": "compact_boundary",
            "compact_metadata": {"pre_tokens": 31657, "post_tokens": 10080},
        }
    )
    assert boundary.text == "Conversation Compacted (31,657 → 10,080 tokens)."
    assert reader.read({"type": "user", "message": {"content": "This session is being continued from…"}}) == []
    (output,) = reader.read(
        {"type": "user", "message": {"content": "<local-command-stdout>Compacted </local-command-stdout>"}}
    )
    assert (output.role, output.text) == ("system", "Compacted")


def test_a_failed_turn_is_an_error_with_its_stats(tmp_path):
    reader = console.EventReader(tmp_path)
    (entry,) = reader.read({"type": "result", "is_error": True, "subtype": "error_max_turns", "total_cost_usd": 0.5})
    assert entry.role == "error" and entry.stats.cost_usd == 0.5


# ── a turn's command ─────────────────────────────────────────────────────────────────────────────────────


def test_a_turn_uses_the_console_settings_and_the_permission_tool(tmp_path):
    options = console.TurnOptions(
        model="sonnet", mode="plan", permission_url="http://127.0.0.1:8765/x", token="t0k", config_dir=tmp_path
    )
    arguments = sandbox.console_claude_arguments("hello", "s-1", options)
    assert arguments[arguments.index("--model") + 1] == "sonnet" and arguments.count("--model") == 1
    assert arguments[arguments.index("--permission-mode") + 1] == "plan"
    assert "--include-partial-messages" in arguments
    config = json.loads(Path(arguments[arguments.index("--mcp-config") + 1]).read_text())
    server = config["mcpServers"]["faraday"]
    assert server == {"type": "http", "url": "http://127.0.0.1:8765/x", "headers": {"X-Turn-Token": "t0k"}}
    assert arguments[arguments.index("--permission-prompt-tool") + 1] == "mcp__faraday__permission"
    assert arguments[-2:] == ["--", "hello"]


# ── permission prompts ───────────────────────────────────────────────────────────────────────────────────

SLEEPY = "import time\ntime.sleep(30)\n"


@pytest.fixture
def running_turn(web, monkeypatch, tmp_path):  # noqa: F811
    runs, client = web
    signed_in(client)
    run = run_at_cp1(runs)
    script = tmp_path / "sleepy.py"
    script.write_text(SLEEPY)
    monkeypatch.setattr(console, "claude_turn_command", lambda *_args, **_kw: [sys.executable, str(script)])
    turn = console.start_turn(run, "go", base_url="http://127.0.0.1:8765")
    yield run, client, turn
    console.stop_turn(run)
    turn.finished.wait(15)


def ask(run, turn, tool, tool_input, results):
    call = {
        "jsonrpc": "2.0",
        "id": 7,
        "method": "tools/call",
        "params": {"name": "permission", "arguments": {"tool_name": tool, "input": tool_input, "tool_use_id": "u1"}},
    }
    thread = threading.Thread(target=lambda: results.append(console_permissions.handle(run, turn.token, call)))
    thread.start()
    return thread


def decision(reply):
    return json.loads(reply["result"]["content"][0]["text"])


def wait_pending(client, run, count=1):
    for _ in range(100):
        pending = client.get(f"/api/runs/{run.name}/console").json()["pending"]
        if len(pending) >= count:
            return pending
        time.sleep(0.05)
    raise AssertionError("no permission prompt appeared")


def test_a_permission_prompt_waits_for_the_page_and_allow_once_runs_the_call(running_turn):
    run, client, turn = running_turn
    results = []
    thread = ask(run, turn, "Bash", {"command": "python3 make.py"}, results)
    (prompt,) = wait_pending(client, run)
    assert prompt["tool"] == "Bash" and prompt["input"] == {"command": "python3 make.py"}
    assert prompt["rule"] == "Bash(python3 make.py *)" and "python3 make.py" in prompt["text"]
    answer = client.post(
        f"/api/runs/{run.name}/console/permissions/{prompt['id']}", json={"decision": "once"}, headers=ORIGIN
    )
    assert answer.status_code == 204
    thread.join(5)
    assert decision(results[0]) == {"behavior": "allow", "updatedInput": {"command": "python3 make.py"}}
    assert [entry.role for entry in turn.entries if entry.role in ("permission", "answer")] == ["permission", "answer"]
    assert client.get(f"/api/runs/{run.name}/console").json()["pending"] == []


def test_deny_sends_the_users_note_to_claude(running_turn):
    run, client, turn = running_turn
    results = []
    thread = ask(run, turn, "Write", {"file_path": "x.md", "content": "hi"}, results)
    (prompt,) = wait_pending(client, run)
    client.post(
        f"/api/runs/{run.name}/console/permissions/{prompt['id']}",
        json={"decision": "deny", "note": "write it to notes.md"},
        headers=ORIGIN,
    )
    thread.join(5)
    assert decision(results[0])["behavior"] == "deny"
    assert "write it to notes.md" in decision(results[0])["message"]


def test_allow_for_this_session_lets_the_same_command_through_until_clear(running_turn):
    run, client, turn = running_turn
    results = []
    thread = ask(run, turn, "Bash", {"command": "python3 a.py"}, results)
    (prompt,) = wait_pending(client, run)
    client.post(
        f"/api/runs/{run.name}/console/permissions/{prompt['id']}", json={"decision": "session"}, headers=ORIGIN
    )
    thread.join(5)
    assert decision(results[0])["behavior"] == "allow"
    again = console_permissions.handle(
        run,
        turn.token,
        {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "permission",
                "arguments": {"tool_name": "Bash", "input": {"command": "python3 a.py --again"}},
            },
        },
    )
    assert decision(again)["behavior"] == "allow"  # no new prompt
    assert client.get(f"/api/runs/{run.name}/console").json()["settings"]["allowed"] == ["Bash(python3 a.py *)"]
    assert client.post(f"/api/runs/{run.name}/console/clear", headers=ORIGIN).status_code == 409  # stop first
    console.stop_turn(run)
    turn.finished.wait(15)
    assert client.post(f"/api/runs/{run.name}/console/clear", headers=ORIGIN).status_code == 204
    assert client.get(f"/api/runs/{run.name}/console").json()["settings"]["allowed"] == []


def test_a_compound_command_is_never_allowed_for_the_session(running_turn):
    run, client, turn = running_turn
    results = []
    thread = ask(run, turn, "Bash", {"command": "python3 a.py && rm -rf x"}, results)
    (prompt,) = wait_pending(client, run)
    assert prompt["rule"] is None  # only Allow Once or Deny
    refused = client.post(
        f"/api/runs/{run.name}/console/permissions/{prompt['id']}", json={"decision": "session"}, headers=ORIGIN
    )
    assert refused.status_code == 409
    client.post(f"/api/runs/{run.name}/console/permissions/{prompt['id']}", json={"decision": "deny"}, headers=ORIGIN)
    thread.join(5)


def test_the_permission_endpoint_answers_only_the_running_turns_token(running_turn):
    run, client, turn = running_turn
    path = f"/api/console-permission/{run.name}"
    init = {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}}
    assert client.post(path, json=init, headers={"X-Turn-Token": "wrong"}).status_code == 403
    assert client.post(path, json=init).status_code == 403
    ok = client.post(path, json=init, headers={"X-Turn-Token": turn.token})
    assert ok.status_code == 200 and ok.json()["result"]["serverInfo"]["name"] == "faraday"
    tools = client.post(
        path, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, headers={"X-Turn-Token": turn.token}
    ).json()["result"]["tools"]
    assert [tool["name"] for tool in tools] == ["permission"]
    note = client.post(
        path, json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers={"X-Turn-Token": turn.token}
    )
    assert note.status_code == 202


def test_questions_and_plan_approval_are_never_held_by_the_permission_tool(running_turn):
    run, _, turn = running_turn
    for tool in ("AskUserQuestion", "ExitPlanMode"):
        reply = console_permissions.handle(run, turn.token, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "permission", "arguments": {"tool_name": tool, "input": {}}}})  # fmt: skip
        assert decision(reply)["behavior"] == "deny"  # the page shows them; the user answers in the console


def test_answers_come_only_from_the_signed_in_page(running_turn):
    run, client, turn = running_turn
    results = []
    thread = ask(run, turn, "Bash", {"command": "make"}, results)
    (prompt,) = wait_pending(client, run)
    url = f"/api/runs/{run.name}/console/permissions/{prompt['id']}"
    assert client.post(url, json={"decision": "once"}, headers={"Origin": "http://evil.example"}).status_code == 403
    client.cookies.clear()
    assert client.post(url, json={"decision": "once"}, headers=ORIGIN).status_code == 401
    signed_in(client)
    client.post(url, json={"decision": "deny"}, headers=ORIGIN)
    thread.join(5)


def test_a_prompt_nobody_answers_is_denied_when_the_turn_stops(running_turn):
    run, client, turn = running_turn
    results = []
    thread = ask(run, turn, "Bash", {"command": "make"}, results)
    wait_pending(client, run)
    console.stop_turn(run)
    thread.join(10)
    assert decision(results[0])["behavior"] == "deny"


# ── stop, settings, new session, files ───────────────────────────────────────────────────────────────────


def test_stop_ends_the_turn_and_says_so(running_turn):
    run, client, turn = running_turn
    assert client.post(f"/api/runs/{run.name}/console/stop", headers=ORIGIN).status_code == 204
    assert turn.finished.wait(15)
    assert not console.is_busy(run)
    assert any(entry.role == "system" and "Stopped" in entry.text for entry in console.history(run))
    assert client.post(f"/api/runs/{run.name}/console/stop", headers=ORIGIN).status_code == 409  # nothing to stop


def test_the_model_and_mode_are_kept_per_run_and_used_by_the_next_turn(web, monkeypatch, tmp_path):  # noqa: F811
    runs, client = web
    signed_in(client)
    run = run_at_cp1(runs)
    url = f"/api/runs/{run.name}/console/settings"
    assert client.put(url, json={"mode": "bypassPermissions"}, headers=ORIGIN).status_code == 400  # never offered
    saved = client.put(url, json={"model": "sonnet", "mode": "plan"}, headers=ORIGIN).json()
    assert saved["model"] == "sonnet" and saved["mode"] == "plan"
    seen = []
    script = tmp_path / "quick.py"
    script.write_text("print('{\"type\": \"result\", \"is_error\": false}')\n")

    def command(run, message, session_id, options):
        seen.append(options)
        return [sys.executable, str(script)]

    monkeypatch.setattr(console, "claude_turn_command", command)
    client.post(f"/api/runs/{run.name}/console", json={"message": "plan it"}, headers=ORIGIN)
    assert (seen[0].model, seen[0].mode) == ("sonnet", "plan") and seen[0].token and seen[0].permission_url


def test_clear_starts_a_new_session(web):  # noqa: F811
    from app.workflow.ledger import load_state, update_state

    runs, client = web
    signed_in(client)
    run = run_at_cp1(runs)
    update_state(run, lambda state: setattr(state, "console_session", "old"))
    assert client.post(f"/api/runs/{run.name}/console/clear", headers=ORIGIN).status_code == 204
    assert load_state(run).console_session is None
    assert console.history(run)[-1].role == "system" and "New Conversation" in console.history(run)[-1].text


def test_at_files_lists_the_runs_files_only(web):  # noqa: F811
    runs, client = web
    signed_in(client)
    run = run_at_cp1(runs)
    (run / ".console.lock").write_text("")
    found = client.get(f"/api/runs/{run.name}/console/files", params={"q": "scr"}).json()
    assert "script.json" in found and all(not name.startswith(".") for name in found)
    assert client.get(f"/api/runs/{run.name}/console/files", params={"q": "../"}).json() == []


# ── the whole path over real HTTP: Claude Code (a fake) asks Faraday, the page answers ──────────────────────


def test_a_turn_asks_for_permission_over_http_and_runs_once_the_page_allows_it(tmp_path, monkeypatch):
    import socket

    import httpx
    import uvicorn
    from app.web import auth
    from app.web.app import create_app
    from test_web import ACCOUNT

    runs = tmp_path / "runs"
    runs.mkdir()
    run = run_at_cp1(runs)
    fake = REPOSITORY_ROOT / "tests" / "fixtures" / "console" / "fake_claude.py"
    monkeypatch.setattr(auth, "claude_code_account", lambda: ACCOUNT)
    monkeypatch.setattr(
        console,
        "claude_turn_command",
        lambda run, message, session, options: [
            sys.executable,
            str(fake),
            *sandbox.console_claude_arguments(message, session, options),
        ],
    )
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(runs), port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    try:
        with httpx.Client(base_url=base, headers={"Origin": base}, timeout=30) as client:
            assert client.post("/api/session").status_code == 200
            path = f"/api/runs/{run.name}/console"
            streamed = []
            sender = threading.Thread(
                target=lambda: streamed.extend(
                    json.loads(line)
                    for line in client.post(path, json={"message": "shorten scene 2"}).text.splitlines()
                )
            )
            sender.start()
            for _ in range(600):  # up to 30 s: a loaded machine starts Python slowly
                pending = client.get(path).json()["pending"]
                if pending:
                    break
                time.sleep(0.05)
            (prompt,) = pending
            assert prompt["id"] == "toolu_bash" and prompt["rule"] == "Bash(python3 tools/check_script.py *)"
            assert client.post(f"{path}/permissions/toolu_bash", json={"decision": "once"}).status_code == 204
            sender.join(30)
    finally:
        server.should_exit = True
    roles = [entry["role"] for entry in streamed]
    assert roles[0] == "you" and "partial" in roles and roles[-1] == "system"
    results = {entry["id"]: entry["text"] for entry in streamed if entry["role"] == "result"}
    assert results["toolu_bash"].endswith("All checks passed.")
    assert any(entry["role"] == "answer" and entry["id"] == "toolu_bash" for entry in streamed)
    stored = [entry.role for entry in console.history(run)]
    assert "partial" not in stored and "permission" in stored and "answer" in stored


# ── what the jail can never do (review A1–A6) ────────────────────────────────────────────────────────────


def test_session_allowances_and_console_settings_live_outside_the_run_folder(running_turn):
    run, client, turn = running_turn
    results = []
    thread = ask(run, turn, "Bash", {"command": "make video"}, results)
    (prompt,) = wait_pending(client, run)
    client.post(
        f"/api/runs/{run.name}/console/permissions/{prompt['id']}", json={"decision": "session"}, headers=ORIGIN
    )
    thread.join(5)
    client.put(f"/api/runs/{run.name}/console/settings", json={"model": "opus"}, headers=ORIGIN)
    written = " ".join(
        path.read_text(errors="ignore")
        for path in run.rglob("*")
        if path.is_file() and path.name != console.CONSOLE_FILE
    )  # the transcript only records it
    assert "Bash(make video *)" not in written and "opus" not in written  # nothing Claude can edit from inside
    assert not console.settings_path(run).resolve().is_relative_to(run.resolve())


def test_a_planted_allowance_in_the_run_folder_changes_nothing(running_turn):
    run, client, turn = running_turn
    # Claude may write anything in the run folder: an allowance planted there must count for nothing
    (run / "console-allowed.json").write_text('["Bash(rm *)"]')
    results = []
    thread = ask(run, turn, "Bash", {"command": "rm -rf scenes"}, results)
    (prompt,) = wait_pending(client, run)  # still asks
    client.post(f"/api/runs/{run.name}/console/permissions/{prompt['id']}", json={"decision": "deny"}, headers=ORIGIN)
    thread.join(5)


@pytest.mark.parametrize(
    ("tool", "tool_input", "rule"),
    [
        ("Bash", {"command": "python3 tools/check.py script.json"}, "Bash(python3 tools/check.py *)"),
        ("Bash", {"command": "python3 -c 'import os'"}, None),  # inline code: once only
        ("Bash", {"command": "bash -c 'curl x'"}, None),
        ("Bash", {"command": "env FOO=1 make"}, None),
        ("Bash", {"command": "find . -exec rm {} ;"}, None),
        ("Bash", {"command": "xargs rm"}, None),
        ("Bash", {"command": "ffprobe clip.mp4"}, "Bash(ffprobe clip.mp4 *)"),
        ("Bash", {"command": "make"}, "Bash(make)"),  # one word: exactly that, never with flags added later
        ("Bash", {"command": "/usr/bin/env bash -c x"}, None),  # a wrapper by its path is still a wrapper
        ("Bash", {"command": "/usr/bin/env bash"}, None),
        ("Bash", {"command": "ls && rm x"}, None),
        ("Bash", {"command": "echo $(whoami)"}, None),
        ("WebFetch", {"url": "https://example.com/a?b"}, "WebFetch(domain:example.com)"),
        ("Write", {"file_path": "/etc/passwd"}, None),  # outside the run: once only
    ],
)
def test_allow_for_this_session_is_narrow(tmp_path, tool, tool_input, rule):
    assert console_permissions.rule_for(tool, tool_input, tmp_path) == rule


def test_a_session_rule_matches_only_what_it_names(tmp_path):
    allows = console_permissions.allows
    assert allows("Bash(python3 tools/check.py *)", "Bash", {"command": "python3 tools/check.py --fast"}, tmp_path)
    assert not allows("Bash(python3 tools/check.py *)", "Bash", {"command": "python3 -c 'x'"}, tmp_path)
    assert not allows("Bash(python3 tools/check.py *)", "Bash", {"command": "python3 tools/check.py; rm x"}, tmp_path)
    assert allows(f"Write({tmp_path.name}/**)", "Write", {"file_path": str(tmp_path / "a.md")}, tmp_path)
    assert not allows(f"Write({tmp_path.name}/**)", "Write", {"file_path": "/etc/hosts"}, tmp_path)
    assert allows("Bash(make)", "Bash", {"command": "make"}, tmp_path)
    assert not allows("Bash(make)", "Bash", {"command": "make -f evil.mk"}, tmp_path)
    assert not allows("Bash(python3 run.py *)", "Bash", {"command": "/usr/bin/python3 -c x"}, tmp_path)
    assert not allows("WebFetch(domain:example.com)", "WebFetch", {"url": "https://example.com.evil.net/"}, tmp_path)


def test_the_turn_token_is_never_on_a_command_line(tmp_path):
    options = console.TurnOptions(permission_url="http://127.0.0.1:8765/x", token="s3cret", config_dir=tmp_path)
    arguments = sandbox.console_claude_arguments("hello", None, options)
    assert not any("s3cret" in argument for argument in arguments)
    config = arguments[arguments.index("--mcp-config") + 1]
    assert "s3cret" in Path(config).read_text() and (os.stat(config).st_mode & 0o077) == 0  # owner-only file


def test_too_many_waiting_prompts_are_denied_at_once(running_turn):
    run, client, turn = running_turn
    results, threads = [], []
    for number in range(console_permissions.MAX_WAITING):
        threads.append(ask(run, turn, "Bash", {"command": f"make {number}"}, results))
    wait_pending(client, run, console_permissions.MAX_WAITING)
    extra = console_permissions.handle(run, turn.token, {"jsonrpc": "2.0", "id": 9, "method": "tools/call",
        "params": {"name": "permission", "arguments": {"tool_name": "Bash", "input": {"command": "make more"}}}})  # fmt: skip
    assert decision(extra)["behavior"] == "deny"
    console.stop_turn(run)
    for thread in threads:
        thread.join(10)


def test_a_prompt_for_a_turn_that_has_ended_is_denied_at_once(running_turn):
    run, _, turn = running_turn
    token = turn.token
    assert console.stop_turn(run)
    assert turn.finished.wait(15)
    assert console.running(run) is None, console.TURNS
    with pytest.raises(PermissionError):
        console_permissions.handle(run, token, {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {}})


def test_a_subagents_own_events_stay_out_of_the_main_transcript(tmp_path):
    reader = console.EventReader(tmp_path)
    inner = {
        "type": "assistant",
        "parent_tool_use_id": "task1",
        "message": {"content": [{"type": "text", "text": "subagent thinking aloud"}]},
    }
    assert reader.read(inner) == []
    assert (
        reader.read(
            {
                "type": "stream_event",
                "parent_tool_use_id": "task1",
                "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "x"}},
            }
        )
        == []
    )


def test_streamed_text_is_sent_in_batches_and_kept_when_the_turn_is_stopped(running_turn, monkeypatch, tmp_path):
    run, _, turn = running_turn
    console.stop_turn(run)
    turn.finished.wait(15)
    script = tmp_path / "chatty.py"
    script.write_text(
        "import json, time\n"
        "for word in ['one ', 'two ', 'three ']*20:\n"
        "    print(json.dumps({'type': 'stream_event', 'event': {'type': 'content_block_delta',"
        " 'delta': {'type': 'text_delta', 'text': word}}}), flush=True)\n"
        "time.sleep(30)\n"
    )
    monkeypatch.setattr(console, "claude_turn_command", lambda *_args, **_kw: [sys.executable, str(script)])
    chatty = console.start_turn(run, "talk")
    for _ in range(100):
        if any(entry.role == "partial" for entry in chatty.entries):
            break
        time.sleep(0.05)
    time.sleep(0.3)
    console.stop_turn(run)
    assert chatty.finished.wait(15)
    partials = [entry for entry in chatty.entries if entry.role == "partial"]
    assert 1 <= len(partials) < 60  # 60 tokens, far fewer lines
    kept = [entry for entry in console.history(run) if entry.role == "claude"]
    assert kept and kept[-1].text.startswith("one two three") and kept[-1].text.endswith("…")
