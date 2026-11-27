"""The whole run, mocked: the real driver (`next`), approvals and change requests, with every agent, command and the
user faked. Each scenario changes one behaviour (a critic that never passes, a build that always fails, a change
request at a checkpoint, ...) and the run must still reach the end: no loop, no dead end, no action nobody handles."""

import json
import re
from dataclasses import dataclass, field

import pytest
from app import narration
from app.workflow import change_requests, critiques, driver, production, run_views, templates
from app.workflow.approvals import ApprovalBlocked, approve_checkpoint
from app.workflow.artifacts import load_scene_plans
from app.workflow.fingerprints import clip_key, final_fingerprint, scene_video_hash
from app.workflow.ledger import count_attempt, update_state
from conftest import (
    make_outline,
    make_plan,
    make_script,
    write_brief,
    write_json_file,
    write_requirements,
    write_review,
)
from schemas.run_state import ClipBuild

MAX_STEPS = 250


@dataclass
class Behaviour:
    """Defaults: every agent and command succeeds first time. A scenario overrides one thing."""

    plan_critic: str = "pass"  # "revise": never passes
    video_critic: str = "pass"
    reviewer_errors: bool = False  # the accuracy reviewer always finds an ERROR
    build_fails_until_hint: bool = False  # accept fails until the user gives a hint
    out_of_sync: bool = False  # every preview is out of sync
    final_error: bool = False  # the final video fails a media check
    confirm_each_scene: bool = False
    requests: dict = field(default_factory=dict)  # checkpoint → (target, kind, text), asked once there


def critique_round(run, scene, kind, verdict):
    prefix = {"plan": "P", "video": "V", "script": "S"}[kind]
    aspect = {"plan": "clarity", "video": "render", "script": "clarity"}[kind]
    issues = [] if verdict == "pass" else [{
        "target": scene, "criterion": f"{prefix}-B1", "tier": "basic", "aspect": aspect, "evidence": "e",
        "problem": "p", "impact": "i", "fix": "f",
    }]  # fmt: skip
    return {
        "reviewed": critiques.critique_subject_hash(run, scene, kind), "verdict": verdict,
        "score": 100 if verdict == "pass" else 75, "summary": "s", "issues": issues,
    }  # fmt: skip


def append_round(run, scene, kind, verdict):
    path = run / critiques.critique_file(scene, kind)
    rounds = json.loads(path.read_text())["rounds"] if path.exists() else []
    write_json_file(path, {"rounds": [*rounds, critique_round(run, scene, kind, verdict)]})


def resolve_named(run, what):
    for request_id in re.findall(r"\b(r\d{3})\b", what):
        if request_id in {request.id for request in change_requests.open_requests(run)}:
            change_requests.resolve_request(run, request_id, "applied")


def direct_user(run):
    """The user's decisions through the workflow functions (what the CLI does)."""

    def decide(checkpoint):  # → True when it needed "Approve with Open Problems"
        try:
            approve_checkpoint(run, checkpoint)
            return False
        except ApprovalBlocked as blocked:
            assert blocked.problems
            approve_checkpoint(run, checkpoint, force=True)
            return True

    def awaiting():
        return [view.target for view in run_views.run_detail(run).awaiting]

    return decide, lambda *request: change_requests.record_change_request(run, *request), awaiting


