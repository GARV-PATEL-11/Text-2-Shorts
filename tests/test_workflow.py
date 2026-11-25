"""The production workflow is enforced in order: requirements → complete script (CP1) → scene-wise visual plans
(CP2) → clip-wise code. Every stage has a gate, and downstream stages refuse to start before upstream approval."""

import argparse
import json

import pytest
from app.commands import production_commands, workflow_commands
from app.workflow import (
    change_requests,
    checkpoints,
    critiques,
    driver,
    fingerprints,
    ledger,
    preferences,
    production,
    run_workspace,
    scene_code,
    status,
    templates,
    validation,
)
from conftest import (
    approve,
    approved_outline,
    confirm_requirements,
    critique_issue,
    make_outline,
    make_plan,
    make_script,
    write_brief,
    write_critique,
    write_json_file,
    write_requirements,
)
from schemas.media import ClipMux, FinalReport
from schemas.run_state import ClipBuild


def approved_script_run(run, *scene_seconds):
    write_brief(run, objectives=["understand the topic"])
    approved_outline(run, scene_seconds)
    script = make_script(*scene_seconds)
    write_json_file(run / "script.json", script)
    write_json_file(run / "script_review.json", {"findings": []})
    approve(run, "script")
    return script


def test_brief_is_validated(tmp_path):
    write_brief(tmp_path, objectives=["see why orbits are ellipses"], style="ELI5")
    assert validation.validate_brief(tmp_path) == []
    write_json_file(tmp_path / "brief.json", {"approach": "zoom", "minutes": 1})
    assert any("requirement" in error for error in validation.validate_brief(tmp_path))


def test_script_covers_every_objective_bridges_scenes_and_fits_its_word_budget(tmp_path):
    write_brief(tmp_path, objectives=["understand the topic"])
    approved_outline(tmp_path, (30, 30))
    script = make_script(30, 30)
    write_json_file(tmp_path / "script.json", script)
    assert validation.validate_script(tmp_path) == []

    def errors_with(change):
        changed = make_script(30, 30)
        change(changed)
        write_json_file(tmp_path / "script.json", changed)
        return " | ".join(validation.validate_script(tmp_path))

    assert "not covered" in errors_with(lambda s: s["objectives"].append("a second objective"))
    assert "bridge_in" in errors_with(lambda s: s["scenes"][1].update(bridge_in=""))  # scene 2 needs a bridge
    assert "bridge_in" in errors_with(lambda s: s["scenes"][0].update(bridge_in="hello"))  # scene 1 has none
    assert "words" in errors_with(lambda s: s["scenes"][0].update(narration="far too short"))
    assert "±20%" in errors_with(lambda s: [scene.update(duration_seconds=60) for scene in s["scenes"]])
    write_brief(tmp_path, objectives=["an objective the script dropped"])
    write_json_file(tmp_path / "script.json", script)
    assert any("an objective the script dropped" in error for error in validation.validate_script(tmp_path))


def test_scene_plans_wait_for_the_approved_script_and_must_follow_it(tmp_path):
    write_brief(tmp_path, objectives=["understand the topic"])
    approved_outline(tmp_path, (30, 30))
    script = make_script(30, 30)
    write_json_file(tmp_path / "script.json", script)
    write_json_file(tmp_path / "scenes" / "s01" / "plan.json", make_plan(script, 1, clip_count=2))
    assert any("CP1" in error for error in validation.validate_plan(tmp_path, "s01"))  # not approved yet

    write_json_file(tmp_path / "script_review.json", {"findings": []})
    approve(tmp_path, "script")
    assert validation.validate_plan(tmp_path, "s01") == []

    changed_plan = make_plan(script, 1, clip_count=2)
    changed_plan["clips"][1]["narration"] += " an extra sentence"
    write_json_file(tmp_path / "scenes" / "s01" / "plan.json", changed_plan)
    assert any("script" in error and "narration" in error for error in validation.validate_plan(tmp_path, "s01"))

    second_plan = make_plan(script, 2)
    second_plan["transition_in"] = ""
    write_json_file(tmp_path / "scenes" / "s02" / "plan.json", second_plan)
    assert any("transition_in" in error for error in validation.validate_plan(tmp_path, "s02"))

    script["scenes"][0]["title"] = "renamed after approval"
    write_json_file(tmp_path / "script.json", script)
    assert any("CP1" in error for error in validation.validate_plan(tmp_path, "s02"))  # approval is now stale


def test_plans_keep_scene_boundaries_empty_and_one_colour_per_symbol(tmp_path):
    script = approved_script_run(tmp_path, 30, 30)
    first = {**make_plan(script, 1), "color_roles": {"a": "BLUE"}}
    second: dict = {**make_plan(script, 2), "color_roles": {"a": "RED"}}
    second["clips"][0]["entry"] = {"persistent_objects": ["x"]}
    write_json_file(tmp_path / "scenes" / "s01" / "plan.json", first)
    write_json_file(tmp_path / "scenes" / "s02" / "plan.json", second)
    errors = " | ".join(validation.validate_plan(tmp_path, "s02"))
    assert "entry must be empty" in errors and "`a`" in errors and "BLUE" in errors


def test_accuracy_reviews_point_at_real_scenes_and_clips_and_errors_block_approval(tmp_path):
    write_brief(tmp_path, objectives=["understand the topic"])
    approved_outline(tmp_path, (30, 30))
    script = make_script(30, 30)
    write_json_file(tmp_path / "script.json", script)
    finding = {"severity": "ERROR", "kind": "FALSE", "quote": "q", "why": "w", "fix": "f"}
    write_json_file(tmp_path / "script_review.json", {"findings": [{**finding, "target": "s09"}]})
    assert any("s09" in error for error in validation.validate_review(tmp_path, "script"))
    write_json_file(tmp_path / "script_review.json", {"findings": [{**finding, "target": "s01"}]})
    with pytest.raises(SystemExit, match="accuracy"):
        approve(tmp_path, "script")

    write_json_file(tmp_path / "script_review.json", {"findings": []})
    approve(tmp_path, "script")
    for number in (1, 2):
        write_json_file(tmp_path / "scenes" / f"s{number:02d}" / "plan.json", make_plan(script, number))
    with pytest.raises(SystemExit, match="plan_review.json"):
        approve(tmp_path, "plan")
    write_json_file(tmp_path / "plan_review.json", {"findings": [{**finding, "target": "s01c09"}]})
    assert any("s01c09" in error for error in validation.validate_review(tmp_path, "plan"))
    write_json_file(tmp_path / "plan_review.json", {"findings": [{**finding, "target": "s01c01", "severity": "WARN"}]})
    for scene_id in ("s01", "s02"):
        write_critique(tmp_path, scene_id, "plan", "pass")
    approve(tmp_path, "plan")


