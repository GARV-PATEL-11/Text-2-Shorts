"""The Claude Code run environment (runtime-environment/): a plugin with skills, agents and hooks, plus the per-run
workspace template."""

import json
import re
from pathlib import Path

from app import config, sandbox, utilities
from app.workflow import run_workspace, status
from conftest import environment_report
from schemas.requirements import Brief
from schemas.run_state import TokenUsage

RUN_ENVIRONMENT = Path(__file__).resolve().parent.parent / "runtime-environment"


def frontmatter(markdown_path: Path) -> dict:
    match = re.match(r"---\n(.*?)\n---\n", markdown_path.read_text(), re.DOTALL)
    assert match, f"{markdown_path} has no frontmatter"
    return dict(line.split(":", 1) for line in match[1].splitlines() if ":" in line)


def test_plugin_layout():
    manifest = json.loads((RUN_ENVIRONMENT / ".claude-plugin" / "plugin.json").read_text())
    assert manifest["name"] == "text-2-shorts-runtime-environment"
    skills = sorted(RUN_ENVIRONMENT.glob("skills/*/SKILL.md"))
    assert skills, "the environment ships at least one skill"
    for skill_path in skills:
        assert frontmatter(skill_path)["name"].strip() == skill_path.parent.name


REFERENCES_DIRECTORY = RUN_ENVIRONMENT / "skills" / "text-2-shorts-produce" / "references"


def test_no_llm_orchestration_in_app():
    app_directory = Path(__file__).resolve().parent.parent / "backend" / "app"
    for module_path in app_directory.rglob("*.py"):
        source = module_path.read_text()
        assert "SYSTEM = " not in source, f"{module_path} holds prompts"
        # The website's console relays the user's own message to the run's Claude Code session, and Home's usage check
        # sends one fixed message that asks for nothing (both in sandbox.py); nowhere else does Python start Claude Code.
        if module_path.name != "sandbox.py":
            assert '"claude", "-p"' not in source, f"{module_path} starts Claude Code with a message"
    sandbox_source = (app_directory / "sandbox.py").read_text()
    assert sandbox_source.count('"claude", "-p"') == 1 and '["claude", "-p", message,' in sandbox_source
    assert not (app_directory / "graph" / "prompts").exists()
    for name in (
        "standards",
        "requirements",
        "topic-list",
        "outline-linear",
        "outline-arc",
        "outline-zoom",
        "script-writing",
        "narrative-structures",
        "script-review",
        "scene-visual-planning",
        "audio-ssml",
        "scene-production",
        "transitions",
    ):
        assert len((REFERENCES_DIRECTORY / f"{name}.md").read_text()) > 300, name
    for agent in (
        "scene-builder",
        "accuracy-reviewer",
        "script-critic",
        "plan-critic",
        "video-critic",
        "audio-refactorer",
        "scene-planner",
    ):
        agent_frontmatter = frontmatter(RUN_ENVIRONMENT / "agents" / f"{agent}.md")
        assert (
            agent_frontmatter["name"].strip() == agent
            and agent_frontmatter["description"].strip()
            and agent_frontmatter["tools"].strip()
        )


def test_standards_reference_matches_the_code():

    text = (REFERENCES_DIRECTORY / "standards.md").read_text()
    assert f"{config.VOICE_LEAD_IN_SECONDS} s" in text and f"{config.END_HOLD_SECONDS} s" in text
    assert "video_settings" in text  # colours, fonts, sizes and background: the template, not a fixed list


