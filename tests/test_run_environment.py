"""The Claude Code run environment (run-environment/): a plugin with skills, agents and hooks, plus the per-run
workspace template."""

import json
import re
from pathlib import Path

RUN_ENVIRONMENT = Path(__file__).resolve().parent.parent / "run-environment"


def frontmatter(markdown_path: Path) -> dict:
    match = re.match(r"---\n(.*?)\n---\n", markdown_path.read_text(), re.S)
    assert match, f"{markdown_path} has no frontmatter"
    return dict(line.split(":", 1) for line in match[1].splitlines() if ":" in line)


def test_plugin_layout():
    manifest = json.loads((RUN_ENVIRONMENT / ".claude-plugin" / "plugin.json").read_text())
    assert manifest["name"] == "text-2-shorts-run-environment"
    skills = sorted(RUN_ENVIRONMENT.glob("skills/*/SKILL.md"))
    assert skills, "the environment ships at least one skill"
    for skill_path in skills:
        assert frontmatter(skill_path)["name"].strip() == skill_path.parent.name


REFERENCES_DIRECTORY = RUN_ENVIRONMENT / "skills" / "text-2-shorts-produce" / "references"


def test_no_llm_orchestration_in_app():
    app_directory = Path(__file__).resolve().parent.parent / "app"
    for module_path in app_directory.rglob("*.py"):
        source = module_path.read_text()
        assert '"claude", "-p"' not in source and "SYSTEM = " not in source, (
            f"{module_path} still orchestrates or holds prompts"
        )
    assert not (app_directory / "graph" / "prompts").exists()
    for name in (
        "standards",
        "requirements",
        "script-writing",
        "narrative-structures",
        "script-review",
        "scene-visual-planning",
        "audio-ssml",
        "scene-production",
        "transitions",
    ):
        assert len((REFERENCES_DIRECTORY / f"{name}.md").read_text()) > 300, name
    for agent in ("clip-builder", "accuracy-reviewer", "plan-critic", "video-critic", "audio-refactorer"):
        agent_frontmatter = frontmatter(RUN_ENVIRONMENT / "agents" / f"{agent}.md")
        assert (
            agent_frontmatter["name"].strip() == agent
            and agent_frontmatter["description"].strip()
            and agent_frontmatter["tools"].strip()
        )
        assert agent_frontmatter["model"].strip() == "sonnet"


def test_standards_reference_matches_the_code():
    from app import run_steps

    text = (REFERENCES_DIRECTORY / "standards.md").read_text()
    assert (
        run_steps.VIDEO_STYLE["background"] in text
        and f"{run_steps.VOICE_LEAD_IN_SECONDS} s" in text
        and f"{run_steps.END_HOLD_SECONDS} s" in text
    )


def test_provision_creates_the_run_workspace(tmp_path):
    from app import cli

    run = tmp_path / "20261120-000000-topic"
    cli.provision_run_workspace(run, {"requirement": "topic", "approach": "zoom", "minutes": 1}, {"problems": []})
    assert cli.read_json(run / "brief.json")["requirement"] == "topic"
    assert cli.read_json(run / "environment_report.json") == {"problems": []}
    assert (run / "CLAUDE.md").read_text() == (RUN_ENVIRONMENT / "workspace" / "CLAUDE.md").read_text()


def test_settings_enable_sandbox_and_deny_secrets():
    settings = json.loads((RUN_ENVIRONMENT / "settings.json").read_text())
    assert (
        settings["sandbox"]["enabled"]
        and settings["sandbox"]["failIfUnavailable"]
        and not settings["sandbox"]["allowUnsandboxedCommands"]
    )
    assert any(".aws" in rule for rule in settings["permissions"]["deny"])


