"""test_id_service.py — Unit tests for IDService."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from unittest.mock import patch

from app.core.id_service import _PREFIX, IDService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _use_tmp_counter(tmp_path: Path):
    """Patch _COUNTER_FILE to a temp location so tests don't touch artifacts/."""
    counter_file = tmp_path / "id_counter.json"
    return patch("app.core.id_service._COUNTER_FILE", counter_file)


# ---------------------------------------------------------------------------
# Session IDs
# ---------------------------------------------------------------------------

class TestSessionIDs:

    def test_first_session_id(self, tmp_path: Path) -> None:
        with _use_tmp_counter(tmp_path):
            sid = IDService.next_session_id()
        assert sid == "T2S_VG_00001"

    def test_increments_sequentially(self, tmp_path: Path) -> None:
        with _use_tmp_counter(tmp_path):
            ids = [IDService.next_session_id() for _ in range(5)]
        assert ids == [
            "T2S_VG_00001",
            "T2S_VG_00002",
            "T2S_VG_00003",
            "T2S_VG_00004",
            "T2S_VG_00005",
            ]

    def test_format_prefix(self, tmp_path: Path) -> None:
        with _use_tmp_counter(tmp_path):
            sid = IDService.next_session_id()
        assert sid.startswith(f"{_PREFIX}_")

    def test_five_digit_zero_padding(self, tmp_path: Path) -> None:
        with _use_tmp_counter(tmp_path):
            sid = IDService.next_session_id()
        # last segment must be 5 digits
        assert sid.split("_")[-1].isdigit()
        assert len(sid.split("_")[-1]) == 5

    def test_counter_persists_across_calls(self, tmp_path: Path) -> None:
        counter_file = tmp_path / "id_counter.json"
        with patch("app.core.id_service._COUNTER_FILE", counter_file):
            IDService.next_session_id()
            IDService.next_session_id()
            sid3 = IDService.next_session_id()
        assert sid3 == "T2S_VG_00003"
        data = json.loads(counter_file.read_text())
        assert data["sessions"] == 3


# ---------------------------------------------------------------------------
# Workflow IDs
# ---------------------------------------------------------------------------

class TestWorkflowIDs:

    def test_first_workflow_for_session(self, tmp_path: Path) -> None:
        with _use_tmp_counter(tmp_path):
            wid = IDService.next_workflow_id("T2S_VG_00001")
        assert wid == "T2S_VG_00001_W01"

    def test_second_workflow_for_same_session(self, tmp_path: Path) -> None:
        with _use_tmp_counter(tmp_path):
            IDService.next_workflow_id("T2S_VG_00001")
            wid = IDService.next_workflow_id("T2S_VG_00001")
        assert wid == "T2S_VG_00001_W02"

    def test_independent_counters_per_session(self, tmp_path: Path) -> None:
        with _use_tmp_counter(tmp_path):
            w1 = IDService.next_workflow_id("T2S_VG_00001")
            w2 = IDService.next_workflow_id("T2S_VG_00002")
        assert w1 == "T2S_VG_00001_W01"
        assert w2 == "T2S_VG_00002_W01"

    def test_two_digit_zero_padding(self, tmp_path: Path) -> None:
        with _use_tmp_counter(tmp_path):
            wid = IDService.next_workflow_id("T2S_VG_00001")
        suffix = wid.split("_W")[-1]
        assert suffix.isdigit()
        assert len(suffix) == 2


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------

class TestThreadSafety:

    def test_concurrent_session_ids_are_unique(self, tmp_path: Path) -> None:
        results: list[str] = []
        lock = threading.Lock()

        def _generate() -> None:
            sid = IDService.next_session_id()
            with lock:
                results.append(sid)

        with _use_tmp_counter(tmp_path):
            threads = [threading.Thread(target=_generate) for _ in range(20)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        assert len(results) == 20
        assert len(set(results)) == 20  # all unique


# ---------------------------------------------------------------------------
# peek_session_count
# ---------------------------------------------------------------------------

class TestPeekSessionCount:

    def test_peek_does_not_increment(self, tmp_path: Path) -> None:
        with _use_tmp_counter(tmp_path):
            count_before = IDService.peek_session_count()
            IDService.peek_session_count()
            count_after = IDService.peek_session_count()
        assert count_before == count_after == 0

    def test_peek_reflects_current_count(self, tmp_path: Path) -> None:
        with _use_tmp_counter(tmp_path):
            IDService.next_session_id()
            IDService.next_session_id()
            assert IDService.peek_session_count() == 2
