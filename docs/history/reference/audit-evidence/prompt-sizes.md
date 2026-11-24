# Measured prompt sizes in the existing app (`app.zip`)

Measured by importing the prompt modules (2026-11-19). Tokens ≈ chars/4 — an estimate; use the Token Counting API or the `cache_read`/`cache_write` columns in `runs/<id>/log.jsonl` for exact values.

| Prompt | chars | ≈ tokens |
|---|---:|---:|
| MANIM_VOCABULARY (catalog) | 38,892 | 9,723 |
| MANIM_CONSTRUCTION_PATTERNS (catalog) | 11,675 | 2,918 |
| MANIM_COMMON_MISTAKES (catalog) | 9,102 | 2,275 |
| REQ_MODIFIER_SYSTEM (refine) | 1,856 | 464 |
| CONCEPTUAL_ZOOM_SYSTEM (outline) | 29,438 | 7,359 |
| PROBLEM_TO_SOLUTION_ARC_SYSTEM (outline) | 31,338 | 7,834 |
| CLASSIC_LINEAR_NARRATIVE_SYSTEM (outline) | 26,802 | 6,700 |
| OUTLINE_CRITIC_SYSTEM | 2,782 | 695 |
| OUTLINE_REFACTOR_SYSTEM | 1,141 | 285 |
| NARRATION_SYSTEM | 609 | 152 |
| Visual plan system (role + 3 catalogs) | 67,006 | 16,751 |
| Visual plan user (inputs EMPTY + static output spec) | 23,080 | 5,770 |
| CRITIC_SYSTEM (plan critic) | 2,343 | 585 |
| REFACTOR_SYSTEM (plan refactor) | 695 | 173 |
| CODE_GEN SYSTEM_PROMPT (identity + 3 catalogs) | 91,924 | 22,981 |
| _DEBUG_IDENTITY_AND_PROTOCOL | 9,149 | 2,287 |
| SCENE_AGENT_PROTOCOL | 1,706 | 426 |
| Render agent appended system prompt (codegen + debug + protocol) | 102,779 | 25,694 |

Note: the render agent's appended prompt is added ON TOP of Claude Code's own default system prompt (`--append-system-prompt-file`), and is re-read (from cache) on every agent turn.
