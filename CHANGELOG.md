# Changelog

## 0.25.0 — 2026-11-24
The frontend council (design system, iconography, UX writing, cultural references, critical reviewer): every icon, word
and state given one deliberate meaning. Decisions and rejected alternatives: `docs/DESIGN_REFERENCE.md`.
- **Icons**: Untitled UI kept (equivalent coverage elsewhere, one stroke family); one meaning per glyph. Claude,
  Request a Change, Console, Preview, Whole Look, Done (CheckCircle) vs a control's tick (Check), Length (stopwatch),
  Started (calendar), Waiting for You (bell), Failed, Warning, Error, Nothing Here, Unavailable, Not Supported each have
  their own; the generic "AI" sparkle is gone. Status pills carry their icon beside the word.
- **One status vocabulary** (`config/status.tsx`): word, icon and chart fill per state, used by the status pills and the
  clips chart. Failed has its own fill; "Done" is the one word for finished work.
- **Design system**: one icon box in three sizes (24/32/40, no 28) with one halo; badges and status pills share one
  24px recipe; button icons scale with the button; pictures r-lg (r-md inside cards); one not-allowed cursor.
- **Words**: errors say what did not load; loading says Loading; no checkpoint codes (CP0–CP4) in labels; "Request a
  Change" and "Open Console" everywhere; "Approve with Open Problems"; "Ready to Begin" before production; shorter
  sign-in, reshuffle and console copy; American spelling to match the template kit; scenes named "Scene 1".
- **Run page**: the duplicate status pill, Stages chip and Clips Built chip removed (the rail and chart carry them);
  the approval bar steps back only while Claude asks; the clips chart sizes each bar by its clip count and lists only
  the states present; "Claude's Next Step" with a count.
- **Quotations**: only Michael Faraday's own words, public domain, verified word for word: the candle lecture on
  sign-in, his 1849 journal line on an empty Home (`config/quotes.ts`). No game or film lines (unverifiable, copyright).
- Markdown fields show a visible "Markdown" tag on their Write/Preview switch instead of a hint line.

## 0.24.1 — 2026-11-24
Each mode's colours computed, not taken as given: deep shades in dark mode, pastels in light mode.
- `video_settings.mode_tones`: dark mode keeps backgrounds deep (lightness ≤ 0.16) and the kit's bright colours,
  brightening only one under 3:1. Light mode turns the background into a pastel of the template's own hue (lightness
  0.93) and each colour into the lightest, softest tone of its hue (saturation ≤ 0.6) that still reads on it: 3:1 for
  shapes, 4.5:1 for secondary text, 7:1 for text. Before, light mode drew dark browns and navies on near-white.
- A neutral background (Accessible Lecture's white) keeps the kit's high-contrast colours; the user's own background
  and accent are never toned.
- Subtitles follow the mode: the box is a deep shade in dark mode and a pale pastel in light mode, and a caption
  colour that would not read on it (white on a pale box) becomes the look's text colour.
- A test checks all of this for every starter in both modes. The starter pictures and the preview cache are re-rendered.

## 0.24.0 — 2026-11-24
The Faraday logo, one journey strip, and pictures instead of paragraphs.
- **Logo**: the brand banner as a white-on-transparent logo (`frontend/src/assets/faraday-logo.webp`) in the header,
  footer and sign-in page; its F mark is the browser tab icon (`faraday-mark.png`).
- **Journey** (`components/navigation/Journey.tsx`): Start a Run loses its heading and paragraph; one compact strip
  shows every stage of a run, and under it the current stage's steps, numbered, taken one after another (template:
  Starter Templates → Build Your Own → Sound → Whole Look; requirements: The Question → Audience & Length → Review).
- **A run at a glance** (`pages/run/Overview.tsx`): under the run's title, lookup chips (stages, approach, length,
  scenes, clips built, waiting for you, open requests, started) and a clips-per-scene stacked bar chart (built, in
  progress, needs you, not started: solid, grey, hatched, outline; a legend and a tooltip on every segment).
- Less text: section descriptions on the template steps and Home cut to short labels.
- **Old previews deleted**: the 210 option pictures drawn on the Standard template (`previews/dark`, `previews/light`),
  their routes (`/previews/{mode}/…`, `/previews/full/{mode}/…`, `POST /api/look/preview`) and the `all`/`one`
  commands. `generate_preview.py warm` pre-renders every option of every element in every starter's look, in both
  modes, at 854×480 and 2560×1440, into the cache the website reads (same names, so they open at once).

## 0.23.1 — 2026-11-24
Previews true to the look, and full screen in 80% of the window.
- **True colours**: every option in Build Your Own is drawn in the user's own look (their starter, every element they
  changed, their custom values), with only that element changed (`POST /api/look/options`,
  `generate_preview.option_in_look`); before, every option was drawn on the Standard template. Only what would hide
  the element is turned on (a grid to see grid colours, a border to see its colour, subtitles to see their style).
- **Exact pixels**: previews are saved as lossless WebP; lossy WebP had shifted saturated colours (`#FC6255` came out
  `#FD6257`). The starter pictures are re-rendered. A test checks a custom background to the exact value.
- **Full screen**: the picture takes 80% of the window; the rest is frosted glass over the page. While the 2560×1440
  render is made (the first time an option is opened, `GET /previews/custom/<name>` renders it from its recipe), the
  preview shows softened under a note that thanks you for your patience; cards say "Rendering in Your Look…".

