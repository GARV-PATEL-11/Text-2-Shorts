"""The frontend (frontend/) and its FastAPI backend (`text-2-shorts serve`): sign-in through Claude Code, runs,
approvals and change requests, media, and the protections of a server that holds the user's work."""

import json
import re
import subprocess

import pytest
from conftest import REPOSITORY_ROOT, approved_outline, make_script, write_brief, write_json_file
from fastapi.testclient import TestClient
from test_workflow import two_scenes_after_cp2

from app.web import auth
from app.web.app import create_app
from schemas.api import ClaudeAccount

FRONTEND = REPOSITORY_ROOT / "frontend"
BASE = "http://127.0.0.1:8765"
ORIGIN = {"Origin": BASE}
ACCOUNT = ClaudeAccount(email="someone@example.com", organization="Example Org", plan="team", method="claude.ai")
NEUTRALS = {
    "#0b0b0d",
    "#17181c",
    "#2a2b31",
    "#3a3b42",
    "#6a6b74",
    "#a3a5ad",
    "#d6d7dc",
    "#f0f0f2",
    "#ffffff",
}  # armakuni.com's dark tokens: night grounds, rules, greys, white type and buttons


@pytest.fixture
def web(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    runs.mkdir()
    monkeypatch.setattr(auth, "claude_code_account", lambda: ACCOUNT)
    with TestClient(create_app(runs), base_url=BASE) as client:
        yield runs, client


def signed_in(client):
    response = client.post("/api/session", headers=ORIGIN)
    assert response.status_code == 200, response.text
    return response.json()


def run_at_cp1(runs):
    run = runs / "20261124-120000-cp1"
    write_brief(run, objectives=["understand the topic"])
    approved_outline(run, (30, 30))
    write_json_file(run / "script.json", make_script(30, 30))
    write_json_file(run / "script_review.json", {"findings": []})
    return run


# ── signing in ────────────────────────────────────────────────────────────────────────────────────────────


def test_signing_in_uses_the_claude_account_claude_code_is_signed_in_to(web):
    _, client = web
    assert client.get("/api/session").json()["signed_in"] is False
    assert client.get("/api/runs").status_code == 401  # nothing without a session
    session = signed_in(client)
    assert session["signed_in"] and session["account"]["email"] == "someone@example.com"
    assert client.cookies.get("t2s_session") and client.get("/api/runs").status_code == 200
    assert client.delete("/api/session", headers=ORIGIN).status_code == 200
    assert client.get("/api/runs").status_code == 401


def test_the_session_cookie_cannot_be_read_by_scripts_or_sent_from_other_sites(web):
    _, client = web
    header = client.post("/api/session", headers=ORIGIN).headers["set-cookie"].lower()
    assert "httponly" in header and "samesite=strict" in header and "path=/" in header


def test_signing_in_is_refused_until_claude_code_is_signed_in(web, monkeypatch):
    _, client = web
    monkeypatch.setattr(auth, "claude_code_account", lambda: None)
    response = client.post("/api/session", headers=ORIGIN)
    assert response.status_code == 401 and "claude auth login" in response.json()["error"]
    assert client.get("/api/session").json()["claude_code_signed_in"] is False


def test_the_claude_code_account_comes_from_claude_auth_status(monkeypatch):
    status = {
        "loggedIn": True,
        "email": "a@b.c",
        "orgName": "Org",
        "subscriptionType": "team",
        "authMethod": "claude.ai",
    }

    def fake_run(command, **options):
        assert command == ["claude", "auth", "status", "--json"]
        return subprocess.CompletedProcess(command, 0, json.dumps(status), "")

    monkeypatch.setattr(auth.subprocess, "run", fake_run)
    account = auth.claude_code_account()
    assert account and (account.email, account.organization, account.plan) == ("a@b.c", "Org", "team")
    status["loggedIn"] = False
    assert auth.claude_code_account() is None

    def missing(command, **options):
        raise FileNotFoundError("claude")

    monkeypatch.setattr(auth.subprocess, "run", missing)
    assert auth.claude_code_account() is None


# ── runs, media ───────────────────────────────────────────────────────────────────────────────────────────


def test_the_api_lists_runs_and_shows_one_run(web):
    runs, client = web
    signed_in(client)
    two_scenes_after_cp2(runs / "20261124-101500-keplers-laws")
    (runs / "20261116-144147-old-run").mkdir()
    write_json_file(runs / "20261116-144147-old-run" / "brief.json", {"topic": "an older brief format"})
    (runs / "20261116-144147-old-run" / "final.mp4").write_bytes(b"mp4")

    listed = {row["id"]: row for row in client.get("/api/runs").json()}
    assert listed["20261124-101500-keplers-laws"]["created"] == "2026-11-24 10:15"
    assert listed["20261116-144147-old-run"]["readable"] is False and listed["20261116-144147-old-run"]["has_final"]
    detail = client.get("/api/runs/20261124-101500-keplers-laws").json()
    assert detail["stages"]["plan"] == "approved" and [scene["scene_id"] for scene in detail["scenes"]] == [
        "s01",
        "s02",
    ]
    assert detail["next"]["actions"][0]["do"] and detail["scenes"][0]["clips"][0]["status"] == "pending"
    old = client.get("/api/runs/20261116-144147-old-run").json()
    assert old["problem"] and old["final_video"] == "/media/20261116-144147-old-run/final.mp4"
    assert old["final_checked"] is False  # no report: the page must not claim the checks passed
    assert client.get("/api/runs/no-such-run").status_code == 404


def test_media_is_served_from_inside_a_run_only_and_can_be_seeked(web):
    runs, client = web
    (runs / "r1").mkdir()
    (runs / "r1" / "final.mp4").write_bytes(b"0123456789")
    (runs / "secret.txt").write_text("outside")
    assert client.get("/media/r1/final.mp4").status_code == 401  # signed-in users only
    signed_in(client)
    assert client.get("/media/r1/final.mp4").content == b"0123456789"
    part = client.get("/media/r1/final.mp4", headers={"Range": "bytes=2-5"})
    assert part.status_code == 206 and part.content == b"2345"  # seeking in long videos
    for bad in ("/media/r1/../secret.txt", "/media/r1/%2e%2e/secret.txt", "/media/..%2Fsecret.txt/x", "/media/r1/"):
        assert client.get(bad).status_code == 404, bad


# ── approvals and change requests ─────────────────────────────────────────────────────────────────────────


def test_the_frontend_approves_a_checkpoint_and_refuses_one_with_open_problems(web):
    runs, client = web
    signed_in(client)
    run_at_cp1(runs)
    detail = client.get("/api/runs/20261124-120000-cp1").json()
    assert [checkpoint["target"] for checkpoint in detail["awaiting"]] == ["script"]
    response = client.post("/api/runs/20261124-120000-cp1/approve", json={"checkpoint": "plan"}, headers=ORIGIN)
    assert response.status_code == 409 and response.json()["problems"]
    response = client.post(
        "/api/runs/20261124-120000-cp1/approve", json={"checkpoint": "script", "notes": "clear"}, headers=ORIGIN
    )
    body = response.json()
    assert response.status_code == 200 and (body["decision"], body["forced"]) == ("approved_with_notes", False)
    assert client.get("/api/runs/20261124-120000-cp1").json()["stages"]["script"] == "approved"
    response = client.post(
        "/api/runs/20261124-120000-cp1/approve", json={"checkpoint": "plan", "force": True}, headers=ORIGIN
    )
    assert response.status_code == 200 and response.json()["forced"] is True


def test_the_frontend_records_change_requests_and_resolves_them(web):
    runs, client = web
    signed_in(client)
    run_at_cp1(runs)
    request = {"target": "s02", "kind": "wording", "text": "shorter sentences", "checkpoint": "script"}
    response = client.post("/api/runs/20261124-120000-cp1/requests", json=request, headers=ORIGIN)
    assert response.status_code == 201 and (response.json()["id"], response.json()["status"]) == ("r001", "open")
    detail = client.get("/api/runs/20261124-120000-cp1").json()
    assert detail["requests"][0]["text"] == "shorter sentences"
    assert detail["decisions"][-1]["decision"] == "changes_requested"
    bad = {"target": "s02", "kind": "colour", "text": "x"}
    response = client.post("/api/runs/20261124-120000-cp1/requests", json=bad, headers=ORIGIN)
    assert response.status_code == 400 and "kind" in response.json()["error"]
    response = client.post(
        "/api/runs/20261124-120000-cp1/requests/r001", json={"status": "declined", "note": "kept"}, headers=ORIGIN
    )
    assert response.status_code == 200 and response.json()["status"] == "declined"
    missing = client.post("/api/runs/20261124-120000-cp1/requests/r009", json={"status": "applied"}, headers=ORIGIN)
    assert missing.status_code == 404


def test_writes_only_come_from_the_page_itself(web):
    runs, client = web
    signed_in(client)
    run_at_cp1(runs)
    path, body = "/api/runs/20261124-120000-cp1/approve", json.dumps({"checkpoint": "script"})
    plain = {**ORIGIN, "Content-Type": "text/plain"}
    assert client.post(path, content=body, headers=plain).status_code == 415  # no cross-site form posts
    evil = {"Origin": "https://evil.example", "Content-Type": "application/json"}
    assert client.post(path, content=body, headers=evil).status_code == 403
    assert client.get("/api/runs", headers={"Host": "evil.example"}).status_code == 400  # DNS rebinding
    assert client.post(path, content=body, headers={**ORIGIN, "Content-Type": "application/json"}).status_code == 200


# ── the frontend files ────────────────────────────────────────────────────────────────────────────────────


def test_the_frontend_is_served_and_loads_the_reference_fonts(web):
    _, client = web
    page = client.get("/")
    assert page.status_code == 200 and page.headers["content-type"].startswith("text/html")
    assert "family=Geist" in page.text and "Fira+Code" in page.text  # Geist to read, Fira Code to interact
    assert "<title>Faraday" in page.text and "Curiosity, Illustrated" in page.text  # the brand
    assert client.get("/styles.css").headers["content-type"].startswith("text/css")
    assert client.get("/app.js").headers["content-type"].startswith("text/javascript")


def test_the_frontend_is_black_with_white_and_grey_only():
    styles = (FRONTEND / "styles.css").read_text()
    colours = {colour.lower() for colour in re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", styles)}
    assert colours <= NEUTRALS, colours - NEUTRALS
    for arguments in re.findall(r"\b(?:rgba?|hsla?)\(([^)]*)\)", styles):  # alpha only on black, white or night
        channels = [part.strip() for part in arguments.split(",")[:3]]
        assert channels in (["0"] * 3, ["255"] * 3, ["11", "11", "13"]), arguments
    assert re.search(r"body\s*\{[^}]*background:\s*var\(--night\)", styles)  # the whole page is black
    grounds = re.findall(r"(?:^|\})\s*([^{}]*)\{[^}]*background(?:-color)?:\s*var\(--(white|paper|mist)\)", styles)
    assert all(".btn" in selector or "button" in selector for selector, _ in grounds), grounds  # white: buttons only


def test_the_frontend_has_no_motion():
    for path in [*FRONTEND.glob("*.css"), *FRONTEND.glob("*.js"), FRONTEND / "index.html"]:
        text = path.read_text()
        assert not re.search(r"@keyframes|animation\s*:(?!\s*none)|transition\s*:(?!\s*none)", text), path.name
        assert "scroll-behavior: smooth" not in text and ".animate(" not in text, path.name


def test_the_frontend_never_writes_html_from_run_data_unescaped():
    script = (FRONTEND / "app.js").read_text()
    assert "innerHTML" not in script and "insertAdjacentHTML" not in script


# ── the website as the only interface: starting runs, and the console to the run's Claude Code session ────


def test_a_run_is_started_from_the_website(web, monkeypatch):
    from app.workflow import run_workspace
    from conftest import environment_report

    runs, client = web
    signed_in(client)
    monkeypatch.setattr(run_workspace, "environment_check", environment_report)
    monkeypatch.setattr(run_workspace, "voice_credentials_problem", lambda tts: None)
    new = {
        "requirement": "Why is the sky blue?",
        "objectives": ["explain scattering"],
        "approach": "linear",
        "minutes": 2,
    }
    response = client.post("/api/runs", json=new, headers=ORIGIN)
    assert response.status_code == 201, response.text
    run_id = response.json()["id"]
    assert re.match(r"^\d{8}-\d{6}-why-is-the-sky-blue$", run_id)
    assert json.loads((runs / run_id / "brief.json").read_text())["objectives"] == ["explain scattering"]
    assert client.post("/api/runs", json={**new, "minutes": 0}, headers=ORIGIN).status_code == 400
    blocked = environment_report().model_copy(update={"problems": ["ffmpeg missing"]})
    monkeypatch.setattr(run_workspace, "environment_check", lambda: blocked)
    response = client.post("/api/runs", json=new, headers=ORIGIN)
    assert response.status_code == 409 and "ffmpeg missing" in response.json()["error"]


FAKE_CLAUDE = """
import json, sys
print(json.dumps({"type": "system", "subtype": "init", "session_id": "session-1"}), flush=True)
say = lambda content: print(json.dumps({"type": "assistant", "message": {"content": content}}), flush=True)
say([{"type": "text", "text": "Reading the brief."}])
say([{"type": "tool_use", "name": "Write", "input": {"file_path": "/x/run/topics.md", "content": "1. a"}}])
print(json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}}), flush=True)
print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "done"}), flush=True)
"""


def test_the_console_relays_messages_to_the_runs_claude_code_session(web, monkeypatch, tmp_path):
    import sys

    from app.web import console

    runs, client = web
    signed_in(client)
    run_at_cp1(runs)
    fake = tmp_path / "fake_claude.py"
    fake.write_text(FAKE_CLAUDE)
    calls = []

    def command(run, message, session):
        calls.append((message, session))
        return [sys.executable, str(fake)]

    monkeypatch.setattr(console, "claude_turn_command", command)
    path = "/api/runs/20261124-120000-cp1/console"
    view = client.get(path).json()
    assert (view["busy"], view["entries"]) == (False, []) and "text-2-shorts-produce" in view["kickoff"]
    response = client.post(path, json={"message": "Start producing the video."}, headers=ORIGIN)
    assert response.status_code == 200 and response.headers["content-type"].startswith("application/x-ndjson")
    entries = [json.loads(line) for line in response.text.splitlines()]
    assert [(entry["role"], entry["text"]) for entry in entries] == [
        ("you", "Start producing the video."),
        ("claude", "Reading the brief."),
        ("tool", "Write topics.md"),
        ("system", "Turn finished."),
    ]
    client.post(path, json={"message": "Go on."}, headers=ORIGIN)
    assert calls == [("Start producing the video.", None), ("Go on.", "session-1")]  # the same session, resumed
    history = client.get(path).json()["entries"]
    assert [entry["role"] for entry in history].count("you") == 2
    assert client.post(path, json={"message": ""}, headers=ORIGIN).status_code == 400


def test_a_run_has_one_console_turn_at_a_time(web, monkeypatch):
    from app.web import console

    runs, client = web
    signed_in(client)
    run = run_at_cp1(runs)
    with console.turn_lock(run) as acquired:
        assert acquired
        response = client.post(f"/api/runs/{run.name}/console", json={"message": "hi"}, headers=ORIGIN)
        assert response.status_code == 409 and client.get(f"/api/runs/{run.name}/console").json()["busy"] is True


def test_a_console_turn_is_the_run_session_in_its_jail():
    from app import sandbox
    from app.config import SESSION_MODEL

    first = sandbox.console_claude_arguments("hello", None)
    assert first[:3] == ["claude", "-p", "hello"] and "--resume" not in first
    assert ["--output-format", "stream-json"] == first[
        first.index("--output-format") : first.index("--output-format") + 2
    ]
    assert first[first.index("--model") + 1] == SESSION_MODEL and "--plugin-dir" in first
    resumed = sandbox.console_claude_arguments("next", "session-1")
    assert resumed[resumed.index("--resume") + 1] == "session-1"
