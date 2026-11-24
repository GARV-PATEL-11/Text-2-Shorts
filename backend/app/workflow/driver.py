"""The driver: exactly the next batch of work, in order (the `next` command)."""

from __future__ import annotations

import re
from pathlib import Path

from schemas.session import Action, ActionBatch

from app.config import REFERENCES_DIRECTORY
from app.workflow.artifacts import load_brief, load_final_report, load_scene_plans, load_script
from app.workflow.change_requests import open_requests, request_route
from app.workflow.checkpoints import stage_approval_problem
from app.workflow.critiques import (
    CRITICS,
    critique_file,
    critique_problems,
    critique_state,
    critique_subject_hash,
    review_problems,
    script_critique_problems,
)
from app.workflow.fingerprints import clip_key, fingerprint
from app.workflow.ledger import is_approval_current, load_state
from app.workflow.preferences import load_preferences
from app.workflow.production import preview_problems, stale_audio
from app.workflow.templates import validate_template
from app.workflow.validation import (
    validate_brief,
    validate_content,
    validate_outline,
    validate_plan,
    validate_review,
    validate_script,
    validate_topics,
)


def next_actions(run: Path) -> ActionBatch:
    """The one batch to do now. The session runs it (in parallel when `parallel`), then asks again. Each action names
    who does it (you, a subagent, a command, the user), its target, and the files to read — by path."""

    def references(*names):
        return [str(REFERENCES_DIRECTORY / name) for name in names]

    def batch(stage: str, actions: list, parallel: bool = False) -> ActionBatch:
        typed = [action if isinstance(action, Action) else Action.model_validate(action) for action in actions]
        for action in typed:  # a question the user answers by approving names its checkpoint
            if action.do == "ask_user" and (decided := re.search(r"approve \. ([\w:]+)`", action.what)):
                action.checkpoint = decided[1]
        return ActionBatch(stage=stage, parallel=parallel, actions=typed)

    def reviewer(stage, mode, file, problems):
        if validate_review(run, stage):
            return [{"do": "subagent", "agent": "accuracy-reviewer", "target": mode, "what": f"{mode} mode → {file}"}]
        return [
            {
                "do": "write",
                "file": "script.json" if stage == "script" else "scenes/*/plan.json",
                "what": "fix: " + "; ".join(problems),
            },
            {"do": "subagent", "agent": "accuracy-reviewer", "target": mode, "what": f"{mode} mode again → {file}"},
        ]

    def critic_loop(scene_id, kind, refactor_file, read):
        problems = critique_problems(run, scene_id, kind) if kind == "video" else []
        if problems and "changes.json" in problems[0]:  # a refactor not recorded yet
            return [{"do": "write", "file": f"scenes/{scene_id}/changes.json", "what": problems[0]}]
        state = critique_state(run, scene_id, kind)
        critic = {
            "do": "subagent",
            "agent": CRITICS[kind],
            "target": scene_id,
            "what": f"one critique round → {critique_file(scene_id, kind)}",
        }
        if state in ("missing", "stale"):
            return [critic]
        if state == "revise":
            refactor = {
                "do": "write",
                "file": refactor_file,
                "read": read,
                "what": f"fix the issues of the last {kind} critique round of {scene_id}",
            }
            if kind == "plan":  # visual planning, refactoring included, is the scene-planner's (Opus)
                refactor = {
                    "do": "subagent",
                    "agent": "scene-planner",
                    "target": scene_id,
                    "read": read,
                    "what": f"refactor mode — fix the issues of the last plan critique round of {scene_id}",
                }
            record = {
                "do": "write",
                "file": f"scenes/{scene_id}/changes.json",
                "what": "append this iteration's ChangeRecord (issue, findings, modification, files, rendering, "
                "audio timing, sync, validation results)",
            }
            return [refactor, record, critic] if kind == "video" else [refactor, critic]
        return []

    if errors := validate_brief(run):
        return batch(
            "1 requirements",
            [
                {
                    "do": "ask_user",
                    "file": "brief.json",
                    "read": references("requirements.md"),
                    "what": "complete and confirm the requirements: " + "; ".join(errors),
                }
            ],
        )
    if script_critique_problems(run):  # the critique comes before the refactor that applies the request
        return batch(
            "3 script",
            [
                {
                    "do": "subagent",
                    "agent": "script-critic",
                    "target": "script",
                    "read": references("script-writing.md", "script-review.md", "transitions.md"),
                    "what": "one critique round for the changes requested at CP1 → script_critique.json",
                }
            ],
        )
    if routed := [action for request in open_requests(run) if (action := request_route(run, request))]:
        return batch("change requests", routed)
    if errors := validate_topics(run):
        return batch(
            "1 requirements",
            [
                {
                    "do": "write",
                    "file": "topics.md",
                    "read": references("topic-list.md"),
                    "what": "the numbered topic list; confirm it with the user — " + errors[0],
                }
            ],
        )
    if errors := validate_content(run):
        return batch(
            "1 requirements",
            [
                {
                    "do": "write",
                    "file": "content.md",
                    "read": references("topic-list.md"),
                    "what": "the content to outline, one '## topic' section each — " + errors[0],
                }
            ],
        )
    if stage_approval_problem(run, "requirements"):
        return batch(
            "1 requirements",
            [
                {
                    "do": "ask_user",
                    "read": references("requirements.md"),
                    "what": "requirements checkpoint: show brief.json (approach = script type, length, audience, "
                    "detail level, depth, complexity, visual and audio expectations), topics.md and content.md; on "
                    "approval `text-2-shorts approve . requirements`",
                }
            ],
        )
    if errors := validate_template(run):
        return batch(
            "1 template",
            [
                {
                    "do": "ask_user",
                    "what": "choose the template: show `text-2-shorts templates`; then `text-2-shorts template . "
                    "<name> [--set key=value …]` (their tweaks) — " + errors[0],
                }
            ],
        )
    if stage_approval_problem(run, "template"):
        return batch(
            "1 template",
            [
                {
                    "do": "ask_user",
                    "what": "template checkpoint: open template_preview.svg and show template.json; on approval "
                    "`text-2-shorts approve . template`",
                }
            ],
        )
    brief = load_brief(run)
    approach = brief.approach if brief else "linear"
    if errors := validate_outline(run):
        guide = (
            ["narrative-structures.md", "outline-linear.md"] if approach == "creative" else [f"outline-{approach}.md"]
        )
        return batch(
            "2 outline",
            [
                {
                    "do": "write",
                    "file": "outline.json",
                    "read": references(*guide),
                    "what": "from content.md — " + "; ".join(errors[:3]),
                }
            ],
        )
    if stage_approval_problem(run, "outline"):
        return batch(
            "2 outline",
            [
                {
                    "do": "ask_user",
                    "what": "CP0: show the outline (segments, timing, visual "
                    "plans); on approval `text-2-shorts approve . outline`",
                }
            ],
        )
    if errors := validate_script(run):
        return batch(
            "3 script",
            [
                {
                    "do": "write",
                    "file": "script.json",
                    "what": "; ".join(errors[:3]),
                    "read": references("standards.md", "script-writing.md", "transitions.md"),
                }
            ],
        )
    if problems := review_problems(run, "script"):
        return batch("3 script", reviewer("script", "script", "script_review.json", problems))
    if stage_approval_problem(run, "script"):
        return batch(
            "3 script",
            [
                {
                    "do": "ask_user",
                    "what": "CP1: self-review, then show the scene table, the full "
                    "narration and the accuracy findings; on approval `text-2-shorts approve . script`",
                    "read": references("script-review.md"),
                }
            ],
        )
    script = load_script(run)
    for scene in script.scenes if script else []:  # plans: one scene at a time, each through its critic loop
        plan_file = f"scenes/{scene.scene_id}/plan.json"
        planning = references("scene-visual-planning.md", "audio-ssml.md", "transitions.md")
        if errors := validate_plan(run, scene.scene_id):
            return batch(
                "4 plans",
                [
                    {
                        "do": "subagent",
                        "agent": "scene-planner",
                        "target": scene.scene_id,
                        "file": plan_file,
                        "read": planning,
                        "what": ("refactor" if (run / plan_file).exists() else "write")
                        + " mode — "
                        + "; ".join(errors[:3]),
                    }
                ],
            )
        if loop := critic_loop(scene.scene_id, "plan", plan_file, planning):
            return batch("4 plans", loop)
    if problems := review_problems(run, "plan"):
        return batch("4 plans", reviewer("plan", "plan", "plan_review.json", problems))
    if stage_approval_problem(run, "plan"):
        return batch(
            "4 plans",
            [
                {
                    "do": "ask_user",
                    "what": "CP2: show each scene's composition, transition_in, clip "
                    "table and last critique round; on approval `text-2-shorts approve . plan`",
                }
            ],
        )
    plans = load_scene_plans(run)
    state = load_state(run)
    production = references("scene-production.md")
    for plan in plans:  # production: scenes in series
        scene_id = plan.scene_id
        if is_approval_current(state, f"scene:{scene_id}", fingerprint(run, [plan])):
            continue
        if load_preferences(run).confirm_each_scene and not is_approval_current(
            state, f"start:{scene_id}", critique_subject_hash(run, scene_id, "plan")
        ):
            return batch(
                "5 production",
                [
                    {
                        "do": "ask_user",
                        "target": scene_id,
                        "what": f"the user asked to confirm "
                        f"each scene: start {scene_id} now? on yes `text-2-shorts approve . "
                        f"start:{scene_id}`",
                    }
                ],
            )
        if stale_audio(run, [plan]):
            return batch(
                "5 production",
                [
                    {
                        "do": "command",
                        "command": "text-2-shorts voice .",
                        "target": scene_id,
                        "what": "narration audio from the planned SSML",
                    }
                ],
            )
        unbuilt = [
            c
            for c in plan.clips
            if (build := state.clips.get(c.clip_id)) is None or build.key != clip_key(run, plan, c)
        ]
        if clip := next(iter(unbuilt), None):  # one clip at a time: the next starts once this one is accepted
            return batch(
                "5 production",
                [
                    {
                        "do": "subagent",
                        "agent": "clip-builder",
                        "target": clip.clip_id,
                        "before": f"text-2-shorts task . {clip.clip_id}",
                        "after": f"text-2-shorts accept . {clip.clip_id}",
                        "what": f"build {clip.clip_id} in its prepared folder (scenes/{scene_id}/work/"
                        f"clip_{clip.index:02d}); a clip that fails accept twice → ask the user",
                    }
                ],
            )
        if problems := preview_problems(run, plan):
            if "out of date" in problems[0]:
                return batch(
                    "5 production",
                    [
                        {
                            "do": "command",
                            "command": f"text-2-shorts preview . {scene_id}",
                            "target": scene_id,
                            "what": "720p30 scene preview + sync.json",
                        }
                    ],
                )
            return batch(
                "5 production",
                [
                    {
                        "do": "subagent",
                        "agent": "audio-refactorer",
                        "target": scene_id,
                        "read": production,
                        "what": "; ".join(problems[:3]),
                    }
                ],
            )
        if loop := critic_loop(
            scene_id,
            "video",
            f"scenes/{scene_id} (sync → audio-refactorer; other issues → `text-2-shorts feedback` + rebuild that clip)",
            production,
        ):
            return batch("5 production", loop)
        return batch(
            "5 production",
            [
                {
                    "do": "ask_user",
                    "target": scene_id,
                    "what": f"CP3: give the user "
                    f"scenes/{scene_id}/preview.mp4, the sync summary and the last critique "
                    f"round; on approval `text-2-shorts approve . {scene_id}`",
                }
            ],
        )
    report = load_final_report(run)
    if not (run / "final.mp4").exists() or report is None or report.fingerprint != fingerprint(run, plans):
        return batch(
            "final",
            [{"do": "command", "command": "text-2-shorts final .", "what": "2560×1440, 120 fps delivery render"}],
        )
    if not is_approval_current(state, "final", fingerprint(run, plans)):
        return batch(
            "final",
            [
                {
                    "do": "ask_user",
                    "what": "CP4: give the user final.mp4 and the media checks; on "
                    "approval `text-2-shorts approve . final`",
                }
            ],
        )
    return batch("done", [])


def format_actions(batch: ActionBatch) -> str:
    lines = [f"stage {batch.stage}" + (" — run these in parallel:" if batch.parallel else ":")]
    for action in batch.actions:
        who = action.agent or action.command or action.do
        line = f"  - [{action.do}] {who}" + (f" · {action.target}" if action.target else "")
        line += f" — {action.what}"
        if action.before:
            line += f" (first `{action.before}`, then `{action.after}`)"
        if action.read:
            line += f"\n      read: {', '.join(action.read)}"
        lines.append(line)
    return "\n".join(lines) if batch.actions else "done: the video is approved."
