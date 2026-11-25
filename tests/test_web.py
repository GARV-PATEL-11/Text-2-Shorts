"""The frontend (frontend/) and its FastAPI backend (`text-2-shorts serve`): sign-in through Claude Code, runs,
approvals and change requests, media, and the protections of a server that holds the user's work."""

import json
import re
import subprocess

import pytest
from app.web import auth
from app.web.app import create_app
from conftest import REPOSITORY_ROOT, approved_outline, make_script, write_brief, write_json_file
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


def test_start_a_run_begins_with_the_template_which_is_saved_and_approved(web, monkeypatch):
    from app.workflow import ledger, run_workspace
    from conftest import environment_report

    runs, client = web
    signed_in(client)
    monkeypatch.setattr(run_workspace, "environment_check", environment_report)
    monkeypatch.setattr(run_workspace, "voice_credentials_problem", lambda tts: None)
    new = {"requirement": "Why do **tides** happen?", "minutes": 2, "look": {"template": "paper", "elements": {}}}
    unreadable = {**new, "look": {"template": "standard", "custom": {"background_color": "#ffffff"}}}
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


def test_a_console_turn_is_the_run_session_in_its_jail():  # Haiku: the user's conversation
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


# ── look & sound ──────────────────────────────────────────────────────────────────────────────────────────


def test_the_look_and_sound_tree_starts_on_defaults_saves_choices_and_custom_values(web, monkeypatch):
    runs, client = web
    run = runs / "20261124-130000-look"
    write_brief(run, objectives=["understand the topic"])  # the question round done, no template yet
    signed_in(client)
    catalogue = client.get("/api/look").json()
    elements = {element["id"]: element for element in catalogue["elements"]}
    assert len(catalogue["templates"]) == 6 and "frame" not in elements  # the delivery format is ours
    assert elements["background_color"]["custom"] == "color or gradient" and elements["grid_type"]["custom"] is None
    assert elements["grid_type"]["previewed"] and not elements["voice"]["previewed"]
    assert {element["kind"] for element in elements.values()} == {"visual", "sound"}
    look = client.get(f"/api/runs/{run.name}/look").json()  # nothing chosen yet: the default starter
    assert look["template"] == "standard" and look["saved"] is False and look["elements"]["voice"]
    assert elements["voice"]["options"][0]["detail"].startswith("Polly")

    choice = {"template": "paper", "elements": {"accent_color": "coral"}, "custom": {"text_font": "Lato"}}
    saved = client.post(f"/api/runs/{run.name}/look", json=choice, headers=ORIGIN).json()
    assert saved["saved"] and saved["elements"]["accent_color"] == "coral" and saved["custom"] == {"text_font": "Lato"}
    unreadable = {"template": "standard", "custom": {"background_color": "#ffffff"}}
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
    still = client.post(f"/api/runs/{run.name}/look/still", json={"template": "blueprint"}, headers=ORIGIN)
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
    unreadable = {"template": "standard", "elements": {}, "custom": {"background_color": "#ffffff"}}
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
    client.post(f"/api/runs/{run.name}/look", json={"template": "standard"}, headers=ORIGIN)
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
    signed_in(client)
    for mode in ("dark", "light"):  # every starter has a dark and a light twin
        starter = client.get(f"/previews/starters/standard/{mode}.webp")
        assert starter.status_code == 200 and starter.headers["content-type"] == "image/webp"
    assert client.get("/previews/starters/nope/dark.webp").status_code == 404
    assert client.get("/previews/starters/standard/sepia.webp").status_code == 404
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


def test_options_are_drawn_in_the_users_own_look_with_exact_colours(web):
    import io

    from PIL import Image

    _, client = web
    signed_in(client)
    look = {"template": "standard", "elements": {"grid_opacity": "faint"}, "custom": {"background_color": "#123456"}}
    answer = client.post("/api/look/options", json={"look": look, "element": "accent_color"}, headers=ORIGIN)
    assert answer.status_code == 200, answer.text
    pictures = answer.json()["pictures"]
    assert len(pictures) >= 3 and all(picture["url"] for picture in pictures)
    image = Image.open(io.BytesIO(client.get(pictures[0]["url"]).content)).convert("RGB")
    assert image.getpixel((427, 300)) == (0x12, 0x34, 0x56)  # the user's own background, to the exact value (lossless)
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
