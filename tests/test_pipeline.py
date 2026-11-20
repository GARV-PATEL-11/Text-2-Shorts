from pathlib import Path

from pydantic import BaseModel

from app.pipeline import parse_envelope


class Scene(BaseModel):
    narration: str


class Narration(BaseModel):
    scenes: list[Scene]


def test_parse_envelope():
    ok = {"subtype": "success", "is_error": False}
    assert parse_envelope({**ok, "result": "hi"}, None) == "hi"
    assert parse_envelope({**ok, "result": ""}, None) is None
    assert parse_envelope({**ok, "is_error": True, "result": "hi"}, None) is None
    assert parse_envelope({"subtype": "error_max_turns", "is_error": False, "result": "x"}, None) is None

    good = {"scenes": [{"scene_id": 1, "narration": "Hello."}]}
    assert parse_envelope({**ok, "structured_output": good}, Narration).scenes[0].narration == "Hello."
    assert parse_envelope({**ok, "structured_output": {"scenes": [{"x": 1}]}}, Narration) is None
    assert parse_envelope({**ok, "result": "no structured output"}, Narration) is None


def test_claude_logs_start_and_end_rows_with_token_breakdown(tmp_path, monkeypatch):
    import json, subprocess
    from app import pipeline

    env = {"is_error": False, "subtype": "success", "result": "hi", "total_cost_usd": 0.01, "num_turns": 1,
           "usage": {"input_tokens": 5, "output_tokens": 7, "cache_read_input_tokens": 100,
                     "cache_creation_input_tokens": 20}, "modelUsage": {"claude-haiku-5-5": {}}}
    monkeypatch.setattr(pipeline, "LLM_CACHE", tmp_path / "cache")
    calls = []
    monkeypatch.setattr(pipeline.subprocess, "run",
                        lambda *a, **k: calls.append(1) or subprocess.CompletedProcess(a, 0, json.dumps(env), ""))
    assert pipeline.claude(tmp_path, "refine", "u", "s") == "hi"
    assert pipeline.claude(tmp_path, "refine", "u", "s") == "hi" and len(calls) == 1   # 2nd identical call: cache
    start, end, hit = [json.loads(l) for l in (tmp_path / "log.jsonl").read_text().splitlines()]
    assert hit["cache_hit"] and hit["cost_usd"] == 0
    assert start["event"] == "start" and end["event"] == "end" and start["call_id"] == end["call_id"]
    assert (end["success"], end["type"], end["stage_no"]) == (True, "llm", 1)
    assert (end["input_tokens"], end["output_tokens"], end["cache_read"], end["cache_write"],
            end["total_input_tokens"], end["model_id"]) == (5, 7, 100, 20, 125, "claude-haiku-5-5")


def test_transient_wait_classifies_limits():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from app.pipeline import transient_wait

    now = datetime(2026, 11, 19, 21, 3, tzinfo=ZoneInfo("Asia/Kolkata"))
    msg = "You've hit your 5-hour limit · resets 1:30am (Asia/Kolkata)"
    assert transient_wait(msg, 0, now) == (4 * 3600 + 27 * 60) + 60            # waits until reset + 1 min
    assert transient_wait("API Error: 529 overloaded", 1) == 40
    assert transient_wait("SyntaxError in scene.py", 0) is None
