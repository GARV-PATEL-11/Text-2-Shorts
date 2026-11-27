import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from app.commands import workflow_commands
from app.workflow import critiques, templates

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIRECTORY = REPOSITORY_ROOT / "backend" / "tools"
FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(TOOLS_DIRECTORY))
sys.path.insert(0, str(REPOSITORY_ROOT / "backend" / "schemas"))


@pytest.fixture(scope="session", autouse=True)
def logs_in_a_temporary_folder(tmp_path_factory):
    """Tests never write into artifacts/logs."""
    import faraday_logging

    faraday_logging.LOG_DIRECTORY = tmp_path_factory.mktemp("logs")
    return faraday_logging.LOG_DIRECTORY


@pytest.fixture(autouse=True)
def no_usage_reported_yet(tmp_path_factory, monkeypatch):
    """Tests never read this computer's real Claude usage (~/.cache/text-2-shorts/usage.json)."""
    from app.web import usage

    monkeypatch.setattr(usage, "USAGE_FILE", tmp_path_factory.mktemp("usage") / "usage.json")
    return usage.USAGE_FILE


@pytest.fixture(scope="session", autouse=True)
def runtime_template_in_a_temporary_folder(tmp_path_factory):
    """Tests never write the chosen template into runtime-environment/template/ (subprocesses inherit the setting)."""
    import os

    folder = tmp_path_factory.mktemp("runtime-template")
    os.environ["TEXT_2_SHORTS_RUNTIME_TEMPLATE"] = str(folder)
    return folder


@pytest.fixture(scope="session")
def api_index(tmp_path_factory):
    """Built once per session from the INSTALLED manim (requires manim==0.20.1)."""
    index_path = tmp_path_factory.mktemp("idx") / "index.json"
    subprocess.run(
        [sys.executable, str(TOOLS_DIRECTORY / "build_manim_api_index.py"), "--out", str(index_path)],
        check=True,
        capture_output=True,
    )
    return index_path


def run_tool(tool, *args):
    process = subprocess.run(
        [sys.executable, str(TOOLS_DIRECTORY / tool), *map(str, args)], capture_output=True, text=True, timeout=300
    )
    return process.returncode, process.stdout


# ── a valid run, stage by stage (brief → script → scene plans), for the workflow tests ─────────────────────────


def words(count, offset=0):
    return " ".join(f"word{offset + i}" for i in range(count))


def write_brief(run, **fields):
    import json

    run.mkdir(parents=True, exist_ok=True)
    brief = {
        "requirement": "topic",
        "approach": "custom",
        "minutes": 1,
        "tts": "polly",
        **fields,
    }
    (run / "brief.json").write_text(json.dumps(brief))
    return brief


def script_scene(number, seconds, wpm=150, scene_count=1):
    """s01 is the index scene (previews what the video covers); later scenes teach and are bridged."""
    budget = int(seconds * wpm / 60)
    bridge = "" if number == 1 else words(6, 1000 * number)
    index = number == 1
    return {
        "scene_id": f"s{number:02d}",
        "role": "index" if index else "content",
        "title": f"scene {number}",
        "objective": "o",
        "key_concepts": ["k"],
        "covers": [] if index and scene_count > 1 else [1],
        "previews": [f"s{later:02d}" for later in range(2, scene_count + 1)] if index else [],
        "duration_seconds": seconds,
        "outline_segment": (None if scene_count > 1 else 1) if index else number - 1,
        "bridge_in": bridge,
        "narration": words(budget - len(bridge.split()), 100 * number),
    }


def make_script(*scene_seconds):
    return {
        "title": "T",
        "structure": "linear",
        "objectives": ["understand the topic"],
        "target_wpm": 150,
        "scenes": [
            script_scene(i, seconds, scene_count=len(scene_seconds)) for i, seconds in enumerate(scene_seconds, 1)
        ],
    }


TOPICS = ["Why the question matters", "The core idea"]


def write_requirements(run, topics=TOPICS):
    """Stage 1 after the brief: the request-modifier topic list and the content the outline is built from."""
    run.mkdir(parents=True, exist_ok=True)
    (run / "topics.md").write_text("".join(f"{i}. {topic}\n" for i, topic in enumerate(topics, 1)))
    (run / "content.md").write_text(
        "".join(f"## {topic}\n{topic} explained in two plain sentences.\n\n" for topic in topics)
    )


def visual_plan(seconds):
    """A visual plan that meets VP2 (sentence count), VP3 (empty canvas first) and VP4 (closing sentence)."""
    count = min(max(round(seconds * 0.7), 20), 60)
    middle = [f"Element {i} draws itself and joins the picture." for i in range(1, count - 1)]
    return " ".join(["The scene opens on an empty canvas.", *middle, "The scene ends with every element visible."])


def make_outline(*segment_seconds, types=None):
    """An outline with these segment lengths; `types` are their stages (a custom approach's own by default)."""
    return {
        "meta": {
            "title": "T",
            "topic": "t",
            "total_duration_seconds": sum(segment_seconds),
            "pace": "medium",
            "target_wpm": 150,
            "approach_name": "Custom",
            "approach_style": "lesson",
        },
        "outline": [
            {
                "scene_id": i,
                "segment_type": (types or [f"part_{chr(96 + n)}" for n in range(1, len(segment_seconds) + 1)])[i - 1],
                "title": f"segment {i}",
                "duration_seconds": seconds,
                "talking_points": ["one idea"],
                "visual_plan": visual_plan(seconds),
                "narration_hint": "calm",
                "transition_to_next": None if i == len(segment_seconds) else "What next?",
            }
            for i, seconds in enumerate(segment_seconds, 1)
        ],
    }