def test_provision_creates_the_run_workspace(tmp_path):

    run = tmp_path / "20261120-000000-topic"
    run_workspace.provision_run_workspace(
        run, Brief(requirement="topic", approach="zoom", minutes=1), environment_report()
    )
    assert utilities.read_json(run / "brief.json")["requirement"] == "topic"
    assert utilities.read_json(run / "environment_report.json")["problems"] == []
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

    if not (shutil.which("bwrap") and subprocess.run(["bwrap", "--ro-bind", "/", "/", "true"]).returncode == 0):
        pytest.skip("needs a working bubblewrap")
    run, sibling = tmp_path / "run", tmp_path / "other"
    run.mkdir(), sibling.mkdir()
    probe = (
        f"touch {run}/ok; touch {sibling}/no 2>/dev/null; touch '{config.REPOSITORY_ROOT}/jail_probe' 2>/dev/null; "
        f"touch ~/home_probe && test -f ~/.claude.json && command -v text-2-shorts >/dev/null && echo fine"
    )
    result = subprocess.run(sandbox.build_jail_command(run, ["sh", "-c", probe]), capture_output=True, text=True)
    assert result.stdout.strip() == "fine", result.stderr
    assert (
        (run / "ok").exists() and not (sibling / "no").exists() and not (config.REPOSITORY_ROOT / "jail_probe").exists()
    )
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

    run = tmp_path / "run"
    run_workspace.provision_run_workspace(run, Brief(requirement="t", approach="zoom", minutes=1), environment_report())
    result = run_hook({"hook_event_name": "SessionStart", "cwd": str(run), "transcript_path": "/x/t.jsonl"})
    assert result.returncode == 0 and "next:" in result.stdout and "topics.md does not exist" in result.stdout
    assert utilities.read_json(run / "state.json")["sessions"] == ["/x/t.jsonl"]

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
    utilities.write_json(tmp_path / "state.json", {"approved": {}, "clips": {}, "sessions": [str(transcript)]})
    assert status.sum_session_tokens(tmp_path) == TokenUsage(
        input=7, output=2, cache_read=20, cache_write=10, messages=2
    )


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
        root / "docs" / "PROJECT_STRUCTURE.md",
        root / "docs" / "guides" / "deployment-guide.md",
        root / ".env.example",
        root / "backend" / "tools" / "README.md",
        *root.glob("backend/app/**/*.py"),
        *RUN_ENVIRONMENT.rglob("*.md"),
        *root.glob(".claude/skills/*/SKILL.md"),
        *RUN_ENVIRONMENT.glob("skills/*/SKILL.md"),
    ]
    stale = re.compile(
        r"text-2-shorts (clips|build|outline)\b|re-run (clips|build)|claude -p|backend/app/graph/prompts|"
        r"backend/app/sandbox\.json|CLIP_BUILDER_SYSTEM|STAGES|"
        r"backend/app/(pipeline|clips|check|speech)\.py|app\.(pipeline|clips|speech)\b|backend/app/graph/models|"
        r"(?<![\w.-])env/|Plan\.md|MODULE_SPECS|DEPLOYMENT\.md|SKILLS_ASSESSMENT|"
        r"\bt2s\b|\bT2S_(FPS|PARALLEL|TTS|BACKGROUND|TARGET_CLIP|STOP_AFTER)\b|"
        r"math\.json|math-reviewer|validate \S+ math\b|clip-planning|outline-review|references/brief\.md"
    )
    hits = [f"{doc.relative_to(root)}: {match[0]}" for doc in docs for match in stale.finditer(doc.read_text())]
    assert not hits, hits


# ── final-review fixes ────────────────────────────────────────────────────────


def run_in_jail(tmp_path, script):
    import shutil
    import subprocess

    import pytest

    if not (shutil.which("bwrap") and subprocess.run(["bwrap", "--ro-bind", "/", "/", "true"]).returncode == 0):
        pytest.skip("needs a working bubblewrap")
    run = tmp_path / "run"
    run.mkdir(exist_ok=True)
    return subprocess.run(sandbox.build_jail_command(run, ["sh", "-c", script]), capture_output=True, text=True)


def test_jail_hides_the_rest_of_home_host_processes_and_repo_env(tmp_path):

    siblings = [path.name for path in config.REPOSITORY_ROOT.parent.iterdir()]
    result = run_in_jail(
        tmp_path,
        f"ls -A '{config.REPOSITORY_ROOT.parent}'; echo ---; test -e ~/.ssh && echo SSH; "
        f"ls /proc | grep -c '^[0-9]'; cat '{config.REPOSITORY_ROOT}/.env' 2>/dev/null | wc -c",
    )
    listing, rest = result.stdout.split("---\n")
    assert listing.split() == [config.REPOSITORY_ROOT.name] or len(siblings) == 1  # other projects are not mounted
    lines = rest.split()
    assert "SSH" not in lines
    assert int(lines[0]) < 10  # own PID namespace
    assert lines[1] == "0"  # the repo's .env is blanked


def test_api_index_lives_outside_the_read_only_repo():

    assert (
        config.REPOSITORY_ROOT not in config.API_INDEX_PATH.parents
        and Path.home() / ".cache" in config.API_INDEX_PATH.parents
    )


def test_hook_finds_the_run_from_a_subfolder(tmp_path):

    run = tmp_path / "run"
    run_workspace.provision_run_workspace(run, Brief(requirement="t", approach="zoom", minutes=1), environment_report())
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

    from conftest import approve, approved_outline, make_script, write_brief, write_json_file

    write_brief(tmp_path / "r", objectives=["understand the topic"])
    approved_outline(tmp_path / "r", (30, 30))
    write_json_file(tmp_path / "r" / "script.json", make_script(30, 30))
    write_json_file(tmp_path / "r" / "script_review.json", {"findings": []})
    approve(tmp_path / "r", "script")
    (tmp_path / "r" / "scenes" / "s01").mkdir(parents=True)
    (tmp_path / "r" / "scenes" / "s01" / "plan.json").write_text('{"scene_id": "s01"}')
    assert any("s01 plan:" in step for step in status.next_steps(tmp_path / "r"))
    assert "next:" in status.status_text(tmp_path / "r")


def test_state_updates_are_safe_across_processes(tmp_path):
    import subprocess
    import sys

    code = (
        "import sys; from pathlib import Path; from app.workflow import ledger\n"
        "from schemas.run_state import ClipBuild\n"
        "for k in range(20): ledger.update_state(Path(sys.argv[1]), "
        "lambda s: s.clips.__setitem__(f'{sys.argv[2]}-{k}', ClipBuild(status='READY')))"
    )
    procs = [
        subprocess.Popen(
            [sys.executable, "-c", code, str(tmp_path), f"p{i}"], cwd=RUN_ENVIRONMENT.parent, stderr=subprocess.DEVNULL
        )
        for i in range(16)
    ]
    codes = [process.wait() for process in procs]

    assert codes == [0] * 16 and len(utilities.read_json(tmp_path / "state.json")["clips"]) == 320


