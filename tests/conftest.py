import json, subprocess, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
FIX = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(TOOLS)); sys.path.insert(0, str(ROOT / "schemas"))

@pytest.fixture(scope="session")
def api_index(tmp_path_factory):
    """Built once per session from the INSTALLED manim (requires manim==0.20.1)."""
    out = tmp_path_factory.mktemp("idx") / "index.json"
    subprocess.run([sys.executable, str(TOOLS / "build_manim_api_index.py"), "--out", str(out)], check=True,
                   capture_output=True)
    return out

def run(tool, *args):
    p = subprocess.run([sys.executable, str(TOOLS / tool), *map(str, args)], capture_output=True, text=True, timeout=300)
    return p.returncode, p.stdout
