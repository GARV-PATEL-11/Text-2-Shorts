import subprocess
import sys
from pathlib import Path
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