def test_voice_and_clip_tasks_wait_for_the_approved_plans(tmp_path):
    script = approved_script_run(tmp_path, 30, 30)
    for number in (1, 2):
        write_json_file(tmp_path / "scenes" / f"s{number:02d}" / "plan.json", make_plan(script, number))
    with pytest.raises(SystemExit, match="CP2"):
        production_commands.handle_voice_command(argparse.Namespace(run=str(tmp_path)))
    with pytest.raises(SystemExit, match="CP2"):
        scene_code.prepare_scene(tmp_path, "s01")

    write_json_file(tmp_path / "plan_review.json", {"findings": []})
    for scene_id in ("s01", "s02"):
        write_critique(tmp_path, scene_id, "plan", "pass")
    approve(tmp_path, "plan")
    edited = make_plan(script, 1)
    edited["composition"] = "changed after approval"
    write_json_file(tmp_path / "scenes" / "s01" / "plan.json", edited)
    with pytest.raises(SystemExit, match="CP2"):  # a plan edited after CP2 needs CP2 again
        scene_code.prepare_scene(tmp_path, "s01")


def test_next_steps_follow_the_stage_order(tmp_path):
    write_brief(tmp_path, objectives=["understand the topic"])
    steps = status.next_steps(tmp_path)
    assert "topics.md" in steps[0] and not any("script" in step or "CP0" in step for step in steps)

    write_requirements(tmp_path)
    confirm_requirements(tmp_path)
    write_json_file(tmp_path / "outline.json", make_outline(30))
    steps = status.next_steps(tmp_path)
    assert any(step.startswith("CP0") for step in steps) and not any("script.json" in step for step in steps)

    approve(tmp_path, "outline")
    script = make_script(30, 30)
    write_json_file(tmp_path / "script.json", script)
    steps = status.next_steps(tmp_path)
    assert any("script_review.json" in step for step in steps) and any(step.startswith("CP1") for step in steps)
    assert not any(step.startswith("s01") for step in steps)  # no visual planning before CP1

    write_json_file(tmp_path / "script_review.json", {"findings": []})
    approve(tmp_path, "script")
    steps = status.next_steps(tmp_path)
    assert any(step.startswith("s01 plan") for step in steps) and any(step.startswith("s02 plan") for step in steps)
    assert not any("voice" in step or step.startswith("build") for step in steps)  # no clips before CP2


def test_new_turns_the_requirements_into_a_valid_brief():
    from app import cli
    from schemas.requirements import Brief

    arguments = cli.build_parser().parse_args(
        [
            "new",
            "Kepler's laws",
            "--objective",
            "explain why orbits are ellipses",
            "--objective",
            "use the third law",
            "--style",
            "story-driven",
            "--approach",
            "creative",
            "--tts",
            "polly",
        ]
    )
    brief = run_workspace.brief_from_arguments(arguments)
    assert brief.objectives == ["explain why orbits are ellipses", "use the third law"]
    assert brief.style == "story-driven" and brief.approach == "creative" and brief.tts == "polly"
    assert isinstance(brief, Brief)  # validated on the way in


def test_a_forced_approval_without_a_script_does_not_open_the_next_stage(tmp_path):
    write_brief(tmp_path, objectives=["understand the topic"])
    approve(tmp_path, "script", force=True)  # nothing to approve yet
    assert checkpoints.stage_approval_problem(tmp_path, "script")


def test_the_script_opens_with_an_index_scene_that_previews_every_later_scene(tmp_path):
    write_brief(tmp_path, objectives=["understand the topic"])
    approved_outline(tmp_path, (20, 20, 20))

    def errors_with(change):
        script = make_script(20, 20, 20)
        change(script)
        write_json_file(tmp_path / "script.json", script)
        return " | ".join(validation.validate_script(tmp_path))

    assert errors_with(lambda s: None) == ""
    assert "index" in errors_with(lambda s: s["scenes"][0].update(role="content", covers=[1]))
    assert "previews" in errors_with(lambda s: s["scenes"][0].update(previews=["s02"]))  # s03 not previewed
    assert "index" in errors_with(lambda s: s["scenes"][2].update(role="index"))  # only s01 is the index
    assert "covers" in errors_with(lambda s: s["scenes"][1].update(covers=[]))  # teaching scenes cover objectives


def test_there_are_three_fixed_approaches_and_one_creative_one():
    from app import cli
    from schemas.requirements import Brief

    for approach in ("zoom", "arc", "linear", "creative"):
        assert cli.build_parser().parse_args(["new", "t", "--approach", approach]).approach == approach
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["new", "t", "--approach", "custom"])
    Brief.model_validate({"requirement": "t", "approach": "creative"})


def test_each_clip_plans_its_audio_as_ssml_over_exactly_its_narration(tmp_path):
    script = approved_script_run(tmp_path, 30, 30)
    plan = make_plan(script, 1, clip_count=2)
    words = plan["clips"][0]["narration"].split()
    plan["clips"][0]["ssml"] = (
        f'<speak>{words[0]} <break time="400ms"/> <prosody rate="95%">{" ".join(words[1:])}</prosody></speak>'
    )
    write_json_file(tmp_path / "scenes" / "s01" / "plan.json", plan)
    assert validation.validate_plan(tmp_path, "s01") == []

    plan["clips"][1]["ssml"] = "<speak>different words</speak>"
    plan["clips"][0]["ssml"] = '<speak><audio src="x.mp3"/>' + " ".join(words) + "</speak>"
    write_json_file(tmp_path / "scenes" / "s01" / "plan.json", plan)
    errors = " | ".join(validation.validate_plan(tmp_path, "s01"))
    assert "s01c02" in errors and "ssml" in errors and "audio" in errors


def plans_ready_for_cp2(run):
    script = approved_script_run(run, 30, 30)
    for number in (1, 2):
        write_json_file(run / "scenes" / f"s{number:02d}" / "plan.json", make_plan(script, number))
    write_json_file(run / "plan_review.json", {"findings": []})
    return script


