import sys as _sys
from pathlib import Path as _Path

# The run environment's settings modules (video_settings, audio_settings, generate_preview) are imported by name.
_RUNTIME_ENVIRONMENT = str(_Path(__file__).resolve().parents[2] / "runtime-environment")
if _RUNTIME_ENVIRONMENT not in _sys.path:
    _sys.path.append(_RUNTIME_ENVIRONMENT)
