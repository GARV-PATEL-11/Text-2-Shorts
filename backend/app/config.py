"""Settings and constants: paths, environment variables, models and effort, the standard video style, timing, render
quality and critique limits. Every tunable value of the `text-2-shorts` command lives here.

Environment variables (read once, after loading the repository's .env):
  TEXT_2_SHORTS_FPS        final frame rate, 60–120 (default 120)
  TEXT_2_SHORTS_PARALLEL   scenes rendered at once by `final` (default 4)
  TEXT_2_SHORTS_TTS        default narration provider for `new`: polly | google
  POLLY_ENGINE, POLLY_VOICE, GOOGLE_VOICE   default voice settings for `new`
Per-run choices (palette, font, voice rate, quality threshold, template) live in the run's preferences.json and
template.json, not here.
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
RUNS_DIRECTORY = REPOSITORY_ROOT / "artifacts" / "runs"  # one workspace per video run (git-ignored)
SCHEMAS_DIRECTORY = BACKEND_DIRECTORY / "schemas"  # read by the run session (--add-dir)
TOOLS_DIRECTORY = BACKEND_DIRECTORY / "tools"  # standalone scripts, also run inside the render jail
CLIP_GATES_PATH = TOOLS_DIRECTORY / "clip_gates.py"  # the ./check gates of one clip
TEMPLATES_DIRECTORY = RUN_ENVIRONMENT / "templates"  # starter video templates
CLIP_BUILDER_AGENT_PATH = RUN_ENVIRONMENT / "agents" / "clip-builder.md"
REFERENCES_DIRECTORY = RUN_ENVIRONMENT / "skills" / "text-2-shorts-produce" / "references"
STANDARDS_PATH = REFERENCES_DIRECTORY / "standards.md"
TOPICS_DIRECTORY = RUN_ENVIRONMENT / "skills" / "manim-ce-0-20-1-reference" / "topics"
PYTHON_EXECUTABLE = sys.executable  # the venv interpreter — manim is installed here
USER_CACHE_DIRECTORY = Path.home() / ".cache"

# ── Manim ──────────────────────────────────────────────────────────────────────────────────────────────────────────
MANIM_VERSION = "0.20.1"  # pinned in pyproject.toml
API_INDEX_PATH = USER_CACHE_DIRECTORY / "text-2-shorts" / f"manim_api_{MANIM_VERSION}.json"  # writable in the jail
ALWAYS_LOADED_TOPICS = ["clip-structure", "timing-and-sync", "positioning-layout"]  # topic cards in every task

# ── Models (Claude Code) ─────────────────────────────────────────────────────────────────────────────────────────
# Visual planning and code generation (refactoring included) run on Opus — the scene-planner and clip-builder
# subagents (runtime-environment/agents/*.md frontmatter); the run session and every other subagent on Sonnet. All at
# medium effort.
SESSION_MODEL, PLANNING_AND_CODE_MODEL, EFFORT = "claude-sonnet-5-5", "claude-opus-5-5", "medium"

# ── Narration defaults for `text-2-shorts new` ───────────────────────────────────────────────────────────────────
DEFAULT_TTS = os.environ.get("TEXT_2_SHORTS_TTS", "polly")
DEFAULT_POLLY_ENGINE = os.environ.get("POLLY_ENGINE", "neural")
DEFAULT_POLLY_VOICE = os.environ.get("POLLY_VOICE", "Matthew")
DEFAULT_GOOGLE_VOICE = os.environ.get("GOOGLE_VOICE", "en-US-Neural2-D")

# ── Video style and timing ───────────────────────────────────────────────────────────────────────────────────────
VIDEO_STYLE = {  # the standard look; preferences.json, then template.json, override it
    "background": "#0e2733",
    "text": "WHITE",
    "focus": "YELLOW",
    "given": "BLUE",
    "derived": "GREEN",
    "warning": "RED",
    "secondary": "GREY_B",
}
VOICE_LEAD_IN_SECONDS, END_HOLD_SECONDS = 0.3, 0.8  # picture before the voice starts / after it ends, every clip
WORD_BUDGET_TOLERANCE = 0.25  # spoken words per scene vs duration_seconds × target_wpm / 60
SYNC_TOLERANCE_SECONDS = 0.35  # spoken vs shown time of a beat

# ── Rendering ────────────────────────────────────────────────────────────────────────────────────────────────────
DRAFT_QUALITY = "m"  # Manim -qm: 1280×720 at 30 fps — every draft and preview; only `final` renders 1440p
FINAL_FRAME_RATE = int(os.environ.get("TEXT_2_SHORTS_FPS", "120"))  # final is always 2560×1440 (-qp, 16:9); 60–120
MAX_PARALLEL_RENDERS = int(os.environ.get("TEXT_2_SHORTS_PARALLEL", "4"))  # scenes rendered at once

# ── Critiques ────────────────────────────────────────────────────────────────────────────────────────────────────
MAX_CRITIQUE_ROUNDS = 3  # per scene plan and per scene video; the score threshold is a per-run preference