def test_every_scene_plan_needs_a_passing_critique_of_its_current_version_before_cp2(tmp_path):
    script = plans_ready_for_cp2(tmp_path)
    with pytest.raises(SystemExit, match="critique"):
        approve(tmp_path, "plan")  # no critique yet
    write_critique(tmp_path, "s01", "plan", "revise", "pass")
    write_critique(tmp_path, "s02", "plan", "pass")
    edited = make_plan(script, 2)
    edited["composition"] = "refactored after the last critique round"
    write_json_file(tmp_path / "scenes" / "s02" / "plan.json", edited)
    with pytest.raises(SystemExit, match="s02.*changed since"):
        approve(tmp_path, "plan")  # the critique must have seen the plan as it is now
    write_critique(tmp_path, "s02", "plan", "pass")
    approve(tmp_path, "plan")


def test_the_critic_loop_stops_after_three_rounds_and_hands_open_issues_to_the_user(tmp_path):
    plans_ready_for_cp2(tmp_path)
    write_critique(tmp_path, "s01", "plan", "pass")
    write_critique(tmp_path, "s02", "plan", "revise", "revise", "revise", "revise")
    assert any("3 rounds" in error for error in critiques.validate_critique(tmp_path, "s02", "plan"))
    write_critique(tmp_path, "s02", "plan", "revise", "revise", "revise")
    with pytest.raises(SystemExit, match="open issues"):
        approve(tmp_path, "plan")  # three rounds used: the user decides
    approve(tmp_path, "plan", force=True)


def test_the_sync_report_compares_when_each_phrase_is_spoken_with_when_its_beat_is_shown(tmp_path):
    from schemas.plans import ScenePlan

    script = approved_script_run(tmp_path, 30, 30)
    plan = make_plan(script, 1)
    plan["clips"][0]["beats"] = ['"word100" → title appears', '"word105" → circle grows']
    write_json_file(tmp_path / "scenes" / "s01" / "plan.json", plan)
    write_json_file(
        tmp_path / "scenes" / "s01" / "audio" / "index.json",
        {"s01c01": {"hash": "h", "seconds": 3.0, "beat_times": [0.0, 1.5]}},
    )
    write_json_file(
        tmp_path / "scenes" / "s01" / "work" / "checks" / "probe.json",
        {"ok": True, "beats": {"clip_01": {"1": 0.3, "2": 2.6}}},
    )
    (tmp_path / "scenes" / "s01" / "work" / "CHANGES.md").write_text("circle starts later than planned")

    report = production.sync_report(tmp_path, ScenePlan.model_validate(plan), {"s01c01": 4.1})
    beats = report.clips[0].beats
    assert [beat.offset for beat in beats] == [0.0, 0.8]  # shown − spoken (the voice starts 0.3 s in)
    assert report.in_sync is False and report.clips[0].audio_fits is True
    assert "circle starts later" in report.clips[0].changes
    assert any("s01c01 beat 2" in problem for problem in report.problems)


def test_planners_and_critics_can_look_up_manim_names(capsys):
    workflow_commands.handle_doc_command(argparse.Namespace(names="Axes.plot,Axes.get_graph", topics=""))
    output = capsys.readouterr().out
    assert "### Axes.plot" in output and "NOT IN Manim" in output.split("### Axes.plot")[1]


def two_scenes_after_cp2(run, clips_in_first_scene=2):
    """CP2 approved for s01 (two clips sharing an object) and s02, with audio for every clip."""
    from app import narration

    script = approved_script_run(run, 30, 30)
    plans = [make_plan(script, 1, clip_count=clips_in_first_scene, exits=[["eq"], []]), make_plan(script, 2)]
    for plan in plans:
        write_json_file(run / "scenes" / plan["scene_id"] / "plan.json", plan)
        write_critique(run, plan["scene_id"], "plan", "pass")
        write_json_file(
            run / "scenes" / plan["scene_id"] / "audio" / "index.json",
            {
                clip["clip_id"]: {
                    "hash": production.voice_key(run, narration.speakable_ssml(clip["ssml"])),
                    "seconds": 2.0,
                }
                for clip in plan["clips"]
            },
        )
    write_json_file(run / "plan_review.json", {"findings": []})
    approve(run, "plan")
    return plans


def test_objects_a_clip_takes_over_must_be_described(tmp_path):
    script = approved_script_run(tmp_path, 30, 30)
    plan = make_plan(script, 1, clip_count=2, exits=[["eq"], []])
    plan["clips"][1]["entry"]["descriptions"] = {}
    write_json_file(tmp_path / "scenes" / "s01" / "plan.json", plan)
    assert any("s01c02" in error and "descriptions" in error for error in validation.validate_plan(tmp_path, "s01"))


def test_a_scene_task_carries_its_plan_and_timings_and_scenes_go_in_series(tmp_path):
    two_scenes_after_cp2(tmp_path)
    task = scene_code.prepare_scene(tmp_path, "s01")
    assert "<CLIP_SEQUENCE>" in task and "_clip_1" in task and "Scene01" in task
    assert (tmp_path / "scenes" / "s01" / "work" / "TASK.json").exists()
    with pytest.raises(SystemExit, match="s01.*CP3"):
        scene_code.prepare_scene(tmp_path, "s02")  # scenes are produced in series
    with pytest.raises(SystemExit, match="s01.*CP3"):
        production_commands.handle_preview_command(argparse.Namespace(run=str(tmp_path), scene="s02"))


def test_every_clip_of_a_scene_shares_the_scene_key(tmp_path):
    from schemas.plans import ScenePlan

    plan = ScenePlan.model_validate(two_scenes_after_cp2(tmp_path)[0])
    assert fingerprints.clip_key(tmp_path, plan, plan.clips[0]) == fingerprints.clip_key(tmp_path, plan, plan.clips[1])


def test_next_hands_out_the_exact_next_batch(tmp_path):
    write_brief(tmp_path, objectives=["understand the topic"])
    assert driver.next_actions(tmp_path).stage == "1 template"  # the look comes first, on the website
    templates.choose_template(tmp_path, "standard", [])
    approve(tmp_path, "template")
    batch = driver.next_actions(tmp_path)
    assert batch.stage == "1 requirements" and batch.actions[0].file == "topics.md"
    assert any(path.endswith("references/topic-list.md") for path in batch.actions[0].read)
    write_requirements(tmp_path)
    assert "approve . requirements" in driver.next_actions(tmp_path).actions[0].what
    confirm_requirements(tmp_path)
    batch = driver.next_actions(tmp_path)  # building the outline is the Opus script-writer's, not the session's
    assert batch.stage.startswith("2") and (batch.actions[0].agent, batch.actions[0].target) == (
        "script-writer",
        "outline",
    )
    assert any(path.endswith("references/outline-linear.md") for path in batch.actions[0].read)

    plans = two_scenes_after_cp2(tmp_path)
    batch = driver.next_actions(tmp_path)  # CP2 approved, audio there: s01's code, one file for the scene
    assert batch.parallel is False
    assert [(a.agent, a.target) for a in batch.actions] == [("scene-builder", "s01")]
    assert batch.actions[0].before == "text-2-shorts task . s01"

    from schemas.plans import ScenePlan

    scene_plan = ScenePlan.model_validate(plans[0])
    for clip in scene_plan.clips:
        key = fingerprints.clip_key(tmp_path, scene_plan, clip)
        ledger.update_state(
            tmp_path, lambda state, c=clip, k=key: state.clips.__setitem__(c.clip_id, ClipBuild(status="READY", key=k))
        )
    batch = driver.next_actions(tmp_path)
    assert batch.actions[0].command == "text-2-shorts preview . s01"  # s02 waits for s01


