"""The user's change requests (requests.jsonl): recording, resolving, routing each to the stage that applies it, and
which checkpoints they block."""

from __future__ import annotations

import re
from pathlib import Path

from schemas.interaction import RequestEvent, ResolutionEvent, TrackedRequest
from schemas.session import Action

from app.utilities import now_text, read_jsonl
from app.workflow.ledger import append_jsonl, record_decision


def load_requests(run: Path) -> list[TrackedRequest]:
    """Every change request with its current status (open, applied or declined) and resolution note."""
    requests: dict[str, TrackedRequest] = {}
    for row in read_jsonl(run / "requests.jsonl"):
        if row["event"] == "request":
            event = RequestEvent.model_validate(row)
            requests[event.id] = TrackedRequest.model_validate(event.model_dump(exclude={"event"}))
        else:
            resolution = ResolutionEvent.model_validate(row)
            if resolution.id in requests:
                requests[resolution.id].status = resolution.status
                requests[resolution.id].note = resolution.note
    return list(requests.values())


def open_requests(run: Path) -> list[TrackedRequest]:
    return [request for request in load_requests(run) if request.status == "open"]


def requests_for(run: Path, *targets: str) -> list[TrackedRequest]:
    return [request for request in load_requests(run) if request.target in targets]


def requests_text(requests: list[TrackedRequest]) -> str:
    return "\n".join(f"- {r.id} [{r.target} · {r.kind} · {r.status}] {r.text}" for r in requests) or "none"


def add_request(run: Path, target: str, kind: str, text: str, checkpoint: str | None = None) -> TrackedRequest:
    event = RequestEvent.model_validate(
        {
            "id": f"r{len(load_requests(run)) + 1:03d}",
            "target": target,
            "kind": kind,
            "text": text,
            "checkpoint": checkpoint,
            "created_at": now_text(),
        }
    )
    append_jsonl(run, "requests.jsonl", event)
    return TrackedRequest.model_validate(event.model_dump(exclude={"event"}))


def resolve_request(run: Path, request_id: str, status: str, note: str = "") -> None:
    if request_id not in {request.id for request in load_requests(run)}:
        raise LookupError(f"no change request {request_id}")
    resolution = ResolutionEvent.model_validate(
        {"id": request_id, "status": status, "note": note, "resolved_at": now_text()}
    )
    append_jsonl(run, "requests.jsonl", resolution)


def record_change_request(
    run: Path, target: str, kind: str, text: str, checkpoint: str | None = None
) -> TrackedRequest:
    """A validated change request; raised at a checkpoint, it is also the decision "changes requested" there."""
    request = add_request(run, target, kind, text, checkpoint)
    if checkpoint:
        record_decision(run, checkpoint, "changes_requested", text, [request.id])
    return request


def resolve_clip_requests(run: Path, clip_id: str) -> None:
    """A clip that was rebuilt and accepted has applied the open requests about how it looks."""
    for request in open_requests(run):
        if request.target == clip_id and request.kind != "audio-timing":
            resolve_request(run, request.id, "applied", f"rebuilt and accepted at {now_text()}")


REQUEST_ROUTES = {
    "wording": "change what is said in script.json (CP1 again, then the affected plans and CP2)",
    "accuracy": "correct the claim in script.json or the scene plan (CP1 or CP2 again)",
    "structure": "change outline.json (CP0 again), then the script",
    "visual": "a clip: it is rebuilt with this request in its TASK.md; a scene or plan: edit scenes/sNN/plan.json",
    "audio-timing": "audio-refactorer re-times that scene's SSML, then voice and preview",
    "style": "update preferences.json (or the script's tone) and rebuild what changes",
    "other": "decide with the user where it belongs",
}


def blocking_requests(run: Path, target: str) -> list[str]:
    """Open change requests that must be applied or declined before this checkpoint is approved."""

    def blocks(request: TrackedRequest) -> bool:
        where, kind = request.target, request.kind
        scene = where[:3] if re.match(r"^s\d{2}", where) else None
        if target == "outline":
            return where == "outline" or kind == "structure"
        if target == "script":
            return where == "script" or (scene is not None and kind in ("wording", "accuracy", "structure"))
        if target == "plan":
            return where == "plan" or (scene is not None and len(where) == 3 and kind == "visual")
        if target.startswith("scene:"):
            return scene == target.removeprefix("scene:")
        return target == "final"

    return [
        f"open change request {r.id} ({r.target}, {r.kind}): {r.text} — apply or decline it first"
        for r in open_requests(run)
        if blocks(r)
    ]


def request_route(run: Path, request: TrackedRequest) -> Action | None:
    """The action that applies an open request now, or None when a later stage applies it (or its target does
    not exist yet)."""
    where, kind = request.target, request.kind
    resolve = f" — then `text-2-shorts resolve . {request.id} applied` (or declined, with the user's agreement)"
    what = f"apply {request.id} ({kind}, {where}): {request.text}{resolve}"
    scene = where[:3] if re.match(r"^s\d{2}", where) else None
    if kind == "structure" or where == "outline":
        return Action(do="write", file="outline.json", what=what) if (run / "outline.json").exists() else None
    if kind in ("wording", "accuracy") or where == "script":
        return Action(do="write", file="script.json", what=what) if (run / "script.json").exists() else None
    if kind == "visual":
        if scene and len(where) == 3 and (run / "scenes" / scene / "plan.json").exists():
            return Action(do="subagent", agent="scene-planner", target=scene, what=f"request mode — {what}")
        return None  # a clip: production rebuilds it with the request in its TASK.md and resolves it on accept
    if kind == "audio-timing":
        return Action(do="subagent", agent="audio-refactorer", target=scene, what=what) if scene else None
    if kind == "style":
        return Action(do="write", file="preferences.json", what=what)
    return Action(do="ask_user", what=what)
