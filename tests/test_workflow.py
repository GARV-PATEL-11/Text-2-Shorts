"""The production workflow is enforced in order: requirements → complete script (CP1) → scene-wise visual plans
(CP2) → clip-wise code. Every stage has a gate, and downstream stages refuse to start before upstream approval."""

import argparse

import pytest
from conftest import approve, make_plan, make_script, write_brief, write_critique, write_json_file

from app import run_steps


def approved_script_run(run, *scene_seconds):
    write_brief(run, objectives=["understand the topic"])
    script = make_script(*scene_seconds)
    write_json_file(run / "script.json", script)
    write_json_file(run / "script_review.json", {"findings": []})
    approve(run, "script")
    return script


def test_brief_is_validated(tmp_path):
    write_brief(tmp_path, objectives=["see why orbits are ellipses"], style="ELI5")
    assert run_steps.validate_brief(tmp_path) == []
    write_json_file(tmp_path / "brief.json", {"approach": "zoom", "minutes": 1})
    assert any("requirement" in error for error in run_steps.validate_brief(tmp_path))


def test_script_covers_every_objective_bridges_scenes_and_fits_its_word_budget(tmp_path):
    write_brief(tmp_path, objectives=["understand the topic"])
    script = make_script(30, 30)
    write_json_file(tmp_path / "script.json", script)
    assert run_steps.validate_script(tmp_path) == []

    def errors_with(change):
        changed = make_script(30, 30)
        change(changed)
        write_json_file(tmp_path / "script.json", changed)
        return " | ".join(run_steps.validate_script(tmp_path))

    assert "not covered" in errors_with(lambda s: s["objectives"].append("a second objective"))
    assert "bridge_in" in errors_with(lambda s: s["scenes"][1].update(bridge_in=""))  # scene 2 needs a bridge
    assert "bridge_in" in errors_with(lambda s: s["scenes"][0].update(bridge_in="hello"))  # scene 1 has none
    assert "words" in errors_with(lambda s: s["scenes"][0].update(narration="far too short"))
    assert "±20%" in errors_with(lambda s: [scene.update(duration_seconds=60) for scene in s["scenes"]])
    write_brief(tmp_path, objectives=["an objective the script dropped"])
    write_json_file(tmp_path / "script.json", script)
    assert any("an objective the script dropped" in error for error in run_steps.validate_script(tmp_path))


def test_scene_plans_wait_for_the_approved_script_and_must_follow_it(tmp_path):
    write_brief(tmp_path, objectives=["understand the topic"])
    script = make_script(30, 30)
    write_json_file(tmp_path / "script.json", script)
    write_json_file(tmp_path / "scenes" / "s01" / "plan.json", make_plan(script, 1, clip_count=2))
    assert any("CP1" in error for error in run_steps.validate_plan(tmp_path, "s01"))  # not approved yet

    write_json_file(tmp_path / "script_review.json", {"findings": []})
    approve(tmp_path, "script")
    assert run_steps.validate_plan(tmp_path, "s01") == []

    changed_plan = make_plan(script, 1, clip_count=2)
    changed_plan["clips"][1]["narration"] += " an extra sentence"
    write_json_file(tmp_path / "scenes" / "s01" / "plan.json", changed_plan)
    assert any("script" in error and "narration" in error for error in run_steps.validate_plan(tmp_path, "s01"))

    second_plan = make_plan(script, 2)
    second_plan["transition_in"] = ""
    write_json_file(tmp_path / "scenes" / "s02" / "plan.json", second_plan)
    assert any("transition_in" in error for error in run_steps.validate_plan(tmp_path, "s02"))

    script["scenes"][0]["title"] = "renamed after approval"
    write_json_file(tmp_path / "script.json", script)
    assert any("CP1" in error for error in run_steps.validate_plan(tmp_path, "s02"))  # approval is now stale


def test_plans_keep_scene_boundaries_empty_and_one_colour_per_symbol(tmp_path):
    script = approved_script_run(tmp_path, 30, 30)
    first = {**make_plan(script, 1), "color_roles": {"a": "BLUE"}}
    second: dict = {**make_plan(script, 2), "color_roles": {"a": "RED"}}
    second["clips"][0]["entry"] = {"persistent_objects": ["x"]}
    write_json_file(tmp_path / "scenes" / "s01" / "plan.json", first)
    write_json_file(tmp_path / "scenes" / "s02" / "plan.json", second)
    errors = " | ".join(run_steps.validate_plan(tmp_path, "s02"))
    assert "entry must be empty" in errors and "`a`" in errors and "BLUE" in errors