def test_requirements_end_with_a_topic_list_and_the_content_the_outline_is_built_from(tmp_path):
    write_brief(tmp_path)
    write_requirements(tmp_path)
    assert validation.validate_topics(tmp_path) == [] and validation.validate_content(tmp_path) == []
    (tmp_path / "topics.md").write_text("1. Why the question matters\n3. The core idea\n")
    assert any("numbered" in error for error in validation.validate_topics(tmp_path))
    write_requirements(tmp_path)
    (tmp_path / "content.md").write_text("## Why the question matters\nText.\n")
    assert any("The core idea" in error for error in validation.validate_content(tmp_path))


def test_the_outline_follows_its_approach_model_and_rules(tmp_path):
    write_brief(tmp_path)
    write_requirements(tmp_path)

    def errors_with(change, approach="linear"):
        write_brief(tmp_path, approach=approach)
        confirm_requirements(tmp_path)  # the brief changed: confirmed again
        outline = make_outline(30, 30, 30)
        change(outline)
        write_json_file(tmp_path / "outline.json", outline)
        return " | ".join(validation.validate_outline(tmp_path))

    segments = lambda outline: outline["outline"]
    assert errors_with(lambda o: None) == ""
    assert "hook" in errors_with(lambda o: segments(o)[0].update(segment_type="concept"))  # A7: hook first
    assert "order" in errors_with(lambda o: segments(o)[1].update(segment_type="recap"))  # A2 relative order
    assert "10" in errors_with(lambda o: segments(o)[1].update(duration_seconds=5))  # G2
    assert "transition_to_next" in errors_with(lambda o: segments(o)[0].update(transition_to_next=None))  # S13
    assert "sentences" in errors_with(
        lambda o: segments(o)[1].update(visual_plan="The scene opens on an empty canvas. The scene ends with a dot.")
    )  # VP2
    assert "The scene ends with" in errors_with(
        lambda o: segments(o)[1].update(
            visual_plan=segments(o)[1]["visual_plan"].replace("The scene ends with", "Finally")
        )
    )  # VP4
    assert "double quotes" in errors_with(
        lambda o: segments(o)[1].update(visual_plan=segments(o)[1]["visual_plan"].replace("Element 3", 'Label "x"'))
    )  # VP5
    assert "visual_plan" in errors_with(lambda o: segments(o)[1].pop("visual_plan"))  # the model's schema
    assert "visualization" in errors_with(lambda o: segments(o)[1].update(segment_type="visualization"), "arc")
    assert "recap" in errors_with(lambda o: None, "zoom")  # C2: the zoom-out recap closes the video


def test_the_script_waits_for_cp0_and_narrates_every_outline_segment_in_order(tmp_path):
    write_brief(tmp_path, objectives=["understand the topic"])
    write_requirements(tmp_path)
    confirm_requirements(tmp_path)
    write_json_file(tmp_path / "outline.json", make_outline(30))
    write_json_file(tmp_path / "script.json", make_script(30, 30))
    assert any("CP0" in error for error in validation.validate_script(tmp_path))
    approve(tmp_path, "outline")
    assert validation.validate_script(tmp_path) == []
    script = make_script(30, 30)
    script["scenes"][1]["outline_segment"] = 2
    write_json_file(tmp_path / "script.json", script)
    assert any("outline_segment" in error for error in validation.validate_script(tmp_path))


def feedback(run, target, kind, text, checkpoint=None):
    workflow_commands.handle_feedback_command(
        argparse.Namespace(run=str(run), target=target, kind=kind, text=text, checkpoint=checkpoint)
    )


def test_change_requests_are_validated_routed_and_resolved(tmp_path):
    write_brief(tmp_path, objectives=["understand the topic"])
    approved_outline(tmp_path, (30, 30))
    write_json_file(tmp_path / "script.json", make_script(30, 30))
    write_json_file(tmp_path / "script_review.json", {"findings": []})
    feedback(tmp_path, "s02", "wording", "say 'orbit' instead of 'path'", checkpoint="script")
    request = change_requests.load_requests(tmp_path)[0]
    assert (request.id, request.status, request.kind) == ("r001", "open", "wording")
    with pytest.raises(SystemExit, match="r001"):
        approve(tmp_path, "script")  # an open request blocks its checkpoint
    write_critique(tmp_path, "script", "script", "revise")  # the one critique iteration the request buys
    action = driver.next_actions(tmp_path).actions[0]
    assert "r001" in action.what and (action.agent, action.target) == ("script-writer", "script")  # routed
    workflow_commands.handle_resolve_command(
        argparse.Namespace(run=str(tmp_path), id="r001", status="applied", note="done")
    )
    assert change_requests.load_requests(tmp_path)[0].status == "applied"
    approve(tmp_path, "script")
    with pytest.raises(SystemExit):
        feedback(tmp_path, "s02", "colour", "brighter")  # not a known kind


def test_checkpoint_decisions_record_how_the_user_decided(tmp_path):
    write_brief(tmp_path, objectives=["understand the topic"])
    approved_outline(tmp_path, (30, 30))
    write_json_file(tmp_path / "script.json", make_script(30, 30))
    write_json_file(tmp_path / "script_review.json", {"findings": []})
    feedback(tmp_path, "script", "style", "a bit warmer", checkpoint="script")
    write_critique(tmp_path, "script", "script", "pass")
    workflow_commands.handle_resolve_command(
        argparse.Namespace(run=str(tmp_path), id="r001", status="declined", note="the user kept it")
    )
    workflow_commands.handle_approve_command(
        argparse.Namespace(run=str(tmp_path), target="script", force=False, notes="good pacing")
    )
    decisions = ledger.load_decisions(tmp_path)
    assert [(d.checkpoint, d.decision) for d in decisions] == [
        ("template", "approved"),
        ("requirements", "approved"),
        ("outline", "approved"),
        ("script", "changes_requested"),
        ("script", "approved_with_notes"),
    ]
    assert decisions[3].requests == ["r001"] and decisions[4].notes == "good pacing"


