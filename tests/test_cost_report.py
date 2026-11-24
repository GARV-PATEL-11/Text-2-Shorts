import json
import sys

from conftest import TOOLS_DIRECTORY

sys.path.insert(0, str(TOOLS_DIRECTORY))
from cost_report import summarize


def test_summarize_existing_log_format(tmp_path):
    rows = [  # exactly the fields pipeline.claude() writes today
        {
            "ts": "t",
            "stage": "outline",
            "scene": None,
            "model": "sonnet",
            "effort": "high",
            "attempt": 1,
            "ok": True,
            "cost_usd": 0.12,
            "duration_ms": 40000,
            "cache_read": 0,
            "cache_write": 9000,
            "error": None,
        },
        {
            "ts": "t",
            "stage": "scene",
            "scene": 1,
            "model": "sonnet",
            "effort": "high",
            "attempt": 1,
            "ok": False,
            "cost_usd": 0.9,
            "duration_ms": 300000,
            "cache_read": 200000,
            "cache_write": 30000,
            "error": "x",
        },
        {
            "ts": "t",
            "stage": "scene",
            "scene": 1,
            "model": "sonnet",
            "effort": "high",
            "attempt": 2,
            "ok": True,
            "cost_usd": 0.7,
            "duration_ms": 250000,
            "cache_read": 180000,
            "cache_write": 5000,
            "error": None,
        },
    ]
    log_path = tmp_path / "log.jsonl"
    log_path.write_text("\n".join(json.dumps(row) for row in rows))
    report = summarize([log_path])
    assert report["total_cost_usd"] == 1.72 and report["render_units"] == 1
    assert report["cost_per_render_unit"] == 1.72 and report["render_cost_per_unit"] == 1.6
    assert report["stages"]["scene"]["retries"] == 1 and report["stages"]["scene"]["failed"] == 1
    assert list(report["stages"])[0] == "scene"  # sorted by cost