def simulate(run, b: Behaviour, user=None):
    """→ (outcome, detail, forced checkpoints). `user`: (decide, ask, awaiting), the website's or the CLI's."""
    decide, ask, awaiting = user or direct_user(run)
    if not (run / "brief.json").exists():
        write_brief(run, objectives=["understand the topic"])
    if b.confirm_each_scene:
        write_json_file(run / "preferences.json", {"confirm_each_scene": True})
    asked, forced, seen, hinted = set(), [], {}, set()
    for step in range(MAX_STEPS):
        batch = driver.next_actions(run)
        key = json.dumps(batch.model_dump(), sort_keys=True)
        seen[key] = seen.get(key, 0) + 1
        if seen[key] >= 6:
            return "LOOP", f"{batch.stage}: {[a.agent or a.command or a.do for a in batch.actions]}", forced
        if not batch.actions:
            return "DONE", f"{step} steps", forced
        for a in batch.actions:
            who = a.agent or a.command or a.do
            if a.do == "ask_user" and batch.stage == "1 template" and a.checkpoint is None:
                templates.choose_template(run, "obsidian", [])
            elif a.do == "ask_user" and "failed accept" in a.what:  # the user's hint, as the driver says to record it
                clip = re.search(r"feedback \. (s\d{2}c\d{2})", a.what)[1]
                hinted.add(a.target)
                change_requests.add_request(run, clip, "visual", "build it with fewer objects")
            elif a.do == "ask_user" and a.checkpoint is None:  # a request routed to the user ("other")
                resolve_named(run, a.what)
            elif a.do == "ask_user":
                checkpoint = a.checkpoint
                if checkpoint not in awaiting():
                    return "DEAD END", f"the driver asks {checkpoint}; the website does not show it", forced
                if checkpoint in b.requests and checkpoint not in asked:
                    asked.add(checkpoint)
                    target, kind, text = b.requests[checkpoint]
                    ask(target, kind, text, checkpoint)
                    continue
                if decide(checkpoint):  # the user ticked "Approve with Open Problems"
                    forced.append(checkpoint)
            elif who == "script-writer" and a.target == "outline":
                write_json_file(run / "outline.json", make_outline(30, 30))
                resolve_named(run, a.what)
            elif who == "script-writer":
                script = make_script(10, 30, 30)
                if (run / "script.json").exists():
                    script["title"] = f"T{step}"  # a refactor changes it
                write_json_file(run / "script.json", script)
                resolve_named(run, a.what)
            elif who == "script-critic":
                append_round(run, "script", "script", "revise")
            elif who == "accuracy-reviewer":
                stage = "script" if a.target == "script" else "plan"
                errors = [{"target": "s02", "kind": "FALSE", "severity": "ERROR", "quote": "q", "why": "w", "fix": "f"}]
                write_review(run, stage, errors if b.reviewer_errors else [])
                count_attempt(run, f"review:{stage}", failed=b.reviewer_errors)  # what the PostToolUse hook does
            elif a.do == "write" and a.file in ("topics.md", "content.md"):
                write_requirements(run)
            elif who == "scene-planner":
                plan = make_plan(json.loads((run / "script.json").read_text()), int(a.target[1:]))
                path = run / "scenes" / a.target / "plan.json"
                if path.exists() and not a.what.startswith("write"):
                    plan["composition"] += f" v{step}"  # a refactor changes it
                write_json_file(path, plan)
                resolve_named(run, a.what)
            elif who == "plan-critic":
                append_round(run, a.target, "plan", b.plan_critic)
            elif who == "text-2-shorts voice .":
                for plan in load_scene_plans(run):
                    write_json_file(run / "scenes" / plan.scene_id / "audio" / "index.json", {
                        clip.clip_id: {
                            "hash": production.voice_key(run, narration.speakable_ssml(clip.ssml)), "seconds": 2.0,
                        }
                        for clip in plan.clips
                    })  # fmt: skip
            elif who == "scene-builder":  # what `accept` records
                plan = next(plan for plan in load_scene_plans(run) if plan.scene_id == a.target)
                passed = not b.build_fails_until_hint or a.target in hinted
                for clip in plan.clips:
                    build = (
                        ClipBuild(status="READY", key=clip_key(run, plan, clip))
                        if passed
                        else ClipBuild(status="FAILED", open_findings=["layout: OVERLAP"])
                    )
                    update_state(run, lambda state, c=clip, built=build: state.clips.__setitem__(c.clip_id, built))
                    if passed:
                        change_requests.resolve_clip_requests(run, clip.clip_id)
                built_from = clip_key(run, plan, plan.clips[0])[:12]
                count_attempt(run, f"build:{a.target}" + ("" if passed else f":{built_from}"), failed=not passed)
            elif a.command and a.command.startswith("text-2-shorts preview"):  # what `preview` records
                problems = ["s01c01 beat 1: shown 1.00s late"] if b.out_of_sync else []
                write_json_file(run / "scenes" / a.target / "sync.json", {
                    "scene_id": a.target, "tolerance": 0.3, "clips": [], "problems": problems,
                    "in_sync": not problems, "scene_hash": scene_video_hash(run, a.target),
                })  # fmt: skip
                count_attempt(run, f"sync:{a.target}", failed=bool(problems))
            elif who == "audio-refactorer":  # re-timed SSML (new voice and preview) that, here, never gets in sync
                path = run / "scenes" / a.target / "plan.json"
                plan = json.loads(path.read_text())
                plan["clips"][0]["ssml"] = plan["clips"][0]["ssml"].replace(
                    "</speak>", ' <break time="100ms"/></speak>'
                )
                write_json_file(path, plan)
                resolve_named(run, a.what)
            elif who == "video-critic":
                append_round(run, a.target, "video", b.video_critic)
            elif a.do == "write" and a.file and a.file.endswith("changes.json"):
                path = run / a.file
                entries = json.loads(path.read_text())["entries"] if path.exists() else []
                scene = a.file.split("/")[1]
                done = len(json.loads((run / "scenes" / scene / "video_critique.json").read_text())["rounds"])
                entries.append({
                    "target": scene, "iteration": done, "issue": "i", "findings": ["f"], "modification": "m",
                    "files_changed": [], "rendering_changes": "r", "audio_timing_changes": "a",
                    "sync_adjustments": "s", "validation_results": "v",
                })  # fmt: skip
                write_json_file(path, {"entries": entries})
            elif a.do == "write" and a.file and a.file.startswith("scenes/"):  # a video refactor: rebuild a clip
                scene = re.search(r"s\d{2}", a.file)[0]
                change_requests.add_request(run, f"{scene}c01", "visual", f"critique fix {step}")
            elif a.do == "write" and a.file == "preferences.json":
                write_json_file(run / "preferences.json", {"confirm_each_scene": b.confirm_each_scene})
                resolve_named(run, a.what)
            elif a.command == "text-2-shorts final .":
                (run / "final.mp4").write_bytes(b"x")
                checks = [{"severity": "ERROR", "code": "PEAK", "message": "clips"}] if b.final_error else []
                write_json_file(run / "final_report.json", {
                    "clips": {}, "final_s": 70, "sum_clips_s": 70, "checks": checks,
                    "fingerprint": final_fingerprint(run, load_scene_plans(run)),
                })  # fmt: skip
            else:
                return "UNHANDLED", f"{a.do} {who} {a.file}: {a.what[:100]}", forced
    return "STEP CAP", "", forced


