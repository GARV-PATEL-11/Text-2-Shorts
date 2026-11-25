import sys as _sys
from pathlib import Path as _Path

# The template modules (backend/templates: video_settings, audio_settings, look_renderer, generate_preview) and the
# run environment's logging (runtime-environment/faraday_logging) are imported by name.
for _directory in ("backend/templates", "runtime-environment"):
    _path = str(_Path(__file__).resolve().parents[2] / _directory)
    if _path not in _sys.path:
        _sys.path.append(_path)
