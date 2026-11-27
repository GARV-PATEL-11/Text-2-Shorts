"""A stand-in for `claude -p --output-format stream-json` in console tests and demos: the same event shapes as a real
turn (fixtures/console/turn-bash.jsonl), streamed with small pauses, and a real permission request to the
--mcp-config server for its shell command. Argv: what app.sandbox.console_claude_arguments builds.

Messages: "/context" answers like Claude Code's /context; a message containing "slow" works for 60 s (to stop it);
"fail" ends with an error; anything else reads, edits, asks to run a command, then answers."""

import json
import sys
import time
import urllib.request

argv = sys.argv[1:]
message = argv[argv.index("--") + 1] if "--" in argv else ""
model = argv[argv.index("--model") + 1] if "--model" in argv else "claude-haiku-5-5"
mode = argv[argv.index("--permission-mode") + 1] if "--permission-mode" in argv else "default"
server = None
if "--mcp-config" in argv:
    with open(argv[argv.index("--mcp-config") + 1]) as config:  # a file, as Faraday writes it (the token stays off argv)
        server = json.load(config)["mcpServers"]["faraday"]
SESSION = "fake-session-1"


def say(event, pause=0.05):
    print(json.dumps(event), flush=True)
    time.sleep(pause)


def stream_text(text):
    say({"type": "stream_event", "event": {"type": "content_block_start", "content_block": {"type": "text"}}})
    for word in text.split(" "):
        say({"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": word + " "}}}, 0.04)
    say({"type": "assistant", "message": {"content": [{"type": "text", "text": text}], "usage": USAGE}})


def tool(ident, name, tool_input, output, error=False, pause=0.3):
    say({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": ident, "name": name, "input": tool_input}], "usage": USAGE}}, pause)
    say({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": ident, "content": output, "is_error": error}]},
         "tool_use_result": {"stdout": output, "stderr": ""}})


def permission(ident, name, tool_input):
    """Ask Faraday, as Claude Code does through --permission-prompt-tool; → the decision."""
    if server is None:
        return {"behavior": "deny", "message": "no permission tool"}
    call = {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "permission", "arguments": {"tool_name": name, "input": tool_input, "tool_use_id": ident}}}
    request = urllib.request.Request(server["url"], data=json.dumps(call).encode(),
                                     headers={"Content-Type": "application/json", **server["headers"]})
    with urllib.request.urlopen(request, timeout=700) as answer:
        return json.loads(json.loads(answer.read())["result"]["content"][0]["text"])


USAGE = {"input_tokens": 2, "cache_read_input_tokens": 30594, "cache_creation_input_tokens": 1001, "output_tokens": 40}
say({"type": "system", "subtype": "init", "session_id": SESSION, "model": model, "permissionMode": mode, "cwd": "/runs/demo",
     "tools": ["Bash", "Read", "Edit", "Write"], "slash_commands": ["text-2-shorts-produce", "compact", "context", "cost"],
     "skills": ["text-2-shorts-produce"], "agents": ["script-writer", "scene-builder", "accuracy-reviewer"]})
started = time.monotonic()
tools = 0
if message.startswith("/context"):
    say({"type": "assistant", "message": {"content": [{"type": "text", "text": "## Context Usage\n\n**Model:** " + model +
        "  \n**Tokens:** 31.6k / 1m (3%)\n\n| Category | Tokens |\n|---|---|\n| System prompt | 3.4k |\n| Messages | 14.4k |"}], "usage": USAGE}})
elif "slow" in message:
    say({"type": "stream_event", "event": {"type": "content_block_start", "content_block": {"type": "thinking"}}})
    time.sleep(60)
elif "fail" in message:
    say({"type": "result", "subtype": "error_during_execution", "is_error": True, "result": "The API returned an error.", "total_cost_usd": 0.001})
    sys.exit(1)
else:
    say({"type": "stream_event", "event": {"type": "content_block_start", "content_block": {"type": "thinking"}}}, 0.6)
    stream_text("I'll read the script first, then shorten the second scene.")
    tool("toolu_read", "Read", {"file_path": "/runs/demo/script.json"}, "\n".join(f"{n:>4}\t line {n}" for n in range(1, 41)))
    tools += 1
    tool("toolu_edit", "Edit", {"file_path": "/runs/demo/script.json",
         "old_string": '"narration": "The moon makes its own light,\nand it shines at night."',
         "new_string": '"narration": "The moon reflects sunlight,\nwhich is why it shines at night."'},
         "The file /runs/demo/script.json has been updated.")
    tools += 1
    command = {"command": "python3 tools/check_script.py script.json", "description": "Check the script"}
    say({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "toolu_bash", "name": "Bash", "input": command}], "usage": USAGE}})
    decision = permission("toolu_bash", "Bash", command)
    tools += 1
    if decision["behavior"] == "allow":
        say({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_bash",
             "content": "script.json: 2 scenes, 61 s\nAll checks passed.", "is_error": False}]}}, 0.2)
        stream_text("Scene 2 now says the moon reflects sunlight, and the script checks pass.")
    else:
        say({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_bash",
             "content": decision.get("message", "denied"), "is_error": True}]}}, 0.2)
        stream_text("Understood: I won't run the check. Scene 2 is updated; tell me what to do next.")
say({"type": "result", "subtype": "success", "is_error": False, "result": "", "session_id": SESSION,
     "total_cost_usd": 0.0041, "duration_ms": round((time.monotonic() - started) * 1000), "num_turns": 2,
     "usage": {"output_tokens": 144}, "modelUsage": {model: {"contextWindow": 1000000, "costUSD": 0.0041}}})