def confirm_requirements(run, template="obsidian"):
    """A template chosen and approved (the first stage), then the requirements checkpoint."""

    templates.choose_template(run, template, [])
    approve(run, "template")
    approve(run, "requirements")


def approved_outline(run, script_scene_seconds):
    """Requirements + an outline approved at CP0, shaped for a script with these scene lengths."""
    import json

    write_requirements(run)
    confirm_requirements(run)
    segments = script_scene_seconds[1:] or script_scene_seconds
    (run / "outline.json").write_text(json.dumps(make_outline(*[max(10, int(s)) for s in segments])))
    approve(run, "outline")


def described(names):
    """A continuity state whose objects are described, so a clip can rebuild them when built alone."""
    return {"persistent_objects": list(names), "descriptions": {name: f"Text '{name}' at top_center" for name in names}}


def make_plan(script, number, clip_count=1, exits=None) -> dict[str, Any]:
    """A scene plan whose clips split the script scene's spoken text (bridge + narration) in order."""
    scene = script["scenes"][number - 1]
    spoken = f"{scene['bridge_in']} {scene['narration']}".split()
    size = -(-len(spoken) // clip_count)
    exits = exits or [[] for _ in range(clip_count)]
    clips = [
        {
            "clip_id": f"{scene['scene_id']}c{i:02d}",
            "index": i,
            "objective": "o",
            "narration": " ".join(spoken[(i - 1) * size : i * size]),
            "ssml": "<speak>" + " ".join(spoken[(i - 1) * size : i * size]) + "</speak>",
            "visual_intent": "v",
            "beats": ["b"],
            "entry": described(exits[i - 2] if i > 1 else []),
            "exit": described(exits[i - 1]),
            "est_seconds": 2,
        }
        for i in range(1, clip_count + 1)
    ]
    plan = {
        "scene_id": scene["scene_id"],
        "index": number,
        "title": scene["title"],
        "objective": "o",
        "composition": "title TOP_STRIP, diagram MAIN_CANVAS",
        "transition_in": "" if number == 1 else "recap image",
        "clips": clips,
    }
    return {**plan, "execution_plan": execution_plan_for(plan)}


def execution_plan_for(plan) -> str:
    """A minimal Scene Execution Plan for a plan: every section, one CLIP block per clip (the gate's checks)."""
    from app.workflow.visual_director import SECTIONS

    clips = "\n\n".join(
        f"CLIP {clip['index']}  |  t=0.0s -> t={clip['est_seconds']}s  |  Duration: {clip['est_seconds']}s  |  "
        f'"{clip["objective"]}"\n1. KEY IDEA\n{clip["objective"]}\n2. SPEECH\nt=0.0-1.0s  "{clip["narration"]}"\n'
        f"3. EVENT TIMELINE\n[{clip['index']}.01] t=0.0-1.0s (1.0s) | HOLD | (scene)\n  what   : nothing moves"
        for clip in plan["clips"]
    )
    return "\n\n".join(f"<{tag}>\n{clips if tag == 'CLIP_SEQUENCE' else '-'}\n</{tag}>" for tag in SECTIONS)


def write_json_file(path, data):
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def approve(run, target, force=False):
    import argparse

    workflow_commands.handle_approve_command(argparse.Namespace(run=str(run), target=target, force=force))


def critique_issue(kind, target, tier="basic", criterion=None, aspect=None):
    """One critique issue of that critic's rubric (a basic need unless told otherwise)."""
    return {
        "target": target,
        "criterion": criterion or f"{kind[0].upper()}-{tier[0].upper() if tier != 'great' else 'X'}1",
        "tier": tier,
        "aspect": aspect or {"script": "clarity", "plan": "clarity", "video": "render"}[kind],
        "evidence": "beat 2 says 'it' with two objects on screen",
        "problem": "unclear beat",
        "impact": "the viewer cannot tell which object moves",
        "fix": "name the object",
    }


def write_review(run, stage, findings=()):
    """script_review.json or plan_review.json from the accuracy-reviewer, reviewing the current script or plans."""
    from app.workflow import fingerprints

    reviewed = fingerprints.script_fingerprint(run) if stage == "script" else fingerprints.plans_fingerprint(run)
    write_json_file(run / f"{stage}_review.json", {"reviewed": reviewed, "findings": list(findings)})


def write_critique(run, scene_id, kind, *verdicts):
    """scenes/sNN/<kind>_critique.json (script_critique.json for the script) with one round per verdict; the last
    round reviewed the current version."""

    current = critiques.critique_subject_hash(run, scene_id, kind)
    rounds = [
        {
            "reviewed": current if number == len(verdicts) else f"older-{number}",
            "verdict": verdict,
            "score": 100 if verdict == "pass" else 75,
            "summary": "the round in two sentences",
            "issues": [] if verdict == "pass" else [critique_issue(kind, scene_id)],
        }
        for number, verdict in enumerate(verdicts, 1)
    ]
    path = run / "script_critique.json" if kind == "script" else run / "scenes" / scene_id / f"{kind}_critique.json"
    write_json_file(path, {"rounds": rounds})


def environment_report():
    """A preflight report with nothing missing (what `text-2-shorts new` writes when the machine is ready)."""
    from schemas.requirements import EnvironmentReport

    return EnvironmentReport(
        manim_version="0.20.1",
        python_version="3.12",
        latex=True,
        dvisvgm=True,
        ffmpeg=True,
        bwrap=True,
        socat=True,
        api_index_hash="",
    )