def test_accuracy_reviews_point_at_real_scenes_and_clips_and_errors_block_approval(tmp_path):
    write_brief(tmp_path, objectives=["understand the topic"])
    script = make_script(30, 30)
    write_json_file(tmp_path / "script.json", script)
    finding = {"severity": "ERROR", "kind": "FALSE", "quote": "q", "why": "w", "fix": "f"}
    write_json_file(tmp_path / "script_review.json", {"findings": [{**finding, "target": "s09"}]})
    assert any("s09" in error for error in run_steps.validate_review(tmp_path, "script"))
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
    assert any("s01c09" in error for error in run_steps.validate_review(tmp_path, "plan"))
    write_json_file(tmp_path / "plan_review.json", {"findings": [{**finding, "target": "s01c01", "severity": "WARN"}]})
    for scene_id in ("s01", "s02"):
        write_critique(tmp_path, scene_id, "plan", "pass")
    approve(tmp_path, "plan")


def test_voice_and_clip_tasks_wait_for_the_approved_plans(tmp_path):
    script = approved_script_run(tmp_path, 30, 30)
    for number in (1, 2):
        write_json_file(tmp_path / "scenes" / f"s{number:02d}" / "plan.json", make_plan(script, number))
    with pytest.raises(SystemExit, match="CP2"):
        run_steps.handle_voice_command(argparse.Namespace(run=str(tmp_path)))
    with pytest.raises(SystemExit, match="CP2"):
        run_steps.prepare_clip(tmp_path, "s01c01")

    write_json_file(tmp_path / "plan_review.json", {"findings": []})
    for scene_id in ("s01", "s02"):
        write_critique(tmp_path, scene_id, "plan", "pass")
    approve(tmp_path, "plan")
    edited = make_plan(script, 1)
    edited["composition"] = "changed after approval"
    write_json_file(tmp_path / "scenes" / "s01" / "plan.json", edited)
    with pytest.raises(SystemExit, match="CP2"):  # a plan edited after CP2 needs CP2 again
        run_steps.prepare_clip(tmp_path, "s01c01")


def test_next_steps_follow_the_stage_order(tmp_path):
    write_brief(tmp_path, objectives=["understand the topic"])
    steps = run_steps.next_steps(tmp_path)
    assert "script.json" in steps[0] and not any("plan" in step or "CP2" in step for step in steps)

    script = make_script(30, 30)
    write_json_file(tmp_path / "script.json", script)
    steps = run_steps.next_steps(tmp_path)
    assert any("script_review.json" in step for step in steps) and any(step.startswith("CP1") for step in steps)
    assert not any(step.startswith("s01") for step in steps)  # no visual planning before CP1

    write_json_file(tmp_path / "script_review.json", {"findings": []})
    approve(tmp_path, "script")
    steps = run_steps.next_steps(tmp_path)
    assert any(step.startswith("s01 plan") for step in steps) and any(step.startswith("s02 plan") for step in steps)
    assert not any("voice" in step or step.startswith("build") for step in steps)  # no clips before CP2


def test_new_turns_the_requirements_into_a_valid_brief():
    from app import cli
    from schemas.models import Brief

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
    brief = cli.brief_from_arguments(arguments)
    assert brief["objectives"] == ["explain why orbits are ellipses", "use the third law"]
    assert brief["style"] == "story-driven" and brief["approach"] == "creative" and brief["voice"]
    Brief.model_validate(brief)


def test_a_forced_approval_without_a_script_does_not_open_the_next_stage(tmp_path):
    write_brief(tmp_path, objectives=["understand the topic"])
    approve(tmp_path, "script", force=True)  # nothing to approve yet
    assert run_steps.stage_approval_problem(tmp_path, "script")


def test_the_script_opens_with_an_index_scene_that_previews_every_later_scene(tmp_path):
    write_brief(tmp_path, objectives=["understand the topic"])

    def errors_with(change):
        script = make_script(20, 20, 20)
        change(script)
        write_json_file(tmp_path / "script.json", script)
        return " | ".join(run_steps.validate_script(tmp_path))

    assert errors_with(lambda s: None) == ""
    assert "index" in errors_with(lambda s: s["scenes"][0].update(role="content", covers=[1]))
    assert "previews" in errors_with(lambda s: s["scenes"][0].update(previews=["s02"]))  # s03 not previewed
    assert "index" in errors_with(lambda s: s["scenes"][2].update(role="index"))  # only s01 is the index
    assert "covers" in errors_with(lambda s: s["scenes"][1].update(covers=[]))  # teaching scenes cover objectives


def test_there_are_three_fixed_approaches_and_one_creative_one():
    from app import cli
    from schemas.models import Brief

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
    assert run_steps.validate_plan(tmp_path, "s01") == []

    plan["clips"][1]["ssml"] = "<speak>different words</speak>"
    plan["clips"][0]["ssml"] = '<speak><audio src="x.mp3"/>' + " ".join(words) + "</speak>"
    write_json_file(tmp_path / "scenes" / "s01" / "plan.json", plan)
    errors = " | ".join(run_steps.validate_plan(tmp_path, "s01"))
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
    assert any("3 rounds" in error for error in run_steps.validate_critique(tmp_path, "s02", "plan"))
    write_critique(tmp_path, "s02", "plan", "revise", "revise", "revise")
    with pytest.raises(SystemExit, match="open issues"):
        approve(tmp_path, "plan")  # three rounds used: the user decides
    approve(tmp_path, "plan", force=True)


