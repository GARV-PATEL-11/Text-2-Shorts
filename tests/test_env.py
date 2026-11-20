"""The Claude Code environment (env/): a plugin with skills, agents and hooks, plus the per-run workspace template."""
import json
import re
from pathlib import Path

ENV = Path(__file__).resolve().parent.parent / "env"


def frontmatter(md: Path) -> dict:
    m = re.match(r"---\n(.*?)\n---\n", md.read_text(), re.S)
    assert m, f"{md} has no frontmatter"
    return dict(line.split(":", 1) for line in m[1].splitlines() if ":" in line)


def test_plugin_layout():
    manifest = json.loads((ENV / ".claude-plugin" / "plugin.json").read_text())
    assert manifest["name"] == "t2s-env"
    skills = sorted(ENV.glob("skills/*/SKILL.md"))
    assert skills, "the environment ships at least one skill"
    for s in skills:
        assert frontmatter(s)["name"].strip() == s.parent.name


REFS = ENV / "skills" / "t2s-produce" / "references"


def test_no_llm_orchestration_in_app():
    app = Path(__file__).resolve().parent.parent / "app"
    for py in app.rglob("*.py"):
        src = py.read_text()
        assert '"claude", "-p"' not in src and "SYSTEM = " not in src, f"{py} still orchestrates or holds prompts"
    assert not (app / "graph" / "prompts").exists()
    for name in ("standards", "brief", "outline-zoom", "outline-arc", "outline-linear", "outline-review", "clip-planning"):
        assert len((REFS / f"{name}.md").read_text()) > 300, name
    for agent in ("clip-builder", "math-reviewer"):
        fm = frontmatter(ENV / "agents" / f"{agent}.md")
        assert fm["name"].strip() == agent and fm["description"].strip() and fm["tools"].strip()
        assert fm["model"].strip() == "sonnet"


def test_standards_reference_matches_the_code():
    from app import clips
    text = (REFS / "standards.md").read_text()
    assert clips.STYLE["background"] in text and f"{clips.LEAD_IN} s" in text and f"{clips.HOLD} s" in text


def test_provision_creates_the_run_workspace(tmp_path):
    from app import pipeline as P
    run = tmp_path / "20261120-000000-topic"
    P.provision(run, {"requirement": "topic", "approach": "zoom", "minutes": 1}, {"problems": []})
    assert P.read_json(run / "brief.json")["requirement"] == "topic"
    assert P.read_json(run / "environment_report.json") == {"problems": []}
    assert (run / "CLAUDE.md").read_text() == (ENV / "workspace" / "CLAUDE.md").read_text()


def test_settings_enable_sandbox_and_deny_secrets():
    s = json.loads((ENV / "settings.json").read_text())
    assert s["sandbox"]["enabled"] and s["sandbox"]["failIfUnavailable"] and not s["sandbox"]["allowUnsandboxedCommands"]
    assert any(".aws" in r for r in s["permissions"]["deny"])


def test_jail_lets_a_session_write_only_its_own_run(tmp_path):
    import shutil, subprocess
    import pytest
    from app import pipeline as P
    if not (shutil.which("bwrap") and subprocess.run(["bwrap", "--ro-bind", "/", "/", "true"]).returncode == 0):
        pytest.skip("needs a working bubblewrap")
    run, sibling = tmp_path / "run", tmp_path / "other"
    run.mkdir(), sibling.mkdir()
    probe = (f"touch {run}/ok; touch {sibling}/no 2>/dev/null; touch '{P.ROOT}/jail_probe' 2>/dev/null; "
             f"touch ~/home_probe && test -f ~/.claude.json && command -v t2s >/dev/null && echo fine")
    out = subprocess.run(P.jail_cmd(run, ["sh", "-c", probe]), capture_output=True, text=True)
    assert out.stdout.strip() == "fine", out.stderr
    assert (run / "ok").exists() and not (sibling / "no").exists() and not (P.ROOT / "jail_probe").exists()
    assert not (Path.home() / "home_probe").exists()          # home writes land in the session's private tmpfs


def run_hook(payload: dict):
    import subprocess, sys
    return subprocess.run([sys.executable, "-m", "app.pipeline", "hook"], input=json.dumps(payload),
                          capture_output=True, text=True, cwd=ENV.parent)


def test_hooks_resume_validate_and_log(tmp_path):
    from app import pipeline as P
    run = tmp_path / "run"
    P.provision(run, {"requirement": "t", "approach": "zoom", "minutes": 1}, {})
    r = run_hook({"hook_event_name": "SessionStart", "cwd": str(run), "transcript_path": "/x/t.jsonl"})
    assert r.returncode == 0 and "next:" in r.stdout and "outline.json does not exist" in r.stdout
    assert P.read_json(run / "state.json")["sessions"] == ["/x/t.jsonl"]

    (run / "scenes" / "s01").mkdir(parents=True)
    (run / "scenes" / "s01" / "plan.json").write_text("{}")
    r = run_hook({"hook_event_name": "PostToolUse", "cwd": str(run), "tool_name": "Write",
                  "tool_input": {"file_path": str(run / "scenes" / "s01" / "plan.json")}})
    assert r.returncode == 2 and "scene_id" in r.stderr                      # errors go back to Claude
    r = run_hook({"hook_event_name": "PostToolUse", "cwd": str(run), "tool_name": "Bash",
                  "tool_input": {"command": "t2s voice ."}})
    assert r.returncode == 0
    rows = [json.loads(l) for l in (run / "log.jsonl").read_text().splitlines()]
    assert [x["tool"] for x in rows] == ["Write", "Bash"] and rows[1]["detail"] == "t2s voice ."


def test_report_sums_session_tokens_once_per_message(tmp_path):
    from app import clips as C, pipeline as P
    t = tmp_path / "s.jsonl"
    msg = lambda i, n: json.dumps({"type": "assistant", "message": {"id": i, "usage": {  # noqa: E731
        "input_tokens": n, "output_tokens": 1, "cache_read_input_tokens": 10, "cache_creation_input_tokens": 5}}})
    t.write_text("\n".join([msg("a", 3), msg("a", 3), msg("b", 4), json.dumps({"type": "user"})]))
    P.write_json(tmp_path / "state.json", {"approved": {}, "clips": {}, "sessions": [str(t)]})
    assert C.session_tokens(tmp_path) == {"input": 7, "output": 2, "cache_read": 20, "cache_write": 10, "messages": 2}


def test_hooks_config_only_calls_real_commands():
    hooks = json.loads((ENV / "hooks" / "hooks.json").read_text())["hooks"]
    commands = [h["command"] for groups in hooks.values() for g in groups for h in g["hooks"]]
    assert commands and all(c.split()[:2] == ["t2s", "hook"] for c in commands)
    skill = (ENV / "skills" / "t2s-produce" / "SKILL.md").read_text()
    for ref in re.findall(r"references/([\w-]+\.md)", skill):
        assert (REFS / ref).exists(), ref
