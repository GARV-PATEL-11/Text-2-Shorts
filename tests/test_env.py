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
