import json, sys
from conftest import TOOLS
sys.path.insert(0, str(TOOLS))
from cost_report import summarize

def test_summarize_existing_log_format(tmp_path):
    rows = [  # exactly the fields pipeline.claude() writes today
        {"ts": "t", "stage": "outline", "scene": None, "model": "sonnet", "effort": "high", "attempt": 1, "ok": True,
         "cost_usd": 0.12, "duration_ms": 40000, "cache_read": 0, "cache_write": 9000, "error": None},
        {"ts": "t", "stage": "scene", "scene": 1, "model": "sonnet", "effort": "high", "attempt": 1, "ok": False,
         "cost_usd": 0.9, "duration_ms": 300000, "cache_read": 200000, "cache_write": 30000, "error": "x"},
        {"ts": "t", "stage": "scene", "scene": 1, "model": "sonnet", "effort": "high", "attempt": 2, "ok": True,
         "cost_usd": 0.7, "duration_ms": 250000, "cache_read": 180000, "cache_write": 5000, "error": None}]
    p = tmp_path / "log.jsonl"; p.write_text("\n".join(json.dumps(r) for r in rows))
    r = summarize([p])
    assert r["total_cost_usd"] == 1.72 and r["render_units"] == 1
    assert r["cost_per_render_unit"] == 1.72 and r["render_cost_per_unit"] == 1.6
    assert r["stages"]["scene"]["retries"] == 1 and r["stages"]["scene"]["failed"] == 1
    assert list(r["stages"])[0] == "scene"  # sorted by cost
