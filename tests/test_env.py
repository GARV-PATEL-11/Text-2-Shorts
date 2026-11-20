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
