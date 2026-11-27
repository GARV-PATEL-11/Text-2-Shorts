"""Contracts between the `text-2-shorts` command and the Claude Code session: the `next` batch, and the hook's
input (from Claude Code) and output (shown to the user and given to Claude)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from schemas.base import Strict


class Action(Strict):
    """One thing to do now: write a file, dispatch a subagent, run a command, or ask the user."""

    do: Literal["write", "subagent", "command", "ask_user"]
    what: str
    agent: str | None = None
    target: str | None = None
    file: str | None = None
    read: list[str] = Field(default_factory=list, description="references to read, by path")
    before: str | None = Field(None, description="command to run before the subagent")
    after: str | None = Field(None, description="command to run after the subagent")
    command: str | None = None
    checkpoint: str | None = Field(None, description="ask_user: the checkpoint the user decides (`approve . <it>`)")
    user_text: str | None = Field(None, description="ask_user: what the site shows the person; `what` is Claude's")


class ActionBatch(Strict):
    """What `text-2-shorts next` returns: the stage and its batch of actions (in parallel when `parallel`)."""

    stage: str
    parallel: bool = False
    actions: list[Action] = Field(default_factory=list)


class HookToolInput(BaseModel):
    """The fields of Claude Code's tool_input the hook uses (the rest is ignored)."""

    model_config = ConfigDict(extra="ignore")
    file_path: str | None = None
    command: str | None = None
    description: str | None = None
    subagent_type: str | None = None


class HookEvent(BaseModel):
    """The JSON Claude Code sends a hook on stdin (only the fields used here; the rest is ignored)."""

    model_config = ConfigDict(extra="ignore")
    hook_event_name: str
    cwd: str | None = None
    transcript_path: str | None = None
    tool_name: str | None = None
    tool_input: HookToolInput = Field(default_factory=HookToolInput)
    agent_id: str | None = Field(None, description="set when the call comes from a subagent, absent in the session")


class SessionStartContext(Strict):
    hookEventName: Literal["SessionStart"] = "SessionStart"
    additionalContext: str


class HookOutput(Strict):
    """What the hook prints: a line for the user, and (at session start) context for Claude."""

    systemMessage: str | None = None
    hookSpecificOutput: SessionStartContext | None = None