def test_a_visual_request_for_a_clip_is_resolved_when_the_clip_is_rebuilt(tmp_path):
    two_scenes_after_cp2(tmp_path)
    feedback(tmp_path, "s01c02", "visual", "make the label larger")
    change_requests.resolve_clip_requests(tmp_path, "s01c02")
    request = change_requests.load_requests(tmp_path)[0]
    assert request.status == "applied" and "rebuilt" in request.note


def test_standing_preferences_and_the_template_shape_every_stage(tmp_path):
    from app import narration
    from schemas.plans import ScenePlan

    plans = two_scenes_after_cp2(tmp_path)
    plan = ScenePlan.model_validate(plans[0])
    key_before = fingerprints.clip_key(tmp_path, plan, plan.clips[0])
    write_json_file(tmp_path / "preferences.json", {"tone": "warm", "pause_ms": 800, "confirm_each_scene": True})
    assert preferences.validate_preferences(tmp_path) == []
    templates.choose_template(tmp_path, "standard", ["accent_color=coral", "speaking_speed=slow"])
    approve(tmp_path, "template")
    assert fingerprints.clip_key(tmp_path, plan, plan.clips[0]) != key_before  # new look → rebuild
    speech = preferences.clip_speech(tmp_path, '<speak>Look [pause] here</speak>', set())
    assert speech == '<speak><prosody rate="90%">Look <break time="800ms"/> here</prosody></speak>'  # slow = 90%
    assert narration.ssml_problems(speech) == []
    batch = driver.next_actions(tmp_path)  # confirm_each_scene: ask before producing s01
    assert batch.actions[0].do == "ask_user" and "start:s01" in batch.actions[0].what
    write_json_file(tmp_path / "preferences.json", {"palette": {"focus": "RED"}})  # the template owns colours now
    assert preferences.validate_preferences(tmp_path)


def test_one_script_critique_iteration_runs_for_each_change_request_at_cp1(tmp_path):
    write_brief(tmp_path, objectives=["understand the topic"])
    approved_outline(tmp_path, (30, 30))
    script = make_script(30, 30)
    write_json_file(tmp_path / "script.json", script)
    write_json_file(tmp_path / "script_review.json", {"findings": []})
    assert driver.next_actions(tmp_path).actions[0].do == "ask_user"  # no critique unless asked: CP1 now

    feedback(tmp_path, "s02", "wording", "shorter sentences", checkpoint="script")
    batch = driver.next_actions(tmp_path)  # critique first, then the refactor (PRD §7)
    assert (batch.actions[0].agent, batch.actions[0].target) == ("script-critic", "script")
    with pytest.raises(SystemExit, match="script_critique"):
        approve(tmp_path, "script")
    write_critique(tmp_path, "script", "script", "revise")
    action = driver.next_actions(tmp_path).actions[0]
    assert (action.agent, action.target) == ("script-writer", "script") and "r001" in action.what  # refactor
    assert action.what.index("script_critique.json") < action.what.index("resolve")  # fix first, resolve last
    workflow_commands.handle_resolve_command(
        argparse.Namespace(run=str(tmp_path), id="r001", status="applied", note="")
    )
    approve(tmp_path, "script")  # one iteration only, then the user decides

    write_critique(tmp_path, "script", "script", "revise", "revise")
    assert any(
        "one critique round per change request" in e for e in critiques.validate_critique(tmp_path, "script", "script")
    )


def video_round(run, verdict, score=None, issues=()):
    round_ = {
        "reviewed": critiques.critique_subject_hash(run, "s01", "video"),
        "verdict": verdict,
        "summary": "what the round found and why",
        "issues": list(issues),
    }
    write_json_file(
        run / "scenes" / "s01" / "video_critique.json",
        {"rounds": [round_ | ({} if score is None else {"score": score})]},
    )
    return critiques.validate_critique(run, "s01", "video")


def test_critique_rounds_are_scored_from_their_tiers_against_the_preferred_threshold(tmp_path):
    two_scenes_after_cp2(tmp_path)
    good, other_good = critique_issue("video", "s01c01", "good"), critique_issue("video", "s01c02", "good", "V-G2")
    assert any("score" in error for error in video_round(tmp_path, "pass"))  # every round is scored
    assert any("90" in error for error in video_round(tmp_path, "pass", 100, [good]))  # 100 − 10 per good to have
    assert video_round(tmp_path, "pass", 90, [good]) == []  # a pass may carry suggestions
    assert any("threshold 85" in error for error in video_round(tmp_path, "pass", 80, [good, other_good]))
    assert any(
        "threshold 85" in error
        for error in video_round(tmp_path, "revise", 97, [critique_issue("video", "s01c01", "great")])
    )
    write_json_file(tmp_path / "preferences.json", {"quality_threshold": 75})
    assert video_round(tmp_path, "pass", 80, [good, other_good]) == []


def test_an_open_basic_need_always_means_revise(tmp_path):
    two_scenes_after_cp2(tmp_path)
    write_json_file(tmp_path / "preferences.json", {"quality_threshold": 70})
    basic = critique_issue("video", "s01c01", "basic", "V-B3")
    assert any("basic" in error for error in video_round(tmp_path, "pass", 75, [basic]))  # 75 ≥ 70 is not enough
    assert video_round(tmp_path, "revise", 75, [basic]) == []


def test_critique_issues_name_a_criterion_of_their_own_critic_and_tier(tmp_path):
    two_scenes_after_cp2(tmp_path)
    assert any(
        "good" in e for e in video_round(tmp_path, "revise", 75, [critique_issue("video", "s01c01", "basic", "V-G3")])
    )
    assert any(
        "P-B1" in e for e in video_round(tmp_path, "revise", 75, [critique_issue("video", "s01c01", "basic", "P-B1")])
    )
    wrong_aspect = critique_issue("video", "s01c01", "basic", aspect="tone")
    assert any("tone" in e for e in video_round(tmp_path, "revise", 75, [wrong_aspect]))


CHANGE = {
    "target": "s01c01",
    "iteration": 1,
    "issue": "unclear beat",
    "findings": ["s01c01 clarity: unclear beat"],
    "modification": "named the object in the beat",
    "files_changed": ["scenes/s01/scene_code.py"],
    "rendering_changes": "label added above the circle",
    "audio_timing_changes": "none",
    "sync_adjustments": "none",
    "validation_results": "accept READY",
    "final_score": 90,
}


