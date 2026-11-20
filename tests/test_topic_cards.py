"""Every code example in every topic card must pass the static validator AND render (dry-run) cleanly
on the installed Manim. A card that teaches broken code is worse than no card."""
import re, tempfile
from pathlib import Path
import pytest
from conftest import ROOT, run

TOPICS = ROOT / ".claude/skills/manim-ce-0-20-1-reference/topics"
EXAMPLES = [(p.stem, m.group(1)) for p in sorted(TOPICS.glob("*.md"))
            for m in re.finditer(r"```python\n(.*?)```", p.read_text(), re.S)]

@pytest.mark.parametrize("topic,code", EXAMPLES, ids=[t for t, _ in EXAMPLES])
def test_topic_example(topic, code, api_index, tmp_path):
    m = re.search(r"class (\w+)\(", code)
    if not m:  # clip-file example: validate as a clip file
        fn = re.search(r"def (clip_\d+)\(", code).group(1)
        f = tmp_path / f"{fn}.py"; f.write_text(code)
        rc, out = run("validate_manim_code.py", f, "--index", api_index, "--clip-file")
        assert rc == 0, out
        return
    f = tmp_path / f"{topic.replace('-', '_')}.py"; f.write_text(code)
    cls = m.group(1)
    rc, out = run("validate_manim_code.py", f, "--index", api_index, "--class-name", cls)
    assert rc == 0, out
    rc, out = run("layout_probe.py", f, cls)
    assert rc == 0, out

def test_every_topic_has_example_or_is_table():
    for p in TOPICS.glob("*.md"):
        assert "```python" in p.read_text() or "|---|" in p.read_text(), p.name
