"""The FastAPI app behind `text-2-shorts serve`: the frontend, sign-in through Claude Code, and a JSON API over the
runs whose requests and responses are the Pydantic contracts in schemas/api.py.

    GET    /, /assets/*                        the frontend (React, built into frontend/dist/)
    GET    /api/session                        SessionView
    POST   /api/session                        sign in with Claude Code's account → SessionView (+ cookie)
    DELETE /api/session                        sign out
    GET    /api/runs                           [RunSummary]
    POST   /api/runs                           NewRunInput → RunSummary (201): a run started from the website
    PATCH  /api/runs/{run}                     RenameInput → RunSummary: a new name (files and id unchanged)
    POST   /api/runs/{run}/duplicate           → RunSummary (201): a new run with its brief and template
    DELETE /api/runs/{run}                     moves it to the runs folder's .trash/ (recoverable)
    GET    /api/profile                        ProfileView: the account, the name you go by, runs and net spend
    PUT    /api/profile                        ProfileInput → ProfileView (kept in the runs folder's .profile.json)
    GET    /api/drafts                         [Draft]: Start a Run as far as the user got, newest first
    PUT    /api/drafts/{id}                    DraftInput → Draft: saved as the user goes
    DELETE /api/drafts/{id}                    the draft is gone (started, or discarded)
    GET    /api/runs/{run}/console             ConsoleView: the console's history, and whether a turn is running
    POST   /api/runs/{run}/console             ConsoleInput → ConsoleEntry lines (NDJSON), one Claude Code turn
    GET    /api/runs/{run}                     RunDetail
    POST   /api/runs/{run}/approve             ApproveInput → CheckpointDecision (409 + problems when blocked)
    POST   /api/runs/{run}/requests            ChangeRequestInput → TrackedRequest (201)
    POST   /api/runs/{run}/requests/{rNNN}     ResolveInput → TrackedRequest
    GET    /api/look                           LookCatalogue: starter templates, every element and its options
    GET    /api/runs/{run}/look                LookView: the run's look and sound (the default until saved)
    POST   /api/runs/{run}/look                LookInput → LookView: template.json (409 + problems when unusable)
    POST   /api/runs/{run}/look/still          LookInput → LookStill: the whole look as one frame, before saving
    POST   /api/runs/{run}/look/voice          LookInput → VoiceSample: hear the voice before saving
    GET    /previews/starters/{name}.webp      a starter template as one frame at 2560×1440
    POST   /api/runs/{run}/reshuffle           ReshuffleInput → ReshuffleView: the optional last stage (apply re-keys clips)
    POST   /api/look/still                     LookInput → LookStill: the whole look as one frame, without a run
    POST   /api/look/options                   LookOptionsInput → every option of an element, drawn in the user's look
    GET    /media/{run}/{path}                 a file inside that run (Range supported, for seeking)
Everything but the frontend files and /api/session needs a session. Writes go through the same workflow functions as
the CLI. Only 127.0.0.1/localhost is served (no DNS rebinding); writes must be JSON from this page's own origin.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

import faraday_logging
import generate_preview
from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import ValidationError
from schemas.api import (
    ApiError,
    ApproveInput,
    BrowserLogBatch,
    ChangeRequestInput,
    ClaudeAccount,
    ConsoleInput,
    ConsoleSettingsInput,
    ConsoleView,
    Draft,
    DraftInput,
    LookCatalogue,
    LookInput,
    LookOptionPicture,
    LookOptionPictures,
    LookOptionsInput,
    LookStill,
    LookView,
    NewRunInput,
    PermissionAnswer,
    PollyVoice,
    ProfileInput,
    ProfileView,
    RenameInput,
    ReshuffleChange,
    ReshuffleInput,
    ReshuffleView,
    ResolveInput,
    RunDetail,
    RunSummary,
    SessionView,
    UsageView,
    VoiceList,
    VoicePreviewInput,
    VoiceSample,
)
from schemas.interaction import CheckpointDecision, TrackedRequest
from schemas.requirements import Brief
from schemas.run_state import ConsoleSettings
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import REPOSITORY_ROOT, RUN_ENVIRONMENT, RUNS_DIRECTORY, SESSION_MODEL
from app.sandbox import KICKOFF_PROMPT
from app.utilities import content_hash, format_validation_errors, now_text, read_json, write_atomic
from app.web import auth, console, console_permissions, usage, voices
from app.workflow import reshuffle, run_workspace, templates
from app.workflow.approvals import ApprovalBlocked, approve_checkpoint
from app.workflow.artifacts import load_brief
from app.workflow.change_requests import load_requests, record_change_request, resolve_request
from app.workflow.ledger import load_state, update_state
from app.workflow.people_wording import people_text
from app.workflow.run_views import run_detail, run_summary

FRONTEND_DIRECTORY = REPOSITORY_ROOT / "frontend" / "dist"  # the React build: `npm ci && npm run build` in frontend/
ASSET_NAME = re.compile(r"^[\w.-]+\.(js|css|woff2?|svg|png|webp)$")
RUN_NAME = re.compile(r"^\w[\w.-]*$")
DRAFT_ID = re.compile(r"^[0-9a-f-]{36}$")
VOICE_SAMPLE = (
    "Here is how your narrator will sound. Square the short sides, add them, and you get the long side squared."
)
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class ApiProblem(Exception):
    """An answer other than success, sent as ApiError JSON."""

    def __init__(self, status: int, error: str, problems: list[str] | None = None):
        super().__init__(error)
        self.status, self.error, self.problems = status, error, problems or []


log = logging.getLogger("app.web")
QUIET = ("/assets/", "/previews/", "/media/")
BROWSER_LOGS_PER_MINUTE = 200  # static files: logged at DEBUG only


@contextmanager
def kept_only_if_set_up(folder: Path):
    """The steps after a new run's folder is made: if any fails, the half-made run is removed (it holds nothing the
    user made yet) and the error says why, instead of an orphan run and a bare 500."""
    try:
        yield
    except (Exception, SystemExit) as error:
        shutil.rmtree(folder, ignore_errors=True)
        log.exception("run %s removed: setting it up failed", folder.name)
        raise ApiProblem(500, "The run could not be set up, so nothing was kept. Try again.") from error


def create_app(runs_directory: Path = RUNS_DIRECTORY) -> FastAPI:
    """The website and its API. Signing in uses the Claude account Claude Code is signed in to on this computer."""
    app = FastAPI(title="Text-2-Shorts", docs_url=None, redoc_url=None, openapi_url=None)
    sessions = auth.Sessions()
    browser = faraday_logging.channel("frontend")
    runs_directory.mkdir(parents=True, exist_ok=True)  # a fresh clone has no artifacts/runs yet
    log.info("serving runs from %s", runs_directory)

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log.exception("%s %s failed", request.method, request.url.path)
            raise
        quiet = request.url.path.startswith(QUIET) and response.status_code < 400
        level = logging.ERROR if response.status_code >= 500 else logging.DEBUG if quiet else logging.INFO
        log.log(level, "%s %s → %s (%.0f ms)", request.method, request.url.path, response.status_code,
                (time.perf_counter() - started) * 1000)  # fmt: skip
        return response

    # ── protections ────────────────────────────────────────────────────────────────────────────────────────
    @app.middleware("http")
    async def same_origin_json_writes(request: Request, call_next):
        if request.method in UNSAFE_METHODS:
            origin, host = request.headers.get("origin"), request.headers.get("host")
            if origin and origin != f"{request.url.scheme}://{host}":
                return problem_response(
                    ApiProblem(403, "This request did not come from the Faraday page. Reload the page and try again.")
                )
            has_body = request.headers.get("content-length", "0") != "0"
            content_type = request.headers.get("content-type", "").split(";")[0].strip()
            if has_body and content_type != "application/json":
                return problem_response(ApiProblem(415, "send JSON"))
        return await call_next(request)

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])

    @app.exception_handler(ApiProblem)
    async def on_problem(request: Request, problem: ApiProblem):
        (log.error if problem.status >= 500 else log.warning)(
            "%s %s: %s %s%s", request.method, request.url.path, problem.status, problem.error,
            f" — {'; '.join(problem.problems)[:1500]}" if problem.problems else "",
            exc_info=problem.__cause__,  # the raw reason behind the plain sentence the site shows
        )  # fmt: skip
        return problem_response(problem)

    @app.exception_handler(RequestValidationError)
    async def on_invalid_request(request: Request, invalid: RequestValidationError):
        log.warning(
            "%s %s: 400 %s", request.method, request.url.path, invalid.errors()[:5]
        )  # the raw form, for the log
        return problem_response(ApiProblem(400, plain_field_errors(invalid.errors(), skip=1)))

    @app.exception_handler(ValidationError)
    async def on_invalid_contract(request: Request, invalid: ValidationError):
        message = "; ".join(format_validation_errors(invalid))
        log.warning("%s %s: 400 %s", request.method, request.url.path, message[:1500], exc_info=invalid)  # M16
        return problem_response(ApiProblem(400, plain_field_errors(invalid.errors())))

    @app.exception_handler(Exception)
    async def on_unexpected(_: Request, error: Exception):
        """Anything else: a plain answer; the type, message and traceback are in the request log, never sent (M16)."""
        return problem_response(
            ApiProblem(
                500, "Something went wrong on this computer. Try again; if it keeps happening, see the log file."
            )
        )

    # ── who is signed in ───────────────────────────────────────────────────────────────────────────────────
    def signed_in_account(request: Request) -> ClaudeAccount:
        account = sessions.account(request.cookies.get(auth.SESSION_COOKIE))
        if account is None:
            raise ApiProblem(401, "Sign in to continue. Your sign-in may have expired or Faraday may have restarted.")
        return account

    def run_folder(run: str) -> Path:
        folder = runs_directory / run
        if not RUN_NAME.match(run) or ".." in run or not folder.is_dir():
            raise ApiProblem(404, "This run no longer exists. It may have been deleted.")
        return folder

    log_budget = {"minute": 0, "left": 0}

    def one_line(text: str) -> str:  # a report is one log line: it can never forge another (L5)
        return re.sub(r"[\x00-\x1f]+", " ⏎ ", text)

    @app.post("/api/logs", status_code=204)
    def browser_logs(batch: BrowserLogBatch) -> Response:
        """What the browser reports, into frontend.log (no session needed: the sign-in page reports too), at most
        BROWSER_LOGS_PER_MINUTE lines a minute."""
        levels = {"debug": logging.DEBUG, "info": logging.INFO, "warn": logging.WARNING, "error": logging.ERROR}
        minute = int(time.time() // 60)
        if log_budget["minute"] != minute:
            log_budget.update(minute=minute, left=BROWSER_LOGS_PER_MINUTE)
        for entry in batch.entries[: max(log_budget["left"], 0)]:
            browser.log(
                levels[entry.level], "%s%s%s", f"[{one_line(entry.page)}] " if entry.page else "",
                one_line(entry.message), f" — {one_line(entry.details)}" if entry.details else "",
            )  # fmt: skip
        log_budget["left"] -= len(batch.entries)
        return Response(status_code=204)

    claude_code = {"checked": 0.0, "signed_in": False}

    def claude_code_signed_in() -> bool:
        """`claude auth status` at most every 30 s: the sign-in page polls this (L5)."""
        if time.monotonic() - claude_code["checked"] > 30:
            claude_code.update(checked=time.monotonic(), signed_in=auth.claude_code_account() is not None)
        return claude_code["signed_in"]

    @app.get("/api/session", response_model=SessionView)
    def session(request: Request) -> SessionView:
        account = sessions.account(request.cookies.get(auth.SESSION_COOKIE))
        if account:
            return SessionView(signed_in=True, account=account)
        return SessionView(signed_in=False, claude_code_signed_in=claude_code_signed_in())

    @app.post("/api/session", response_model=SessionView)
    def sign_in(request: Request, response: Response) -> SessionView:
        account = auth.claude_code_account()
        if account is None:
            raise ApiProblem(
                401,
                "Claude Code Is Not Signed In. Sign in through Claude Code on this computer, then try again.",
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

    @app.get("/api/usage", response_model=UsageView)
    def usage_limits(request: Request) -> UsageView:
        return usage.latest(signed_in_account(request).plan)

    @app.post("/api/usage", response_model=UsageView)
    def check_usage_limits(request: Request) -> UsageView:
        """Asks Claude Code for fresh numbers (a one-line Haiku turn), then answers as GET does."""
        plan = signed_in_account(request).plan
        usage.check()
        return usage.latest(plan)

    # ── runs ───────────────────────────────────────────────────────────────────────────────────────────────
    @app.get("/api/runs", response_model=list[RunSummary], dependencies=[Depends(signed_in_account)])
    def runs() -> list[RunSummary]:
        summaries = []
        for run in sorted(runs_directory.iterdir(), reverse=True):
            if not run.is_dir() or run.name.startswith("."):  # .drafts, .trash
                continue
            try:
                summaries.append(run_summary(run))
            except Exception:  # one run that cannot be read (or vanished mid-poll) never hides the others
                log.exception("run list: skipped %s", run.name)
        return summaries

    @app.post("/api/runs", response_model=RunSummary, status_code=201)
    def start_run(new: NewRunInput, account: ClaudeAccount = Depends(signed_in_account)) -> RunSummary:
        """A new run; with `look`, its first stage (the template) is saved and approved as the user chose it."""
        brief = Brief.model_validate(
            {
                **new.model_dump(exclude={"look", "name"}),
                "objectives": [objective for objective in new.objectives if objective.strip()],
            }
        )
        template = None
        if new.look:  # checked before anything is created: a refused look leaves no half-made run
            try:
                template = templates.build_template(new.look.template, new.look.elements, new.look.custom, {})
            except FileNotFoundError as unknown:
                raise ApiProblem(404, "That starter look is not available. Choose another.") from unknown
            if problems := templates.video_settings.problems(template):
                raise ApiProblem(409, "This Look and Sound cannot be used yet.", problems)
        try:
            folder = run_workspace.create_run(brief, runs_directory)
        except run_workspace.RunNotCreated as problem:
            raise ApiProblem(409, str(problem)) from problem
        with kept_only_if_set_up(folder):
            if new.name.strip():
                update_state(folder, lambda state: setattr(state, "name", new.name.strip()))
            if template:
                templates.save_template(folder, template)
                approve_checkpoint(folder, "template", "chosen in Start a Run", by=account.email)
            return run_summary(folder)

    @app.patch("/api/runs/{run}", response_model=RunSummary, dependencies=[Depends(signed_in_account)])
    def rename_run(run: str, rename: RenameInput) -> RunSummary:
        folder = run_folder(run)
        update_state(folder, lambda state: setattr(state, "name", rename.name.strip()))
        return run_summary(folder)

    @app.post("/api/runs/{run}/duplicate", response_model=RunSummary, status_code=201)
    def duplicate_run(run: str, account: ClaudeAccount = Depends(signed_in_account)) -> RunSummary:
        """A new run from this one's brief and look (and preferences): its own folder, nothing produced yet."""
        source = run_folder(run)
        brief = load_brief(source)
        if brief is None:
            raise ApiProblem(409, "This run cannot be duplicated because its Requirements cannot be read.")
        try:
            folder = run_workspace.create_run(brief, runs_directory)
        except run_workspace.RunNotCreated as problem:
            raise ApiProblem(409, str(problem)) from problem
        with kept_only_if_set_up(folder):
            for name in ("preferences.json", "template.json"):
                if (source / name).exists():
                    (folder / name).write_text((source / name).read_text())
            name = f"Copy of {run_summary(source).name}"[:120]
            update_state(folder, lambda state: setattr(state, "name", name))
            if (folder / "template.json").exists() and not templates.validate_template(folder):
                approve_checkpoint(folder, "template", f"copied from {source.name}", by=account.email)
            return run_summary(folder)

    @app.delete("/api/runs/{run}", status_code=204, dependencies=[Depends(signed_in_account)])
    def delete_run(run: str) -> Response:
        """Not deleted for good: the folder moves to .trash/ in the runs folder, where it can be moved back."""
        folder = run_folder(run)
        with console.turn_lock(folder) as free:  # held during the move: no turn can start on a run being moved
            if not free:
                raise ApiProblem(409, "Claude is still working on this run. Wait for it to finish, then delete it.")
            trash = runs_directory / ".trash"
            trash.mkdir(exist_ok=True)
            target, copy = trash / folder.name, 1
            while target.exists():  # deleted before under the same name: keep both
                copy += 1
                target = trash / f"{folder.name}-{copy}"
            folder.rename(target)
        log.info("run %s moved to %s", folder.name, target.relative_to(runs_directory))
        return Response(status_code=204)

    def profile_view(account: ClaudeAccount) -> ProfileView:
        saved = runs_directory / ".profile.json"
        name = ProfileInput.model_validate_json(saved.read_text()).name if saved.exists() else ""
        runs = [run for run in runs_directory.iterdir() if run.is_dir() and not run.name.startswith(".")]
        spend = 0.0
        for run in runs:
            try:
                spend += load_state(run).spend_usd
            except ValidationError:
                continue  # a run an older version made: no spend recorded
        return ProfileView(name=name, account=account, runs=len(runs), spend_usd=round(spend, 2))

    @app.get("/api/profile", response_model=ProfileView)
    def profile(account: ClaudeAccount = Depends(signed_in_account)) -> ProfileView:
        return profile_view(account)

    @app.put("/api/profile", response_model=ProfileView)
    def save_profile(change: ProfileInput, account: ClaudeAccount = Depends(signed_in_account)) -> ProfileView:
        write_atomic(runs_directory / ".profile.json", ProfileInput(name=change.name.strip()).model_dump_json())
        return profile_view(account)

    def draft_path(draft: str) -> Path:
        if not DRAFT_ID.match(draft):
            raise ApiProblem(404, "This draft no longer exists.")
        return runs_directory / ".drafts" / f"{draft}.json"

    @app.get("/api/drafts", response_model=list[Draft], dependencies=[Depends(signed_in_account)])
    def drafts() -> list[Draft]:
        saved = [Draft.model_validate_json(path.read_text()) for path in (runs_directory / ".drafts").glob("*.json")]
        return sorted(saved, key=lambda draft: draft.updated, reverse=True)

    @app.put("/api/drafts/{draft}", response_model=Draft, dependencies=[Depends(signed_in_account)])
    def save_draft(draft: str, data: DraftInput) -> Draft:
        path = draft_path(draft)
        path.parent.mkdir(exist_ok=True)
        saved = Draft(**data.model_dump(), id=draft, updated=now_text())
        write_atomic(path, saved.model_dump_json(indent=2))
        return saved

    @app.delete("/api/drafts/{draft}", status_code=204, dependencies=[Depends(signed_in_account)])
    def delete_draft(draft: str) -> Response:
        draft_path(draft).unlink(missing_ok=True)
        return Response(status_code=204)

    @app.get("/api/runs/{run}/console", response_model=ConsoleView, dependencies=[Depends(signed_in_account)])
    def console_view(run: str) -> ConsoleView:
        folder = run_folder(run)
        settings = read_json(RUN_ENVIRONMENT / "settings.json") or {}
        rules = {key: list(settings.get("permissions", {}).get(key, [])) for key in ("allow", "deny")}
        return ConsoleView(
            busy=console.is_busy(folder),
            entries=console.history(folder),
            kickoff=KICKOFF_PROMPT,
            settings=console.load_settings(folder).model_copy(update={"allowed": console_permissions.allowed(folder)}),
            session=console.session_info(folder),
            pending=console_permissions.pending(folder),
            rules=rules,
            default_model=SESSION_MODEL,
            spend_usd=load_state(folder).spend_usd,
        )

    @app.post("/api/runs/{run}/console", dependencies=[Depends(signed_in_account)])
    def console_turn(run: str, turn: ConsoleInput, request: Request) -> StreamingResponse:
        folder = run_folder(run)
        running = console.start_turn(folder, turn.message, str(request.base_url))  # the server owns the turn
        if running is None:
            raise ApiProblem(409, "Claude is still working on the previous message")
        return StreamingResponse(console.follow_lines(running), media_type="application/x-ndjson")

    @app.get("/api/runs/{run}/console/follow", dependencies=[Depends(signed_in_account)])
    def console_follow(run: str) -> StreamingResponse:
        """A page that opens while a turn runs follows it: the whole turn so far (its prompt first, live text
        included), then what comes, until it ends."""
        running = console.running(run_folder(run))
        if running is None:
            raise ApiProblem(409, "No turn is running")
        return StreamingResponse(console.follow_lines(running), media_type="application/x-ndjson")

    @app.post("/api/runs/{run}/console/stop", status_code=204, dependencies=[Depends(signed_in_account)])
    def console_stop(run: str) -> Response:
        if not console.stop_turn(run_folder(run)):
            raise ApiProblem(409, "Nothing is running")
        return Response(status_code=204)

    @app.post("/api/runs/{run}/console/clear", status_code=204, dependencies=[Depends(signed_in_account)])
    def console_clear(run: str) -> Response:
        folder = run_folder(run)
        with console.turn_lock(folder) as free:
            if not free:
                raise ApiProblem(409, "Claude is still working: stop it first, then start a new conversation")
            console.clear(folder)
        return Response(status_code=204)

    @app.put(
        "/api/runs/{run}/console/settings", response_model=ConsoleSettings, dependencies=[Depends(signed_in_account)]
    )
    def console_settings(run: str, change: ConsoleSettingsInput) -> ConsoleSettings:
        folder = run_folder(run)
        settings = console.load_settings(folder)
        if change.model is not None:
            settings.model = change.model
        if change.mode is not None:
            settings.mode = change.mode
        console.save_settings(folder, settings)
        return settings.model_copy(update={"allowed": console_permissions.allowed(folder)})

    @app.post(
        "/api/runs/{run}/console/permissions/{prompt}", status_code=204, dependencies=[Depends(signed_in_account)]
    )
    def console_permission_answer(run: str, prompt: str, decision: PermissionAnswer) -> Response:
        try:
            console_permissions.answer(run_folder(run), prompt, decision.decision, decision.note.strip())
        except KeyError as missing:
            raise ApiProblem(404, "This permission prompt was already answered or has ended") from missing
        except ValueError as refused:
            raise ApiProblem(409, str(refused)) from refused
        return Response(status_code=204)

    @app.get("/api/voices", response_model=VoiceList, dependencies=[Depends(signed_in_account)])
    def voice_list() -> VoiceList:
        try:
            listed = voices.voice_list()
        except voices.VoicesUnavailable as unavailable:
            raise ApiProblem(503, str(unavailable)) from unavailable
        curated = {
            f"{variant['polly']['voice_id']}:{variant['polly'].get('engine', 'neural')}": option
            for option, variant in templates.video_settings.library()["voice"]["variants"].items()
        }
        return VoiceList(provider=voices.PROVIDER, template=voices.TEMPLATE,
                         voices=[PollyVoice(**voice) for voice in listed], curated=curated)  # fmt: skip

    @app.post("/api/voices/preview", dependencies=[Depends(signed_in_account)])
    def voice_preview(asked: VoicePreviewInput) -> Response:
        """A few seconds of one narrator: the preview sentence with this voice, engine and speed."""
        library = templates.video_settings.library()
        speed = library["speaking_speed"]["variants"].get(asked.speed)
        if speed is None:
            raise ApiProblem(400, "Choose a speed from the list.")
        try:
            audio = voices.preview(asked.voice, asked.engine, speed)
        except voices.VoicesUnavailable as unavailable:
            raise ApiProblem(503, str(unavailable)) from unavailable
        except ValueError as refused:
            raise ApiProblem(400, "This voice is not available with that engine. Choose another.") from refused
        return Response(audio, media_type="audio/mpeg", headers={"Cache-Control": "private, max-age=86400"})

    @app.get("/api/runs/{run}/console/files", response_model=list[str], dependencies=[Depends(signed_in_account)])
    def console_files(run: str, q: str = "") -> list[str]:
        return console.run_files(run_folder(run), q)

    @app.post("/api/console-permission/{run}")
    async def console_permission_tool(run: str, request: Request) -> Response:
        """The run's Claude Code asks here (MCP over HTTP) whether a tool call may run; authorised by the running
        turn's token, never by the session cookie. The answer comes from the signed-in page."""
        try:
            message = await request.json()
            folder = run_folder(run)
            answered = await run_in_threadpool(console_permissions.handle, folder, request.headers.get("x-turn-token"),
                                               message)  # fmt: skip
        except PermissionError:
            return Response(status_code=403)
        except (ValueError, ApiProblem):
            return Response(status_code=400)
        if answered is None:
            return Response(status_code=202)
        return JSONResponse(answered)

    @app.get("/api/runs/{run}", response_model=RunDetail, dependencies=[Depends(signed_in_account)])
    def run(run: str) -> RunDetail:
        return run_detail(run_folder(run))

    @app.post("/api/runs/{run}/approve", response_model=CheckpointDecision)
    def approve(
        run: str, approval: ApproveInput, account: ClaudeAccount = Depends(signed_in_account)
    ) -> CheckpointDecision:
        try:
            return approve_checkpoint(
                run_folder(run),
                approval.checkpoint,
                approval.notes,
                approval.force,
                by=account.email,
                seen=approval.fingerprint,
            )
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
            raise ApiProblem(404, "That change request no longer exists.") from missing
        return next(request for request in load_requests(folder) if request.id == request_id)

    # ── look & sound: the template tree ────────────────────────────────────────────────────────────────────
    @app.get("/api/look", response_model=LookCatalogue, dependencies=[Depends(signed_in_account)])
    def look_catalogue() -> LookCatalogue:
        return templates.catalogue()

    @app.get("/api/runs/{run}/look", response_model=LookView, dependencies=[Depends(signed_in_account)])
    def run_look(run: str) -> LookView:
        return templates.look_view(run_folder(run))

    def chosen(folder: Path, look: LookInput) -> dict:
        try:
            return templates.chosen_template(folder, look.template, look.elements, look.custom)
        except ValueError as unknown:
            raise ApiProblem(404, "That starter look is not available. Choose another.") from unknown

    def usable(folder: Path, look: LookInput) -> dict:
        template = chosen(folder, look)
        if problems := templates.template_problems(template, folder):
            raise ApiProblem(409, "This Look and Sound cannot be used yet.", problems)
        return template

    @app.post("/api/runs/{run}/look", response_model=LookView, dependencies=[Depends(signed_in_account)])
    def save_look(run: str, look: LookInput) -> LookView:
        folder = run_folder(run)
        if problems := templates.save_template(folder, chosen(folder, look)):
            raise ApiProblem(409, "This Look and Sound cannot be used yet.", problems)
        return templates.look_view(folder)

    @app.post("/api/runs/{run}/look/voice", response_model=VoiceSample, dependencies=[Depends(signed_in_account)])
    def voice_sample(run: str, look: LookInput) -> VoiceSample:
        """A few seconds of the chosen voice at the chosen speed (calls Polly or Google with your credentials)."""
        folder = run_folder(run)
        template = usable(folder, look)
        brief = load_brief(folder)
        try:
            generate_preview.voice_sample(template, brief.tts if brief else "polly", folder / "look_voice_sample.mp3")
        except Exception as failed:  # credentials, network, an unknown voice id: say which
            raise ApiProblem(
                502, "The voice sample could not be made. Check your voice account and try again."
            ) from failed
        return VoiceSample(url=f"/media/{run}/look_voice_sample.mp3?v={content_hash(template)[:8]}")

    @app.post("/api/runs/{run}/look/still", response_model=LookStill, dependencies=[Depends(signed_in_account)])
    def look_still(run: str, look: LookInput) -> LookStill:
        """The whole chosen look as one frame, rendered by Manim exactly as clips get it (a few seconds)."""
        folder = run_folder(run)
        template = usable(folder, look)
        (folder / "look_preview.json").write_text(json.dumps(template))
        try:
            generate_preview.render_in_subprocess(
                ["still", str(folder / "look_preview.json"), str(folder / "look_preview.webp")]
            )
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as failed:
            raise ApiProblem(
                502, "The preview could not be drawn. Try again; if it keeps failing, see the log file."
            ) from failed
        return LookStill(
            url=f"/media/{run}/look_preview.webp?v={content_hash(template)[:8]}",
            note=generate_preview.font_note(template),
        )

    @app.post("/api/runs/{run}/reshuffle", response_model=ReshuffleView, dependencies=[Depends(signed_in_account)])
    def reshuffle_look(run: str, wanted: ReshuffleInput) -> ReshuffleView:
        """A deterministic reshuffle of the saved look: shown (apply=False) or saved, clips recoloured (apply=True)."""
        folder = run_folder(run)
        if not (folder / "template.json").exists():
            raise ApiProblem(409, "Choose a Look and Sound first. There is nothing to reshuffle yet.")
        before = templates.current_template(folder)
        if wanted.apply and (problems := reshuffle.apply(folder, wanted.seed, list(wanted.groups))):
            raise ApiProblem(409, "This reshuffle cannot be used. Try another.", problems)
        after = (
            templates.current_template(folder)
            if wanted.apply
            else reshuffle.proposal(folder, wanted.seed, list(wanted.groups))
        )
        mode = after["elements"].get("theme_mode", "dark")
        return ReshuffleView(
            look=LookInput(
                template=after["name"],
                elements=after["elements"],
                custom={
                    element: templates.video_settings.custom_value(element, override, mode)
                    for element, override in after.get("overrides", {}).items()
                },
            ),
            changes=[
                ReshuffleChange(element=element, before=before["elements"][element], after=variant)
                for element, variant in after["elements"].items()
                if before["elements"].get(element) != variant
            ],
            applied=wanted.apply,
        )

    @app.post("/api/look/still", response_model=LookStill, dependencies=[Depends(signed_in_account)])
    def any_look_still(look: LookInput) -> LookStill:
        """The whole look as one 2560×1440 frame without a run (Start a Run's first step); cached."""
        try:
            template = templates.build_template(
                look.template, look.elements, {k: v for k, v in look.custom.items() if v.strip()}, {}
            )
        except FileNotFoundError as unknown:
            raise ApiProblem(404, "That starter look is not available. Choose another.") from unknown
        if problems := templates.video_settings.problems(template):
            raise ApiProblem(409, "This Look and Sound cannot be used yet.", problems)
        path = generate_preview.still_path(template)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            (path.parent / f"{path.stem}.json").write_text(json.dumps(template))
            try:
                generate_preview.render_in_subprocess(["still", str(path.parent / f"{path.stem}.json"), str(path)])
            except (RuntimeError, OSError, subprocess.TimeoutExpired) as failed:
                raise ApiProblem(
                    502, "The preview could not be drawn. Try again; if it keeps failing, see the log file."
                ) from failed
        return LookStill(url=f"/previews/custom/{path.name}", note=generate_preview.font_note(template))

    @app.get("/previews/starters/{name}.webp", dependencies=[Depends(signed_in_account)])
    def starter_preview(name: str, card: bool = False) -> FileResponse:
        """A starter template, in its own mode, as one frame at 2560×1440 (generate_preview.py starters), rendered now
        if missing; `?card=true`: the 1280×720 copy its gallery card shows."""
        if name not in templates.template_names():
            raise ApiProblem(404, "That starter look is not available. Choose another.")
        path = generate_preview.starter_path(name)
        if not path.exists():
            try:
                generate_preview.render_in_subprocess(["starters", "--only", name])
            except (RuntimeError, OSError, subprocess.TimeoutExpired) as failed:
                raise ApiProblem(
                    502, "The preview could not be drawn. Try again; if it keeps failing, see the log file."
                ) from failed
        return FileResponse(generate_preview.starter_card(name) if card else path, media_type="image/webp")

    @app.post("/api/look/options", response_model=LookOptionPictures, dependencies=[Depends(signed_in_account)])
    def look_options(wanted: LookOptionsInput) -> LookOptionPictures:
        """Every option of one element drawn in the user's own look (their colours, background, font), so what they
        see is what their video gets. Rendered once per look in one process; the 2560×1440 ones when opened."""
        library = templates.video_settings.library()
        if wanted.element not in generate_preview.PREVIEWED:
            raise ApiProblem(404, "This option has no preview picture.")
        look = wanted.look
        custom = {element: value for element, value in look.custom.items() if value.strip()}
        try:
            base = templates.build_template(look.template, look.elements, custom, {})
        except FileNotFoundError as unknown:
            raise ApiProblem(404, "That starter look is not available. Choose another.") from unknown
        candidates = [(variant, {"variant": variant}) for variant in library[wanted.element]["variants"]]
        if custom.get(wanted.element):
            candidates.append(("__custom__", {"custom": custom[wanted.element]}))
        pictures, jobs = [], []
        for option, setting in candidates:
            template = generate_preview.option_in_look(base, wanted.element, **setting)
            if templates.video_settings.problems(template):
                pictures.append(LookOptionPicture(option=option))
                continue
            small, full = generate_preview.custom_path(template), generate_preview.still_path(template)
            if not small.exists():
                jobs.append({"template": template, "path": str(small)})
            if not full.exists():  # rendered by GET /previews/custom/<name> when the user opens it
                full.parent.mkdir(parents=True, exist_ok=True)
                (full.parent / f"{full.stem}.json").write_text(json.dumps(template))
            pictures.append(
                LookOptionPicture(
                    option=option, url=f"/previews/custom/{small.name}", full=f"/previews/custom/{full.name}"
                )
            )
        if jobs:
            jobs_file = generate_preview.CUSTOM_DIRECTORY / f"jobs-{content_hash(jobs)[:12]}.json"
            jobs_file.write_text(json.dumps(jobs))
            try:
                generate_preview.render_in_subprocess(["batch", str(jobs_file)])
            except (RuntimeError, OSError, subprocess.TimeoutExpired) as failed:
                raise ApiProblem(
                    502, "The preview could not be drawn. Try again; if it keeps failing, see the log file."
                ) from failed
            finally:
                jobs_file.unlink(missing_ok=True)
        return LookOptionPictures(pictures=pictures)

    @app.get("/previews/custom/{name}", dependencies=[Depends(signed_in_account)])
    def custom_preview_image(name: str) -> FileResponse:
        path = generate_preview.CUSTOM_DIRECTORY / name
        if not re.fullmatch(r"[0-9a-f]{20}\.webp", name):
            raise ApiProblem(404, "no such preview")
        recipe = path.with_suffix(".json")
        if not path.is_file() and recipe.is_file():  # a full-size picture asked for the first time: render it now
            try:
                generate_preview.render_in_subprocess(["still", str(recipe), str(path)])
            except (RuntimeError, OSError, subprocess.TimeoutExpired) as failed:
                raise ApiProblem(
                    502, "The preview could not be drawn. Try again; if it keeps failing, see the log file."
                ) from failed
        if not path.is_file():
            raise ApiProblem(404, "no such preview")
        return FileResponse(path, media_type="image/webp")

    @app.get("/media/{run}/{path:path}", dependencies=[Depends(signed_in_account)])
    def media(run: str, path: str) -> FileResponse:
        folder = run_folder(run).resolve()
        file = (folder / path).resolve()
        if not path or ".." in Path(path).parts or not file.is_relative_to(folder) or not file.is_file():
            raise ApiProblem(404, "no such file in this run")
        return FileResponse(file)  # answers Range requests, so long videos can be seeked

    # ── the frontend ───────────────────────────────────────────────────────────────────────────────────────
    @app.get("/", include_in_schema=False)
    def frontend() -> Response:
        index = FRONTEND_DIRECTORY / "index.html"
        if not index.is_file():
            return Response(
                "Faraday's website has not been built yet. Build it once (see the README), then reload this page.",
                status_code=503,
                media_type="text/plain",
            )
        return FileResponse(index, media_type="text/html", headers={"Cache-Control": "no-store"})

    @app.get("/assets/{name}", include_in_schema=False)
    def frontend_asset(name: str) -> FileResponse:
        asset = FRONTEND_DIRECTORY / "assets" / name
        if not ASSET_NAME.match(name) or not asset.is_file():
            raise ApiProblem(404, "no such file")
        return FileResponse(asset, headers={"Cache-Control": "public, max-age=31536000, immutable"})  # hashed names

    return app


FIELD_LABELS = {"objectives": "Objectives", "requirement": "Topic", "minutes": "Length", "approach": "Approach"}


def plain_field_errors(errors, skip: int = 0) -> str:
    """'Topic is too short. Objectives needs a value.': the fields a form got wrong, in the site's words (C3)."""
    sentences = []
    for error in errors:
        field = next((str(part) for part in error["loc"][skip:] if not isinstance(part, int)), "details")
        label = FIELD_LABELS.get(field, field.replace("_", " ").capitalize())
        what = {"missing": "needs a value", "string_too_short": "is too short"}.get(error["type"], "is not valid")
        sentences.append(f"{label} {what}.")
    return " ".join(dict.fromkeys(sentences))


def problem_response(problem: ApiProblem) -> JSONResponse:
    return JSONResponse(
        ApiError(
            error=problem.error, problems=problem.problems, people_problems=[people_text(p) for p in problem.problems]
        ).model_dump(),
        status_code=problem.status,
    )
