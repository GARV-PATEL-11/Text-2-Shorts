import subprocess
import sys
from pathlib import Path
from typing import Any
import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIRECTORY = REPOSITORY_ROOT / "tools"
FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(TOOLS_DIRECTORY))
sys.path.insert(0, str(REPOSITORY_ROOT / "schemas"))


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
        "approach": "zoom",
        "minutes": 1,
        "tts": "polly",
        "voice": "Matthew",
        "engine": "neural",
        "font": None,
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
        "bridge_in": bridge,
        "narration": words(budget - len(bridge.split()), 100 * number),
    }


def make_script(*scene_seconds):
    return {
        "title": "T",
        "structure": "zoom",
        "objectives": ["understand the topic"],
        "target_wpm": 150,
        "scenes": [
            script_scene(i, seconds, scene_count=len(scene_seconds)) for i, seconds in enumerate(scene_seconds, 1)
        ],
    }


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
    return {
        "scene_id": scene["scene_id"],
        "index": number,
        "title": scene["title"],
        "objective": "o",
        "composition": "title top_center, diagram center",
        "transition_in": "" if number == 1 else "recap image",
        "clips": clips,
    }


def write_json_file(path, data):
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def approve(run, target, force=False):
    import argparse

    from app import run_steps

    run_steps.handle_approve_command(argparse.Namespace(run=str(run), target=target, force=force))


def write_critique(run, scene_id, kind, *verdicts):
    """scenes/sNN/<kind>_critique.json with one round per verdict; the last round reviewed the current version."""
    from app import run_steps

    current = run_steps.critique_subject_hash(run, scene_id, kind)
    rounds = [
        {
            "reviewed": current if number == len(verdicts) else f"older-{number}",
            "verdict": verdict,
            "issues": []
            if verdict == "pass"
            else [{"target": scene_id, "aspect": "clarity", "problem": "unclear beat", "fix": "name the object"}],
        }
        for number, verdict in enumerate(verdicts, 1)
    ]
    write_json_file(run / "scenes" / scene_id / f"{kind}_critique.json", {"rounds": rounds})