def test_the_sync_report_compares_when_each_phrase_is_spoken_with_when_its_beat_is_shown(tmp_path):
    from schemas.models import ScenePlan

    script = approved_script_run(tmp_path, 30, 30)
    plan = make_plan(script, 1)
    plan["clips"][0]["beats"] = ['"word100" → title appears', '"word105" → circle grows']
    write_json_file(tmp_path / "scenes" / "s01" / "plan.json", plan)
    write_json_file(
        tmp_path / "scenes" / "s01" / "audio" / "index.json",
        {"s01c01": {"hash": "h", "seconds": 3.0, "beat_times": [0.0, 1.5]}},
    )
    write_json_file(
        tmp_path / "scenes" / "s01" / "work" / "clip_01" / "checks" / "probe.json", {"beats": {"1": 0.3, "2": 2.6}}
    )
    (tmp_path / "scenes" / "s01" / "work" / "clip_01" / "CHANGES.md").write_text("circle starts later than planned")

    report = run_steps.sync_report(tmp_path, ScenePlan.model_validate(plan), {"s01c01": 4.1})
    beats = report["clips"][0]["beats"]
    assert [beat["offset"] for beat in beats] == [0.0, 0.8]  # shown − spoken (the voice starts 0.3 s in)
    assert report["in_sync"] is False and report["clips"][0]["audio_fits"] is True
    assert "circle starts later" in report["clips"][0]["changes"]
    assert any("s01c01 beat 2" in problem for problem in report["problems"])


def test_planners_and_critics_can_look_up_manim_names(capsys):
    run_steps.handle_doc_command(argparse.Namespace(names="Axes.plot,Axes.get_graph", topics=""))
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
                    "hash": run_steps.voice_key(run, narration.speakable_ssml(clip["ssml"])),
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
    assert any("s01c02" in error and "descriptions" in error for error in run_steps.validate_plan(tmp_path, "s01"))


def test_clips_of_a_scene_are_prepared_in_parallel_but_scenes_in_series(tmp_path):
    two_scenes_after_cp2(tmp_path)
    work = run_steps.prepare_clip(tmp_path, "s01c02")  # clip_01 is not built: fine, clips are independent
    task = (work / "TASK.md").read_text()
    assert "self.entry(" in task and "Text 'eq' at top_center" in task
    assert not list((work / "scene" / "clips").glob("clip_01.py"))  # built and checked on its own
    with pytest.raises(SystemExit, match="s01.*CP3"):
        run_steps.prepare_clip(tmp_path, "s02c01")  # scenes are produced in series
    with pytest.raises(SystemExit, match="s01.*CP3"):
        run_steps.handle_preview_command(argparse.Namespace(run=str(tmp_path), scene="s02"))


def test_a_clip_does_not_go_stale_when_another_clip_of_its_scene_changes(tmp_path):
    from schemas.models import ScenePlan

    plans = two_scenes_after_cp2(tmp_path)
    plan = ScenePlan.model_validate(plans[0])
    before = run_steps.clip_key(tmp_path, plan, plan.clips[1])
    (tmp_path / "scenes" / "s01" / "clips").mkdir(parents=True, exist_ok=True)
    (tmp_path / "scenes" / "s01" / "clips" / "clip_01.py").write_text("def clip_01(self):\n    pass\n")
    assert run_steps.clip_key(tmp_path, plan, plan.clips[1]) == before


def test_next_hands_out_the_exact_next_batch(tmp_path):
    write_brief(tmp_path, objectives=["understand the topic"])
    batch = run_steps.next_actions(tmp_path)
    assert batch["stage"].startswith("2") and batch["actions"][0]["file"] == "script.json"
    assert any(path.endswith("references/script-writing.md") for path in batch["actions"][0]["read"])

    plans = two_scenes_after_cp2(tmp_path)
    batch = run_steps.next_actions(tmp_path)  # CP2 approved, audio there: build every clip of s01 at once
    assert batch["parallel"] is True
    assert [(a["agent"], a["target"]) for a in batch["actions"]] == [
        ("clip-builder", "s01c01"),
        ("clip-builder", "s01c02"),
    ]
    assert batch["actions"][0]["before"] == "text-2-shorts task . s01c01"

    from schemas.models import ScenePlan

    scene_plan = ScenePlan.model_validate(plans[0])
    for clip in scene_plan.clips:
        key = run_steps.clip_key(tmp_path, scene_plan, clip)
        run_steps.update_state(
            tmp_path, lambda state, c=clip, k=key: state["clips"].__setitem__(c.clip_id, {"status": "READY", "key": k})
        )
    batch = run_steps.next_actions(tmp_path)
    assert batch["actions"][0]["command"] == "text-2-shorts preview . s01"  # s02 waits for s01
