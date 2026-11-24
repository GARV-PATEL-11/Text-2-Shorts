"""The optional last stage: a deterministic reshuffle of the look (colours, fonts, background, grid, border).

No Claude: the built clips keep their code, with each colour role's hex and the font family swapped for the new
template's (clips take both as literals from TASK.md), and are re-keyed, so the next actions are only the scene
previews (CP3) and the final render. The previous final video is kept in versions/."""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path

import video_settings

from app.workflow.approvals import approve_checkpoint
from app.workflow.artifacts import load_scene_plans
from app.workflow.fingerprints import clip_key
from app.workflow.ledger import load_state, update_state
from app.workflow.templates import current_template, look, save_template

HEX_LITERAL = re.compile(r"#[0-9a-fA-F]{6}(?![0-9a-fA-F])")


def proposal(run: Path, seed: int, groups: list[str]) -> dict:
    """The run's template reshuffled (nothing written)."""
    return video_settings.reshuffle(current_template(run), seed, groups)


def recolour(code: str, before: dict, after: dict) -> str:
    """Clip code with every role's hex and the font family of `before` replaced by `after`'s (video_settings.settings).
    Two roles sharing one hex before: the first role's new colour wins."""
    colours: dict[str, str] = {}
    for role, colour in before["roles"].items():
        if role in after["roles"]:
            colours.setdefault(colour.lower(), after["roles"][role])
    code = HEX_LITERAL.sub(lambda found: colours.get(found.group().lower(), found.group()), code)
    for quote in "\"'":
        code = code.replace(f"{quote}{before['font']}{quote}", f"{quote}{after['font']}{quote}")
    return code


def apply(run: Path, seed: int, groups: list[str]) -> list[str]:
    """Save the reshuffled template (approved: the user chose it), recolour and re-key the built clips, keep the old
    final video. Problems instead when the new template cannot be used (nothing changed then)."""
    plans = load_scene_plans(run)
    builds = load_state(run).clips
    current = {  # clips built for the look as it is now: those are recoloured and stay built
        clip.clip_id
        for plan in plans
        for clip in plan.clips
        if (build := builds.get(clip.clip_id)) and build.status == "READY" and build.key == clip_key(run, plan, clip)
    }
    before = look(run)
    if errors := save_template(run, proposal(run, seed, groups)):
        return errors
    after = look(run)
    for plan in plans:
        for clip in plan.clips:
            path = run / "scenes" / plan.scene_id / "clips" / f"clip_{clip.index:02d}.py"
            if clip.clip_id in current and path.exists():
                path.write_text(recolour(path.read_text(), before, after))
    keys = {clip.clip_id: clip_key(run, plan, clip) for plan in plans for clip in plan.clips if clip.clip_id in current}
    update_state(run, lambda state: [setattr(state.clips[clip_id], "key", key) for clip_id, key in keys.items()])
    if (run / "final.mp4").exists():
        (run / "versions").mkdir(exist_ok=True)
        shutil.move(run / "final.mp4", run / "versions" / f"final-before-reshuffle-{seed}.mp4")
    approve_checkpoint(run, "template", f"reshuffled: {', '.join(groups)} (seed {seed})")
    logging.getLogger(__name__).info(
        "%s: reshuffled %s with seed %s, %d clips recoloured", run.name, groups, seed, len(current)
    )
    return []