def test_every_video_refactor_iteration_is_recorded_before_cp3(tmp_path):
    two_scenes_after_cp2(tmp_path)
    write_critique(tmp_path, "s01", "video", "revise", "pass")
    assert any("changes.json" in p for p in critiques.critique_problems(tmp_path, "s01", "video"))
    write_json_file(tmp_path / "scenes" / "s01" / "changes.json", {"entries": [CHANGE | {"iteration": 4}]})
    assert critiques.validate_changes(tmp_path, "s01")  # iterations are 1–3
    write_json_file(tmp_path / "scenes" / "s01" / "changes.json", {"entries": [CHANGE]})
    assert critiques.validate_changes(tmp_path, "s01") == []
    assert critiques.critique_problems(tmp_path, "s01", "video") == []
    text = critiques.write_changes_text(tmp_path).read_text()
    assert "s01c01 — iteration 1" in text and "named the object in the beat" in text

    write_critique(tmp_path, "s01", "video", "revise", "revise", "revise")  # three rounds below the threshold
    problems = critiques.critique_problems(tmp_path, "s01", "video")
    assert any("iteration 2" in p for p in problems)  # every refactor between rounds is recorded
    write_json_file(tmp_path / "scenes" / "s01" / "changes.json", {"entries": [CHANGE, CHANGE | {"iteration": 2}]})
    assert ["REQUIRES ATTENTION" in p for p in critiques.critique_problems(tmp_path, "s01", "video")] == [True]


def test_every_stage_scene_and_clip_has_a_status_kept_in_state_json(tmp_path):
    write_brief(tmp_path, objectives=["understand the topic"])
    approved_outline(tmp_path, (30, 30))
    statuses = status.update_statuses(tmp_path)
    assert (statuses["outline"], statuses["script"], statuses["final"]) == ("approved", "pending", "pending")
    write_json_file(tmp_path / "script.json", {"scenes": []})
    assert status.update_statuses(tmp_path)["script"] == "in_progress"  # written, not valid yet
    write_json_file(tmp_path / "script.json", make_script(30, 30))
    write_json_file(tmp_path / "script_review.json", {"findings": []})
    assert status.update_statuses(tmp_path)["script"] == "requires_user_approval"
    feedback(tmp_path, "s02", "wording", "shorter", checkpoint="script")
    status.update_statuses(tmp_path)
    assert ledger.load_state(tmp_path).status["script"] == "requires_refactoring"  # persisted
    assert "script: requires_refactoring" in status.status_text(tmp_path)


def test_clip_and_scene_statuses_follow_the_build(tmp_path):
    two_scenes_after_cp2(tmp_path)
    statuses = status.update_statuses(tmp_path)
    assert (statuses["plan"], statuses["s01"], statuses["s01c01"]) == ("approved", "pending", "pending")
    ledger.update_state(tmp_path, lambda state: state.clips.__setitem__("s01c01", ClipBuild(status="FAILED")))
    statuses = status.update_statuses(tmp_path)
    assert (statuses["s01"], statuses["s01c01"]) == ("failed", "failed")


def test_requirements_capture_depth_and_expectations_and_are_confirmed_at_their_checkpoint(tmp_path):
    write_brief(
        tmp_path,
        detail_level="detailed",
        explanation_depth="rigorous",
        technical_complexity="advanced",
        visual_expectations="clean diagrams, no clutter",
        audio_expectations="calm voice, light music",
    )
    assert validation.validate_brief(tmp_path) == []
    write_brief(tmp_path, detail_level="enormous")
    assert validation.validate_brief(tmp_path)
    write_brief(tmp_path)
    write_requirements(tmp_path)
    write_json_file(tmp_path / "outline.json", make_outline(30, 30))
    assert any("template" in error for error in validation.validate_outline(tmp_path))  # the look comes first
    assert "Look & sound" in driver.next_actions(tmp_path).actions[0].what
    with pytest.raises(SystemExit, match="template"):  # and requirements cannot be approved before it
        approve(tmp_path, "requirements")
    templates.choose_template(tmp_path, "standard", [])
    approve(tmp_path, "template")
    assert driver.next_actions(tmp_path).actions[0].do == "ask_user"
    assert any("requirements" in error for error in validation.validate_outline(tmp_path))  # then the requirements


def test_a_template_is_chosen_from_the_library_customised_and_approved(tmp_path):
    assert {"standard", "chalkboard", "paper", "blueprint"} <= set(templates.template_names())
    write_brief(tmp_path, objectives=["understand the topic"])
    write_requirements(tmp_path)
    assert "Look & sound" in driver.next_actions(tmp_path).actions[0].what  # the first stage
    with pytest.raises(SystemExit, match="nope"):
        templates.choose_template(tmp_path, "nope", [])
    with pytest.raises(SystemExit, match="grid_type"):
        templates.choose_template(tmp_path, "paper", ["grid_type=hexagons"])  # not a variant
    with pytest.raises(SystemExit, match="contrast"):  # the user's own colour, unreadable under white text
        templates.choose_template(tmp_path, "standard", ["custom.background_color=#ffffff"])
    templates.choose_template(
        tmp_path,
        "paper",
        ["accent_color=coral", "custom.text_font=Lato", "custom.voice=Joanna", "transition_seconds=0.8"],
    )
    template = json.loads((tmp_path / "template.json").read_text())
    assert (template["name"], template["elements"]["accent_color"], template["transition_seconds"]) == (
        "paper",
        "coral",
        0.8,
    )
    view = templates.look_view(tmp_path)  # the website reads back exactly what was chosen
    assert view.saved and view.custom == {"text_font": "Lato", "voice": "Joanna"}
    assert templates.look(tmp_path)["font"] == "Lato" and templates.sound(tmp_path)["voice"] == "Joanna"
    assert "font=\"Lato\"" in templates.look_brief(tmp_path)  # what every clip's TASK.md says
    approve(tmp_path, "template")
    approve(tmp_path, "requirements")
    write_json_file(tmp_path / "outline.json", make_outline(30, 30))
    assert validation.validate_outline(tmp_path) == []


