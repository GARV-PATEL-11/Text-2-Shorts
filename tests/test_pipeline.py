from pathlib import Path

from app.pipeline import Narration, map_outline, mux_args, parse_envelope


def test_parse_envelope():
    ok = {"subtype": "success", "is_error": False}
    assert parse_envelope({**ok, "result": "hi"}, None) == "hi"
    assert parse_envelope({**ok, "result": ""}, None) is None
    assert parse_envelope({**ok, "is_error": True, "result": "hi"}, None) is None
    assert parse_envelope({"subtype": "error_max_budget_usd", "is_error": False, "result": "x"}, None) is None

    good = {"scenes": [{"scene_id": 1, "narration": "Hello."}]}
    assert parse_envelope({**ok, "structured_output": good}, Narration).scenes[0].narration == "Hello."
    assert parse_envelope({**ok, "structured_output": {"scenes": [{"x": 1}]}}, Narration) is None
    assert parse_envelope({**ok, "result": "no structured output"}, Narration) is None


def test_map_outline():
    meta, scenes = map_outline({"meta": {"title": "T"}, "outline": [
        {"scene_id": 2, "title": "A", "visual_plan": "vp", "talking_points": ["p1", "p2"], "duration_seconds": 12},
        {"title": "B", "talking_points": []},
        ]})
    assert meta == {"title": "T"}
    assert scenes[0] == {"scene_id": 2, "title": "A", "description": "vp\np1\np2", "duration_seconds": 12}
    assert scenes[1]["scene_id"] == 2 and scenes[1]["duration_seconds"] == 30  # positional fallback (i + 1)


def test_mux_args_pads_shorter_stream():
    args = mux_args(Path("v.mp4"), Path("a.mp3"), Path("o.mp4"), video_s=10.0, audio_s=12.5)
    assert args[args.index("-t") + 1] == "12.500"
    assert "stop_duration=2.500" in args[args.index("-filter_complex") + 1]

    args = mux_args(Path("v.mp4"), Path("a.mp3"), Path("o.mp4"), video_s=15.0, audio_s=12.5)
    assert args[args.index("-t") + 1] == "15.000"
    assert "stop_duration=0.000" in args[args.index("-filter_complex") + 1]


def test_plan_refine_keeps_progress_on_failure_and_resumes(tmp_path, monkeypatch):
    import argparse, json
    from app import pipeline
    from app.graph.prompts.visual_plan_critic_prompt import CritiqueResult

    d = tmp_path / "scenes" / "001"
    d.mkdir(parents=True)
    (d / "plan.md").write_text("orig")
    (tmp_path / "outline.json").write_text("{}")
    (tmp_path / "narration.json").write_text(json.dumps({"scenes": [{"scene_id": 1, "narration": "n", "audio_seconds": 1}]}))
    monkeypatch.setattr(pipeline, "map_outline", lambda o: ({}, [{"scene_id": 1, "title": "t", "duration_seconds": 1}]))
    calls = []

    def fake(run, stage, *a, **k):  # critic 6 → rewrite → critic hits usage limit
        calls.append(stage)
        if stage == "plan_refactor":
            return "rewrite"
        if len(calls) == 3:
            raise RuntimeError("limit")
        return CritiqueResult(approved=False, score=6 if len(calls) == 1 else 9, critique="c")

    monkeypatch.setattr(pipeline, "claude", fake)
    args = argparse.Namespace(run=str(tmp_path), scenes=None, feedback=None, refine=True, rounds=4)
    pipeline.cmd_plan(args)
    assert (d / "plan.md").read_text() == "rewrite"  # progress kept
    review = json.loads((d / "plan_review.json").read_text())
    assert review["score"] is None and [h["score"] for h in review["history"]] == [6]

    pipeline.cmd_plan(args)  # resume: critic scores the rewrite, no duplicate snapshot
    review = json.loads((d / "plan_review.json").read_text())
    assert review["score"] == 9 and review["history"][0]["version"] == "plan.v2.md"
    assert sorted(p.name for p in d.glob("plan.v*.md")) == ["plan.v1.md", "plan.v2.md"]