def test_jail_lets_a_session_write_only_its_own_run(tmp_path):
    import shutil
    import subprocess
    import pytest
    from app import cli

    if not (shutil.which("bwrap") and subprocess.run(["bwrap", "--ro-bind", "/", "/", "true"]).returncode == 0):
        pytest.skip("needs a working bubblewrap")
    run, sibling = tmp_path / "run", tmp_path / "other"
    run.mkdir(), sibling.mkdir()
    probe = (
        f"touch {run}/ok; touch {sibling}/no 2>/dev/null; touch '{cli.REPOSITORY_ROOT}/jail_probe' 2>/dev/null; "
        f"touch ~/home_probe && test -f ~/.claude.json && command -v text-2-shorts >/dev/null && echo fine"
    )
    result = subprocess.run(cli.build_jail_command(run, ["sh", "-c", probe]), capture_output=True, text=True)
    assert result.stdout.strip() == "fine", result.stderr
    assert (run / "ok").exists() and not (sibling / "no").exists() and not (cli.REPOSITORY_ROOT / "jail_probe").exists()
    assert not (Path.home() / "home_probe").exists()  # home writes land in the session's private tmpfs


def run_hook(payload: dict):
    import subprocess
    import sys

    return subprocess.run(
        [sys.executable, "-m", "app.cli", "hook"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=RUN_ENVIRONMENT.parent,
    )


def test_hooks_resume_validate_and_log(tmp_path):
    from app import cli

    run = tmp_path / "run"
    cli.provision_run_workspace(run, {"requirement": "t", "approach": "zoom", "minutes": 1}, {})
    result = run_hook({"hook_event_name": "SessionStart", "cwd": str(run), "transcript_path": "/x/t.jsonl"})
    assert result.returncode == 0 and "next:" in result.stdout and "script.json does not exist" in result.stdout
    assert cli.read_json(run / "state.json")["sessions"] == ["/x/t.jsonl"]

    (run / "scenes" / "s01").mkdir(parents=True)
    (run / "scenes" / "s01" / "plan.json").write_text("{}")
    result = run_hook(
        {
            "hook_event_name": "PostToolUse",
            "cwd": str(run),
            "tool_name": "Write",
            "tool_input": {"file_path": str(run / "scenes" / "s01" / "plan.json")},
        }
    )
    assert result.returncode == 2 and "CP1" in result.stderr  # errors go back to Claude: no plans before CP1
    result = run_hook(
        {
            "hook_event_name": "PostToolUse",
            "cwd": str(run),
            "tool_name": "Bash",
            "tool_input": {"command": "text-2-shorts voice ."},
        }
    )
    assert result.returncode == 0
    rows = [json.loads(line) for line in (run / "log.jsonl").read_text().splitlines()]
    assert [row["tool"] for row in rows] == ["Write", "Bash"] and rows[1]["detail"] == "text-2-shorts voice ."


def test_report_sums_session_tokens_once_per_message(tmp_path):
    from app import cli, run_steps

    transcript = tmp_path / "s.jsonl"

    def assistant_message(message_id, input_tokens):
        usage = {
            "input_tokens": input_tokens,
            "output_tokens": 1,
            "cache_read_input_tokens": 10,
            "cache_creation_input_tokens": 5,
        }
        return json.dumps({"type": "assistant", "message": {"id": message_id, "usage": usage}})

    transcript.write_text(
        "\n".join(
            [
                assistant_message("a", 3),
                assistant_message("a", 3),
                assistant_message("b", 4),
                json.dumps({"type": "user"}),
            ]
        )
    )
    cli.write_json(tmp_path / "state.json", {"approved": {}, "clips": {}, "sessions": [str(transcript)]})
    assert run_steps.sum_session_tokens(tmp_path) == {
        "input": 7,
        "output": 2,
        "cache_read": 20,
        "cache_write": 10,
        "messages": 2,
    }


def test_hooks_config_only_calls_real_commands():
    hooks = json.loads((RUN_ENVIRONMENT / "hooks" / "hooks.json").read_text())["hooks"]
    commands = [hook["command"] for groups in hooks.values() for group in groups for hook in group["hooks"]]
    assert commands and all(command.split()[:2] == ["text-2-shorts", "hook"] for command in commands)
    skill = (RUN_ENVIRONMENT / "skills" / "text-2-shorts-produce" / "SKILL.md").read_text()
    for reference in re.findall(r"references/([\w-]+\.md)", skill):
        assert (REFERENCES_DIRECTORY / reference).exists(), reference


def test_docs_have_no_stale_commands():
    root = RUN_ENVIRONMENT.parent
    docs = [
        root / "README.md",
        root / "docs" / "deployment-guide.md",
        root / ".env.example",
        root / "tools" / "README.md",
        root / "docs" / "skills-assessment.md",
        *root.glob("app/**/*.py"),
        *RUN_ENVIRONMENT.rglob("*.md"),
        *root.glob(".claude/skills/*/SKILL.md"),
        *RUN_ENVIRONMENT.glob("skills/*/SKILL.md"),
    ]
    stale = re.compile(
        r"text-2-shorts (clips|build|outline)\b|re-run (clips|build)|claude -p|app/graph/prompts|"
        r"app/sandbox\.json|CLIP_BUILDER_SYSTEM|STAGES|"
        r"app/(pipeline|clips|check|speech)\.py|app\.(pipeline|clips|speech)\b|app/graph/models|"
        r"(?<![\w.-])env/|Plan\.md|MODULE_SPECS|DEPLOYMENT\.md|SKILLS_ASSESSMENT|"
        r"\bt2s\b|\bT2S_(FPS|PARALLEL|TTS|BACKGROUND|TARGET_CLIP|STOP_AFTER)\b|"
        r"outline\.json|math\.json|math-reviewer|approve \S+ outline|validate \S+ (outline|math)\b|clip-planning|"
        r"outline-(zoom|arc|linear|review)|references/brief\.md|app/outline_models"
    )
    hits = [f"{doc.relative_to(root)}: {match[0]}" for doc in docs for match in stale.finditer(doc.read_text())]
    assert not hits, hits


# ── final-review fixes ────────────────────────────────────────────────────────


def run_in_jail(tmp_path, script):
    import shutil
    import subprocess
    import pytest
    from app import cli

    if not (shutil.which("bwrap") and subprocess.run(["bwrap", "--ro-bind", "/", "/", "true"]).returncode == 0):
        pytest.skip("needs a working bubblewrap")
    run = tmp_path / "run"
    run.mkdir(exist_ok=True)
    return subprocess.run(cli.build_jail_command(run, ["sh", "-c", script]), capture_output=True, text=True)


def test_jail_hides_the_rest_of_home_host_processes_and_repo_env(tmp_path):
    from app import cli

    siblings = [path.name for path in cli.REPOSITORY_ROOT.parent.iterdir()]
    result = run_in_jail(
        tmp_path,
        f"ls -A '{cli.REPOSITORY_ROOT.parent}'; echo ---; test -e ~/.ssh && echo SSH; "
        f"ls /proc | grep -c '^[0-9]'; cat '{cli.REPOSITORY_ROOT}/.env' 2>/dev/null | wc -c",
    )
    listing, rest = result.stdout.split("---\n")
    assert listing.split() == [cli.REPOSITORY_ROOT.name] or len(siblings) == 1  # other projects are not mounted
    lines = rest.split()
    assert "SSH" not in lines
    assert int(lines[0]) < 10  # own PID namespace
    assert lines[1] == "0"  # the repo's .env is blanked


def test_api_index_lives_outside_the_read_only_repo():
    from app import cli, run_steps

    assert (
        cli.REPOSITORY_ROOT not in run_steps.API_INDEX_PATH.parents
        and Path.home() / ".cache" in run_steps.API_INDEX_PATH.parents
    )


def test_hook_finds_the_run_from_a_subfolder(tmp_path):
    from app import cli

    run = tmp_path / "run"
    cli.provision_run_workspace(run, {"requirement": "t", "approach": "zoom", "minutes": 1}, {})
    (run / "scenes" / "s01").mkdir(parents=True)
    (run / "scenes" / "s01" / "plan.json").write_text("{}")
    result = run_hook(
        {
            "hook_event_name": "PostToolUse",
            "cwd": str(run / "scenes" / "s01"),
            "tool_name": "Write",
            "tool_input": {"file_path": str(run / "scenes" / "s01" / "plan.json")},
        }
    )
    assert result.returncode == 2 and (run / "log.jsonl").exists()


def test_status_survives_a_malformed_plan(tmp_path):
    from app import run_steps

    from conftest import approve, make_script, write_brief, write_json_file

    write_brief(tmp_path / "r", objectives=["understand the topic"])
    write_json_file(tmp_path / "r" / "script.json", make_script(30, 30))
    write_json_file(tmp_path / "r" / "script_review.json", {"findings": []})
    approve(tmp_path / "r", "script")
    (tmp_path / "r" / "scenes" / "s01").mkdir(parents=True)
    (tmp_path / "r" / "scenes" / "s01" / "plan.json").write_text('{"scene_id": "s01"}')
    assert any("s01 plan:" in step for step in run_steps.next_steps(tmp_path / "r"))
    assert "next:" in run_steps.status_text(tmp_path / "r")


def test_state_updates_are_safe_across_processes(tmp_path):
    import subprocess
    import sys

    code = (
        "import sys; from pathlib import Path; from app import run_steps\n"
        "for k in range(20): run_steps.update_state(Path(sys.argv[1]), "
        "lambda s: s['clips'].__setitem__(f'{sys.argv[2]}-{k}', {'status': 'READY'}))"
    )
    procs = [
        subprocess.Popen(
            [sys.executable, "-c", code, str(tmp_path), f"p{i}"], cwd=RUN_ENVIRONMENT.parent, stderr=subprocess.DEVNULL
        )
        for i in range(16)
    ]
    codes = [process.wait() for process in procs]
    from app import cli

    assert codes == [0] * 16 and len(cli.read_json(tmp_path / "state.json")["clips"]) == 320


def test_skill_scripts_are_the_repo_tools_not_copies():
    scripts = sorted((RUN_ENVIRONMENT / "skills" / "manim-ce-0-20-1-reference" / "scripts").glob("*.py"))
    assert scripts
    for script in scripts:
        assert script.is_symlink() and script.resolve() == (RUN_ENVIRONMENT.parent / "tools" / script.name).resolve(), (
            script.name
        )


def test_every_skill_and_agent_meets_the_standard():
    root = RUN_ENVIRONMENT.parent
    files = [
        *root.glob(".claude/skills/*/SKILL.md"),
        *RUN_ENVIRONMENT.glob("skills/*/SKILL.md"),
        *RUN_ENVIRONMENT.glob("agents/*.md"),
    ]
    assert len(files) == 10  # 3 repo skills, 2 run-environment skills, 5 subagents
    for path in files:
        desc = frontmatter(path)["description"].strip()
        assert desc.startswith("Use when") and len(desc) <= 500, f"{path}: {desc[:60]}"
        body = path.read_text().split("---", 2)[2]
        assert len(body.split()) <= 650, f"{path}: {len(body.split())} words"


def test_run_environment_is_not_gitignored():
    import subprocess

    files = [
        str(path.relative_to(RUN_ENVIRONMENT.parent))
        for path in RUN_ENVIRONMENT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    ]
    ignored = subprocess.run(
        ["git", "check-ignore", *files], cwd=RUN_ENVIRONMENT.parent, capture_output=True, text=True
    ).stdout
    assert not ignored.strip(), f"git ignores parts of the environment:\n{ignored}"


def test_the_command_is_named_after_the_project():
    import tomllib

    pyproject = tomllib.loads((RUN_ENVIRONMENT.parent / "pyproject.toml").read_text())
    assert pyproject["project"]["scripts"] == {"text-2-shorts": "app.cli:main"}


def test_the_workflow_skill_lists_every_reference_by_path():
    skill = (RUN_ENVIRONMENT / "skills" / "text-2-shorts-produce" / "SKILL.md").read_text()
    for reference in sorted(REFERENCES_DIRECTORY.glob("*.md")):
        assert f"references/{reference.name}" in skill, reference.name
