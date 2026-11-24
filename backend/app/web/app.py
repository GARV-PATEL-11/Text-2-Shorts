"""The FastAPI app behind `text-2-shorts serve`: the frontend, sign-in through Claude Code, and a JSON API over the
runs whose requests and responses are the Pydantic contracts in schemas/api.py.

    GET    /, /styles.css, /app.js            the frontend
    GET    /api/session                        SessionView
    POST   /api/session                        sign in with Claude Code's account → SessionView (+ cookie)
    DELETE /api/session                        sign out
    GET    /api/runs                           [RunSummary]
    POST   /api/runs                           NewRunInput → RunSummary (201): a run started from the website
    GET    /api/runs/{run}/console             ConsoleView: the console's history, and whether a turn is running
    POST   /api/runs/{run}/console             ConsoleInput → ConsoleEntry lines (NDJSON), one Claude Code turn
    GET    /api/runs/{run}                     RunDetail
    POST   /api/runs/{run}/approve             ApproveInput → CheckpointDecision (409 + problems when blocked)
    POST   /api/runs/{run}/requests            ChangeRequestInput → TrackedRequest (201)
    POST   /api/runs/{run}/requests/{rNNN}     ResolveInput → TrackedRequest
    GET    /media/{run}/{path}                 a file inside that run (Range supported, for seeking)
Everything but the frontend files and /api/session needs a session. Writes go through the same workflow functions as
the CLI. Only 127.0.0.1/localhost is served (no DNS rebinding); writes must be JSON from this page's own origin.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import ValidationError
from schemas.api import (
    ApiError,
    ApproveInput,
    ChangeRequestInput,
    ClaudeAccount,
    ConsoleInput,
    ConsoleView,
    NewRunInput,
    ResolveInput,
    RunDetail,
    RunSummary,
    SessionView,
)
from schemas.interaction import CheckpointDecision, TrackedRequest
from schemas.requirements import Brief
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import (
    DEFAULT_GOOGLE_VOICE,
    DEFAULT_POLLY_ENGINE,
    DEFAULT_POLLY_VOICE,
    REPOSITORY_ROOT,
    RUNS_DIRECTORY,
)
from app.sandbox import KICKOFF_PROMPT
from app.utilities import format_validation_errors
from app.web import auth, console
from app.workflow import run_workspace
from app.workflow.approvals import ApprovalBlocked, approve_checkpoint
from app.workflow.change_requests import load_requests, record_change_request, resolve_request
from app.workflow.run_views import run_detail, run_summary

FRONTEND_DIRECTORY = REPOSITORY_ROOT / "frontend"
FRONTEND_FILES = {"index.html": "text/html", "styles.css": "text/css", "app.js": "text/javascript"}
RUN_NAME = re.compile(r"^\w[\w.-]*$")
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class ApiProblem(Exception):
    """An answer other than success, sent as ApiError JSON."""

    def __init__(self, status: int, error: str, problems: list[str] | None = None):
        super().__init__(error)
        self.status, self.error, self.problems = status, error, problems or []


def create_app(runs_directory: Path = RUNS_DIRECTORY) -> FastAPI:
    app = FastAPI(title="Text-2-Shorts", docs_url=None, redoc_url=None, openapi_url=None)
    sessions = auth.Sessions()

    # ── protections ────────────────────────────────────────────────────────────────────────────────────────
    @app.middleware("http")
    async def same_origin_json_writes(request: Request, call_next):
        if request.method in UNSAFE_METHODS:
            origin, host = request.headers.get("origin"), request.headers.get("host")
            if origin and origin != f"{request.url.scheme}://{host}":
                return problem_response(ApiProblem(403, "changes come only from this page"))
            has_body = request.headers.get("content-length", "0") != "0"
            content_type = request.headers.get("content-type", "").split(";")[0].strip()
            if has_body and content_type != "application/json":
                return problem_response(ApiProblem(415, "send JSON"))
        return await call_next(request)

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])

    @app.exception_handler(ApiProblem)
    async def on_problem(_: Request, problem: ApiProblem):
        return problem_response(problem)

    @app.exception_handler(RequestValidationError)
    async def on_invalid_request(_: Request, invalid: RequestValidationError):
        messages = [f"{'.'.join(str(part) for part in error['loc'][1:])}: {error['msg']}" for error in invalid.errors()]
        return problem_response(ApiProblem(400, "; ".join(messages)))

    @app.exception_handler(ValidationError)
    async def on_invalid_contract(_: Request, invalid: ValidationError):
        return problem_response(ApiProblem(400, "; ".join(format_validation_errors(invalid))))

    # ── who is signed in ───────────────────────────────────────────────────────────────────────────────────
    def signed_in_account(request: Request) -> ClaudeAccount:
        account = sessions.account(request.cookies.get(auth.SESSION_COOKIE))
        if account is None:
            raise ApiProblem(401, "sign in first")
        return account

    def run_folder(run: str) -> Path:
        folder = runs_directory / run
        if not RUN_NAME.match(run) or ".." in run or not folder.is_dir():
            raise ApiProblem(404, f"no run {run}")
        return folder

    @app.get("/api/session", response_model=SessionView)
    def session(request: Request) -> SessionView:
        account = sessions.account(request.cookies.get(auth.SESSION_COOKIE))
        if account:
            return SessionView(signed_in=True, account=account)
        return SessionView(signed_in=False, claude_code_signed_in=auth.claude_code_account() is not None)

    @app.post("/api/session", response_model=SessionView)
    def sign_in(response: Response) -> SessionView:
        account = auth.claude_code_account()
        if account is None:
            raise ApiProblem(
                401,
                "Claude Code on this machine is not signed in. Run `claude auth login` in a terminal, sign in on "
                "claude.ai, then continue here.",
            )
        response.set_cookie(
            auth.SESSION_COOKIE,
            sessions.open(account),
            max_age=auth.SESSION_SECONDS,
            httponly=True,
            samesite="strict",
            path="/",
        )
        return SessionView(signed_in=True, account=account)

    @app.delete("/api/session", response_model=SessionView)
    def sign_out(request: Request, response: Response) -> SessionView:
        sessions.close(request.cookies.get(auth.SESSION_COOKIE))
        response.delete_cookie(auth.SESSION_COOKIE, path="/", httponly=True, samesite="strict")
        return SessionView(signed_in=False)

    # ── runs ───────────────────────────────────────────────────────────────────────────────────────────────
    @app.get("/api/runs", response_model=list[RunSummary], dependencies=[Depends(signed_in_account)])
    def runs() -> list[RunSummary]:
        return [run_summary(run) for run in sorted(runs_directory.iterdir(), reverse=True) if run.is_dir()]

    @app.post("/api/runs", response_model=RunSummary, status_code=201, dependencies=[Depends(signed_in_account)])
    def start_run(new: NewRunInput) -> RunSummary:
        brief = Brief.model_validate(
            {
                **new.model_dump(),
                "objectives": [objective for objective in new.objectives if objective.strip()],
                "voice": DEFAULT_GOOGLE_VOICE if new.tts == "google" else DEFAULT_POLLY_VOICE,
                "engine": DEFAULT_POLLY_ENGINE,
            }
        )
        try:
            return run_summary(run_workspace.create_run(brief, runs_directory))
        except run_workspace.RunNotCreated as problem:
            raise ApiProblem(409, str(problem)) from problem

    @app.get("/api/runs/{run}/console", response_model=ConsoleView, dependencies=[Depends(signed_in_account)])
    def console_view(run: str) -> ConsoleView:
        folder = run_folder(run)
        return ConsoleView(busy=console.is_busy(folder), entries=console.history(folder), kickoff=KICKOFF_PROMPT)

    @app.post("/api/runs/{run}/console", dependencies=[Depends(signed_in_account)])
    def console_turn(run: str, turn: ConsoleInput) -> StreamingResponse:
        folder = run_folder(run)
        lock = console.turn_lock(folder)
        if not lock.__enter__():
            lock.__exit__(None, None, None)
            raise ApiProblem(409, "Claude is still working on the previous message")

        def stream():
            try:
                for entry in console.run_turn(folder, turn.message):
                    yield entry.model_dump_json() + "\n"
            finally:
                lock.__exit__(None, None, None)  # held for the whole turn, released when the stream ends

        return StreamingResponse(stream(), media_type="application/x-ndjson")

    @app.get("/api/runs/{run}", response_model=RunDetail, dependencies=[Depends(signed_in_account)])
    def run(run: str) -> RunDetail:
        return run_detail(run_folder(run))

    @app.post("/api/runs/{run}/approve", response_model=CheckpointDecision, dependencies=[Depends(signed_in_account)])
    def approve(run: str, approval: ApproveInput) -> CheckpointDecision:
        try:
            return approve_checkpoint(run_folder(run), approval.checkpoint, approval.notes, approval.force)
        except ApprovalBlocked as blocked:
            raise ApiProblem(409, str(blocked), blocked.problems) from blocked
        except SystemExit as stopped:  # a workflow gate that stops the command line
            raise ApiProblem(409, str(stopped.code)) from stopped

    @app.post(
        "/api/runs/{run}/requests",
        response_model=TrackedRequest,
        status_code=201,
        dependencies=[Depends(signed_in_account)],
    )
    def request_change(run: str, change: ChangeRequestInput) -> TrackedRequest:
        return record_change_request(run_folder(run), change.target, change.kind, change.text, change.checkpoint)

    @app.post(
        "/api/runs/{run}/requests/{request_id}",
        response_model=TrackedRequest,
        dependencies=[Depends(signed_in_account)],
    )
    def resolve(run: str, request_id: str, resolution: ResolveInput) -> TrackedRequest:
        folder = run_folder(run)
        try:
            resolve_request(folder, request_id, resolution.status, resolution.note)
        except LookupError as missing:
            raise ApiProblem(404, str(missing)) from missing
        return next(request for request in load_requests(folder) if request.id == request_id)

    @app.get("/media/{run}/{path:path}", dependencies=[Depends(signed_in_account)])
    def media(run: str, path: str) -> FileResponse:
        folder = run_folder(run).resolve()
        file = (folder / path).resolve()
        if not path or ".." in Path(path).parts or not file.is_relative_to(folder) or not file.is_file():
            raise ApiProblem(404, "no such file in this run")
        return FileResponse(file)  # answers Range requests, so long videos can be seeked

    # ── the frontend ───────────────────────────────────────────────────────────────────────────────────────
    def frontend_file(name: str) -> FileResponse:
        return FileResponse(
            FRONTEND_DIRECTORY / name, media_type=FRONTEND_FILES[name], headers={"Cache-Control": "no-store"}
        )

    app.get("/", include_in_schema=False)(lambda: frontend_file("index.html"))
    app.get("/styles.css", include_in_schema=False)(lambda: frontend_file("styles.css"))
    app.get("/app.js", include_in_schema=False)(lambda: frontend_file("app.js"))
    return app


def problem_response(problem: ApiProblem) -> JSONResponse:
    return JSONResponse(
        ApiError(error=problem.error, problems=problem.problems).model_dump(), status_code=problem.status
    )
