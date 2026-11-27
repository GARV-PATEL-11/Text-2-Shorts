"""The frontend (frontend/) and its FastAPI backend (`text-2-shorts serve`): sign-in through Claude Code, runs,
approvals and change requests, media, and the protections of a server that holds the user's work."""

import json
import re
import subprocess

import pytest
from app.web import auth
from app.web.app import create_app
from conftest import REPOSITORY_ROOT, approved_outline, make_script, write_brief, write_json_file, write_review
from fastapi.testclient import TestClient
from schemas.api import ClaudeAccount
from test_workflow import two_scenes_after_cp2

FRONTEND = REPOSITORY_ROOT / "frontend"
SOURCE = FRONTEND / "src"  # React + TypeScript; built into frontend/dist/ (served)
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
    write_review(run, "script", [])
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


def test_signing_in_needs_the_token_serve_printed(tmp_path, monkeypatch):  # H6
    monkeypatch.setattr(auth, "claude_code_account", lambda: ACCOUNT)
    with TestClient(create_app(tmp_path / "runs", sign_in_token="s3cret"), base_url=BASE) as client:
        assert client.post("/api/session", headers=ORIGIN).status_code == 403  # any local process: refused
        wrong = client.post("/api/session", headers={**ORIGIN, "X-Faraday-Token": "guess"})
        assert wrong.status_code == 403
        right = client.post("/api/session", headers={**ORIGIN, "X-Faraday-Token": "s3cret"})
        assert right.status_code == 200 and client.get("/api/runs").status_code == 200


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


def test_a_fresh_clone_without_a_runs_folder_lists_no_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "claude_code_account", lambda: ACCOUNT)
    with TestClient(create_app(tmp_path / "runs"), base_url=BASE) as client:
        signed_in(client)
        response = client.get("/api/runs")
    assert response.status_code == 200, response.text
    assert response.json() == []


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
    assert body["by"] == ACCOUNT.email  # who approved, kept with the decision
    assert client.get("/api/runs/20261124-120000-cp1").json()["stages"]["script"] == "approved"
    response = client.post(
        "/api/runs/20261124-120000-cp1/approve", json={"checkpoint": "plan", "force": True}, headers=ORIGIN
    )
    assert response.status_code == 200 and response.json()["forced"] is True


def test_an_approval_from_the_page_is_for_the_version_the_page_showed(web):  # M9
    runs, client = web
    signed_in(client)
    run = run_at_cp1(runs)
    shown = client.get("/api/runs/20261124-120000-cp1").json()["awaiting"][0]
    assert shown["target"] == "script" and shown["fingerprint"]
    script = json.loads((run / "script.json").read_text())
    script["scenes"][0]["narration"] += " Added by an agent after the page loaded."
    write_json_file(run / "script.json", script)
    write_review(run, "script")
    seen = {"checkpoint": "script", "fingerprint": shown["fingerprint"]}
    response = client.post("/api/runs/20261124-120000-cp1/approve", json=seen, headers=ORIGIN)
    assert response.status_code == 409 and "changed since" in response.json()["error"]
    current = client.get("/api/runs/20261124-120000-cp1").json()["awaiting"][0]["fingerprint"]
    seen["fingerprint"] = current
    assert client.post("/api/runs/20261124-120000-cp1/approve", json=seen, headers=ORIGIN).status_code == 200


def test_a_half_written_file_keeps_the_run_page_readable(web):  # H3
    runs, client = web
    signed_in(client)
    run = run_at_cp1(runs)
    (run / "script.json").write_text('{"title": "cut off mid-wri')  # an agent mid-write, or a trailing comma
    detail = client.get("/api/runs/20261124-120000-cp1").json()
    assert detail["problem"] is None and detail["summary"]["readable"]
    assert detail["stages"]["script"] != "approved"  # what cannot be read is simply not approved
    assert any(run["id"] == "20261124-120000-cp1" for run in client.get("/api/runs").json())