## 0.23.0 — 2026-11-24
Logging everywhere, Start a Run from the template, Claude's questions on every stage, Markdown, the full width.
- **Logging** (`runtime-environment/faraday_logging.py`): one format for backend (`artifacts/logs/backend.log`: every
  request, refusal, run created, template saved, approval, reshuffle, console turn), frontend (`services/log.ts` →
  `POST /api/logs` → `frontend.log`: uncaught errors, React crashes, failed requests, actions, pages) and runtime
  (each run's `logs/runtime.log`: commands the session calls and why they stopped, hook events; preview renders).
  Runtime logging never writes to stderr (it would reach Claude's context). Level and folder from the environment.
- **Start a Run starts with the template**: step 1 is the starter gallery and Build Your Own (shared with the Template
  stage as `useTemplateEditor`); starting saves and approves it (`NewRunInput.look`, checked before anything is made),
  so the run opens at the requirements. Approving a stage moves the page to the next one. `POST /api/look/still`
  renders the whole look without a run.
- **Claude on every stage** (`ClaudePanel`): Claude's last message (Markdown), its questions with one-click answers
  (AskUserQuestion is captured as `question` console entries with `options`), a reply box, and Start Production before
  the first turn. The session is told its last message shows there.
- **Markdown** in and out: Write/Preview fields for the question, change requests, checkpoint notes and replies;
  rendered for Claude's messages, the console, topics.md, content.md, the brief, change requests and notes
  (`react-markdown` + `remark-gfm`; raw HTML never rendered). Run titles are their question as one Title Case line.
- **Width**: the page uses up to 2400px (was 1440px), with a wider gutter; reading text keeps its measure.
- **Title Case**: remaining labels (run titles, counts, checkpoint labels from the API, summary values).

## 0.22.0 — 2026-11-24
Template first, an optional deterministic reshuffle last, full screen at the delivery size, Title Case, Untitled UI icons.
- **Stage order**: Template (look and sound) is the first stage, before the requirements. The driver hands it out
  first; requirements cannot be approved before the template (`approvals.py`, `validation.validate_outline`).
- **Reshuffle** (optional, after the final video): `video_settings.reshuffle(template, seed, groups)` picks new
  variants for colours, fonts, background, grid or border from the seed alone (same seed, same look; never sizes, so
  layouts hold; unreadable picks skipped). `workflow/reshuffle.py` applies it without Claude: each role's hex and the
  font family are swapped in the built clips, the clips are re-keyed (still built), the template is approved, and the
  previous `final.mp4` moves to `versions/`. `POST /api/runs/{run}/reshuffle` shows it (`apply: false`) or applies it.
- **Full screen**: a lightbox on the same page that fills the window, sharpens to a 2560×1440 render
  (`/previews/full/…`, rendered once and cached) and offers the browser's full screen; videos get a full screen button.
- **Starter gallery**: each starter template as one 2560×1440 frame (`generate_preview.py starters`,
  `/previews/starters/<name>.webp`), as the Template stage's first tab; Build Your Own is the element tree.
- **Sharper text in previews**: `look_renderer.typeset` sets Text 4× larger and scales it down, fixing Pango's uneven
  letter spacing at small sizes ("Sq uare"). All 210 option previews re-rendered.
- **Icons**: Untitled UI Icons (`@untitledui/icons`, MIT), one meaning each: palette (template), clipboard
  (requirements), dataflow (outline), pen (script), storyboard grid (scene plans), clapperboard (scenes), play
  (final), shuffle (reshuffle). Progress steps with a ring on the current step and filled connectors.
- **Title Case** for every heading, label, button, tab, step, badge and status (`titleCase()` for data labels);
  sentences stay sentences.

## 0.21.0 — 2026-11-24
Frontend standardization, through a five-person review council (designer, React architect, interaction engineer,
QA & accessibility, design systems) and two critique-refactor rounds. Report: `artifacts/reports/frontend-standardization.md`.
- Structure: `app/` (routes, session), `services/` (one request core), `types/`, `hooks/` (`useApi`, `useAction`,
  `useRuns`, `useRunFile`), `config/`, `components/{ui,layout,navigation,feedback,media}`, `pages/run/stages/`.
  No circular imports; no prop-drilled error handler; nothing remounts after a write.
- Tokens and contracts in `styles/tokens.css` (spacing on a 4px scale, radii, type roles, control heights, icons,
  layout, elevation, layers, motion, media ratios) and four stylesheets that use them.
- Run page in two panes: a rail (progress, vertical stages, console and change actions) and the stage, with an
  approval bar when it waits for you. Underlined tabs; the template select and Save in the tab bar; the workflow's own
  "next" text folded away. Home as a two-column hero; the wizard with a live summary.
- Motion contract: fades and colour changes only (the drawer is the one slide), token durations, nothing scales or
  bounces, and reduced motion turns it all off. The test enforces it instead of "no motion".
- System messages: one `SystemMessage` for loading, empty, missing, pending, unavailable, offline, unsupported,
  restricted, success and error — a game-style spaced label, a heading, one line, an action; told apart by label,
  icon and border, never colour.
- Media: `VideoPreview` (ratio-locked box, loading, buffering, error with retry, empty, duration), `AudioPreview`
  (waveform from Web Audio, seek, volume, fallback scrubber), `ImagePreview` (ratio and fit presets, skeleton, broken
  state, enlarge beside the radio, never inside it).
- Accessibility: skip link that keeps the route, plain disclosures instead of misused tree roles, focus moves on page
  and stage change, `document.title`, persistent live regions, errors in place with retry, keyboard-reachable
  scrolling tables, control borders at 3.7:1, a reason shown for a disabled Approve, the console's keys explained.
- Fixes: stale responses for another run, a lost last console line, a failed sign-out shown, a failed re-read after a
  write shown as out of date.

## 0.20.0 — 2026-11-24
Look & sound: the template kit, one settings source, a preview for every option, and a React website.
- **Template kit** added as given at `runtime-environment/template_kit/` (22 elements in `elements.json`, 7 starter
  templates); it replaces the 3 old starters (moved to `artifacts/trash/templates-0.19/`). The kit's Python is kept
  but not run: everything below is our own code, reading the kit's JSON.
- **`video_settings.py`** (look) and **`audio_settings.py`** (sound): resolve the run's `template.json`, check it
  (every element set, known options, custom values, text contrast ≥ 4.5:1) and are the one source the pipeline
  reads: TASK.md's TEMPLATE block (colour roles, font, sizes, safe area), the voice for the brief's provider and the
  speaking rate, the clip key, and `drawing()` — everything the renderer draws.
- **`look_renderer.py`**: our Manim drawing of a look: backdrop (solid, gradient, glow, texture; 7 grids), 6
  borders, text and maths in the template's font and sizes, a still subtitle line (7 styles, 6 positions, 7
  highlight modes). The scene harness now draws the backdrop and border behind every clip (`self.content()` clears
  the clips' own objects); the layout probe ignores them. Previews and videos come from the same code.
- **`generate_preview.py`**: `fonts` (the templates' OFL fonts from Google Fonts, registered per process — nothing
  installed system-wide), `all` (every element × option × mode: 210 previews in `runtime-environment/previews/`,
  2.9 MB, about 45 s), `one` (one option or the user's own value), `still` (the whole chosen look), `voice`.
- **Q&A first, then the look**: requirements, then the template checkpoint, then generation. Delivery stays
  2560×1440 at 120 fps (the template's `frame` is not offered); subtitles are previewed, burned in later.
- **Website rebuilt in React** (Vite + TypeScript, `frontend/src/`, built into `frontend/dist/` and served by
  FastAPI; `npm run dev` for live reload). Same pages, still black and white with no motion (tests scan the source).
  **Look & sound** is a tree (Look → mode, background, grid, colour, type, border; Sound → narration, subtitles):
  every option is a card with its preview in the chosen mode only, the starter's value preselected (`default` /
  `changed` / `custom`), a custom value for background colour, accent colour, text font, voice and speed (rendered
  when entered), Hear for each voice and speed, Preview the whole look, Save. No Claude call anywhere in it.
- **Website redesign** (React Aria Components, Untitled UI's shapes, still black and white): a one-tier header; pages
  Home, Start a run (a three-step wizard), Ongoing, Previous runs (searchable, with progress bars), and a run page with
  breadcrumbs, a progress bar, a seven-stage stepper and each stage's own view with sub-stage tabs (Requirements:
  brief · topics · content; Look & sound: look · sound · whole look; Outline; Script: script · accuracy · critique;
  Plans: plans · critiques · accuracy; Scenes: one tab per scene with its player; Final: video · media checks — each
  with its checkpoint, approved with an explicit "I accept these open problems" checkbox). The console is a side
  drawer, asking for a change a modal; video players, an audio player, image previews in a modal, colour and gradient
  pickers (a custom background can be a two-colour gradient: `custom.background_color=#top,#bottom`), a subtitles
  toggle, empty states. `RunSummary.stages_approved`; briefs from before 0.20 still read (their voice and font are
  dropped).
- API: `GET /api/look`, `GET|POST /api/runs/{run}/look`, `POST …/look/still`, `POST …/look/voice`,
  `GET /previews/{mode}/{element}/{option}.webp`, `POST /api/look/preview`, `GET /assets/*`.
- Contracts: `VideoTemplate` is now starter name + `elements` + `overrides` + assembly fields; `Brief` loses
  `voice`, `engine`, `font`; `Preferences` loses `palette`, `background`, `font`, `voice_rate_percent`
  (`new --voice/--engine/--font` removed); `ClipTask.look` replaces `background`. clip-builder.md changed: every
  clip key changes. CI sets up Node 22 and builds the website before the tests.

## 0.19.0 — 2026-11-24
Model policy: Haiku talks, Opus builds, Sonnet critiques and does audio.
- **Run session → Haiku** (`claude-haiku-5-5`): the user's conversation (website console), refining requirements
  (brief, topics, content, preferences, template), routing what `next` returns, records (`changes.json`). It
  builds nothing itself.
- **Opus builds and refactors everything but audio**: new **script-writer** subagent writes and refactors the
  outline and the script (modes: outline, outline refactor, script, script refactor), including script-critic
  rounds, accuracy ERRORs and wording/accuracy/structure change requests; scene-planner fixes plan accuracy ERRORs
  (one scene per call); clip-builder unchanged.
- **Sonnet**: script-, plan-, video-critic, accuracy-reviewer, audio-refactorer.
- Config: `SESSION_MODEL`, `BUILD_MODEL`, `REVIEW_AND_AUDIO_MODEL`, `EFFORT` (replaces `PLANNING_AND_CODE_MODEL`).
- Tests: every agent's model by role; the outline stage and change requests dispatch the script-writer; nothing
  asks the session to write `outline.json`, `script.json` or a plan; a script refactor fixes the critique round
  before it resolves the request.
- Docs: README, PROJECT_STRUCTURE, workspace CLAUDE.md and the workflow skill.
- Removed the repo-session developer skills (`make-short`, `text-2-shorts-clip-debugging`,
  `text-2-shorts-prompt-maintenance`): the website starts runs, and nothing in the product used them.

## 0.18.0 — 2026-11-24
Critics and refactorers: tiered rubrics, derived scores, explainable reports.
- **Tiers**: every critique issue names a rubric `criterion` (`S-`/`P-`/`V-` + `B` basic need · `G` good to have ·
  `X` great if followed + number) and its `tier`. Basic needs must always hold: any open one means `revise` at any
  score. A `pass` may carry good and great suggestions.
- **Scores are derived**: 100 − 25 per basic − 10 per good − 3 per great; the validator recomputes them. The script
  critic is scored too.
- **Explainable reports**: each issue carries `evidence` (quote, beat, frame time, sync offset), `problem`,
  `impact` and `fix`; each round carries a `summary` and `strengths` (what a refactor must keep).
- **Agents**: script-critic, plan-critic and video-critic rewritten around their rubric tables; accuracy-reviewer
  and audio-refactorer restructured (modes, rubric, finding fields, rules, output, reply); scene-planner's refactor
  mode follows the protocol. clip-builder is unchanged (editing it marks every clip stale).
- **Shared reference** `critique-protocol.md`: tiers, scoring, issue writing, an example round, and how refactorers
  act on a round (basic → good → great, smallest change, keep strengths, never decline silently, routing).
  `next` hands it to every critic and refactor step; the script refactor reads the last `script_critique.json`.
- Contract: `CritiqueIssue` + `criterion`, `tier`, `evidence`, `impact`; `CritiqueRound.score` required,
  + `summary`, `strengths`. Critique files written before 0.18 no longer validate: re-run the critic for those scenes.
- Tests: tier scoring, basic needs blocking, criterion prefix and aspect per critic, and each critic's rubric table
  checked against what the validator accepts. JSON schemas re-exported, including the console and new-run ones that
  0.17 had not exported.

## 0.17.1 — 2026-11-24
Ready to ship: CI green, lint clean, project settings current.
- **CI**: installs the Cairo and Pango headers (`libcairo2-dev`, `libpango1.0-dev`, `build-essential`, `python3-dev`) —
  manimpango and pycairo publish no Linux wheels, so `uv sync` built them from source and failed at
  `pkg-config pangocairo`. `uv sync --locked` (a stale `uv.lock` fails), then `ruff check` and `ruff format --check`
  before the tests.
- **Lint**: the whole tree passes ruff 0.17's default rules; `PLW1510` is ignored on purpose (every `subprocess.run`
  reads `returncode` itself). Real fixes: the console's session-id callback binds its value, `preflight` catches only
  import failures, integer env defaults are strings, scripts with a shebang are executable.
- **Settings**: `.claude/settings.json` allows the current `text-2-shorts` command, `artifacts/runs/` and opening videos
  in Chrome (it still allowed the removed `app.pipeline` and `runs/`). `.env.example` says how to use it.

## 0.17.0 — 2026-11-24
The website is the only interface, connected to Claude Code.
- **Start runs on the website**: the `faraday new` form → `POST /api/runs` → `create_run()` (preflight, voice
  credentials, font, workspace), shared with `text-2-shorts new`.
- **Console**: each message is one turn of the run's Claude Code session (`claude -p … --output-format stream-json
  --resume <session>` in the run's jail, with the same plugin, settings, model and effort as `open`), streamed to the
  page as `ConsoleEntry` lines (you, claude, tool, system, error) and kept in the run's `console.jsonl`. One turn at a
  time per run (409 otherwise); the session id is kept in `state.json` (`console_session`).
- **Terminal look**: Fira Code at its Retina weight (450), ligatures on, for the console, forms and approval panels;
  Fraunces headings, Geist text; still black and white, no motion.
- The no-orchestration test now allows exactly one relay (`sandbox.console_claude_arguments`, the user's own message)
  and still forbids prompts in Python. The run guide tells the session the user talks to it through the website.

## 0.16.0 — 2026-11-24
Faraday: "Curiosity, Illustrated". The frontend after a critic refactor loop (report:
`artifacts/reports/frontend-critic-refactor-loop.md`).
- Rebrand of everything a person sees (title, bar, sign-in, home, footer, README); the CLI and package keep their names.
- Run header: counts from the run's files and a 7-stage strip (Scenes added, derived from real scene statuses), the
  current stage marked; status glyphs; plain stage names; static loading state; one-line empty states; tighter rhythm;
  a single-column stage list on phones.
- Truthfulness: `RunDetail.final_checked`; no "every check passed" or delivered-size claim for unchecked videos.
- Type: Fraunces (soft serif) for headings and the Faraday wordmark; Geist for text and controls; Geist Mono for ids.
- Still black and white only, no motion.

## 0.15.0 — 2026-11-24
FastAPI backend, sign-in with Claude, and an all-black frontend.
- **FastAPI**: `backend/app/web/app.py` replaces the standard-library server; every request and response is a Pydantic
  model (`schemas/api.py`); errors are `ApiError` JSON. `text-2-shorts serve` runs it with uvicorn on 127.0.0.1.
  Videos answer HTTP Range requests, so they can be seeked.
- **Sign in with Claude**: "Continue with Claude" opens a session for the Claude account Claude Code is signed in to on
  this machine (`claude auth status --json`, `backend/app/web/auth.py`). Not signed in: the page says to run
  `claude auth login`, which opens claude.ai. No password or token passes through the web view. Sessions: random
  tokens in an HttpOnly, SameSite=Strict cookie, 12 hours, in memory; sign out from the bar. Every API and media route
  needs a session.
- **All black**: the page is `#0b0b0d` with `#17181c` cards, white type, white pill and outlined buttons, after the dark
  sections of armakuni.com; tests enforce the palette (greys only), the black ground and the absence of motion.
- Dependencies: `fastapi`, `uvicorn`; dev: `httpx` (the test client).

## 0.14.0 — 2026-11-24
The frontend approves checkpoints and records changes.
- **Waiting for you**: every checkpoint the user can decide now (those waiting for approval and the one the next batch
  asks about), with its open problems. Approve (with optional notes), or approve anyway when problems are open (recorded
  as forced), or ask for changes.
- **Ask for a change**: a form for any stage, scene or clip and any kind of change; open requests can be marked applied
  or declined.
- **One code path**: `approve_checkpoint()`, `record_change_request()` and `resolve_request()` in `backend/app/workflow/`
  serve both the CLI (`approve`, `feedback`, `resolve`) and the web API (`POST /api/runs/<run>/approve`, `/requests`,
  `/requests/<rNNN>`), so gates, fingerprints and decision records are identical.
- **Safe on this machine**: the server answers only for 127.0.0.1/localhost (no DNS rebinding); writes must be JSON
  from the page's own origin (no cross-site form posts); bodies are capped and validated (`ApproveInput`,
  `ChangeRequestInput`, `ResolveInput`).
- `Action.checkpoint` names the checkpoint an ask-the-user action decides; `record_decision()` returns the decision.

## 0.13.0 — 2026-11-24
Top-level folders by role, Pydantic contracts for every file and payload, and a frontend.
- **Folders**: `frontend/`; `backend/` (`app/`, `schemas/`, `tools/`); `runtime-environment/` (was `run-environment/`;
  plugin `text-2-shorts-runtime-environment`); `artifacts/` (`runs/`, `reports/`, `trash/`); `docs/` (with
  `PROJECT_STRUCTURE.md`); `tests/`. New runs are created in `artifacts/runs/`.
- **Contracts everywhere**: `backend/schemas/` split by domain (base, requirements, script, plans, reviews, interaction,
  run_state, media, session, api; never-used contracts isolated in `unused_contracts.py`). New contracts for
  `state.json` (`RunState`), `log.jsonl`, the audio index, `TASK.json`, gate results, scene renders, `sync.json`,
  `assembly.json`, `final_report.json`, requests and decisions, the `next` batch, the hook's input and output, the
  environment report and token totals. Code and tools read and write through them; `export_json_schemas.py` exports
  every live contract (56).
- **Frontend**: `text-2-shorts serve` (read-only, 127.0.0.1:8765) serves `frontend/`, a black-and-white page in the
  type and neutral palette of armakuni.com (Geist, Geist Mono): the run list, where a run stands, what happens next,
  scenes with their previews, the final video with its checks, change requests and decisions. No motion; tests
  enforce the colours, the absence of motion and that run data is never parsed as HTML.
- **Fixed**: the topic-card tests had silently stopped finding the cards after the move; a guard test now fails.

## 0.12.0 — 2026-11-24
Repository restructure by responsibility; no behaviour change (the same 111 tests pass).
- **`app/` split**: `run_steps.py` (2,532 lines) and `cli.py` became `cli.py` (entry point), `config.py` (every
  setting; environment variables read once), `utilities.py`, `sandbox.py`, `commands/` (handlers: run, workflow,
  production, hook) and `workflow/` (ledger, change requests, preferences, templates, artifacts, fingerprints,
  checkpoints, validation, critiques, production, clips, approvals, driver, status, run workspace). No import cycles.
- **Moves**: `app/clip_gates.py` → `tools/` (a standalone script run in the render jail); `app/outline_models/` →
  `schemas/outline_models/`; `diagrams/` → `docs/diagrams/` (superseded ones → `docs/history/diagrams/`); docs into
  `docs/guides/`, `docs/changes/`, `docs/history/` (architecture plan, module specifications, skills assessment,
  proposed stages, reference material).
- **New**: `PROJECT_STRUCTURE.md` (every folder and module, dependency layers, run workspace, where changes go),
  `docs/reports/unused-files-inventory.md` (removal candidates with evidence; nothing deleted) and
  `docs/reports/restructuring-report.md`.
- Tests import the module they exercise; references in README, tools README, skills and guides updated.

## 0.11.0 — 2026-11-24
The PRD's workflow rules: clips in sequence, one script critique per requested change, scored critiques with
escalation, a refactor log, statuses, requirements and template checkpoints, music, sound effects and transitions.
- **Clips in sequence**: `task` refuses a clip until the earlier clips of its scene are accepted and copies them into
  the task folder (the clip starts from their real end state); `next` hands out one clip at a time. Replaces 0.9's
  parallel clips; `self.entry` stays.
- **Script critique on request**: no critique loop before CP1. Each change the user asks for at CP1 buys exactly one
  script-critic round (dispatched before the refactor); more rounds than requests is a validation error.
- **Scored critiques**: plan and video critique rounds carry a 0–100 score; the verdict must follow
  `quality_threshold` (preferences.json, default 85). After 3 rounds below it the scene REQUIRES ATTENTION and needs
  the user (`approve --force`, recorded).
- **Refactor log**: every video refactor iteration is a `ChangeRecord` in `scenes/sNN/changes.json` (issue,
  findings, modification, files, rendering, audio timing, sync, validation, score), required before CP3; the hook
  writes the run's `changes.txt`. `validate <run> changes --scene sNN`.
- **Statuses**: every stage, scene and clip is pending · in_progress · completed · failed · requires_refactoring ·
  requires_user_approval · approved, saved in `state.json` and shown by `status`.
- **Requirements**: `Brief` gains detail_level, explanation_depth, technical_complexity, visual_expectations,
  audio_expectations; `approve <run> requirements` confirms brief, topics and content before the outline.
- **Templates**: `run-environment/templates/` (standard-dark from standards.md, chalkboard, paper-light);
  `text-2-shorts templates`, `text-2-shorts template <run> <name> --set key=value` → `template.json` (`VideoTemplate`:
  colours, type scale, animation and transition style, density, composition, pacing, music) +
  `template_preview.svg`; `approve <run> template`. Precedence: standard < preferences < template; TASK.md and the clip
  key carry it.
- **Script content**: script scenes name on_screen_text (the plan must show it), animations, audio and transition
  requirements, and depends_on (earlier scenes only).
- **Audio from the user's files**: clip `sound_effects` and the template's `music` (must exist in the run folder),
  mixed at assembly.
- **Assembly**: stream parameters checked before concatenation; scenes joined with the template's transition (cut,
  fade through the background, crossfade).
