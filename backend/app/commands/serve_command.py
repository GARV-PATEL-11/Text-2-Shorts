"""`text-2-shorts serve`: the web view (frontend/ and its FastAPI backend, app/web/) on this machine only."""

from __future__ import annotations

import secrets

import uvicorn

from app.web.app import create_app


def handle_serve_command(arguments) -> None:
    token = secrets.token_urlsafe(18)  # only whoever sees this terminal can sign in (H6)
    print(f"Text-2-Shorts: http://127.0.0.1:{arguments.port}/#/signin?token={token}")
    print("  open that link to sign in with Claude Code's account (valid until serve stops; Ctrl+C to stop)")
    uvicorn.run(create_app(sign_in_token=token), host="127.0.0.1", port=arguments.port, log_level="warning")
