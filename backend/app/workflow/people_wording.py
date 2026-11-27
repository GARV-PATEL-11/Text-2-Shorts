"""The one place a checkpoint problem Claude reads becomes a sentence a person reads on the website.

Claude and the command line keep the exact problem text (they act on it, tests assert it); `people_text` maps the
same string to plain words for the site, as an ADDITIONAL field. A problem with no rule here is shown unchanged.
Rules use the site's own words: no CPn, file names, rule codes or ids (A2, VP3, s01)."""

from __future__ import annotations

import re

TARGETS = {"requirements": "Requirements", "template": "Look & Sound", "outline": "Outline", "script": "Script",
           "plan": "Scene Plans", "scenes": "All Scenes", "final": "Final Video"}  # fmt: skip
RULES: list[tuple[str, str]] = [
    (
        r"^(?:scene:|start:)?s(\d{2}) changed since you opened it.*",
        "Scene {0} changed since you opened this page. Reload to see the current version.",
    ),
    (
        r"^(.+?) changed since you opened it.*",
        "This stage changed since you opened this page. Reload to see the current version.",
    ),
    (
        r"^the requirements checkpoint .* is not approved.*",
        "The Requirements have not been approved, or they changed after you approved them. Approve them first.",
    ),
    (
        r"^the template checkpoint .* is not approved.*",
        "The Look & Sound has not been approved, or it changed after you approved it. Approve it first.",
    ),
    (
        r"^CP0 .* is not approved.*",
        "The Outline has not been approved, or it changed after you approved it. Approve it first.",
    ),
    (
        r"^CP1 .* is not approved.*",
        "The Script has not been approved, or it changed after you approved it. Approve it first.",
    ),
    (
        r"^CP2 .* is not approved.*",
        "The Scene Plans have not been approved, or they changed after you approved them. Approve them first.",
    ),
    (
        r"^open change request \S+ \((\S+?)[,)].*? — apply or decline it first$",
        "A change request is still open for {0}. Claude must apply it or you must decline it first.",
    ),
    (
        r"^script: changes were requested at CP1 — run the script-critic \(round (\d+) of (\d+)\)$",
        "You asked for script changes. Claude will review the script again (round {0} of {1}) before you can approve it.",
    ),
    (r"^no scene plans yet$", "Scene Plans: Not Made Yet"),
    (
        r"^s(\d{2}): has a plan but is not a scene of the script.*",
        "Scene {0} has a plan but is not in the script. Claude will remove it.",
    ),
    (r"^final\.mp4 is missing or out of date$", "The Final Video is missing or out of date."),
    (r"^media check \w+: (.*)$", "Video check: {0}"),
    (r"^s(\d{2}): no valid plan$", "Scene {0} has no valid plan yet."),
    (r"^s(\d{2})c\d{2}: .* is not built from its current inputs$", "Scene {0} has a clip that is out of date."),
    (r"^s(\d{2}): .* is not built from its current inputs$", "Scene {0} has a clip that is out of date."),
    (r"^s(\d{2}): preview missing or out of date.*", "Scene {0}'s preview is missing or out of date."),
    (r"^topics\.md does not exist$", "The topic list is missing."),
    (r"^topics\.md must be a numbered list.*", "The topic list must be a numbered list, one topic per line."),
    (r"^content\.md does not exist$", "The research notes are missing."),
    (r"^content\.md has no '## (.+)' section$", "The research notes have no section for {0}."),
    (r"^content\.md section '(.+)' is empty$", "The notes for {0} are empty."),
    (r"^content\.md sections must follow.*", "The research notes must follow the order of the topic list."),
    (r"^brief\.json does not exist$", "The Requirements are missing."),
    (r"^outline\.json does not exist$", "The Outline has not been written yet."),
    (r"^script\.json does not exist$", "The Script has not been written yet."),
    (r"^scenes/s(\d{2})/plan\.json does not exist$", "Scene {0} has no plan yet. Claude will write it."),
    (
        r"^segment (\d+): (\d+(?:\.\d+)?)s — every segment is 10–120 s.*",
        "Scene {0} runs {1} s; every scene must be 10 to 120 s.",
    ),
    (
        r"^segment (\d+): visual_plan's first sentence.*",
        "Scene {0}: the first sentence of the visual plan must describe the empty screen.",
    ),
    (
        r"^segment (\d+): visual_plan's last sentence.*",
        "Scene {0}: the last sentence of the visual plan must begin 'The scene ends with'.",
    ),
    (r"^objective (\d+) is not covered by any scene.*", "Learning objective {0} is not covered by any scene."),
    (
        r"^s(\d{2}) has (\d+) spoken words, but (\S+)s at (\d+) wpm needs about (\d+).*",
        "Scene {0} has {1} spoken words, but {2} s needs about {4}. Shorten the narration or lengthen the scene.",
    ),
    (
        r"^scenes total (\S+)s but the target is (\S+)s.*",
        "The scenes add up to {0} s, but the target is {1} s (plus or minus 20%). Shorten or merge scenes.",
    ),
    (
        r"^s(\d{2}): the clips' narration must be.*",
        "Scene {0}'s narration no longer matches the approved Script. To change the words, change the Script and approve it again.",
    ),
    (
        r"^s(\d{2}): the script's on-screen text '(.*)' appears in no clip.*",
        "The on-screen text '{1}' appears in no clip of Scene {0}.",
    ),
    (
        r"^s(\d{2})c\d{2}: sound effect .* not found.*",
        "A sound-effect file for Scene {0} was not found. Check the file you chose.",
    ),
    (
        r"^s\d{2}c\d{2} entry must be empty.*|^s\d{2}c\d{2} exit must be empty.*",
        "Scenes must start and end on an empty screen.",
    ),
    (
        r"^`(.+?)` is (\S+) here but (\S+) in s(\d{2}): one colour per symbol$",
        "The symbol {0} is {1} here but {2} in Scene {3}; one colour per symbol.",
    ),
    (r"^s(\d{2}) transition_in is empty.*", "Scene {0} needs a description of how it opens from the previous scene."),
    (
        r"^script_review\.json does not exist.*|^plan_review\.json does not exist.*",
        "The accuracy check has not been done yet. Claude will do it before you approve.",
    ),
    (
        r"^script_review\.json reviewed an older version.*",
        "The accuracy check was done on an older Script. Claude will check it again.",
    ),
    (
        r"^plan_review\.json reviewed an older version.*",
        "The accuracy check was done on older Scene Plans. Claude will check them again.",
    ),
    (
        r"^(?:script|plan)_review\.json: unknown target .*",
        "The accuracy review mentions something that is not in the Script. Claude will fix the review.",
    ),
    (r"^accuracy ERROR in (\S+): (.*)$", "Accuracy problem in {0}: {1}"),
    (
        r"^(?:\S*critique\S*\.json)(?: does not exist.*|: .*)$",
        "Claude's review file needs fixing. Claude will redo the review.",
    ),
    (
        r"^s(\d{2}): record the refactor .*|^s(\d{2}): the \w+ changed since the last critique round.*|^s(\d{2}): \w+ critique round \d+ asks.*",
        "Claude is still reviewing Scene {0}.",
    ),
    (
        r"^s(\d{2}): REQUIRES ATTENTION — (\d+) critique rounds with issues left;.*?: (.*)$",
        "Scene {0} still has open issues after {1} review rounds: {2}. Approve with Open Problems to accept them, or Request a Change.",
    ),
    (
        r"^s(\d{2}) out of sync — .*",
        "In Scene {0} the voice and the picture are out of step. Claude will adjust the timing.",
    ),
    (r"^template\.json does not exist.*", "Choose a Look and Sound first."),
    (r"^template\.json is not JSON.*", "The Look and Sound file is damaged. Choose it again."),
    (r"^music .* not found.*", "The music file you chose was not found."),
]
COMPILED = [(re.compile(pattern, re.DOTALL), words) for pattern, words in RULES]


def people_text(problem: str) -> str:
    """The sentence the site shows for a checkpoint problem; the problem itself when no rule covers it."""
    for pattern, words in COMPILED:
        if match := pattern.match(problem):
            groups = [group for group in match.groups() if group is not None]
            groups = [str(int(group)) if group.isdigit() and len(group) == 2 else group for group in groups]
            groups = [
                TARGETS.get(group) or (f"Scene {int(group[1:])}" if re.fullmatch(r"s\d{2}", group) else group)
                for group in groups
            ]
            try:
                return words.format(*groups)
            except IndexError:
                return problem
    return problem