def test_skill_scripts_are_the_repo_tools_not_copies():
    scripts = sorted((RUN_ENVIRONMENT / "skills" / "manim-ce-0-20-1-reference" / "scripts").glob("*.py"))
    assert scripts
    for script in scripts:
        target = (RUN_ENVIRONMENT.parent / "backend" / "tools" / script.name).resolve()
        assert script.is_symlink() and script.resolve() == target, script.name


def test_every_skill_and_agent_meets_the_standard():
    root = RUN_ENVIRONMENT.parent
    files = [
        *root.glob(".claude/skills/*/SKILL.md"),
        *RUN_ENVIRONMENT.glob("skills/*/SKILL.md"),
        *RUN_ENVIRONMENT.glob("agents/*.md"),
    ]
    assert len(files) == 10  # 2 runtime-environment skills, 8 subagents (no repo-session skills)
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


def test_outline_and_topic_references_are_generated_from_the_script_prompts_package():
    import sys

    sys.path.insert(0, str(RUN_ENVIRONMENT / "prompts"))
    import export_references
    import script_prompts

    assert "{user_raw_input}" in script_prompts.REQ_MODIFIER_SYSTEM  # the one placeholder the topic prompt keeps
    for name, text in export_references.references().items():  # drift between the package and the references
        assert (REFERENCES_DIRECTORY / name).read_text() == text, (
            f"{name}: run runtime-environment/prompts/export_references.py"
        )


def test_conversation_on_haiku_builders_and_refactorers_on_opus_critics_and_audio_on_sonnet():
    builders = {
        "script-writer",
        "scene-planner",
        "scene-builder",
    }  # build and refactor outline, script, plans, scene code
    reviewers_and_audio = {"script-critic", "plan-critic", "video-critic", "accuracy-reviewer", "audio-refactorer"}
    agents = {path.stem: frontmatter(path) for path in RUN_ENVIRONMENT.glob("agents/*.md")}
    assert set(agents) == builders | reviewers_and_audio
    for name, fields in agents.items():
        expected = config.BUILD_MODEL if name in builders else config.REVIEW_AND_AUDIO_MODEL
        assert (fields["model"].strip(), fields["effort"].strip()) == (expected, "medium"), name
    assert (config.SESSION_MODEL, config.BUILD_MODEL, config.REVIEW_AND_AUDIO_MODEL) == (
        "claude-haiku-5-5",
        "claude-opus-5-5",
        "claude-sonnet-5-5",
    )
    command = sandbox.session_command()  # the session: the user's conversation, requirements, routing
    assert command[command.index("--model") + 1] == config.SESSION_MODEL


def test_every_write_and_command_is_shown_to_the_user(tmp_path):

    run = tmp_path / "run"
    run_workspace.provision_run_workspace(run, Brief(requirement="t", approach="zoom", minutes=1), environment_report())
    (run / "preferences.json").write_text('{"tone": "warm"}')
    result = run_hook(
        {
            "hook_event_name": "PostToolUse",
            "cwd": str(run),
            "tool_name": "Write",
            "tool_input": {"file_path": str(run / "preferences.json")},
        }
    )
    shown = json.loads(result.stdout)["systemMessage"]
    assert result.returncode == 0 and "preferences.json" in shown and "valid" in shown
    result = run_hook(
        {
            "hook_event_name": "PostToolUse",
            "cwd": str(run),
            "tool_name": "Bash",
            "tool_input": {"command": "text-2-shorts voice ."},
        }
    )
    assert "text-2-shorts voice ." in json.loads(result.stdout)["systemMessage"]
    result = run_hook(
        {
            "hook_event_name": "PostToolUse",
            "cwd": str(run),
            "tool_name": "Task",
            "tool_input": {"subagent_type": "scene-builder", "description": "build s01"},
        }
    )
    assert "scene-builder" in json.loads(result.stdout)["systemMessage"]


def test_each_critic_has_a_tiered_rubric_the_validator_accepts():
    """Every rubric row in a critic's agent file is a criterion id its critique rounds may cite."""
    from app.workflow import critiques

    for kind, prefix in critiques.CRITERION_PREFIX.items():
        text = (RUN_ENVIRONMENT / "agents" / f"{critiques.CRITICS[kind]}.md").read_text()
        rows = re.findall(r"^\| ([A-Z]-[A-Z]\d{1,2}) \| ([\w-]+) \|", text, re.MULTILINE)
        ids = [criterion for criterion, _ in rows]
        assert ids and len(ids) == len(set(ids)), kind
        assert {criterion[0] for criterion in ids} == {prefix}, kind
        assert {criterion[2] for criterion in ids} == {"B", "G", "X"}, kind  # basic, good to have, great
        assert {aspect for _, aspect in rows} <= critiques.ASPECTS[kind], kind
    assert (REFERENCES_DIRECTORY / "critique-protocol.md").exists()
