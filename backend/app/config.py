"""Settings and constants: paths, environment variables, models and effort, the standard video style, timing, render
quality and critique limits. Every tunable value of the `text-2-shorts` command lives here.

Environment variables (read once, after loading the repository's .env):
  TEXT_2_SHORTS_FPS        final frame rate, 60–120 (default 120)
  TEXT_2_SHORTS_PARALLEL   scenes rendered at once by `final` (default 4)
  TEXT_2_SHORTS_TTS        default narration provider for `new`: polly | google
Per-run choices live in the run's template.json (look and sound: backend/templates/video_settings.py and
audio_settings.py) and preferences.json (tone, pauses, quality threshold), not here.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────────────────────────────────────────────
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]  # backend/app/config.py → the repository
BACKEND_DIRECTORY = REPOSITORY_ROOT / "backend"  # backend/app/ (the command), backend/schemas/, backend/tools/
RUN_ENVIRONMENT = REPOSITORY_ROOT / "runtime-environment"  # Claude Code plugin + settings + workspace template
TEMPLATES_DIRECTORY = REPOSITORY_ROOT / "backend" / "templates"  # the template kit, starters, previews, look modules


def runtime_template_directory() -> Path:
    """Where the chosen template is copied for the run environment (runtime-environment/template/; tests move it)."""
    return Path(os.environ.get("TEXT_2_SHORTS_RUNTIME_TEMPLATE") or RUN_ENVIRONMENT / "template")


RUNS_DIRECTORY = REPOSITORY_ROOT / "artifacts" / "runs"  # one workspace per video run (git-ignored)
REPORTS_DIRECTORY = REPOSITORY_ROOT / "artifacts" / "reports"  # reports over every run (mistakes.json/.md)
SCHEMAS_DIRECTORY = BACKEND_DIRECTORY / "schemas"  # read by the run session (--add-dir)
TOOLS_DIRECTORY = BACKEND_DIRECTORY / "tools"  # standalone scripts, also run inside the render jail
SCENE_GATES_PATH = TOOLS_DIRECTORY / "scene_gates.py"  # the ./check gates of one scene's code
SCENE_BUILDER_AGENT_PATH = RUN_ENVIRONMENT / "agents" / "scene-builder.md"
REFERENCES_DIRECTORY = RUN_ENVIRONMENT / "skills" / "text-2-shorts-produce" / "references"
STANDARDS_PATH = REFERENCES_DIRECTORY / "standards.md"
TOPICS_DIRECTORY = RUN_ENVIRONMENT / "skills" / "manim-ce-0-20-1-reference" / "topics"
PYTHON_EXECUTABLE = sys.executable  # the venv interpreter — manim is installed here
USER_CACHE_DIRECTORY = Path.home() / ".cache"

# ── Manim ──────────────────────────────────────────────────────────────────────────────────────────────────────────
MANIM_VERSION = "0.20.1"  # pinned in pyproject.toml
API_INDEX_PATH = USER_CACHE_DIRECTORY / "text-2-shorts" / f"manim_api_{MANIM_VERSION}.json"  # writable in the jail
# the Manim reference, in every clip task (one stable block, so it caches): which names exist, how to write clips
# (PART 9 is this project's harness), what still goes wrong
ALWAYS_LOADED_TOPICS = ["manim-construction-patterns", "manim-vocabulary", "manim-common-mistakes"]

# ── Models (Claude Code) ─────────────────────────────────────────────────────────────────────────────────────────
# Who runs on what (subagents: runtime-environment/agents/*.md frontmatter; a test keeps them equal). All at medium.
# Haiku — the run session: the user's conversation (the website console), refining requirements, routing the batch
#   `next` returns, records. It builds nothing itself.
# Opus — every builder and refactor except audio: script-writer (outline, script), scene-planner (plans),
#   scene-builder (scene code).
# Sonnet — every critic and reviewer (script-, plan-, video-critic, accuracy-reviewer) and audio (audio-refactorer).
SESSION_MODEL = "claude-haiku-5-5"
BUILD_MODEL = "claude-opus-5-5"
REVIEW_AND_AUDIO_MODEL = "claude-sonnet-5-5"
EFFORT = "medium"

# ── Narration defaults for `text-2-shorts new` ───────────────────────────────────────────────────────────────────
DEFAULT_TTS = os.environ.get("TEXT_2_SHORTS_TTS", "polly")  # the provider; the voice itself is the template's

# ── Timing ───────────────────────────────────────────────────────────────────────────────────────────────────────
VOICE_LEAD_IN_SECONDS, END_HOLD_SECONDS = 0.3, 0.8  # picture before the voice starts / after it ends, every clip
WORD_BUDGET_TOLERANCE = 0.25  # spoken words per scene vs duration_seconds × target_wpm / 60
SYNC_TOLERANCE_SECONDS = 0.35  # spoken vs shown time of a beat

# ── Rendering ────────────────────────────────────────────────────────────────────────────────────────────────────
DRAFT_QUALITY = "m"  # Manim -qm: 1280×720 at 30 fps — every draft and preview; only `final` renders 1440p
FINAL_FRAME_RATE = int(os.environ.get("TEXT_2_SHORTS_FPS", "120"))  # final is always 2560×1440 (-qp, 16:9); 60–120
USAGE_GATE_PERCENT = 85  # a Claude usage window this full: every next step waits for the user
MAX_PARALLEL_RENDERS = int(os.environ.get("TEXT_2_SHORTS_PARALLEL", "4"))  # scenes rendered at once

# ── Critiques ────────────────────────────────────────────────────────────────────────────────────────────────────
MAX_CRITIQUE_ROUNDS = 3  # per scene plan and per scene video; the score threshold is a per-run preference
MAX_ATTEMPTS = 3  # failed builds, out-of-sync previews or accuracy ERROR reviews in a row before the user decides