def test_script_scenes_name_their_on_screen_text_animations_audio_transitions_and_dependencies(tmp_path):
    write_brief(tmp_path, objectives=["understand the topic"])
    approved_outline(tmp_path, (30, 30))
    script = make_script(30, 30)
    script["scenes"][1] |= {
        "on_screen_text": ["F = ma"],
        "animations": ["the force arrow grows"],
        "audio_requirements": "a short pause after the formula",
        "transition_requirements": "the index list shrinks into the corner",
        "depends_on": ["s01"],
    }
    write_json_file(tmp_path / "script.json", script)
    assert validation.validate_script(tmp_path) == []
    script["scenes"][0]["depends_on"] = ["s02"]
    write_json_file(tmp_path / "script.json", script)
    assert any("earlier scenes" in error for error in validation.validate_script(tmp_path))
    script["scenes"][0]["depends_on"] = []
    write_json_file(tmp_path / "script.json", script)
    write_json_file(tmp_path / "script_review.json", {"findings": []})
    approve(tmp_path, "script")
    plan = make_plan(script, 2)
    write_json_file(tmp_path / "scenes" / "s02" / "plan.json", plan)
    assert any("F = ma" in error for error in validation.validate_plan(tmp_path, "s02"))  # the plan must show it
    plan["clips"][0]["on_screen_math"] = ["F = ma"]
    write_json_file(tmp_path / "scenes" / "s02" / "plan.json", plan)
    assert validation.validate_plan(tmp_path, "s02") == []


def test_delivery_checks_cover_silence_peaks_decoding_duration_and_completeness(tmp_path):
    import subprocess

    from schemas.plans import ScenePlan

    video = tmp_path / "final.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=320x240:r=30:d=4"]
        + ["-f", "lavfi", "-i", "sine=frequency=440:duration=4,volume=8", "-filter_complex"]
        + ["[1:a]afade=t=out:st=1:d=0.1[a]", "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-c:a", "aac"]
        + [str(video)],
        check=True,
    )
    codes = {finding.code for finding in production.check_final_media(video)}
    assert {"RESOLUTION", "ASPECT_RATIO", "SILENCE", "TRUE_PEAK"} <= codes and "DECODE_ERRORS" not in codes

    script = approved_script_run(tmp_path, 30, 30)
    plans = [ScenePlan.model_validate(make_plan(script, number)) for number in (1, 2)]
    mux = ClipMux(video_s=30, audio_s=29, out_s=30, video_padded_s=0, audio_padded_s=1)
    report = FinalReport(clips={"s01c01": mux}, final_s=30.0, sum_clips_s=30.0)  # s02c01 missing; 30 s of 60 s
    codes = {finding.code for finding in production.check_delivery(tmp_path, plans, report)}
    assert codes == {"MISSING_CLIPS", "DURATION"}


def test_sound_effects_and_music_come_from_the_users_own_files(tmp_path):
    two_scenes_after_cp2(tmp_path)
    plan = json.loads((tmp_path / "scenes" / "s01" / "plan.json").read_text())
    plan["clips"][0]["sound_effects"] = [{"file": "assets/pop.mp3", "at": 0.5}]
    write_json_file(tmp_path / "scenes" / "s01" / "plan.json", plan)
    assert any("assets/pop.mp3" in error for error in validation.validate_plan(tmp_path, "s01"))
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "pop.mp3").write_bytes(b"x")
    assert validation.validate_plan(tmp_path, "s01") == []
    with pytest.raises(SystemExit, match="music"):
        templates.choose_template(tmp_path, "standard", ["music=assets/song.mp3"])
    (tmp_path / "assets" / "song.mp3").write_bytes(b"x")
    templates.choose_template(tmp_path, "standard", ["music=assets/song.mp3"])
    assert templates.validate_template(tmp_path) == []


def test_scene_plans_are_written_and_refactored_by_the_scene_planner(tmp_path):
    approved_script_run(tmp_path, 30, 30)
    action = driver.next_actions(tmp_path).actions[0]
    assert (action.do, action.agent, action.target) == ("subagent", "scene-planner", "s01")
    plans_ready_for_cp2(tmp_path)
    write_critique(tmp_path, "s01", "plan", "revise")
    refactor = driver.next_actions(tmp_path).actions[0]
    assert (refactor.agent, refactor.target) == ("scene-planner", "s01")
    write_critique(tmp_path, "s01", "plan", "pass")
    feedback(tmp_path, "s02", "visual", "bigger diagram")
    route = driver.next_actions(tmp_path).actions[0]
    assert (route.agent, route.target) == ("scene-planner", "s02") and "r001" in route.what


def test_outline_and_script_are_built_and_refactored_by_the_script_writer_never_the_session(tmp_path):
    import inspect
    import re

    two_scenes_after_cp2(tmp_path)
    for target, kind in [("outline", "structure"), ("script", "wording"), ("s01", "accuracy")]:
        request = change_requests.record_change_request(tmp_path, target, kind, "say it more simply", "script")
        action = change_requests.request_route(tmp_path, request)
        assert action is not None and (action.do, action.agent) == ("subagent", "script-writer"), (target, kind)
    source = inspect.getsource(driver) + inspect.getsource(change_requests)
    session_writes = re.findall(r'"file": "([^"]+)"|file="([^"]+)"', source)
    built = {"outline.json", "script.json", "scenes/*/plan.json"}
    assert not built & {name for pair in session_writes for name in pair}, session_writes


def test_every_starter_template_is_usable_in_dark_and_light_mode():
    import video_settings

    for name in templates.template_names():
        for mode in ("dark", "light"):
            template = video_settings.starter(name)
            template["elements"]["theme_mode"] = mode
            assert video_settings.problems(template) == [], (name, mode)
            assert video_settings.settings(template)["background"].startswith("#")


def test_a_custom_background_can_be_one_colour_or_a_gradient(tmp_path):
    write_brief(tmp_path)
    templates.choose_template(
        tmp_path, "standard", ["background_type=gradient", "custom.background_color=#101820,#000000"]
    )
    assert templates.look_view(tmp_path).custom == {"background_color": "#101820,#000000"}  # read back as entered
    assert templates.drawing(tmp_path)["background"]["shade"] == "#000000"  # the gradient's bottom
    with pytest.raises(SystemExit, match="RRGGBB"):
        templates.choose_template(tmp_path, "standard", ["custom.background_color=#101820,black"])