- **Final checks**: adds 16:9 aspect ratio, true peak, silences, decode errors, duration against the script, missing
  clips.
- **Models**: visual planning and code generation, refactoring included, run on Opus 5.5 at medium effort: the new
  **scene-planner** subagent (writes and refactors scene plans, applies visual change requests) and the
  clip-builder. The run session (`--model claude-sonnet-5-5 --effort medium`) and every other subagent run on
  Sonnet 5.5 at medium effort.
- **Everything shown**: the session runs `--verbose`; the PostToolUse hook shows the user each write (with its
  validation result), command and subagent (`systemMessage`) and logs it with what was shown; the SessionStart hook
  shows the run state and next batch to the user as well as to Claude; the skill tells the session to report every
  change in one line.
- Docs: caching controls (Claude Code's TTL and disable variables) in the README; agents, references, skill, diagram
  and README follow the new rules.

## 0.10.0 — 2026-11-24
The outline stage returns; the user's tweaks, decisions and preferences become validated contracts.
- **Outline stage (CP0)**: `app/outline_models/` (base, Conceptual Zoom, Problem-Solution Arc, Classic Linear
  Narrative) are restored, plus `VideoOutline` for the creative approach. `outline.json` is validated by the
  approach's model and the outline prompts' checkable rules: segment order (A2/B2/C2) and first/last segment
  (A7/B3/C2), 10–120 s per segment (G2), transitions (S13) and the visual-plan standard (VP2 sentence count, VP3
  opening, VP4 closing, VP5 no double quotes). `text-2-shorts approve <run> outline` is CP0.
- **Prompts package**: `run-environment/prompts/script_prompts/` (request modifier + three outline prompts, shared
  blocks in `_shared.py`), rendered to `references/topic-list.md` and `references/outline-{linear,arc,zoom}.md` by
  `run-environment/prompts/export_references.py`; a test fails when they drift.
- **Requirements end with `topics.md` and `content.md`**: the request modifier's numbered list, then one
  `## <topic>` section per topic — the outline's `raw_content`. Both validated.
- **Script narrates the outline**: `ScriptScene.outline_segment`; the scenes after the index scene narrate every
  outline segment once, in order. The script waits for CP0.
- **Change requests** (`ChangeRequest`, `requests.jsonl`): `text-2-shorts feedback <run> <target> --kind
  wording|visual|audio-timing|accuracy|structure|style|other --text … [--checkpoint …]`; `text-2-shorts resolve
  <run> rNNN applied|declined`. Open requests block their checkpoint; `next` routes them; a clip's visual request
  resolves when the clip is accepted. (`--scope` and `feedback.jsonl` are gone.)
- **Checkpoint decisions** (`CheckpointDecision`, `decisions.jsonl`): every approval (`--notes` for approved with
  notes; forced flagged) and every change requested at a checkpoint.
- **Script critic loop**: `script-critic` subagent, one combined critic, at most 3 rounds before CP1
  (`script_critique.json`: outline-fit, clarity, flow, pacing, speakability, tone); CP1 needs a passing round on the
  current script, or the user accepts the open issues after round 3. `text-2-shorts hash <run> script`,
  `validate <run> script-critique`.
- **Standing preferences** (`Preferences`, `preferences.json`, copied from the repo root by `new`): tone, palette
  roles, background, font, voice rate, pause length, confirm each scene (`approve <run> start:sNN`). Applied to
  clip keys, TASK.md, render background and the voice SSML.

## 0.9.0 — 2026-11-23
Option B: a deterministic driver for the Claude Code session; scenes produced in series, a scene's clips in parallel.
- **`text-2-shorts next <run> [--json]`** returns the exact next batch — who does what (write, subagent, command,
  ask the user), for which target, reading which files — and whether it runs in parallel. The session start hook
  prints it; the produce skill is now a loop around it.
- **Clips of a scene in parallel**: the harness's `self.entry(name, make)` returns the previous clip's object in the
  composed scene and builds it from `make()` when a clip runs alone, so every clip is built and checked on its own
  (`text-2-shorts task` no longer waits for or copies earlier clips). Plans describe every carried object
  (`ContinuityState.descriptions`, required for entry objects); `./check static` reports `ENTRY_NOT_STANDALONE`.
- **Scenes in series**: `task` and `preview` for a scene refuse to start until every earlier scene passed CP3;
  status and `next` stop at the first open scene.
- **Clip keys** no longer include the previous clip's code: clips are independent, the entry contract is their
  interface; mismatches show in the scene preview and the video critique.
- `clip-structure` topic card, clip-builder, scene-production and scene-visual-planning references updated.

## 0.8.0 — 2026-11-23
Visual and audio planned together, critic-refactor loops, audio re-timed to the built video, 720p30 drafts.
- **Approaches**: three fixed (`zoom`, `arc`, `linear`) and one `creative` (a structure designed for the topic, or the
  user's own); `custom` is gone.
- **Index scene**: `script.json` must open with s01 (`role: "index"`) saying what the video covers; its `previews`
  list every later scene.
- **Audio planned with the visuals**: every clip has `ssml` — exactly its narration words with `<break>`,
  `<prosody rate>`, `<emphasis>`, … (checked: well-formed, allowed tags, same words). `voice` synthesises from it
  (symbols spoken by name, engine-unsupported tags dropped for Polly, one mark per word for Google).
- **Plan critic loop**: `plan-critic` subagent, one combined critic, at most 3 rounds per scene
  (`scenes/sNN/plan_critique.json`); CP2 needs a passing round on each scene's current plan, or the user accepts the
  open issues after round 3.
- **Beat marks**: clips call `self.beat(n)` where beat n starts (harness method; probe gate `BEAT_MARKS_MISSING`);
  the clip-builder writes `CHANGES.md`.
- **Scene preview + sync report**: `text-2-shorts preview <run> sNN` renders the whole scene at 720p30 with audio
  and writes `sync.json` (spoken vs shown time per beat, audio fit, CHANGES.md) — the changes-made document for the
  new `audio-refactorer` subagent, which re-times the SSML (tags only) to the video.
- **Video critic loop**: `video-critic` subagent, at most 3 rounds per scene (`video_critique.json`); CP3 needs a
  current preview, speech in sync with the animation (±0.35 s) and the critique done.
- **Keys**: a clip's code key no longer includes its SSML or audio (re-timing audio does not rebuild clips); CP3 and
  the final render fingerprint include the audio; CP2 ignores SSML-only edits.
- **Resolution**: drafts (`./check render`) and previews at 1280×720, 30 fps; final delivery 2560×1440 at 120 fps by
  default (`TEXT_2_SHORTS_FPS`, 60–120); the media check expects the configured rate.
- **Commands**: `preview`, `hash <run> sNN plan|video`, `doc <Names>`; `validate … plan-critique|video-critique --scene sNN`.
- **References**: `audio-ssml.md`, `scene-production.md`; the workflow skill lists every reference by path and reads
  each once per session.

## 0.7.0 — 2026-11-23
Staged workflow: requirements → complete script → scene-wise visual plans → clip-wise code, enforced in order.
- **Stage 1, requirements**: `brief.json` gains `objectives` (`--objective`, repeatable) and `style` (`--style`);
  `--approach custom` for the user's own structure; the brief is validated (`Brief`).
- **Stage 2, complete script** replaces the outline: `script.json` (`Script`) holds every scene's objective, key
  concepts, duration, spoken `bridge_in` and complete narration. Gate: every objective covered, bridges present,
  words per scene within ±25% of duration × wpm, total length ±20%. CP1 approves the script.
- **Stage 3, scene visual plans**: `ScenePlan` gains `composition` and `transition_in` (`segment_type`,
  `transition_to_next` removed). A plan's clip narration must equal the approved script's text for that scene, word
  for word. CP2 approves the plans.
- **Order enforced**: plans are rejected before CP1; `voice` and `task` refuse to run before CP2; checkpoints store
  fingerprints, so editing an approved script or plan makes its checkpoint stale. `text-2-shorts status` stops at
  the first open stage.
- **Accuracy reviews at both stages**: subagent `accuracy-reviewer` (was `math-reviewer`) writes
  `script_review.json` (per scene) and `plan_review.json` (per clip, on-screen maths and labels; replaces
  `math.json`). ERROR findings block the checkpoint.
- **Transitions on two levels**: simple continuity between clips; a spoken bridge plus a visual recap between scenes
  (`references/transitions.md`).
- **Prompts**: one reference per stage — `requirements.md`, `script-writing.md`, `narrative-structures.md`,
  `script-review.md`, `scene-visual-planning.md`, `transitions.md` (+ `standards.md`). The legacy outline prompts
  (`outline-zoom/arc/linear.md`, ~93 KB, which also forced 50–70-line visual plans into the outline),
  `outline-review.md`, `brief.md` and `clip-planning.md` are removed; `app/outline_models/` is replaced by `Script`.
- **Commands**: `approve <run> script|plan|sNN|final`; `validate <run> brief|script|script-review|plan|plan-review`.
- **Migration**: runs started before 0.7 have `outline.json`/`math.json` and must be restarted with
  `text-2-shorts new`.

## 0.6.0 — 2026-11-20
Naming standardisation; no behaviour change. Rules, vocabulary, full mapping and exceptions:
`docs/naming-conventions.md`.
- **Modules**: `app/pipeline.py` → `app/cli.py`, `app/clips.py` → `app/run_steps.py`, `app/check.py` →
  `app/clip_gates.py`, `app/speech.py` → `app/narration.py` (the Polly/Google synthesizers moved there too),
  `app/graph/models/` → `app/outline_models/`.
- **Folders and docs**: `env/` → `run-environment/` (plugin `t2s-env` → `text-2-shorts-run-environment`), `prompts/` →
  `docs/proposed-stages/`, `Plan.md` → `docs/architecture-plan.md`, every Markdown file in kebab-case.
- **Identifiers**: descriptive names for module constants, functions and ~400 locals across `app/`, `tools/`,
  `schemas/` and `tests/` (e.g. `LEAD_IN` → `VOICE_LEAD_IN_SECONDS`, `jail_cmd` → `build_jail_command`).
- **`TASK.json`**: `clip`/`class`/`seconds` → `clip_name`/`scene_class_name`/`clip_seconds`.
- **Tooling**: Ruff (format + lint, line length 120) as a dev dependency; Pyrefly search paths configured.
- **The command is `text-2-shorts`** (was `t2s`), and the `t2s` prefix is gone everywhere: skills
  `text-2-shorts-produce`, `text-2-shorts-clip-debugging`, `text-2-shorts-prompt-maintenance`; environment variables
  `TEXT_2_SHORTS_FPS`, `_PARALLEL`, `_TTS` (and the internal `_BACKGROUND`, `_TARGET_CLIP`, `_STOP_AFTER`); API index
  cache `~/.cache/text-2-shorts/`.
- **Migration**: `uv sync` installs the `text-2-shorts` entry point and removes `t2s` (`uv run` does it
  automatically). Rename `T2S_FPS`, `T2S_PARALLEL`, `T2S_TTS` in your `.env` to `TEXT_2_SHORTS_…` (old names are
  ignored). Anything calling `python -m app.pipeline` uses `python -m app.cli`. A clip folder prepared by 0.5 needs
  `text-2-shorts task <run> <clip>` again before `text-2-shorts accept`. Runs, state, feedback and logs are unchanged;
  a run session started before the update must be reopened (`text-2-shorts open`) to load the renamed skills.

## 0.5.0 — 2026-11-20
Claude Code-native execution (Plan.md §30).
- **Inverted control**: no Python orchestrator and no `claude -p` per stage. One interactive Claude Code session per
  run writes the outline and clip plans and dispatches two subagents (clip-builder per clip, math-reviewer).
- **Environment as code** (`env/`): a Claude Code plugin (workflow skill + references, subagents, hooks), session
  settings (sandbox + permissions) and the per-run CLAUDE.md. All prompts moved there verbatim from Python.
- **Per-run isolation**: `t2s new` provisions `runs/<id>/`; `t2s open` runs Claude Code in a bubblewrap jail where only
  the run folder (plus Claude Code's own state/caches) is writable and `$HOME` is private.
- **Deterministic commands** for the session: `t2s validate`, `task`, `accept`, `hook`, `report`; `status` lists the
  next steps. Hooks: session start → status; every tool call → log; written outline/plan/math → validated.
- **Removed**: `pipeline.claude()`, the LLM result cache, limit waits, `STAGES`, `t2s outline/clips/build`,
  `app/graph/prompts/`, `app/sandbox.json` (→ `env/settings.json`).

## 0.4.0 — 2026-11-20
- **Voice providers: AWS Polly or Google Cloud TTS**, chosen per video (`t2s new --tts polly|google`, `--voice`,
  `--engine` for Polly). Google uses SSML `<mark>` timepoints for word timings (beat sync) and falls back to plain text
  for voices without SSML (e.g. Chirp 3 HD). `new` checks the chosen provider's credentials.
- **Removed Kokoro** (engine, model download/SHA pin, `kokoro-onnx` dependency).

## 0.3.0 — 2026-11-20
- **Shared rules sent once**: `VIDEO_STANDARDS` + ELI5/Feynman `EXPLANATION_STYLE` in every stage's static (cached)
  system prompt; always-on Manim topic cards moved into the clip agent's system prompt, so `API_CARDS.md` holds only
  clip-specific cards.
- **Consistency**: palette roles, type scale, zones and timing standards; each symbol keeps one colour across the
  video (`color_roles` carried scene to scene).
- **Explanation style**: ELI5/Feynman rules in the outline and clip-planner prompts.
- **Audio–visual sync**: 0.3 s visual lead-in and ≥ 0.8 s hold per clip; `[pause]` markers; with Polly, beat start
  times from word speech marks in `TASK.md`.
- **Scene transitions**: scenes start and end on an empty frame (enforced; a violating plan is sent back once); the
  last clip transitions out, the next scene re-draws the previous final image. Fixes a latent crash when a plan
  carried objects across scenes.
- **Speech** (`app/speech.py`): symbols in backticks spoken by name, Greek letters, math symbols, units after
  numbers, abbreviations, M-vs-m disambiguation; Polly SSML with plain-text fallback and word marks; Polly neural is
  the default engine; `new` checks AWS credentials.
- **Fixes**: final assembly no longer re-encodes to 30 fps (media checks now verify ≥ 60 fps); `.env.example` no
  longer overrides real AWS credentials with placeholders.

## 0.2.0 — 2026-11-20
Clip-level pipeline (Plan.md roadmap P2–P14, smallest forms; see the status note in `docs/MODULE_SPECS.md`).

- **Clip-level generation**: scenes are planned as 4–20 s clips (`t2s clips`) with Pydantic-validated continuity
  contracts and a math verifier; narration audio per clip (`t2s voice`); one sandboxed agent per clip writes one
  file, gated by `./check` (validator → layout/timing probe → section render → frames) and re-checked in a jail
  before it is accepted (`t2s build`); final per-scene render with one Manim section per clip, per-clip A/V sync,
  EBU R128 loudness and media checks (`t2s final`).
- **Human checkpoints**: `t2s approve outline | plan | sNN | final`; scoped `t2s feedback`; `t2s status`. Only what
  changed is rebuilt (content-hash keys cascade through each scene's clips).
- **Runner**: identical non-agent calls answered from `.cache/llm/`; rate/overload backoff; usage limits waited out
  to their reset time; structured start/end log rows with full token breakdown.
- **Output**: always 2560×1440, `T2S_FPS` 60–120, chosen font, one background for every clip.
- **Prompt caching**: byte-identical system prompts; per-call data only in the user message.
- **`t2s` command**, GitHub Actions CI, deterministic outline length check, preflight before `new`, Kokoro SHA-256
  pin, hardened agent sandbox.
- **Removed**: the scene-level Director DSL path (`tts`, `plan`, `render`, `assemble`), its prompts and the
  hand-written Manim catalogues; spend budgets; unused dependencies, configs and vendored skills.
