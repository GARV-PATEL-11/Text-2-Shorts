# Existing application inventory (app.zip, audited 2026-11-19)

The original source is not redistributed here; this is the file list used for Plan.md §3.

| File | Lines |
|---|---:|
| app/__init__.py | 0 |
| app/graph/__init__.py | 0 |
| app/graph/models/__init__.py | 0 |
| app/graph/models/base_models.py | 99 |
| app/graph/models/classic_linear_narrative.py | 69 |
| app/graph/models/conceptual_zoom.py | 67 |
| app/graph/models/problem_solution_arc.py | 66 |
| app/graph/prompts/__init__.py | 0 |
| app/graph/prompts/manim_reference.py | 1038 |
| app/graph/prompts/outline_critic_prompt.py | 147 |
| app/graph/prompts/render_debug_prompt.py | 474 |
| app/graph/prompts/script_gen_prompt.py | 1709 |
| app/graph/prompts/visual_code_gen_prompt.py | 919 |
| app/graph/prompts/visual_plan_critic_prompt.py | 145 |
| app/graph/prompts/visual_plan_gen_prompt.py | 776 |
| app/pipeline.py | 549 |
| app/sandbox.json | 9 |

Missing from the archive: `.claude/skills/make-short/SKILL.md` (referenced by pipeline.py), dependency manifest,
tests, README. `__pycache__` shows CPython 3.14 bytecode.
