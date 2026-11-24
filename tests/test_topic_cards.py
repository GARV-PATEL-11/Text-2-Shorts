"""Every code example in every topic card must pass the static validator AND render (dry-run) cleanly
on the installed Manim. A card that teaches broken code is worse than no card."""

import re

import pytest
from conftest import REPOSITORY_ROOT, run_tool

TOPICS = REPOSITORY_ROOT / "runtime-environment/skills/manim-ce-0-20-1-reference/topics"
EXAMPLES = [
    (topic_path.stem, match.group(1))
    for topic_path in sorted(TOPICS.glob("*.md"))
    for match in re.finditer(r"```python\n(.*?)```", topic_path.read_text(), re.S)
]


def test_topic_cards_are_found():
    assert len(EXAMPLES) >= 10, f"no topic-card examples under {TOPICS}"  # a wrong path must fail, not skip


@pytest.mark.parametrize("topic,code", EXAMPLES, ids=[example_topic for example_topic, _ in EXAMPLES])
def test_topic_example(topic, code, api_index, tmp_path):
    match = re.search(r"class (\w+)\(", code)
    if not match:  # clip-file example: validate as a clip file
        function_name = re.search(r"def (clip_\d+)\(", code).group(1)
        example_path = tmp_path / f"{function_name}.py"
        example_path.write_text(code)
        exit_code, output = run_tool("validate_manim_code.py", example_path, "--index", api_index, "--clip-file")
        assert exit_code == 0, output
        return
    example_path = tmp_path / f"{topic.replace('-', '_')}.py"
    example_path.write_text(code)
    class_name = match.group(1)
    exit_code, output = run_tool(
        "validate_manim_code.py", example_path, "--index", api_index, "--class-name", class_name
    )
    assert exit_code == 0, output
    exit_code, output = run_tool("layout_probe.py", example_path, class_name)
    assert exit_code == 0, output


def test_every_topic_has_example_or_is_table():
    for topic_path in TOPICS.glob("*.md"):
        assert "```python" in topic_path.read_text() or "|---|" in topic_path.read_text(), topic_path.name