def test_one_run_that_cannot_be_summarised_does_not_hide_the_others(web, monkeypatch):  # M10
    from app.web import app as web_app

    runs, client = web
    signed_in(client)
    run_at_cp1(runs)
    (runs / "20261124-130000-broken").mkdir()
    summarise = web_app.run_summary

    def breaks_on_one(run):
        if run.name.endswith("broken"):
            raise OSError("a file vanished mid-poll")
        return summarise(run)

    monkeypatch.setattr(web_app, "run_summary", breaks_on_one)
    response = client.get("/api/runs")
    assert response.status_code == 200 and [run["id"] for run in response.json()] == ["20261124-120000-cp1"]


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
    every_scene = {"target": "scenes", "kind": "visual", "text": "slower everywhere"}  # Scenes' "All Scenes"
    assert client.post("/api/runs/20261124-120000-cp1/requests", json=every_scene, headers=ORIGIN).status_code == 201


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
    assets = re.findall(r'(?:src|href)="(/assets/[^"]+)"', page.text)  # the React build's hashed bundles
    kinds = {client.get(asset).headers["content-type"].split(";")[0] for asset in assets}
    assert {"text/css", "text/javascript"} <= kinds, kinds
    assert client.get("/assets/../index.html").status_code == 404


def test_the_frontend_is_black_with_white_and_grey_only():
    styles = "\n".join(path.read_text() for path in sorted((SOURCE / "styles").glob("*.css")))
    for path in SOURCE.rglob("*.ts*"):  # no colour hides in the components either
        colours = {colour.lower() for colour in re.findall(r"#[0-9a-fA-F]{6}\b", path.read_text())}
        assert colours <= NEUTRALS, (path.name, colours - NEUTRALS)
    colours = {colour.lower() for colour in re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", styles)}
    assert colours <= NEUTRALS, colours - NEUTRALS
    for arguments in re.findall(r"\b(?:rgba?|hsla?)\(([^)]*)\)", styles):  # alpha only on black, white or night
        channels = [part.strip() for part in arguments.split(",")[:3]]
        assert channels in (["0"] * 3, ["255"] * 3, ["11", "11", "13"]), arguments
    assert re.search(r"body\s*\{[^}]*background:\s*var\(--night\)", styles)  # the whole page is black
    grounds = re.findall(r"(?:^|\})\s*([^{}]*)\{[^}]*background(?:-color)?:\s*var\(--(white|paper|mist)\)", styles)
    assert all(".btn" in selector or "button" in selector for selector, _ in grounds), grounds  # white: buttons only


def test_motion_follows_the_contract_and_stops_when_reduced():
    """Fades and colour changes in token durations; the drawer is the one slide; nothing scales or bounces; reduced
    motion collapses every duration to 0 (styles/motion.css, styles/tokens.css)."""
    styles = {
        path.name: re.sub(r"/\*.*?\*/", "", path.read_text(), flags=re.DOTALL)
        for path in (SOURCE / "styles").glob("*.css")
    }
    everything = "\n".join(styles.values())
    assert (
        "prefers-reduced-motion: reduce" in styles["tokens.css"]
        and "prefers-reduced-motion: reduce" in styles["motion.css"]
    )
    assert not re.search(r"transition\s*:\s*all|transition-property\s*:\s*all", everything)
    assert not re.search(r"scale\(|bounce|spring", everything)
    durations = re.findall(r"(?:transition(?:-duration)?|animation)\s*:([^;]*);", everything)
    endless = [value for value in durations if "var(--motion-" not in value and value.strip() != "none"]
    assert all(value.strip().endswith("infinite") for value in endless), endless  # only waiting indicators loop
    for name, body in re.findall(r"@keyframes\s+([\w-]+)\s*\{((?:[^{}]*\{[^}]*\})*[^}]*)\}", everything):
        properties = set(re.findall(r"([a-z-]+)\s*:", body))
        assert properties <= {"opacity", "transform"}, (name, properties)
    for path in [*SOURCE.rglob("*.ts*"), FRONTEND / "index.html"]:
        text = path.read_text()
        assert "scroll-behavior: smooth" not in text and ".animate(" not in text, path.name


def test_the_frontend_never_writes_html_from_run_data_unescaped():
    for path in SOURCE.rglob("*.ts*"):  # React escapes text; nothing may bypass it
        script = path.read_text()
        assert "dangerouslySetInnerHTML" not in script and "innerHTML" not in script, path.name


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
        "approach": "step_by_step",
        "minutes": 4,
    }
    response = client.post("/api/runs", json=new, headers=ORIGIN)
    assert response.status_code == 201, response.text
    run_id = response.json()["id"]
    assert re.match(r"^\d{8}-\d{6}-why-is-the-sky-blue$", run_id)
    assert json.loads((runs / run_id / "brief.json").read_text())["objectives"] == ["explain scattering"]
    assert json.loads((runs / run_id / "state.json").read_text())["builder_prompt"]  # pinned for this run (M7)
    for minutes in (0, 2.5, 21):  # a new video is 3–20 minutes of teaching
        assert client.post("/api/runs", json={**new, "minutes": minutes}, headers=ORIGIN).status_code == 400
    blocked = environment_report().model_copy(update={"problems": ["ffmpeg missing"]})
    monkeypatch.setattr(run_workspace, "environment_check", lambda: blocked)
    response = client.post("/api/runs", json=new, headers=ORIGIN)
    assert response.status_code == 409 and "ffmpeg missing" in response.json()["error"]


