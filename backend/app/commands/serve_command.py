"""`text-2-shorts serve`: the web view (frontend/ and its FastAPI backend, app/web/) on this machine only."""

from __future__ import annotations

import uvicorn

from app.utilities import cli_quote
from app.web.app import create_app


def handle_serve_command(arguments) -> None:
    print(cli_quote("serve") + "\n")
    print(f"Text-2-Shorts: http://127.0.0.1:{arguments.port}/")
    print("  sign in with Claude Code's account on this computer (Ctrl+C to stop)")
    uvicorn.run(create_app(), host="127.0.0.1", port=arguments.port, log_level="warning")
