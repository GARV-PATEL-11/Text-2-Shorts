# backend/tools/ — deterministic components

Standalone CLIs, tested on Manim 0.20.1 (`uv run pytest -q`). The `text-2-shorts` command calls them: `clip_gates.py` (the `./check` gates: validator,
probe, harness, doc cards; run in the render jail), `text-2-shorts final` (harness, assembly), `text-2-shorts new` (preflight), `text-2-shorts task` (API index, doc cards).

| Tool | Purpose | Tests |
|---|---|---|
| `preflight.py` | Fail-fast environment check (Manim pin, LaTeX, **dvisvgm**, ffmpeg, bwrap, socat, Claude Code version) | manual |
| `build_manim_api_index.py` | Introspect installed Manim → JSON index (classes, functions, constants, modules) | `test_api_index.py` |
| `doc_cards.py` | Exact-name API cards + topic cards for one clip (~0.5–1.5k tokens) | via topic tests |
| `validate_manim_code.py` | Static gate: syntax, forbidden imports/calls, removed APIs, unknown names/methods/kwargs, scene class, clip file + continuity contracts | `test_validate_manim_code.py` |
| `layout_probe.py` | Dry-run geometry & timing: OUT_OF_FRAME (camera-aware), OVERLAP (per text leaf), TINY_TEXT, per-clip duration vs narration | `test_layout_probe.py` |
| `scene_harness.py` | Compose scene from isolated clip files; render all clips or one target clip via Manim sections; 9:16 | `test_scene_harness.py` |
| `assemble_clips.py` | Per-clip A/V mux (pad shorter), concat, EBU R128 loudnorm, report | `test_assemble_clips.py` |
| `cost_report.py` | Cost/attempt/cache summary from `log.jsonl` (works on today's log format) | `test_cost_report.py` |
| `audit_prompt_catalog.py` | Check names in prompt files against the API index (finds banned-but-existing and missing names) | used for audit evidence |
| `clip_gates.py` | The `./check` gates of one clip (static, probe, render, frames); re-run by `accept` in the render jail | `test_clips.py` |
| `check_diagrams.mjs` | Parse `docs/diagrams/*.mmd` with Mermaid 11 | — |

Known limitations (documented, not hidden):
- `validate_manim_code.py`: kwargs are only checked for classes whose `__init__` has no `**kwargs` (most Manim classes
  accept `**kwargs`, so a misspelt style kwarg can pass statically and fail at render). UNKNOWN_METHOD is a WARN because
  methods are checked against the union of all classes, not the receiver's type.
- `layout_probe.py`: judges geometry from bounding boxes after each `play()`; transient overlaps *during* an animation
  are not sampled; overlap between a text leaf and a non-text shape is not flagged (intentional: labels sit on shapes).
- `scene_harness.py`: clip ordering relies on `clip_NN` lexical order (zero-padded numbers required).