def test_a_run_that_fails_while_being_set_up_is_not_left_behind(web, monkeypatch):  # M13
    from app.web import app as web_app
    from app.workflow import run_workspace
    from conftest import environment_report

    runs, client = web
    signed_in(client)
    monkeypatch.setattr(run_workspace, "environment_check", environment_report)
    monkeypatch.setattr(run_workspace, "voice_credentials_problem", lambda tts: None)

    def disk_full(*_):
        raise OSError("disk full")

    monkeypatch.setattr(web_app, "update_state", disk_full)
    new = {"requirement": "Why is the sky blue?", "objectives": ["x"], "approach": "step_by_step", "minutes": 4}
    response = client.post("/api/runs", json={**new, "name": "Sky"}, headers=ORIGIN)
    assert response.status_code == 500 and "disk full" in response.json()["error"]
    assert [path.name for path in runs.iterdir() if not path.name.startswith(".")] == []


def test_start_a_run_begins_with_the_template_which_is_saved_and_approved(web, monkeypatch):
    from app.workflow import ledger, run_workspace
    from conftest import environment_report

    runs, client = web
    signed_in(client)
    monkeypatch.setattr(run_workspace, "environment_check", environment_report)
    monkeypatch.setattr(run_workspace, "voice_credentials_problem", lambda tts: None)
    new = {"requirement": "Why do **tides** happen?", "minutes": 4, "look": {"template": "paper", "elements": {}}}
    unreadable = {**new, "look": {"template": "obsidian", "custom": {"background_color": "#ffffff"}}}
    refused = client.post("/api/runs", json=unreadable, headers=ORIGIN)
    assert refused.status_code == 409 and not list(runs.iterdir())  # refused before any run is made
    created = client.post("/api/runs", json=new, headers=ORIGIN)
    assert created.status_code == 201, created.text
    run = runs / created.json()["id"]
    assert json.loads((run / "template.json").read_text())["name"] == "paper"
    assert "template" in ledger.load_state(run).approved  # the first stage is done: the run opens at requirements
    still = client.post("/api/look/still", json={"template": "paper"}, headers=ORIGIN)  # no run needed
    assert still.status_code == 200, still.text
    assert client.get(still.json()["url"]).headers["content-type"] == "image/webp"


