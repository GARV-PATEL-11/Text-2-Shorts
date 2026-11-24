"""Signing in to the web view with the Claude account Claude Code is signed in to on this machine.

There is no password here. Signing in asks Claude Code (`claude auth status --json`) which Claude account this machine
is signed in to; if it is signed in, the web view opens a session for that account. To sign in to Claude itself, the
user runs `claude auth login`, which opens claude.ai in the browser (like "Sign in with Google"). The session is a
random token in an HttpOnly, SameSite=Strict cookie, kept in this server's memory only.
"""

from __future__ import annotations

import secrets
import subprocess
import time

from pydantic import ValidationError
from schemas.api import ClaudeAccount, ClaudeAuthStatus

SESSION_COOKIE = "t2s_session"
SESSION_SECONDS = 24 * 3600


def claude_code_account() -> ClaudeAccount | None:
    """The Claude account Claude Code is signed in to on this machine, or None (signed out, or no Claude Code)."""
    try:
        completed = subprocess.run(["claude", "auth", "status", "--json"], capture_output=True, text=True, timeout=20)
        status = ClaudeAuthStatus.model_validate_json(completed.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired, ValidationError):
        return None
    if not status.loggedIn or not status.email:
        return None
    return ClaudeAccount(
        email=status.email,
        organization=status.orgName or "",
        plan=status.subscriptionType or "",
        method=status.authMethod or "",
    )


class Sessions:
    """Signed-in browsers: token → (account, expiry). In memory: restarting the server signs everyone out."""

    def __init__(self) -> None:
        self.by_token: dict[str, tuple[ClaudeAccount, float]] = {}

    def open(self, account: ClaudeAccount) -> str:
        token = secrets.token_urlsafe(32)
        self.by_token[token] = (account, time.time() + SESSION_SECONDS)
        return token

    def account(self, token: str | None) -> ClaudeAccount | None:
        account, expires = self.by_token.get(token or "", (None, 0.0))
        if account is None or expires < time.time():
            self.by_token.pop(token or "", None)
            return None
        return account

    def close(self, token: str | None) -> None:
        self.by_token.pop(token or "", None)