SCENARIOS = {
    "happy path": (Behaviour(), []),
    "confirm each scene": (Behaviour(confirm_each_scene=True), []),
    "plan critic never passes": (Behaviour(plan_critic="revise"), ["plan"]),
    "video critic never passes": (Behaviour(video_critic="revise"), ["scenes"]),
    "accuracy reviewer always finds an ERROR": (Behaviour(reviewer_errors=True), ["script", "plan"]),
    "a scene fails to build until the user gives a hint": (Behaviour(build_fails_until_hint=True), []),
    "previews stay out of sync": (Behaviour(out_of_sync=True), ["scenes"]),
    "the final video fails a media check": (Behaviour(final_error=True), ["final"]),
    "structure change at CP0": (Behaviour(requests={"outline": ("outline", "structure", "add a segment")}), []),
    "wording change at CP1": (Behaviour(requests={"script": ("s02", "wording", "shorter")}), []),
    "visual change on a scene at CP2": (Behaviour(requests={"plan": ("s02", "visual", "bigger diagram")}), []),
    "visual change on a clip at CP3": (Behaviour(requests={"scenes": ("s02c01", "visual", "slower")}), []),
    "audio-timing change at CP3": (Behaviour(requests={"scenes": ("s02", "audio-timing", "longer pause")}), []),
    "style change at CP3": (Behaviour(requests={"scenes": ("s02", "style", "calmer")}), []),
    "other change at the final video": (Behaviour(requests={"final": ("final", "other", "other music")}), []),
    "visual change at the final video": (Behaviour(requests={"final": ("s02c01", "visual", "redo")}), []),
}