FAKE_CLAUDE = """
import json, sys
print(json.dumps({"type": "system", "subtype": "init", "session_id": "session-1"}), flush=True)
say = lambda content: print(json.dumps({"type": "assistant", "message": {"content": content}}), flush=True)
say([{"type": "text", "text": "Reading the brief."}])
say([{"type": "tool_use", "name": "Write", "input": {"file_path": "/x/run/topics.md", "content": "1. a"}}])
say([{"type": "tool_use", "name": "AskUserQuestion", "input": {"questions": [
    {"header": "Length", "question": "How long?", "options": [{"label": "2 min"}, {"label": "3 min"}]}]}}])
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
        ("question", "**Length** — How long?"),  # shown on the stage page, answerable with one click
        ("system", "Turn finished."),
    ]
    assert entries[3]["options"] == ["2 min", "3 min"]
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


def test_a_console_turn_outlives_the_page_that_sent_it(web, monkeypatch, tmp_path):  # H7, M14
    import sys

    from app.web import console

    runs, _ = web
    run = run_at_cp1(runs)
    slow = tmp_path / "slow_claude.py"
    slow.write_text(
        "import json, sys, time\n"
        "sys.stderr.write('x' * 200_000)\n"  # more than a pipe holds: must not hang the turn (M14)
        "print(json.dumps({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'one'}]}}), flush=True)\n"
        "time.sleep(0.5)\n"
        "print(json.dumps({'type': 'result', 'subtype': 'success', 'is_error': False}), flush=True)\n"
    )
    monkeypatch.setattr(console, "claude_turn_command", lambda *_: [sys.executable, str(slow)])
    turn = console.start_turn(run, "go")
    assert turn is not None and console.start_turn(run, "again") is None  # one turn at a time
    follower = console.follow(turn)
    assert next(follower).role == "you"
    follower.close()  # the page reloads mid-turn: the turn goes on, holding its lock
    assert console.is_busy(run)
    turn.finished.wait(10)
    assert [entry.role for entry in console.history(run)] == ["you", "claude", "system"]
    assert not console.is_busy(run)


def test_a_console_turn_is_the_run_session_in_its_jail():  # Haiku: the user's conversation
    from app import sandbox
    from app.config import SESSION_MODEL

    first = sandbox.console_claude_arguments("hello", None)
    assert first[:2] == ["claude", "-p"] and first[-2:] == ["--", "hello"] and "--resume" not in first
    assert ["--output-format", "stream-json"] == first[
        first.index("--output-format") : first.index("--output-format") + 2
    ]
    assert first[first.index("--model") + 1] == SESSION_MODEL and "--plugin-dir" in first
    resumed = sandbox.console_claude_arguments("next", "session-1")
    assert resumed[resumed.index("--resume") + 1] == "session-1"
    dash = sandbox.console_claude_arguments("--settings=x.json shorter intro", "session-1")
    assert dash[-2:] == ["--", "--settings=x.json shorter intro"]  # never read as a Claude Code option


# ── look & sound ──────────────────────────────────────────────────────────────────────────────────────────


def test_the_look_and_sound_tree_starts_on_defaults_saves_choices_and_custom_values(web, monkeypatch):
    runs, client = web
    run = runs / "20261124-130000-look"
    write_brief(run, objectives=["understand the topic"])  # the question round done, no template yet
    signed_in(client)
    catalogue = client.get("/api/look").json()
    elements = {element["id"]: element for element in catalogue["elements"]}
    assert len(catalogue["templates"]) == 12 and "frame" not in elements  # the delivery format is ours
    assert elements["background_color"]["custom"] == "color or gradient" and elements["grid_type"]["custom"] is None
    assert elements["grid_type"]["previewed"] and not elements["voice"]["previewed"]
    assert {element["kind"] for element in elements.values()} == {"visual", "sound"}
    look = client.get(f"/api/runs/{run.name}/look").json()  # nothing chosen yet: the default starter
    assert look["template"] == "obsidian" and look["saved"] is False and look["elements"]["voice"]
    assert elements["voice"]["options"][0]["detail"].startswith("Polly")

    choice = {"template": "paper", "elements": {"accent_color": "coral"}, "custom": {"text_font": "Lato"}}
    saved = client.post(f"/api/runs/{run.name}/look", json=choice, headers=ORIGIN).json()
    assert saved["saved"] and saved["elements"]["accent_color"] == "coral" and saved["custom"] == {"text_font": "Lato"}
    unreadable = {"template": "obsidian", "custom": {"background_color": "#ffffff"}}
    refused = client.post(f"/api/runs/{run.name}/look", json=unreadable, headers=ORIGIN)
    assert refused.status_code == 409 and any("contrast" in problem for problem in refused.json()["problems"])

    from app import narration

    spoken = []
    monkeypatch.setattr(
        narration, "create_speech_synthesizer", lambda sound: lambda text: spoken.append((sound, text)) or (b"mp3", [])
    )
    sample = client.post(
        f"/api/runs/{run.name}/look/voice", json={**choice, "elements": {"speaking_speed": "slow"}}, headers=ORIGIN
    )
    assert sample.status_code == 200 and (run / "look_voice_sample.mp3").read_bytes() == b"mp3"
    sound, text = spoken[0]
    assert sound["voice"] and 'rate="90%"' in text  # the voice and speed chosen, before saving


def test_the_look_can_be_previewed_as_one_rendered_frame(web):
    runs, client = web
    run = runs / "20261124-140000-still"
    write_brief(run, objectives=["understand the topic"])
    signed_in(client)
    still = client.post(f"/api/runs/{run.name}/look/still", json={"template": "graphite"}, headers=ORIGIN)
    assert still.status_code == 200, still.text
    assert (run / "look_preview.webp").read_bytes()[8:12] == b"WEBP"
    assert client.get(still.json()["url"].split("?")[0]).headers["content-type"] == "image/webp"


def test_a_custom_value_is_drawn_in_the_users_look_with_its_options(web):
    _, client = web
    signed_in(client)
    look = {"template": "paper", "elements": {}, "custom": {"accent_color": "#123456"}}
    answer = client.post("/api/look/options", json={"look": look, "element": "accent_color"}, headers=ORIGIN).json()
    custom = next(picture for picture in answer["pictures"] if picture["option"] == "__custom__")
    assert client.get(custom["url"]).headers["content-type"] == "image/webp"
    unreadable = {"template": "obsidian", "elements": {}, "custom": {"background_color": "#ffffff"}}
    answer = client.post("/api/look/options", json={"look": unreadable, "element": "background_color"}, headers=ORIGIN)
    custom = next(picture for picture in answer.json()["pictures"] if picture["option"] == "__custom__")
    assert custom["url"] is None  # white text on white: no picture, the card says why


def test_a_reshuffle_is_shown_before_it_is_applied_and_the_same_seed_gives_the_same_look(web):
    runs, client = web
    run = runs / "20261124-150000-reshuffle"
    write_brief(run, objectives=["understand the topic"])
    signed_in(client)
    wanted = {"seed": 7, "groups": ["colours", "fonts"]}
    refused = client.post(f"/api/runs/{run.name}/reshuffle", json=wanted, headers=ORIGIN)
    assert refused.status_code == 409  # nothing to reshuffle before the template is chosen
    client.post(f"/api/runs/{run.name}/look", json={"template": "obsidian"}, headers=ORIGIN)
    first = client.post(f"/api/runs/{run.name}/reshuffle", json=wanted, headers=ORIGIN).json()
    again = client.post(f"/api/runs/{run.name}/reshuffle", json=wanted, headers=ORIGIN).json()
    assert first == again and first["changes"] and not first["applied"]
    assert {change["element"] for change in first["changes"]} <= {
        "primary_palette", "secondary_palette", "accent_color", "text_font", "math_font"
    }  # fmt: skip
    assert client.get(f"/api/runs/{run.name}/look").json()["elements"] != first["look"]["elements"]  # not saved yet
    bad = client.post(f"/api/runs/{run.name}/reshuffle", json={"seed": 7, "groups": ["sizes"]}, headers=ORIGIN)
    assert bad.status_code == 400  # this API answers invalid input with 400


def test_starter_templates_and_options_have_full_size_pictures(web):
    _, client = web
    import io

    from PIL import Image

    signed_in(client)
    starter = client.get("/previews/starters/obsidian.webp")  # each starter in its own mode
    assert starter.status_code == 200 and starter.headers["content-type"] == "image/webp"
    assert client.get("/previews/starters/nope.webp").status_code == 404
    card = client.get("/previews/starters/obsidian.webp?card=true")  # the gallery card's own, smaller copy
    assert card.status_code == 200 and Image.open(io.BytesIO(card.content)).size == (1280, 720)
    assert client.get("/previews/custom/0123456789abcdef0123.webp").status_code == 404  # nothing to render it from


def test_the_browser_reports_into_frontend_log_and_requests_are_logged(web, logs_in_a_temporary_folder, caplog):
    import logging

    _, client = web
    batch = {"entries": [{"level": "error", "message": "TypeError in LookTree", "page": "#/new", "details": "at x"}]}
    with caplog.at_level(logging.INFO, logger="app.web"):
        assert client.post("/api/logs", json=batch, headers=ORIGIN).status_code == 204
        assert client.get("/api/runs").status_code == 401
    written = (logs_in_a_temporary_folder / "frontend.log").read_text()
    assert "ERROR" in written and "frontend" in written and "[#/new] TypeError in LookTree — at x" in written
    assert any("GET /api/runs → 401" in record.getMessage() for record in caplog.records)
    too_many = {"entries": [{"level": "info", "message": "x"}] * 51}
    assert client.post("/api/logs", json=too_many, headers=ORIGIN).status_code == 400


def test_browser_reports_cannot_forge_log_lines_or_flood_the_log(web, logs_in_a_temporary_folder):  # L5
    _, client = web
    forged = {"entries": [{"level": "info", "message": "ok\n2026-11-27 ERROR app.web forged line"}]}
    assert client.post("/api/logs", json=forged, headers=ORIGIN).status_code == 204
    batch = {"entries": [{"level": "info", "message": "spam"}] * 50}
    for _ in range(10):
        client.post("/api/logs", json=batch, headers=ORIGIN)
    written = (logs_in_a_temporary_folder / "frontend.log").read_text()
    assert "\n2026-11-27 ERROR app.web forged line" not in written  # one entry is one line
    assert written.count("spam") <= 200  # a budget per minute, then dropped


def test_expired_sessions_are_swept_and_claude_auth_status_is_not_asked_on_every_poll(web, monkeypatch):  # L5
    import time

    sessions = auth.Sessions()
    old = sessions.open(ACCOUNT)
    sessions.by_token[old] = (ACCOUNT, time.time() - 1)
    sessions.open(ACCOUNT)
    assert old not in sessions.by_token
    _, client = web
    asked = []
    monkeypatch.setattr(auth, "claude_code_account", lambda: asked.append(1) or ACCOUNT)
    for _ in range(5):
        client.get("/api/session")
    assert len(asked) == 1


def test_an_unexpected_error_answers_with_its_cause_and_is_logged(tmp_path, monkeypatch, caplog):  # M16
    import logging

    from app.web import app as web_app

    monkeypatch.setattr(auth, "claude_code_account", lambda: ACCOUNT)

    def breaks(_):
        raise RuntimeError("state.json vanished")

    monkeypatch.setattr(web_app, "run_detail", breaks)
    application = create_app(tmp_path / "runs")
    (tmp_path / "runs" / "20261124-120000-x").mkdir()
    with TestClient(application, base_url=BASE, raise_server_exceptions=False) as client, caplog.at_level(logging.INFO):
        signed_in(client)
        response = client.get("/api/runs/20261124-120000-x")
    assert response.status_code == 500 and "state.json vanished" in response.json()["error"]
    assert any(record.exc_info for record in caplog.records if "failed" in record.getMessage())


def test_options_are_drawn_in_the_users_own_look_with_exact_colours(web):
    import io

    from PIL import Image

    _, client = web
    signed_in(client)
    look = {"template": "obsidian", "elements": {"grid_opacity": "faint"}, "custom": {"background_color": "#123456"}}
    answer = client.post("/api/look/options", json={"look": look, "element": "accent_color"}, headers=ORIGIN)
    assert answer.status_code == 200, answer.text
    pictures = answer.json()["pictures"]
    assert len(pictures) >= 3 and all(picture["url"] for picture in pictures)
    image = Image.open(io.BytesIO(client.get(pictures[0]["url"]).content)).convert("RGB")
    assert image.getpixel((4, 240)) == (
        0x12,
        0x34,
        0x56,
    )  # the user's own background (outside the frame), exact (lossless)
    full = client.get(pictures[0]["full"])  # 2560×1440, rendered when first opened
    assert full.status_code == 200 and Image.open(io.BytesIO(full.content)).size == (2560, 1440)
    unknown = client.post("/api/look/options", json={"look": look, "element": "voice"}, headers=ORIGIN)
    assert unknown.status_code == 404


def test_every_borrowed_line_is_credited_and_linked_and_the_brand_line_is_untouched():
    import re

    voice = (FRONTEND / "src" / "config" / "voice.ts").read_text()
    lines = re.findall(r'^  (\w+): \{ text: "([^"]+)", source: [`"]([^`"]+)[`"], url: (\S+) \},$', voice, re.MULTILINE)
    declared = re.findall(r"^  (\w+): \{ text:", voice, re.MULTILINE)
    assert lines and len(lines) == len(declared)  # every line has its text, its source and its link
    for name, text, source, url in lines:
        assert source.strip() and url.startswith(('"https://', "candle(")), name
    used = set(re.findall(r"LINES\.(\w+)", voice))
    assert used <= set(declared) and set(declared) <= used  # no unused or undefined line
    assert not any("Curiosity, Illustrated" in text for _, text, _, _ in lines)  # the brand line is never replaced
    home = (FRONTEND / "src" / "pages" / "Home.tsx").read_text()
    assert "Curiosity, Illustrated." in home


def test_a_usage_file_that_cannot_be_written_never_stops_a_turn(monkeypatch, tmp_path):  # L6
    from app.web import usage

    monkeypatch.setattr(usage, "USAGE_FILE", tmp_path / "not-a-folder" / "usage.json")
    (tmp_path / "not-a-folder").write_text("a file where the folder should be")
    event = {"type": "rate_limit_event", "rate_limit_info": {"unifiedWindows": {"five_hour": {"utilization": 0.1}}}}
    assert usage.record(event) is False  # logged and skipped: the console turn goes on


def test_usage_limits_follow_claude_codes_rate_limit_events(web, monkeypatch, tmp_path):
    import json

    from app.web import usage

    _, client = web
    monkeypatch.setattr(usage, "USAGE_FILE", tmp_path / "usage.json")
    assert client.get("/api/usage").status_code == 401  # signed in only
    signed_in(client)
    assert client.get("/api/usage").json()["windows"] == []  # nothing reported yet
    event = {
        "type": "rate_limit_event",
        "rate_limit_info": {
            "unifiedWindows": {
                "five_hour": {"utilization": 0.25, "resetsAt": 1795599000, "status": "allowed"},
                "seven_day": {"utilization": 0.49, "resetsAt": 1795867200, "status": "allowed"},
            }
        },
    }
    assert not usage.record({"type": "assistant"}) and usage.record(event)  # a console turn's event is kept
    view = client.get("/api/usage").json()
    assert [(w["id"], w["used_percent"], w["resets_at"]) for w in view["windows"]] == [
        ("five_hour", 25.0, 1795599000),
        ("seven_day", 49.0, 1795867200),
    ]
    assert view["plan"] == ACCOUNT.plan and view["checked_at"]
    fresher = json.loads(json.dumps(event))
    fresher["rate_limit_info"]["unifiedWindows"]["five_hour"]["utilization"] = 0.3
    monkeypatch.setattr(usage, "probe", lambda: '{"type": "system"}\n' + json.dumps(fresher) + "\n")
    checked = client.post("/api/usage", headers=ORIGIN).json()  # Check Now: one probe turn
    assert checked["windows"][0]["used_percent"] == 30.0


def test_the_website_offers_exactly_the_backends_approaches():
    import re

    from schemas.outline_models.approaches import APPROACHES

    offered = re.findall(r'\{ id: "(\w+)", label:', (FRONTEND / "src" / "config" / "approaches.ts").read_text())
    assert offered == list(APPROACHES)


def test_every_frame_carries_the_faraday_mark_above_the_content():
    import video_settings

    template = video_settings.starter("ivory")
    drawing = video_settings.drawing(template)
    assert drawing["brand"]["color"] == video_settings.resolve(template)["roles"]["text"]  # readable in both modes
    assert f"below y = {video_settings.content_top(drawing['inset'])}" in video_settings.brief(template)


def test_a_run_lives_on_this_machine_from_its_first_draft_to_its_trash(web, monkeypatch):
    from app.workflow import run_workspace
    from conftest import environment_report

    runs, client = web
    signed_in(client)
    monkeypatch.setattr(run_workspace, "environment_check", environment_report)
    monkeypatch.setattr(run_workspace, "voice_credentials_problem", lambda tts: None)

    draft_id = "0b6b2f0e-8c3e-4f53-9a8e-2d4a5c6f7a10"  # Start a Run saves as the user goes, before any run exists
    draft = {"name": "Tides", "step": 3, "requirement": "Why do tides happen?", "minutes": "5", "approach": "feynman"}
    assert client.put(f"/api/drafts/{draft_id}", json=draft, headers=ORIGIN).status_code == 200
    listed = client.get("/api/drafts").json()
    assert [d["id"] for d in listed] == [draft_id] and listed[0]["step"] == 3  # survives a refresh or a sign-out
    assert client.get("/api/runs").json() == []  # a draft is not a run (and .drafts is not listed as one)
    assert client.put("/api/drafts/../x", json=draft, headers=ORIGIN).status_code == 404

    started = client.post("/api/runs", json={"requirement": "Why do tides happen?", "minutes": 5, "name": "Tides"},
                          headers=ORIGIN).json()  # fmt: skip
    assert client.delete(f"/api/drafts/{draft_id}", headers=ORIGIN).status_code == 204
    assert started["name"] == "Tides" and started["status"] == "configuring" and started["updated"]
    unnamed = client.post(
        "/api/runs", json={"requirement": "Why is ice slippery?", "minutes": 4}, headers=ORIGIN
    ).json()
    assert unnamed["name"].startswith("Why is ice slippery — ")  # named from its topic and date

    renamed = client.patch(f"/api/runs/{started['id']}", json={"name": "Moon and Tides"}, headers=ORIGIN).json()
    assert renamed["name"] == "Moon and Tides" and renamed["id"] == started["id"]  # its files and id stay
    copy = client.post(f"/api/runs/{started['id']}/duplicate", headers=ORIGIN)
    assert copy.status_code == 201 and copy.json()["name"] == "Copy of Moon and Tides"
    assert json.loads((runs / copy.json()["id"] / "brief.json").read_text())["requirement"] == "Why do tides happen?"

    assert client.delete(f"/api/runs/{started['id']}", headers=ORIGIN).status_code == 204
    assert (runs / ".trash" / started["id"] / "brief.json").exists()  # recoverable, not gone
    assert started["id"] not in [run["id"] for run in client.get("/api/runs").json()]


def test_a_run_deleted_twice_under_the_same_name_keeps_both_in_the_trash(web):  # L7
    runs, client = web
    signed_in(client)
    for content in ("first", "second"):
        run = run_at_cp1(runs)
        (run / "note.txt").write_text(content)
        assert client.delete(f"/api/runs/{run.name}", headers=ORIGIN).status_code == 204
    kept = sorted((path / "note.txt").read_text() for path in (runs / ".trash").iterdir())
    assert kept == ["first", "second"]


def test_the_profile_keeps_your_name_and_adds_up_what_every_run_cost(web):
    from app.workflow import ledger

    runs, client = web
    signed_in(client)
    for name, cost in (("20261126-100000-a", 1.25), ("20261126-110000-b", 0.5)):
        write_brief(runs / name)
        ledger.update_state(runs / name, lambda state, cost=cost: setattr(state, "spend_usd", cost))
    view = client.get("/api/profile").json()
    assert (view["runs"], view["spend_usd"], view["account"]["email"]) == (2, 1.75, ACCOUNT.email)
    assert client.put("/api/profile", json={"name": " Garv "}, headers=ORIGIN).json()["name"] == "Garv"
    assert client.get("/api/profile").json()["name"] == "Garv"  # kept on this machine
