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