@pytest.mark.parametrize("name", SCENARIOS)
def test_every_path_through_a_run_reaches_the_end(tmp_path, name):
    behaviour, expected_forced = SCENARIOS[name]
    outcome, detail, forced = simulate(tmp_path / "20261126-120000-flow", behaviour)
    assert outcome == "DONE", detail
    assert sorted(set(forced)) == sorted(expected_forced)  # only a loop that gave up asks the user to accept it


def test_a_whole_run_driven_from_the_website(tmp_path, monkeypatch):
    """The website's own calls: start the run with its look, then every decision through the API exactly as the
    frontend sends it (approve, force when the checkpoint shows open problems, request a change), reading the run
    page after each one. Agents are faked as above. The run must end done, with its final video on the page."""
    from app.web import auth
    from app.web.app import create_app
    from app.workflow import run_workspace
    from conftest import environment_report
    from fastapi.testclient import TestClient
    from schemas.api import ClaudeAccount

    origin = {"Origin": "http://127.0.0.1:8765"}
    monkeypatch.setattr(auth, "claude_code_account", lambda: ClaudeAccount(email="a@b.c", method="claude.ai"))
    monkeypatch.setattr(run_workspace, "environment_check", environment_report)
    monkeypatch.setattr(run_workspace, "voice_credentials_problem", lambda tts: None)
    runs = tmp_path / "runs"
    runs.mkdir()
    with TestClient(create_app(runs), base_url="http://127.0.0.1:8765") as client:
        assert client.post("/api/session", headers=origin).status_code == 200
        new = {"requirement": "Why is the sky blue?", "minutes": 4, "look": {"template": "obsidian", "elements": {}}}
        created = client.post("/api/runs", json=new, headers=origin)
        assert created.status_code == 201, created.text
        run_id = created.json()["id"]
        run = runs / run_id
        write_brief(run, objectives=["understand the topic"])  # the fakes write a one-minute custom video

        def detail():
            response = client.get(f"/api/runs/{run_id}")
            assert response.status_code == 200, response.text
            return response.json()

        def decide(checkpoint):
            problems = next(view["problems"] for view in detail()["awaiting"] if view["target"] == checkpoint)
            body = {"checkpoint": checkpoint, "notes": "", "force": bool(problems)}  # CheckpointPanel.tsx
            response = client.post(f"/api/runs/{run_id}/approve", json=body, headers=origin)
            assert response.status_code == 200, response.text
            return bool(problems)

        def ask(target, kind, text, checkpoint):  # ChangeModal.tsx
            body = {"target": target, "kind": kind, "text": text, "checkpoint": checkpoint}
            response = client.post(f"/api/runs/{run_id}/requests", json=body, headers=origin)
            assert response.status_code == 201, response.text

        behaviour = Behaviour(video_critic="revise", requests={"script": ("s02", "wording", "shorter")})
        outcome, info, forced = simulate(
            run, behaviour, (decide, ask, lambda: [v["target"] for v in detail()["awaiting"]])
        )
        assert outcome == "DONE", info
        assert forced == ["scenes"]
        page = detail()
        assert page["summary"]["stage"] == "done" and page["summary"]["has_final"] and page["final_video"]
        assert page["awaiting"] == [] and not [r for r in page["requests"] if r["status"] == "open"]
        listed = {summary["id"]: summary for summary in client.get("/api/runs").json()}
        assert listed[run_id]["stage"] == "done"  # Previous Runs lists it as finished