def test_a_reshuffle_is_deterministic_recolours_built_clips_and_keeps_them_built(tmp_path):
    import video_settings
    from app.workflow import reshuffle
    from schemas.plans import ScenePlan

    starter = video_settings.starter("standard")
    first = video_settings.reshuffle(starter, 7, ["colours", "fonts"])
    assert first == video_settings.reshuffle(starter, 7, ["fonts", "colours"])  # same seed → same look
    assert first != video_settings.reshuffle(starter, 8, ["colours", "fonts"])
    assert first["elements"]["typography"] == starter["elements"]["typography"]  # sizes, so layouts, never change
    assert video_settings.problems(first) == []
    with pytest.raises(ValueError, match="sizes"):
        video_settings.reshuffle(starter, 7, ["sizes"])

    before = {"roles": {"text": "#FFFFFF", "focus": "#FFD54F"}, "font": "Inter"}
    after = {"roles": {"text": "#111111", "focus": "#2962FF"}, "font": "Lato"}
    code = 'Text("a", color="#ffd54f", font="Inter"); Dot(color="#FFFFFF"); keep="#FFD54F80"; other="#123456"'
    assert reshuffle.recolour(code, before, after) == (
        'Text("a", color="#2962FF", font="Lato"); Dot(color="#111111"); keep="#FFD54F80"; other="#123456"'
    )

    plans = [ScenePlan.model_validate(plan) for plan in two_scenes_after_cp2(tmp_path)]
    clip = plans[0].clips[0]
    clip_file = tmp_path / "scenes" / "s01" / "scene_code.py"
    clip_file.parent.mkdir(parents=True, exist_ok=True)
    text_colour = templates.look(tmp_path)["roles"]["text"]
    clip_file.write_text(f'Text("x", color="{text_colour}")')
    ledger.update_state(
        tmp_path,
        lambda state: state.clips.__setitem__(
            clip.clip_id, ClipBuild(status="READY", key=fingerprints.clip_key(tmp_path, plans[0], clip))
        ),
    )
    (tmp_path / "final.mp4").write_bytes(b"old")
    look_before, code_before = templates.look(tmp_path), clip_file.read_text()
    assert reshuffle.apply(tmp_path, 7, ["colours"]) == []
    assert clip_file.read_text() == reshuffle.recolour(code_before, look_before, templates.look(tmp_path))
    build = ledger.load_state(tmp_path).clips[clip.clip_id]
    assert build.key == fingerprints.clip_key(tmp_path, plans[0], clip)  # still built: no Claude rebuild
    assert (tmp_path / "versions" / "final-before-reshuffle-7.mp4").read_bytes() == b"old"
    assert ledger.is_approval_current(
        ledger.load_state(tmp_path), "template", fingerprints.template_fingerprint(tmp_path)
    )


def test_runtime_commands_log_into_the_run_and_never_to_stderr(tmp_path, capsys):
    import logging

    import faraday_logging

    path = faraday_logging.configure("runtime", tmp_path, console=False)
    logging.getLogger("app.cli").warning("approve stopped: CP0 is not approved")
    assert path == tmp_path / "logs" / "runtime.log"
    assert "WARNING runtime  app.cli  approve stopped" in path.read_text()
    assert capsys.readouterr().err == ""  # the session's context stays clean
    blocked = tmp_path / "file"
    blocked.write_text("")
    assert faraday_logging.configure("runtime", blocked, console=False) is None  # unwritable: skipped, not fatal
    for handler in list(logging.getLogger().handlers):
        if getattr(handler, "_faraday", False):
            logging.getLogger().removeHandler(handler)


def test_dark_mode_is_deep_and_light_mode_is_pastel_and_everything_stays_readable():
    import video_settings as v

    for name in v.starter_names():
        for mode in ("dark", "light"):
            template = v.starter(name)
            template["elements"] |= {"theme_mode": mode, "subtitles": "on"}
            look, drawing = v.resolve(template), v.drawing(template)
            ground, roles = look["background"]["base"], look["roles"]
            _, lightness, saturation = v.hls(ground)
            if mode == "dark":
                assert lightness <= 0.16, (name, ground)  # a deep shade
            elif saturation >= v.NEUTRAL:
                assert lightness >= 0.9, (name, ground)  # a pale pastel of the template's own hue
                assert all(v.hls(roles[role])[2] <= 0.6 + 1e-6 for role in v.GRAPHIC_ROLES if role in roles)  # soft
            assert v.contrast(roles["text"], ground) >= 7, (name, mode)
            assert all(v.contrast(roles[role], ground) >= 3 for role in v.GRAPHIC_ROLES if role in roles), (name, mode)
            subtitles = drawing["subtitles"]
            box = subtitles["style"].get("box")
            behind = box["color"] if box and box.get("opacity", 1) >= 0.6 else ground
            assert v.contrast(subtitles["text_color"], behind) >= 4.5, (name, mode)
    own = v.starter("standard")
    own["elements"]["theme_mode"] = "light"
    own["overrides"] = {"accent_color": v.custom_override("accent_color", "#123456", "light")}
    assert v.resolve(own)["roles"]["accent"] == "#123456"  # the user's own colour is never toned


def test_the_visual_director_task_is_filled_from_the_run_and_its_plan_lives_in_plan_json(tmp_path):
    from pathlib import Path

    from app.workflow import visual_director

    script = approved_script_run(tmp_path, 30, 30)
    task = visual_director.task(tmp_path, "s02")
    assert "__SCENE_ID__" not in task and "__TARGET_DURATION__" not in task  # str.replace filled both tokens
    assert "Scene Execution Plan for s02" in task and "### TARGET_DURATION\n30 seconds" in task
    assert script["scenes"][1]["narration"].split()[0] in task and "COLOUR ROLES" in task  # narration, TEMPLATE
    read_first = task.splitlines()[0].removeprefix("READ FIRST, in this order: ").split(", ")
    assert [Path(path).name for path in read_first] == [
        "visual-director-system.md",
        "manim-construction-patterns.md",
        "manim-vocabulary.md",
        "manim-common-mistakes.md",
    ] and all(Path(path).exists() for path in read_first)
    assert not (tmp_path / "scenes").exists()  # nothing written: the planner reads the printed task

    plan = make_plan(script, 1, clip_count=2)
    write_json_file(tmp_path / "scenes" / "s01" / "plan.json", plan)
    assert validation.validate_plan(tmp_path, "s01") == []
    for broken, message in [
        (plan["execution_plan"].replace("<CAMERA_SCRIPT>", "<CAMERA>"), "CAMERA_SCRIPT"),
        (plan["execution_plan"].replace("CLIP 2 ", "CLIP 3 "), "one block each"),
        ("", "plan-task"),
    ]:
        write_json_file(tmp_path / "scenes" / "s01" / "plan.json", {**plan, "execution_plan": broken})
        assert any(message in error for error in validation.validate_plan(tmp_path, "s01")), message
    assert "CLIP 2" in visual_director.clip_block(plan["execution_plan"], 2)
