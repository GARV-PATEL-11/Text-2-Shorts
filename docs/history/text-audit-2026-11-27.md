# Faraday — User-Facing Text & Messaging Inventory (2026-11-27)

*An audit only: no message in the code was changed. Branch CCW-V02 at `2604a34`.*

## How to read this
- **Scope:** everything a person can see or hear. That covers the website (every page, component, notice,
  placeholder, aria and alt text, and texts that appear only on failure), backend texts that reach the website
  (API errors, checkpoint problems, run views, console lines, the Look & sound catalogue), the command line
  (`text-2-shorts …` output, exit messages and help), and the texts the run's Claude session relays to the user.
  Developer logs are listed separately (Part 3, "Internal logs") and are not user-facing.
- **Size:** 788 inventory rows: Part 1 (A1–A229, app shell and main pages), Part 2 (B1–B259, run pages),
  Part 3 (C1–C300, backend). Plus 61 detailed findings (29 + 16 + 16).
- **Each row:** Exact Text · Location (file:line) · Element Type · Trigger / Condition · Purpose · Meaning ·
  Expected User Action · Source · Status (functional, redundant, outdated, misleading, inconsistent or
  potentially unused).
- **Method:** three readers went through every line of their area. I re-checked the headline findings in the
  code (marked ✔ below). Line numbers may be off by a few lines in places, and some Status cells are judgement
  calls: check the code before acting on a single row.
- **House style:** labels use Title Case on purpose ("Claude Is Working"). That is not counted as an error; only
  breaks from it are.

## Summary of findings (all three parts, merged and ranked by user impact)

1. **Text written for Claude or for developers is shown to users** (C-F1, C-F2, C-F3, C-F7; B-14).
   - Checkpoint problems and "Claude's Next Step" say "run the accuracy-reviewer subagent" or
     "record the refactor in changes.json". They also use CP0–CP4, a name for the stages that appears nowhere
     else on the site, plus file names and rule codes (VP2, A2, P-B3).
   - The Look & sound notes are developer text ✔: "Manim primitives", "Pango … install_fonts.py downloads all of
     them" (`elements.json:64,762,1042`).
   - The usage gate (added today) shows the raw window id (`five_hour`) and the sentence "Ask the user…" on the
     site.
   - *Recommendation:* every problem carries a user text and a Claude text, and the site shows only the user
     text. Add a one-sentence `summary` per Look element for users.
2. **Raw errors reach users** (C-F4): pydantic field paths, `KeyError: 's01'`, up to 1,500 characters of Manim
   stderr, and the console's stderr tail.
   - **Regression from the remediation ✔:** Phase 5's catch-all 500 handler answers
     `f"{type(error).__name__}: {error}"` (`app.py:197`).
   - *Recommendation:* plain sentences for known failures; keep the detail in the logs, which already hold it.
3. **Feedback shown where nobody sees it** (A, B-1).
   - Rename, Delete and Discard errors on the run lists render behind the open dialog.
   - The Change-request notice is written into a modal that has already closed.
   - Reshuffle's working and error texts sit behind its confirm dialog.
   - "Claude Finished" from the console goes to a page notice hidden behind the console drawer.
   - Page notices are never cleared, so they stay after they stop being true.
4. **Messages that say something untrue** (A, B-2, B-3, B-4, B-8, C-F5).
   - Sign-in says "You Stay Signed In for 12 Hours"; the server keeps sessions for 24 h ✔ (`SignIn.tsx:68`,
     `auth.py:19`).
   - A server that does not answer is reported as "Claude Code Is Not Signed In".
   - "Limit Reached" shows for any usage status other than "allowed" ✔ (`Home.tsx:45`).
   - "Claude Finished" also shows after a broken or failed turn: `streamTurn` resolves on any end of the stream.
   - **Regression from the remediation:** "Change Request … Recorded: Claude Is Applying It" is announced before
     the turn starts, and its failure, including a 409, is dropped (`ChangeModal.tsx`, Phase 3 / M20).
   - Reshuffle contradicts itself ✔. The dialog says it "Renders the Previews and Final Video Again"; the notice
     after it says to "Send Any Message in the Console" (`Reshuffle.tsx:72,115`).
   - The run list calls every unreadable run "Older Version: Final Video Only", damaged runs included
     (`RunList.tsx:88`). The run page decides its title by a text prefix.
5. **Disabled controls give no reason** (A, B-5): Continue, Start, Save, Send Request (needs 3+ characters), and
   Preview and Apply in Reshuffle.
6. **No feedback while loading or on failure** (A, B-7).
   - Usage-check failures are swallowed.
   - A failed audio load says only "Waveform Unavailable".
   - The Claude panel renders nothing while it loads.
   - Plan cards and scene code vanish when a fetch fails, and "No Execution Plan" also shows on a fetch failure.
   - Several errors have no Try Again.
   - A missing draft silently opens a blank Start a Run.
7. **Inconsistent terminology** (A, B-9, C-F6).
   - Product: Faraday vs Text-2-Shorts (the serve banner and the hook messages).
   - Stages: Template vs Look & sound; plan vs Scene Plans.
   - Run status: Ongoing / In Progress / Waiting for You / Awaiting Approval / Finished / Completed / Done.
   - Requests: Open Requests / Change Requests / Changes / Request a Change.
   - Spelling: "colour" and "Analysed" ✔ vs "Color".
8. **Raw ids and unformatted values** (B-10, C-F7): "Scene s03", "Clip c0301", `r01 · wording on outline · open`,
   "scene:s01 changed since you opened it", raw ISO timestamps, `no run 20261124-…`.
9. **Duplicates and fragile coupling** (C-F8, B-15).
   - "no starter template" ×4, "this look and sound cannot be used yet" ×4, five "could not be rendered" variants.
   - Turn notices are duplicated across the panel and the console.
   - **Regression from the remediation ✔:** when a session starts, its message prints the next batch twice.
     Phase 5's change to `status_text` adds it, and `hook_command.py:78` also appends it.
   - **Known ruling:** refusing force matches problem text by substring (`approvals.py`, Phase 1). Rewording a
     problem would silently allow force on an unseen video.
10. **Accessibility gaps** (A, B-12).
    - Console speakers are told apart only by CSS class.
    - The whole Claude panel is `aria-live`, so streamed text is announced again and again.
    - Every table has the same accessible name.
    - Chart details are hover-only.
    - Tab counts are bare badges.
    - "Open Problems" is not a heading.
    - aria-labels are worded inconsistently.
    - There is no `<noscript>` fallback.
11. **Grammar and plurals** (B-13) ✔: "1 Elements Change" (`Reshuffle.tsx:66`), "1 words" (`Writing.tsx:49`),
    "Scenes Is Waiting for Your Decision" (`RunPage.tsx:143`), lowercase hints that come from the backend.
12. **The usage-gate message is unclear** (C-F9).
    - It shows the raw window id, and the time has no date or time zone.
    - Steps are listed as raw `agent target` pairs.
    - `usage-ok` prints the stage code ("3 script").
13. **Requests on plans, scenes, a scene, a clip or the final video are invisible** (B-11). Only Outline and
    Script have a Changes tab, so a request made through the new "All Scenes" target can't be followed on the
    site.
14. **Probably unused** (B-16, C): `GROUP_NAMES.subtitles`, `VOICE_SAMPLE`, the CLI flags `--scenes` and
    `--clips`, and the "Created" notice (the page navigates away first).

## Recommendations, in order
1. Separate the audiences. Give each problem and next step a user text, shown on the site, and a Claude text,
   shown to the session. Add a user `summary` per Look element. This fixes items 1, 7 and 8 at the root.
2. Map raw errors to plain sentences in one place (the API error handlers and `problem_response`). Fix the
   Phase 5 catch-all so it says "Something went wrong; the details are in the log."
3. Make every notice true and visible: errors inside open dialogs, a turn result that comes from a real end
   event, the change-request turn awaited, notices cleared on stage change, one Reshuffle statement.
4. One glossary (Faraday, Look & sound, Scene Plans, Requirements, Change Requests) and one formatter for
   scenes, clips, requests and dates.
5. A reason next to every disabled control, and a Try Again on every load failure.
6. Replace text matching with codes: `UNFORCEABLE` gets a problem code, and the run gets a `problem_kind`.
   Remove the duplicated batch from the session-start message.
7. The accessibility items in 10, then the grammar items in 11.

---


# Part 1 — App shell, Home, run lists, Start a Run, Sign In (rows A1–A229)
Scope: frontend/src/{app,components,config,hooks,services}, pages/{Home,RunList,NewRun,SignIn}.tsx, index.html. Paths are relative to /home/garv/Projects/Side Quests/Text-2-Shorts/frontend/src unless stated. Candle = Michael Faraday, The Chemical History of a Candle. Template steps rendered inside Start a Run (pages/run/stages/look/*) belong to the other audit. Rows group by file; where a row lists several strings they share one element/behaviour.


### Document shell, app and session (index.html, app/**, hooks, services)

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| A1 | Faraday · Curiosity, Illustrated | index.html:6 | document title | Initial load, until a Page sets its own title | Browser tab title | Brand + tagline | None | frontend hardcoded | inconsistent (order is "Brand · Tagline"; Page titles are "Page · Faraday") |
| A2 | Faraday (Curiosity, Illustrated): follow each video run, choose its look and sound, approve its checkpoints and ask for changes. Sign in with the Claude account your Claude Code uses. | index.html:7 | meta description | Search/link previews | Describe the app | What the app does | None | frontend hardcoded | inconsistent (sentence case; "checkpoints" and "look and sound" are terms the UI calls "stages"/"template") |
| A3 | (no <noscript> element) | index.html | noscript | JavaScript disabled | - | - | - | - | inconsistent (blank white/black page with no message; see Findings) |
| A4 | ${title} · Faraday | components/layout/Page.tsx:8 | document title (template) | Every Page; titles passed: "Home", "Start a Run", "Sign In", "Ongoing Runs", "Previous Runs" | Tab title follows page | Page name | None | dynamic | functional |
| A5 | Opening Your Workspace… | app/App.tsx:17 | SystemMessage title (loading) | Session check pending, or checked but no account yet | Wait | Page is loading | Wait | frontend hardcoded | functional |
| A6 | Checking Which Claude Account This Computer Uses | app/App.tsx:17 | SystemMessage text | same | Explain wait | Session lookup | Wait | frontend hardcoded | misleading (also shown for the instant between a failed lookup and the redirect to sign-in; does not mention a server that is down) |
| A7 | Signing out failed: ${message} | app/session.tsx:65 | error text (returned to Profile dialog) | DELETE /api/session fails | Report failed sign-out | You are still signed in | Retry | dynamic (message from http.ts / backend) | inconsistent (sentence case; "Signing Out…" is Title Case) |
| A8 | sign in first | services/http.ts:29 | Error message (SignedOut) | HTTP 401 | Internal; never rendered (session.fail redirects) | - | - | frontend hardcoded | potentially unused (swallowed by fail(); only visible in logs) |
| A9 | Faraday's server did not answer. Check that `text-2-shorts serve` is running. | services/http.ts:27 | error text | fetch throws (server down/network) | Say server unreachable | Connection problem | Start the server | frontend hardcoded | functional (backticks are shown literally in Notice/SystemMessage) |
| A10 | ${answer.error} / ${path} answered ${status} | services/http.ts:34 | error text (fallback) | Non-OK response with no JSON `error` | Last-resort message | Exposes API path and status code | Retry / report | dynamic (backend API `error`, else template) | misleading (developer wording, e.g. "/api/runs answered 500") |
| A11 | ${error} — ${problems joined} | services/http.ts:15 | error text (ApiError.full) | Any ApiError shown via useAction/Notice | One line of error plus problem list | Backend-supplied detail | Fix the named problems | backend API (error, problems[]) | functional |
| A12 | The console sent no reply. | services/http.ts:65 | ApiError text | Console POST has no body | Stream failure | Console turn produced nothing | Retry | frontend hardcoded | functional |
| A13 | A reply from Claude could not be read; the rest of the turn continues. | services/http.ts:74 | console entry (role error) | A streamed NDJSON line fails to parse | Tell user a line was dropped | Part of reply lost | Wait / re-ask | frontend hardcoded | functional (sentence case, unlike UI) |
| A14 | ${working} (e.g. "Saving…") → note text; ${done}; errorText(error) | hooks/useAction.ts:20-30 | Notice (polite / assertive) | Any action started with run() | One message per action: working, result, or error | - | - | dynamic | functional |
| A15 | [faraday] ${message}; "Failed: ${working}"; "Opened #/…"; "Faraday opened at …"; "Uncaught: …"; "Unhandled promise rejection" | services/log.ts:34,52-56; hooks/useAction.ts:29 | console/log only | Logging | Developer log, never in the UI | - | - | frontend hardcoded | functional (not user-visible; listed for completeness) |
| A16 | Hash route labels: Home / Start a Run / Ongoing / Previous Runs | app/routes.ts:9-12 | navigation link labels | Header nav | Main sections | Sections of site | Click | frontend hardcoded | inconsistent ("Ongoing" nav vs "Ongoing Runs" page title; others match) |

### Header, footer, profile (components/layout)

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| A17 | Skip to Content | components/layout/Shell.tsx:25 | skip link | Keyboard focus at page start | Bypass header | - | Press Enter | frontend hardcoded | functional |
| A18 | Faraday: home | Shell.tsx:28 | aria-label on logo link | Always | Name for icon-only brand link | Goes home | Click | frontend hardcoded | inconsistent (sentence case; Breadcrumbs uses "Home") |
| A19 | Faraday | components/layout/Logo.tsx:18 | svg aria-label (role img) | Logo anywhere (header, footer, sign-in, Home hero/closing) | Alt text | Brand name | None | frontend hardcoded | redundant (footer and hero logos repeat the name next to the text "Curiosity, Illustrated.") |
| A20 | Main | Shell.tsx:31 | nav aria-label | Header nav | Landmark name | - | - | frontend hardcoded | functional |
| A21 | {avatar initial} {shown name}; title = email | Shell.tsx:39-41 | button (opens profile) + tooltip | Signed in | Open profile dialog | Your name (profile name, else email local part) | Click to open Your Profile | dynamic (profile.name / account.email) | inconsistent (no accessible hint that it opens a profile dialog; only aria-haspopup) |
| A22 | Curiosity, Illustrated. | Shell.tsx:54; SignIn.tsx:62; Home.tsx:170,198 | footer / brand line / hero title / closing motto | Footer on every page except Home; Sign In; Home hero and closing | Brand line | Tagline | None | frontend hardcoded | redundant (up to 3 copies on Home: hero title, closing motto, plus page title and tab title) |
| A23 | Your Profile | components/layout/Profile.tsx:32 | modal title | Header user button | Dialog heading | - | - | frontend hardcoded | functional |
| A24 | {who.email} | Profile.tsx:32 | modal description | Dialog open | Show account | Signed in as | - | backend API (account.email) | functional |
| A25 | Close | components/feedback/Overlay.tsx:24,52; media/ImagePreview.tsx:71 | icon button aria-label | Any Modal/Drawer/Lightbox | Close dialog | - | Click / Esc | frontend hardcoded | functional |
| A26 | Your Name | Profile.tsx:38 | field label | Profile dialog | Edit display name | - | Type | frontend hardcoded | functional |
| A27 | {email local part} (placeholder) | Profile.tsx:38 | placeholder | Name empty | Show fallback name | Used when blank | - | dynamic | functional |
| A28 | How Faraday Shows You; Kept on This Computer | Profile.tsx:39 | field hint | Profile dialog | Explain scope | Stored locally | - | frontend hardcoded | functional |
| A29 | Organization / Plan / Signed In With / Runs Here / Net Spend | Profile.tsx:41-45 | dt labels | Profile dialog | Account facts | - | Read | frontend hardcoded | inconsistent ("Runs Here", "Net Spend" are unexplained; see note row) |
| A30 | — (em dash) | Profile.tsx:41-45 | dd fallback | Value missing | Placeholder | No data | - | frontend hardcoded | functional |
| A31 | {organization} / {titleCase(plan)} / {method} / {runs} / ${spend_usd.toFixed(2)} | Profile.tsx:41-45 | dd values | Profile dialog | Show facts | - | Read | backend API (profile, account) | functional |
| A32 | Net Spend Adds Up the Cost Claude Code Reports for Every Console Turn; on a Subscription It Is What the Same Use Would Cost at API Prices | Profile.tsx:47 | note | Profile dialog | Explain "Net Spend" | Figure is notional on subscriptions | Read | frontend hardcoded | inconsistent (long sentence in Title Case with semicolon; breaks readability) |
| A33 | Sign Out | Profile.tsx:34 | button | Profile footer | End session | - | Click | frontend hardcoded | functional |
| A34 | Save | Profile.tsx:35 | button (disabled when name unchanged or busy) | Profile footer | Save name | - | Click | frontend hardcoded | inconsistent (disabled with no explanation; stays "Save" after saving) |
| A35 | Saving… | Profile.tsx:21 | Notice (polite) | Save pressed | Progress | - | Wait | frontend hardcoded | functional |
| A36 | Saved | Profile.tsx:24 | Notice (polite) | Save finished | Success | - | - | frontend hardcoded | inconsistent (stays in the dialog until closed; reappears stale on re-open because action.note is never cleared) |
| A37 | Signing Out… | Profile.tsx:26 | Notice (polite) | Sign Out pressed | Progress | - | Wait | frontend hardcoded | functional |
| A38 | Skip target "#app" (main, tabIndex -1) | Shell.tsx:49 | landmark | - | - | - | - | - | functional (no label text) |

### Feedback components (components/feedback, voice catalogue)

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| A39 | Loading / Processing / Pending / Nothing Here / Not Made Yet / Unavailable / Connection Lost / Not Supported / Access Restricted / Done / Error | components/feedback/SystemMessage.tsx:18-28 | sr-only prefix "{label}: " before each SystemMessage title | Any SystemMessage | Screen-reader kind announcement (visual label is icon only) | State of the message | Listen | frontend hardcoded | inconsistent (the Title Case kind label is only for screen readers; sighted users get icon only, so e.g. "Pending" vs "Not Made Yet" are not visible) |
| A40 | {title}, {children}, {action} | SystemMessage.tsx:51-54 | heading/body/action slots | Every state message | Content passed by callers | - | - | dynamic | functional |
| A41 | {said line} + credit | SystemMessage.tsx:32-35,53 | quotation under message | Non-compact messages: loading→loading, processing→processing, pending→pending, offline→offline, restricted→restricted, unavailable/error→failed, unsupported→lost, success→approved | Flavour text | See Voice section | - | frontend config (voice.ts) | misleading (a quote like "Houston, we have a problem." is added under every non-compact error; "unsupported" gets Blade Runner "like tears in rain") |
| A42 | {progress} | SystemMessage.tsx:55-57 | progressbar (aria-label = title) | progress prop given | Show progress | - | - | dynamic | functional |
| A43 | {label} / {valueText} (e.g. "40%" or valueLabel) | components/feedback/ProgressBar.tsx:14 | progress label and value | Any ProgressBar (hideLabel false) | Named progress | - | - | dynamic | functional |
| A44 | {state.label} on status pill: Approved / Done / In Progress / Being Revised / Waiting for You / Failed / Not Started | config/status.tsx:11-17 via feedback/StatusPill.tsx:13 | status pill | Any stage/scene/clip status | One status vocabulary | State word | - | frontend config | inconsistent (see RunList STATUS: "Awaiting Approval", "Completed", "Configuring") |
| A45 | {value} (raw status id fallback) | StatusPill.tsx:13 | status pill fallback | Unknown status id | Fallback | Shows raw snake_case, e.g. requires_x | - | backend API (status) | misleading (unlabelled raw id) |
| A46 | Done / In Progress / Waiting for You / Failed / Not Started | config/status.tsx:22-26 | chart legend | Run overview clips chart | Legend | - | - | frontend config | redundant (duplicates STATES labels) |
| A47 | (Modal/Drawer) title, description, footer | feedback/Overlay.tsx:21-22,49-50 | dialog heading + description | Any dialog | Titles from callers | - | - | dynamic | functional |
| A48 | Notice (live regions, empty by default) | feedback/Notice.tsx:8-9 | role=status / role=alert | Any action result | Announce results | - | - | dynamic | functional |

### Voice lines (config/voice.ts, rendered by components/ui/Said.tsx)

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| A49 | There is no better, there is no more open door by which you can enter into the study of natural philosophy, than by considering the physical phenomena of a candle. — Michael Faraday, The Chemical History of a Candle, Lecture I (1860) | config/voice.ts:11 (moments welcome, closing) | epigraph (blockquote + cite) | Sign In (welcome, random of 2); Home closing (random of 2) | Brand voice | Quote | None | frontend config | functional |
| A50 | Hello and, again, welcome to the Aperture Science computer-aided enrichment center. — Portal (2007), GLaDOS | voice.ts:30 (welcome) | epigraph | Sign In (random) | Brand voice | Quote | None | frontend config | functional |
| A51 | I claim the privilege of speaking to juveniles as a juvenile myself. — Candle Lecture I | voice.ts:12 (audience) | inline quote | Start a Run, Audience & Length step | Voice | Quote | None | frontend config | functional |
| A52 | What is the cause? Why does it occur? — Candle Lecture I | voice.ts:13 (homeLead) | lead quote | Home hero | Voice | Quote | None | frontend config | functional |
| A53 | We come here to be philosophers — Candle Lecture I | voice.ts:14 (question) | inline quote | Start a Run, The Question step | Voice | Quote | None | frontend config | functional |
| A54 | Science isn't about why, it's about why not. — Portal 2, Cave Johnson | voice.ts:34 (question) | inline quote | same | Voice | Quote | None | frontend config | functional |
| A55 | See how beautifully these are coloured — Candle Lecture I | voice.ts:15 (chooseLook) | inline quote | Used in pages/run (other agent); not in this scope | Voice | Quote ("coloured" is the source spelling) | None | frontend config | functional |
| A56 | let us make an experiment or two. — Candle, Lecture IV | voice.ts:16 (review, readyToBegin) | inline quote | Start a Run, Review step | Voice | Quote | None | frontend config | inconsistent (lower-case fragment shown as a full line) |
| A57 | All we have to decide is what to do with the time that is given to us. — The Fellowship of the Ring, Gandalf | voice.ts:39 (review) | inline quote | Start a Run, Review step | Voice | Quote | None | frontend config | functional |
| A58 | We have now some very interesting points to study. — Candle, Lecture II | voice.ts:17 (openingRun) | inline quote | Run opening (other scope) | Voice | Quote | None | frontend config | functional |
| A59 | Hey, you. You're finally awake. — Skyrim, Ralof | voice.ts:37 (openingRun) | inline quote | Run opening (other scope) | Voice | Quote | None | frontend config | functional |
| A60 | This waiting is a curious and wonderful thing. — Candle, Lecture VI | voice.ts:18 (loading, rendering) | inline quote | Every non-compact loading SystemMessage (loading); lightbox sharpening wait (rendering) | Voice | Quote | None | frontend config | functional |
| A61 | It is curious to see how different substances wait — Candle, Lecture VI | voice.ts:19 (loading, pending) | inline quote | Loading / Pending messages | Voice | Quote | None | frontend config | functional |
| A62 | Vectors included! | voice.ts:63 (loading) | splash text (no credit) | Loading messages | Voice | Joke splash | None | frontend config | functional |
| A63 | You solve one problem... and you solve the next one... and then the next. — The Martian, Mark Watney | voice.ts:29 (processing) | inline quote | "Processing" SystemMessages (non-compact) | Voice | Quote | None | frontend config | functional |
| A64 | A wizard is never late, Frodo Baggins. Nor is he early; he arrives precisely when he means to. — Gandalf | voice.ts:41 (pending, rendering) | inline quote | Pending / render waits | Voice | Quote | None | frontend config | misleading (reads as if the wait is intentional/unlimited for a failed or slow render) |
| A65 | Ask why. Then ask again! | voice.ts:65 (pending) | splash text | Pending messages | Voice | Splash | None | frontend config | functional |
| A66 | Every frame is code! | voice.ts:66 (rendering) | splash text | Render waits | Voice | Splash | None | frontend config | functional |
| A67 | Help me, Obi-Wan Kenobi. You're my only hope. — Star Wars, Leia | voice.ts:43 (asks) | inline quote | Run page (other scope) | Voice | Quote | None | frontend config | functional |
| A68 | Wake me, when you need me. — Halo 3, Master Chief | voice.ts:36 (nothingToDecide) | inline quote | CheckpointPanel (other scope) | Voice | Quote | None | frontend config | functional |
| A69 | Yes! We have proved it by combustion — Candle, Lecture V | voice.ts:20 (approved) | inline quote | Success SystemMessages (non-compact) | Voice | Quote | None | frontend config | functional |
| A70 | You're doing very well. — Portal, GLaDOS | voice.ts:32 (approved) | inline quote | same | Voice | Quote | None | frontend config | functional |
| A71 | This was a triumph. / We're made of star-stuff. We are a way for the cosmos to know itself. / Even the smallest person can change the course of the future. | voice.ts:31,45,40 (complete; closing also uses star-stuff) | inline quote / epigraph | Run complete (other scope); Home closing (star-stuff) | Voice | Quotes | None | frontend config | functional |
| A72 | Mostly harmless — Hitchhiker's Guide | voice.ts:26 (noChanges) | inline quote | Run page (other scope) | Voice | Quote | None | frontend config | functional |
| A73 | Houston, we have a problem. / Failure is not an option! / I have a very bad feeling about this. | voice.ts:22,23,44 (failed) | inline quote | Every non-compact "unavailable" or "error" SystemMessage (Could Not Load Runs, Could Not Load Templates, Could Not Load Your Draft, ...) | Voice | Quotes | None | frontend config | misleading ("Failure is not an option!" under a failure; jokes in an error state) |
| A74 | The Enrichment Center regrets to inform you that this next test is impossible. / Houston, we have a problem. | voice.ts:33,22 (renderFailed) | inline quote | Lightbox when the full-size render fails | Voice | Quotes | None | frontend config | misleading ("impossible" overstates a recoverable fetch failure) |
| A75 | DON'T PANIC — Hitchhiker's Guide cover | voice.ts:25 (offline) | inline quote | offline SystemMessage (RunPage, other scope) | Voice | Quote | None | frontend config | functional |
| A76 | I'm sorry, Dave. I'm afraid I can't do that. / You shall not pass! | voice.ts:24,42 (restricted) | inline quote | restricted SystemMessage | Voice | Quotes | None | frontend config | potentially unused (no caller uses kind="restricted"; grep) |
| A77 | All those moments will be lost in time, like tears in rain. — Blade Runner | voice.ts:27 (lost; used for kind "unsupported") | inline quote | unsupported SystemMessage (RunPage, other scope) | Voice | Quote | None | frontend config | misleading (melancholy line for "this run cannot be shown") |
| A78 | It's dangerous to go alone! Take this. / This is only the beginning. — Zelda; Dune | voice.ts:35,28 (noRuns, readyToBegin) | inline quote | Ongoing Runs empty state (noRuns) | Voice | Quote | None | frontend config | functional |
| A79 | Nothing is too wonderful to be true, if it be consistent with the laws of nature — Faraday journal 1849 / Do it all, everything! — Minecraft splash | voice.ts:21,38 (nothingInProgress) | inline quote | Home, no ongoing run | Voice | Quote | None | frontend config | functional |
| A80 | (moments chooseLook, readyToBegin, asks, nothingToDecide, complete, noChanges, openingRun) | voice.ts:55-76 | VOICE keys | Only used from pages/run (not in scope) | - | - | - | frontend config | (verify in other audit; none used by files in this scope) |
| A81 | Said wrapper: `<q>…</q> <cite>source</cite>` | components/ui/Said.tsx:18-21 | inline markup | Any Said | Quote and credit are read in full by screen readers | - | - | dynamic | inconsistent (credit read as plain text after the quote; no "quote from" cue) |

### Sign In (pages/SignIn.tsx)

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| A82 | Sign In | SignIn.tsx:60,63 | document title and h1 | Sign-in route | Page name | - | - | frontend hardcoded | functional |
| A83 | Uses the Claude Account Already on This Computer | SignIn.tsx:64 | page lead | Sign-in | Explain method | No separate credentials | Read | frontend hardcoded | functional |
| A84 | Continue with Claude | SignIn.tsx:67 | button (disabled while busy) | Sign-in | Start session | Uses local Claude Code account | Click | frontend hardcoded | misleading (nothing opens claude.ai; it only checks the local login and needs the `?token=` link) |
| A85 | No Password Needed: You Stay Signed In for 12 Hours | SignIn.tsx:68 | note | Sign-in | Session length | Says 12 h | Read | frontend hardcoded | outdated (backend SESSION_SECONDS = 24 * 3600 in backend/app/web/auth.py:19, i.e. 24 hours) |
| A86 | Checking Your Sign-In… | SignIn.tsx:49 | Notice (polite) | Continue pressed | Progress | - | Wait | frontend hardcoded | functional |
| A87 | {ApiError.full} (e.g. 403 message about the missing link) | SignIn.tsx:50-54 + http.ts | Notice (assertive) | POST /api/session fails | Failure | Backend text (token missing/wrong) or the server-down text | Use the link `text-2-shorts serve` printed | backend API (error) | functional (depends on backend wording; not audited here) |
| A88 | Claude Code Is Not Signed In | SignIn.tsx:73 | h2 in card | codeSignedIn false (session says not signed in, OR the first session lookup failed) | Setup help | Claude Code needs login | Follow steps | frontend hardcoded | misleading (also appears when the server is simply unreachable) |
| A89 | Open a Terminal on This Computer | SignIn.tsx:75 | list item | same | Step 1 | - | Open terminal | frontend hardcoded | functional |
| A90 | Run `claude auth login`. It Opens claude.ai So You Can Sign In | SignIn.tsx:76 | list item | same | Step 2 | - | Run command | frontend hardcoded | functional (code literal inside Title Case sentence) |
| A91 | Come Back Here and Continue | SignIn.tsx:77 | list item | same | Step 3 | - | Click Continue | frontend hardcoded | functional |

### Home (pages/Home.tsx)

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| A92 | Home | Home.tsx:166 | document title | Home | Page name | - | - | frontend hardcoded | functional |
| A93 | A Question In, a Narrated Explainer Video Out: Claude Writes It, Manim Draws It, You Approve Every Stage | Home.tsx:171 | hero lead | Home | Pitch | - | Read | frontend hardcoded | functional |
| A94 | Quick Actions | Home.tsx:173 | nav aria-label | Home | Landmark | - | - | frontend hardcoded | functional |
| A95 | Start a Run / Continue / Previous Runs | Home.tsx:174-176 | link buttons | Always / only when a run is ongoing / always | Shortcuts | Continue opens the live run | Click | frontend hardcoded | redundant ("Continue" and the "Open Run" button in the Live Run card go to the same run) |
| A96 | Live Run | Home.tsx:181 | h2 | Home | Section title | - | - | frontend hardcoded | functional |
| A97 | {n} Ongoing · {m} Finished | Home.tsx:182 | note | runs loaded | Counts | - | - | dynamic | inconsistent ("Finished" here vs "Previous Runs" nav vs "Completed" status) |
| A98 | Could Not Load Runs + {error.message} | Home.tsx:184 | SystemMessage unavailable (compact) | GET /api/runs fails | Failure | - | Reload page | dynamic | inconsistent (no Try Again button, unlike RunList; raw message) |
| A99 | Loading Your Runs | Home.tsx:185 | SystemMessage loading (compact) | runs pending | Wait | - | Wait | frontend hardcoded | functional |
| A100 | Nothing in Progress + {nothingInProgress quote} | Home.tsx:188-189 | SystemMessage empty (compact) | No ongoing run | Empty state | - | Click Start a Run | frontend hardcoded | functional (no action button; the quote replaces any hint of what to do) |
| A101 | Claude Is Working / Waiting for You / Done / Ready to Continue | Home.tsx:101-104 | Pill | Live run state | Run state | Busy / awaiting checkpoint / finished / otherwise | Read | frontend hardcoded | misleading (shows "Ready to Continue" while the console is still loading; the "Done" branch is unreachable because the live run is taken from the ongoing list) |
| A102 | Stages of this run | Home.tsx:120 | Journey nav aria-label | Live run | Landmark | - | - | frontend hardcoded | inconsistent (sentence case) |
| A103 | Loading This Run | Home.tsx:122 | SystemMessage loading (compact) | run detail pending | Wait | - | - | frontend hardcoded | functional |
| A104 | Stages Approved / {percent}% | Home.tsx:123 | progress label + value | Live run | Progress | n of 7 approved as percent | - | dynamic | functional (percent rounds; no "x of 7") |
| A105 | Now / Since Start; chips label "This Run Now" | Home.tsx:124-127 | Chip labels, list aria-label | Live run | Facts | Stage name; elapsed since folder created | - | dynamic | functional ("Now" label is vague next to a stage name) |
| A106 | {d} d {h} h / {h} h {m} min / {m} min | Home.tsx:24-28 | elapsed text | Live run | Elapsed time | - | - | dynamic | inconsistent (abbreviations d/h/min, no Title Case, fine for units) |
| A107 | Problems | Home.tsx:129 | h3 | Live run | Section | - | - | frontend hardcoded | functional |
| A108 | None | Home.tsx:136 | note with icon | No problems | Empty | - | - | frontend hardcoded | functional |
| A109 | {data.problem}; {checkpoint.label}: {text}; {Scene title} Failed; {final check message} | Home.tsx:105-110 | list items | Problems exist | List problems (max 4) | - | Open the run | backend API (problem, checkpoints, final_checks) + template | misleading (list is silently cut to 4 with no "+N more"; scene "Failed" text is Title Case, others are backend sentences) |
| A110 | Updates | Home.tsx:140 | h3 | Console entries exist | Section | - | - | frontend hardcoded | functional |
| A111 | {HH:MM} {role badge: You/Claude/Question/Tool/System/Error} {entry text as plain text} | Home.tsx:144-146 | list | Console log | Latest 4 console entries | - | - | backend API (entry.role, text) | inconsistent (role words come from raw ids; time is the server timestamp text, not localised) |
| A112 | Open Run | Home.tsx:153 | link button | Live run | Open | - | Click | frontend hardcoded | functional |
| A113 | {n} More in Progress | Home.tsx:154 | link | Other ongoing runs | Go to list | - | Click | dynamic | inconsistent ("In Progress" vs "Ongoing") |
| A114 | Usage Limits | Home.tsx:73 | h2 | Home | Section | - | - | frontend hardcoded | functional |
| A115 | {Plan} | Home.tsx:74 | badge | usage.plan | Plan | - | - | backend API (plan) | functional |
| A116 | Updated {h:mm AM/PM} | Home.tsx:75 | note | checked_at set | Freshness | - | - | dynamic | inconsistent (sentence case; "en-US" 12h clock hard-wired) |
| A117 | Refresh / Checking | Home.tsx:76-77 | button (disabled while checking) | Usage | Manual re-check | Starts a short Haiku turn | Click | frontend hardcoded | functional (no result text for success) |
| A118 | Could Not Load Usage + {error.message} | Home.tsx:80 | SystemMessage unavailable (compact) | GET /api/usage fails | Failure | - | Click Refresh | dynamic | functional |
| A119 | Loading Usage | Home.tsx:81 | SystemMessage loading (compact) | pending | Wait | - | - | frontend hardcoded | functional |
| A120 | Asking Claude Code / Not Checked Yet | Home.tsx:82 | SystemMessage processing / empty (compact) | No windows yet | Wait or empty | - | Click Refresh | frontend hardcoded | functional |
| A121 | Current Session / All Models / Opus / Sonnet / {titleCase(id)} | Home.tsx:30 | limit names | usage windows | Name windows | five_hour, seven_day, ... | - | frontend hardcoded + backend API (id) | inconsistent (shown as "Current Session" in one group and "All Models" under Weekly Limits; "All Models" is only meaningful by group) |
| A122 | Weekly Limits | Home.tsx:86 | h3 | Weekly windows exist | Group | - | - | frontend hardcoded | functional |
| A123 | Resets at {time} / Resets {Mon} {time} | Home.tsx:35-37 | text | Limit not reached | Reset time | - | - | dynamic | inconsistent (sentence case, 12h en-US) |
| A124 | Limit Reached · Resets … | Home.tsx:45 | text with warning icon | status !== "allowed" | Limit hit | - | Wait | dynamic | misleading (any non-"allowed" status, e.g. a warning status, is labelled "Limit Reached") |
| A125 | {name}: Used (aria-label on bar); {n}% Used | Home.tsx:47-48 | progress aria-label, text | Per window | Usage | - | - | dynamic | functional |
| A126 | Closing: Curiosity, Illustrated. + closing quote | Home.tsx:197-199 | footer | Home | Brand close | - | - | frontend hardcoded | redundant (see Curiosity, Illustrated. row) |

### Ongoing and Previous Runs (pages/RunList.tsx)

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| A127 | Ongoing Runs / Previous Runs | RunList.tsx:39 | title, breadcrumb, h1 | List page | Page name | - | - | frontend hardcoded | inconsistent (nav labels "Ongoing" / "Previous Runs") |
| A128 | Newest First; Drafts From Start a Run on Top / Newest First, With Their Final Videos | RunList.tsx:157 | lead | List page | Describe sort | - | Read | frontend hardcoded | functional (sort order is backend's; not verified here) |
| A129 | Search Runs | RunList.tsx:161 | placeholder | Search field | Search | - | Type | frontend hardcoded | functional |
| A130 | Search ongoing runs / Search previous runs | RunList.tsx:159 | aria-label | Search field | Name | - | - | dynamic | inconsistent (sentence case) |
| A131 | Run / Template / Status / Where It Is / Progress / Last Saved / Actions (sr-only) | RunList.tsx:127-128 | table headers | Table | Columns | - | - | frontend hardcoded | functional |
| A132 | Table (scrolls sideways on small screens) | RunList.tsx:123 | region aria-label | Table wrapper | Name scroll region | Reads out an instruction instead of a name | - | frontend hardcoded | misleading (no name of what the table is) |
| A133 | Untitled Run | RunList.tsx:67 | draft name fallback | Draft with no name and no requirement | Fallback | - | - | frontend hardcoded | functional |
| A134 | Not Started Yet / Draft / Start a Run | RunList.tsx:68,71,72 | sub text, badge, "Where It Is" cell | Draft rows | Mark draft | - | Click to resume | frontend hardcoded | redundant ("Not Started Yet", "Draft" and "Start a Run" say the same thing in three cells) |
| A135 | — (em dash) | RunList.tsx:70,73,86 | cell fallback | No data | Placeholder | - | - | frontend hardcoded | functional |
| A136 | Started {created} | RunList.tsx:84 | sub text | Each run | Creation time | - | - | backend API (created) | functional |
| A137 | In Progress / Configuring / Awaiting Approval / Failed / Completed | RunList.tsx:27 | status badges | Each run | Run status | - | - | frontend hardcoded | inconsistent (vs StatusPill: "Waiting for You", "Done", "Not Started") |
| A138 | {stageName(stage)} / Older Version: Final Video Only / Final Video (badge) | RunList.tsx:88 | "Where It Is" cell | Each run | Stage | - | - | frontend config + hardcoded | redundant (badge "Final Video" next to stage "Final Video") |
| A139 | {n} of {7} / Not Tracked; aria label "{run.name}: Stages Approved" | RunList.tsx:92-96 | progress text | Each run | Progress | - | - | dynamic | functional |
| A140 | {run.updated} | RunList.tsx:98 | cell | Each run | Last saved | - | - | backend API (updated) | functional |
| A141 | {draft.updated with T replaced, first 16 chars} | RunList.tsx:74 | cell | Draft rows | Last saved | - | - | backend API (updated) | inconsistent (format "2026-11-27 14:05" vs time-only elsewhere) |
| A142 | Rename {run.name} / Duplicate {run.name} / Move {run.name} to the Trash / Discard Draft | RunList.tsx:76,100-102 | icon-button aria-labels | Row actions | Name icon buttons | - | Click | dynamic | inconsistent (run.name may be empty where the link uses a fallback title; "Discard Draft" does not say which draft) |
| A143 | Rename the Run / Only the Name Changes: Its Files and Progress Stay | RunList.tsx:139 | modal title, description | Rename pressed | Dialog | - | - | frontend hardcoded | functional |
| A144 | Name (required) / Cancel / Rename | RunList.tsx:140-141 | field, buttons | Rename dialog | - | - | Edit, confirm | frontend hardcoded | functional |
| A145 | Move {run.name} to the Trash? / It Leaves Your Runs; Its Folder Moves to .trash in the Runs Folder, Where It Can Be Restored | RunList.tsx:144-145 | confirm dialog | Delete pressed | Confirm | Reversible by hand | Confirm or Keep It | dynamic | misleading (says "Restored" but the UI has no restore; user must move a folder) |
| A146 | Keep It / Move to the Trash | RunList.tsx:146 | buttons | Delete dialog | Confirm | - | Click | frontend hardcoded | functional |
| A147 | Discard This Draft? / The Choices Made So Far in Start a Run Are Deleted / Keep It / Discard | RunList.tsx:148-149 | confirm dialog | Discard pressed | Confirm | Permanent | Confirm | frontend hardcoded | functional |
| A148 | Renaming… / Renamed to {name} | RunList.tsx:46,48 | Notice | Rename | Progress/success | - | - | dynamic | functional |
| A149 | Checking This Computer, Then Copying the Run… | RunList.tsx:50 | Notice working | Duplicate | Progress | - | Wait | frontend hardcoded | functional |
| A150 | {copy.name} Created | RunList.tsx:53 | Notice success | Duplicate done | Success | - | - | dynamic | misleading (page navigates to the copy at once; the Notice is on the page being left and never seen) |
| A151 | Moving to the Trash… / {name} Moved to the Trash | RunList.tsx:55,57 | Notice | Delete | Progress/success | - | - | dynamic | functional |
| A152 | Discarding the Draft… / Draft Discarded | RunList.tsx:59,61 | Notice | Discard | Progress/success | - | - | frontend hardcoded | functional |
| A153 | Could Not Load Runs + {error.message} + Try Again | RunList.tsx:108 | SystemMessage unavailable | GET /api/runs fails | Failure | - | Click Try Again | dynamic | functional |
| A154 | Loading Your Runs | RunList.tsx:109 | SystemMessage loading | pending | Wait | - | - | frontend hardcoded | functional |
| A155 | No Matches + Nothing in {ongoing runs or previous runs} mentions “{query}”. + Clear Search | RunList.tsx:112-113 | SystemMessage empty | Search with no hits | Empty | - | Clear Search | dynamic | inconsistent (body is sentence case with a full stop) |
| A156 | Nothing in Progress / No Finished Run Yet + {noRuns quote} / A Run Lands Here Once Its Final Video Is Approved + Start a Run | RunList.tsx:116-118 | SystemMessage empty | No runs | Empty | - | Click Start a Run | frontend hardcoded | functional |
| A157 | Could Not Load Your Drafts + {message} + Try Again | RunList.tsx:166 | SystemMessage unavailable (compact) | GET /api/drafts fails | Failure | - | Try Again | dynamic | functional |

### Start a Run (pages/NewRun.tsx; template steps live in pages/run and are out of scope)

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| A158 | Start a Run | NewRun.tsx:230,231 | document title, Journey aria-label | Page | - | - | - | frontend hardcoded | functional |
| A159 | Starter Templates / Audio & Subtitles / Whole Look / The Question / Audience & Length / Review | NewRun.tsx:37-42 | journey step buttons | Page | Step names | - | Click | frontend hardcoded | functional |
| A160 | Template / Requirements / Outline / Script / Scene Plans / Scenes / Final Video / Reshuffle (+ sr-only " (Optional)") | config/stages.tsx:13-20; Journey.tsx:21 | journey stage labels | Journey | Stage names | - | - | frontend config | inconsistent (Start a Run ticks "Template" as done while on the Requirements steps although it is approved only when the run starts) |
| A161 | Steps of this stage | navigation/Journey.tsx:25 | ol aria-label | Journey | Landmark | - | - | frontend hardcoded | inconsistent (sentence case) |
| A162 | All Changes Saved · {HH:MM} / Saving… / Not Saved: Trying Again on Your Next Change | NewRun.tsx:123 | status line (polite) | Draft autosave | Save state | - | - | dynamic | misleading (the time is the first 5 chars of the server timestamp; time zone unverified; "Not Saved" gives no retry button, only retry "on your next change") |
| A163 | (empty status line) | NewRun.tsx:244 | status | idle | - | - | - | - | inconsistent (no text before the first change, so a restored or brand-new draft shows nothing) |
| A164 | Name Your Run / Optional: Skip It and the Run Is Named From Its Topic and Date | NewRun.tsx:246 | modal title, description | New run (no ?draft) | Name the run | - | Type or skip | frontend hardcoded | functional |
| A165 | Run Name | NewRun.tsx:249 | field label | Name modal | - | - | Type | frontend hardcoded | functional |
| A166 | Untitled Run — {Mon d, yyyy} | NewRun.tsx:249 | placeholder | Name modal | Suggest a name | - | - | dynamic | misleading (skipping gives a name from topic and date; the placeholder suggests "Untitled Run") |
| A167 | Skip / Enter | NewRun.tsx:247 | button | Name modal | Close modal | Empty name = Skip; filled = Enter | Click | dynamic | inconsistent ("Enter" is a key name, not an action; should be "Use This Name") |
| A168 | Loading Templates | NewRun.tsx:179 | SystemMessage loading | catalogue pending | Wait | - | - | frontend hardcoded | functional |
| A169 | Could Not Load Templates + {message} | NewRun.tsx:178 | SystemMessage unavailable | GET /api/look fails | Failure | - | - | dynamic | inconsistent (no Try Again, unlike the draft error) |
| A170 | Could Not Load Your Draft + {message} + Try Again | NewRun.tsx:173-174 | SystemMessage unavailable | GET /api/drafts fails on restore | Failure | - | Try Again | dynamic | functional |
| A171 | Continue: {next step label} | NewRun.tsx:161 | button (disabled until step valid) | Steps 1-5 | Next | - | Click | dynamic | inconsistent (disabled with no reason given; see Findings) |
| A172 | Back | NewRun.tsx:165 | button | Step > 1 | Previous | - | Click | frontend hardcoded | functional |
| A173 | Start the Run | NewRun.tsx:162 | button | Review step | Create run | - | Click | frontend hardcoded | functional |
| A174 | Checking Manim, LaTeX, ffmpeg and Voice Credentials, Then Creating the Run… | NewRun.tsx:137 | Notice working | Start pressed | Progress | Preflight checks | Wait | frontend hardcoded | functional |
| A175 | {ApiError.full} on start failure | NewRun.tsx:222 | Notice (assertive) | POST /api/runs fails | Failure | e.g. missing tool | Fix and retry | backend API (error, problems) | functional |
| A176 | A Question Works Best | NewRun.tsx:192 | hint | Question step | - | - | - | frontend hardcoded | functional |
| A177 | What Should the Video Explain? (* required) | NewRun.tsx:188 | markdown field label | Question step | - | - | Type | frontend hardcoded | functional |
| A178 | Why is the sky blue, and why are sunsets red? | NewRun.tsx:189 | placeholder | Question field | Example | - | - | frontend hardcoded | inconsistent (sentence case) |
| A179 | Markdown / Write / Preview / Nothing to Preview Yet | components/ui/fields.tsx:39-46 | tag, toggle buttons, empty preview | Markdown fields | Edit/preview | - | Click | frontend hardcoded | functional |
| A180 | {label}: Write or Preview (Markdown Supported) | fields.tsx:37 | group aria-label | Markdown fields | - | - | - | dynamic | functional |
| A181 | Objectives / explain Rayleigh scattering⏎say why sunsets are red | NewRun.tsx:193-194 | field label, placeholder | Question step | - | - | Type | frontend hardcoded | functional |
| A182 | One per Line: What the Viewer Can Do Afterwards (Optional) / At Most 8 Objectives: {n} Now | NewRun.tsx:192 | hint (replaced when over limit) | Objectives | - | - | Trim list | dynamic | inconsistent (the only validation text; counts "Now") |
| A183 | How Should It Be Told? / Approach (radio group aria-label) | NewRun.tsx:201-202 | label, aria-label | Audience step | - | - | Pick | frontend hardcoded | inconsistent (visible label and accessible name differ) |
| A184 | ELI5 / Visual Intuition / Story-Driven / Step-by-Step Breakdown / Feynman Deep Dive / Mathematical & Technical / Real-World Case Study / Custom + hints ("Everyday Analogies and Simple Shapes · 3–5 Min", ...) | config/approaches.ts:4-11 | radio cards | Audience step | Teaching approach | - | Pick | frontend config | inconsistent ("Analysed" is British; the rest is American; "Min" abbreviated) |
| A185 | How Should It Be Taught? / Teaching Style, Depth, Examples, Pacing, Visuals or Your Own Scene Order / conversational, with everyday examples⏎start from a question, end with a challenge | NewRun.tsx:208-210 | field, hint, placeholder | approach = custom | - | - | Type | frontend hardcoded | functional (not required but nothing says optional) |
| A186 | Length (Minutes) / 3–20 of Teaching; Intro and Closing Are Extra | NewRun.tsx:213 | field label, hint | Audience step | - | Out of 3-20 disables Continue | Type | frontend hardcoded | misleading (picking an approach silently overwrites any length you typed) |
| A187 | Audience / For Example: Curious Beginners, Students | NewRun.tsx:214 | field label, hint | Audience step | - | - | Type | frontend hardcoded | functional |
| A188 | Voice Provider / AWS Polly: Uses Your ~/.aws Credentials / Google Cloud: Uses Your gcloud Application-Default Login | NewRun.tsx:29-32,217-218 | radio cards | Audience step | TTS choice | - | Pick | frontend hardcoded | functional |
| A189 | Starting Checks This Computer, Saves Your Template and Opens the Run | NewRun.tsx:220 | note | Review step | Explain Start | - | Read | frontend hardcoded | functional |
| A190 | Your run so far (aside aria-label); Your Run | NewRun.tsx:148-149 | aside label, h2 | Steps 4-6 | Summary | - | - | frontend hardcoded | inconsistent (sentence case aria-label vs Title Case heading; two names) |
| A191 | Template / Explain / Objectives / Approach / Length / Audience / Voice Provider | NewRun.tsx:151-157 | summary dt | Summary | - | - | - | frontend hardcoded | inconsistent ("Explain" for the question field "What Should the Video Explain?") |
| A192 | {Template} · {n} Changed / Claude Suggests Some / {n} Min / — | NewRun.tsx:152-155 | summary dd | Summary | - | - | - | dynamic | functional |

### Navigation and tabs (components/navigation, ui/Tabs)

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| A193 | Home | components/navigation/Breadcrumbs.tsx:9 | aria-label on home-icon link | Breadcrumbs | Name icon link | - | - | frontend hardcoded | functional |
| A194 | Waiting for You / Optional | navigation/ProgressSteps.tsx:22 | step hint | Run side rail | State hint | - | - | frontend hardcoded | functional |
| A195 | (Optional) sr-only | navigation/Journey.tsx:21 | screen-reader text | Optional stage | - | - | - | frontend hardcoded | inconsistent (visible "Reshuffle" has no visible Optional hint on Journey, only sr-only) |
| A196 | {n} waiting | components/ui/Tabs.tsx:157 | aria-label on count badge | tab.count > 0 | Name count | - | - | dynamic | misleading (hard-codes "waiting" for any count) |
| A197 | {label}, {tab text} | Tabs.tsx | tablist aria-label | Tabs | - | - | - | dynamic | functional |

### Media players and images (components/media)

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| A198 | No Image | media/ImagePreview.tsx:18 | media state text | Image fails to load | Failure | - | - | frontend hardcoded | inconsistent (no reason, no retry) |
| A199 | Full screen: {alt} (aria-label); Full Screen (title) | ImagePreview.tsx:101 | icon button | Beside images | Open lightbox | - | Click | dynamic | inconsistent (aria sentence case, title Title Case) |
| A200 | Full Screen / Exit Full Screen | ImagePreview.tsx:68 | button | Lightbox with fullscreen API | Toggle | - | Click | frontend hardcoded | functional |
| A201 | {alt} (dialog name and heading), {caption} | ImagePreview.tsx:57,62-63 | dialog | Lightbox | - | - | - | dynamic | functional |
| A202 | 2560 × 1440 / Preview Size / Sharpening… | ImagePreview.tsx:53,65 | badge (polite) | Lightbox with fullSrc | Render quality | - | Wait | frontend hardcoded | functional |
| A203 | {rendering quote} | ImagePreview.tsx:79 | status | Full-size render pending | Wait | - | - | frontend config | misleading (the only visible text in the spinner area is a movie quote; the actual state is only in the badge) |
| A204 | Full Size Did Not Render: Showing the Preview + {renderFailed quote} | ImagePreview.tsx:82 | status | Full-size load fails | Failure | - | - | frontend hardcoded + config | functional |
| A205 | (lightbox images alt="") | ImagePreview.tsx:75,85 | img alt | Lightbox | - | - | - | - | functional (the title above carries the description) |
| A206 | No Video Yet / {emptyHint} | media/VideoPreview.tsx:13,32-33 | empty state (default prop) | src missing | Empty | - | - | frontend hardcoded (default) / dynamic | functional |
| A207 | Loading the video | VideoPreview.tsx:49 | spinner aria-label | loading/buffering | Wait | - | - | frontend hardcoded | inconsistent (sentence case; no visible text) |
| A208 | Play / Play again: {label} | VideoPreview.tsx:51 | big play button aria-label | Before start / after end | Play | - | Click | dynamic | functional |
| A209 | {m:ss} | VideoPreview.tsx:55 | duration | Metadata loaded, not started | - | - | - | dynamic | functional |
| A210 | Full screen / Exit full screen: {label}; Full Screen / Exit Full Screen (title) | VideoPreview.tsx:58 | icon button | fullscreen supported | Toggle | - | Click | dynamic | inconsistent (aria sentence case, title Title Case) |
| A211 | {label} (video aria-label) | VideoPreview.tsx:44 | video | - | - | - | - | dynamic | functional |
| A212 | Could Not Play This Video / Try Again | VideoPreview.tsx:64-65 | alert + button | Media error | Failure | - | Click | frontend hardcoded | misleading (no reason; 404 and decode errors read the same) |
| A213 | Play / Pause | media/AudioPreview.tsx:83 | icon button label | Audio row | - | - | Click | frontend hardcoded | functional |
| A214 | Position / Volume | AudioPreview.tsx:107,114 | slider aria-labels | Audio row | - | - | Drag | frontend hardcoded | functional |
| A215 | {m:ss} of {m:ss} (aria-valuetext); {m:ss} / {m:ss} | AudioPreview.tsx:108,111 | time text | Audio row | - | - | - | dynamic | functional |
| A216 | Waveform Unavailable | AudioPreview.tsx:117 | note | Peaks cannot be computed (too large, undecodable, OR audio file missing) | Failure | - | - | frontend hardcoded | misleading (also shown when the audio itself failed to load; no audio error handler or play-failure message) |
| A217 | {label} (group aria-label) | AudioPreview.tsx:76 | group | - | - | - | - | dynamic | functional |

### Fields, pickers, helpers (components/ui)

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| A218 | * (required marker, aria-hidden) | ui/fields.tsx:19 | visual only | isRequired | Mark required | - | - | frontend hardcoded | inconsistent (react-aria still announces "required"; fine) but no visible legend |
| A219 | (FieldError, native validation text) | fields.tsx:24 | error slot | Native validation | - | - | - | - | potentially unused (no form submit, so FieldError never renders; validation is replaced by silently disabled buttons) |
| A220 | {option.label} {detail} / {hint} | fields.tsx select, checkbox, toggle, cards | labels | callers | - | - | - | dynamic | functional (Select/Checkbox/Toggle exported; usage in pages/run) |
| A221 | , {srLabel} (sr-only) | fields.tsx:125 | card label suffix | twin cards | - | - | - | dynamic | functional |
| A222 | Hex | ui/pickers.tsx:36 (shown as 66-30) | label | Color picker | - | - | Type | frontend hardcoded | functional (no invalid-hex message) |
| A223 | From This Template / Template colors | pickers.tsx:44,45 | label, swatch group aria-label | swatches present | - | - | Click | frontend hardcoded | inconsistent (two names for one group) |
| A224 | Edit the top color / Edit the bottom color | pickers.tsx:70,72 | aria-label on stop buttons | Gradient picker | - | - | Click | frontend hardcoded | inconsistent (sentence case; no pressed state) |
| A225 | Linear, Top to Bottom / Swap the Colors | pickers.tsx:75,76 | label, icon button aria-label | Gradient picker | - | - | Click | frontend hardcoded | inconsistent ("Swap the Colors" Title Case; stop buttons sentence case) |
| A226 | Top Color / Bottom Color | pickers.tsx:79 | group aria-label | Gradient picker | - | - | - | dynamic | functional |
| A227 | Nothing (WithCode, titleCase, plainText, runTitle) | ui/text.tsx; ui/Markdown.tsx | helpers | - | titleCase rewrites run titles, e.g. "3-body problem" | - | - | dynamic | functional (titleCase mangles user-typed text such as run topics; see Findings) |
| A228 | Markdown links open in a new tab | ui/Markdown.tsx:12 | link behaviour | any link | - | - | - | - | inconsistent (no indication to users or screen readers that a new tab opens) |
| A229 | (Icon components: all svg icons are aria-hidden / decorative via @untitledui props; icon-only Buttons pass `label`) | ui/icons.tsx; ui/Button.tsx:17 | accessibility | - | - | - | - | - | functional (Button with no children and no `label` would be unnamed; callers checked in scope all pass label) |

### Findings (A)

Ranked by user impact (1 = highest).

1. **Failures inside dialogs are invisible to sighted users (A143-A152, A33-A37).** RunList.tsx:165 renders `<Notice>` on the page, but Rename/Delete/Discard dialogs (RunList.tsx:138-150) stay open on top of it; on failure `done()` is not called, so the modal remains and the error text appears underneath the overlay. Only screen readers hear it (role=alert). Same pattern for NewRun naming is fine, but ProfileDialog does render its own Notice (Profile.tsx:48), so RunList is the outlier. Recommend: render `<Notice note={action.note} />` inside each Modal body.
2. **Sign-in page misreports a down server (A88, A5-A6).** SignIn.tsx:45 `.catch(() => setCodeSignedIn(false))` and session.tsx:51 `.catch(toSignIn)` mean an unreachable backend shows "Claude Code Is Not Signed In" with terminal steps. The real problem ("Faraday's server did not answer", http.ts:27) is only seen after pressing Continue. Recommend: distinguish network failure from `claude_code_signed_in === false` and show the http.ts message with the serve command.
3. **Session length is wrong (A85).** SignIn.tsx:68 says "12 Hours"; backend/app/web/auth.py:19 `SESSION_SECONDS = 24 * 3600` and cookie max_age (app.py:263). Recommend: read from the API or change to 24 Hours.
4. **Disabled Continue / Save / Start with no reason (A171, A173, A34, A186, A177).** NewRun.tsx:299-300 `ready` silently disables Continue when the question is under 3 characters, minutes outside 3-20, or more than 8 objectives (only the last has a message, A182). `FieldError` (fields.tsx:24) can never show because there is no form submit. Profile Save (Profile.tsx:35) is disabled without a cue. Recommend: show a one-line reason next to the button (e.g. "Type at least 3 characters") or use `validationBehavior="aria"`.
5. **Usage check failures are swallowed (A117, A120).** Home.tsx:62 `send(...).catch(() => undefined)`: if the Haiku check fails, the button returns to "Refresh" and the old numbers stay, with no error and no "Updated" change. Also the background check every 30 s (Home.tsx:65) spends a model turn silently. Recommend: show "Could not check usage" in the card on failure.
6. **"Limit Reached" shown for any non-"allowed" status (A124).** Home.tsx:45 treats every status other than `allowed` as reached; backend/schemas/api.py:318 says "allowed, or why not (e.g. rejected)". A warning-type status would read as a hard limit. Recommend: map known statuses; show "Rejected" only for rejected.
7. **Live Run pill is wrong in two states (A101).** Home.tsx:101-104: while `log.data` is still loading the pill says "Ready to Continue" (not busy by default); the "Done" branch is unreachable because `live` comes from `runs.ongoing` (excludes finished, hooks/useRuns.ts:12). Recommend: show nothing/"Checking" until the console loads; delete the dead branch.
8. **Duplicate success message is never seen (A149, A150).** RunList.tsx:52-53 navigates to the copy first, then returns "{name} Created"; the notice lives on the page being left. Also the 8-10 second copy has no per-row indicator. Recommend: show the message on the new run's page or skip it.
9. **Audio failures and load errors read as a waveform problem (A216).** AudioPreview.tsx:117 "Waveform Unavailable" is the only text if the audio file 404s or fails; `<audio>` has no onError and `play()` rejection is ignored (AudioPreview.tsx:71). Recommend: onError sets "Could Not Load This Audio"; catch play() failures.
10. **Humorous quotes under real errors (A41, A73, A74, A77).** SystemMessage.tsx:32-35 adds "Failure is not an option!", "Houston, we have a problem.", "...this next test is impossible." under every non-compact unavailable/error and render failure; "unsupported" gets "like tears in rain". Tone can undermine a real failure and the quotes are read aloud by screen readers inside role=alert. Recommend: keep quotes for loading/empty/success only, or exempt errors that block work.
11. **Draft restore and autosave edge cases (A162, A163, A164).** NewRun.tsx:68-73: opening `#/new?draft=<id>` for a draft that no longer exists (discarded elsewhere) silently opens a blank form (no message; saving "idle"). Autosave failure text "Not Saved: Trying Again on Your Next Change" (line 123) offers no retry and no cause. The time shown is the first 5 chars of server `updated` (timezone unverified). The name modal appears for new runs only. Recommend: show "Draft not found: starting a new one"; add Retry.
12. **Approach pick silently overwrites Length (A184, A186).** NewRun.tsx:200-203 resets minutes to the approach default on every approach click; no message. Recommend: only set when the user has not edited minutes, or say "Length set to 4 Min for this approach".
13. **Name modal confusion (A164, A166, A167).** Button reads "Enter" (NewRun.tsx:247), placeholder "Untitled Run - {date}" suggests that will be the name, but the description says skipping names it from topic and date. Recommend: button "Use This Name"/"Skip", placeholder "Optional name".
14. **Trash text promises restore that the UI cannot do (A145).** RunList.tsx:145 "Where It Can Be Restored" but there is no Restore action. Recommend: "You Can Move the Folder Back by Hand" or add Restore.
15. **Stale "Saved" in the profile dialog (A36).** Profile.tsx:21-25 sets note "Saved"; action.note is never cleared on close/reopen (useAction has setNote but Profile does not call it), so reopening shows "Saved" (and a stale error). Recommend: clear note in the isOpen effect (Profile.tsx:20).
16. **Raw/internal strings reach users (A10, A45, A9, A111, A8).** http.ts:34 shows "/api/runs answered 500"; StatusPill.tsx:13 prints raw status ids; Home Updates badge uses raw role ids (`titleCase(entry.role)`, Home.tsx:145); A9 shows literal backticks around `text-2-shorts serve` because Notice renders plain text. Recommend: friendly fallbacks and render backticks with `WithCode`.
17. **Terminology: same state, several names.** "Ongoing" (nav A16) / "Ongoing Runs" (A127) / "In Progress" (A113, A137, A44) / "Live Run" (A96); "Previous Runs" (A95, A127) / "Finished" (A97) / "Completed" (A137) / "Done" (A44); run status "Awaiting Approval" (A137) vs pill "Waiting for You" (A44, A101, A194); "Configuring" appears only in RunList; "Start a Run" vs "Start the Run" (A173); "template" vs "look" vs "starter" (A2, A159); "checkpoint" vs "stage" (A2, A109). Recommend a single glossary: pick Ongoing/Finished (or Previous), and use the StatusPill words everywhere (config/status.tsx is already the "one vocabulary" but RunList.tsx:27 bypasses it).
18. **Title Case house style broken (visible):** A7 "Signing out failed:", A9, A12, A13 (sentence case messages), A116 "Updated {time}", A123 "Resets at ...", A136 "Started {created}", A148 "Renamed to {name}", A155 "Nothing in ... mentions ...", A178 and A181 placeholders (examples, acceptable), A196 `{n} waiting`. Accessibility labels are consistently sentence case: A18 "Faraday: home", A102, A130, A161, A190, A199, A207, A210, A224 (but A225 "Swap the Colors" and A201 are Title Case), so the rule is applied inconsistently inside one component (pickers.tsx:70-76). Recommend: decide whether aria-labels follow house style; make visible strings Title Case.
19. **Titles and branding inconsistencies (A1, A4, A22, A126).** index.html title "Faraday · Curiosity, Illustrated" vs Page titles "Home · Faraday" (reverse order). "Curiosity, Illustrated." appears as hero h1 + closing motto on Home (A22, A126) and in the footer elsewhere. Logo aria-label "Faraday" (A19) is repeated beside text in footer/hero. The tab title is not updated on the loading/redirect screen (App.tsx:17 has no Page).
20. **No `<noscript>` (A3).** index.html has only `<div id="root">`; with JS disabled/blocked the page is blank. Recommend one line: "Faraday Needs JavaScript".
21. **Voice catalogue issues (A56, A64, A80, A76).** "let us make an experiment or two." is a lower-case fragment used as a full line (review, readyToBegin); "A wizard is never late..." under Pending/render waits reads as if slowness is fine; the `restricted` moment (Dave/You shall not pass) is unused (no `kind="restricted"` callers: grep in src); several moments (chooseLook, asks, nothingToDecide, complete, noChanges, openingRun) are used only in pages/run (other audit). Quotes are read verbatim by screen readers with the credit appended and no "quotation" cue (A81).
22. **Voice quote replaces guidance in empty states (A100, A156).** Home empty state "Nothing in Progress" has a quote but no action button, while RunList does (RunList.tsx:116-118); the Home hero already has "Start a Run". Minor; consider adding a hint line.
23. **RunList table accessibility and labels (A132, A142, A134, A138).** Region aria-label "Table (scrolls sideways on small screens)" is an instruction, not a name; row actions use `run.name` which can be empty where the link falls back to `runTitle(run.topic)` (RunList.tsx:83 vs 100-102, 150: label "Rename ", "{copy.name} Created"); "Discard Draft" does not say which; draft rows say "Not Started Yet", "Draft" and "Start a Run" in three cells; "Final Video" stage and "Final Video" badge duplicate (RunList.tsx:88). Recommend: label the region "Ongoing Runs table", reuse the displayed title for aria-labels, trim duplicate cells.
24. **Problems list silently truncated (A109).** Home.tsx:107-110/problems.slice(0,4) hides the rest with no "+N more". Recommend: add a count linking to the run.
25. **Journey ticks Template as done during Start a Run (A160).** NewRun.tsx:233-236 sets Template state "done" when on requirements steps, although the template is approved only when Start is pressed (NewRun.tsx:136-143). Minor misstatement of system state.
26. **Media accessibility/feedback gaps (A198, A203, A207, A212, A199, A210).** "No Image" and "Could Not Play This Video" give no cause/retry (image has no retry); lightbox waiting area shows only a quote (the real state is the badge "Sharpening…", ImagePreview.tsx:65); "Loading the video" spinner is aria-label only; aria vs title casing differs ("Full screen" / "Full Screen"). Markdown links open new tabs with no cue (A228, Markdown.tsx:12). Gradient stop buttons have no pressed state (A224).
27. **Spelling variants (A184, A55).** "Analysed" in config/approaches.ts:10 (British) while the UI uses "color" (American); "coloured" is a verbatim quote (acceptable).
28. **Stale comments describing old behaviour (not user-visible).** ImagePreview.tsx:40 says "a note thanks you for waiting" (now a Said quote); Shell.tsx:1-3 ok. Low impact.
29. **Duplicates to consolidate.** Status words (A44 vs A46 vs A137), "Loading Your Runs" (A99, A154), "Could Not Load Runs" (A98, A153: one with Try Again, one without), "Sign Out"/"Save"/"Close" fine. Home "Continue" (A95) and "Open Run" (A112) target the same run.

#### Counts
Rows: A1-A229. Findings: 29.


# Part 2 — Run pages: checkpoints, change requests, Claude panel, console, stages (rows B1–B259)
Paths are relative to `frontend/src/pages/run/` unless prefixed. "FH" = frontend hardcoded. Columns: # | Exact Text | Location | Element Type | Trigger | Purpose | Meaning | Expected User Action | Source | Status.
Text produced by shared components is out of scope except what this scope passes in. Quote texts inside `Said` come from `config/voice.ts` (frontend config).

### RunPage.tsx

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| B1 | `Run` | RunPage.tsx:80,90 | Page title (document title) | Load error, or run still loading | Tab title before run is known | Generic placeholder | None | frontend hardcoded | functional |
| B2 | `Could Not Load This Run` | RunPage.tsx:81 | SystemMessage title (unavailable) | `detail.error && !run` | Tell load failed | Run could not be fetched | Retry or go back | frontend hardcoded | functional |
| B3 | `Try Again` | RunPage.tsx:82,125 | Button | Load error / stale error | Reload run | Retry fetch | Click | frontend hardcoded | functional |
| B4 | `All Runs` | RunPage.tsx:83 | Button | Load error | Navigate `#/ongoing` | List of runs | Click | frontend hardcoded | inconsistent (list pages are called "Ongoing Runs"/"Previous Runs"; goes to ongoing even for finished runs) |
| B5 | `{detail.error.message}` | RunPage.tsx:85,126 | SystemMessage body | Load error | Reason | Error text | Read | backend API (error message via errorText/ApiError) | functional |
| B6 | `Opening the Run` (+ Said `openingRun`: "We have now some very interesting points to study." / "Hey, you. You're finally awake.") | RunPage.tsx:90 | SystemMessage loading | `!run` | Loading state | Run being fetched | Wait | frontend hardcoded + frontend config (voice.openingRun) | functional |
| B7 | `Previous Runs` / `Ongoing Runs` | RunPage.tsx:93 | Breadcrumb label | finished vs not | Back link | List the run belongs to | Click | frontend hardcoded | functional |
| B8 | `${step.label} · ${run.summary.name \|\| runTitle(run.summary.topic)}` | RunPage.tsx:102 | Document title | Always | Tab title | Open stage and run name | None | dynamic (STAGE_STEPS label + backend summary.name/topic) | functional |
| B9 | `Run` | RunPage.tsx:105 | aria-label on rail `<aside>` | Non-problem run | Name the landmark | Rail landmark | SR navigation | frontend hardcoded | ambiguous (says "Run", not what the rail holds; page title also "Run") |
| B10 | `Stages Approved` | RunPage.tsx:106 | ProgressBar label | Rail | Progress label | Count of approved required stages | None | frontend hardcoded | functional |
| B11 | `${approved} of ${REQUIRED_STEPS.length}` | RunPage.tsx:106 | ProgressBar valueLabel | Rail | Value | e.g. "3 of 7" | None | dynamic | functional |
| B12 | `Stages of This Run` | RunPage.tsx:107 | ProgressSteps label | Rail | Nav label | Stage list | Pick a stage | frontend hardcoded | functional |
| B13 | stage labels `Template`, `Requirements`, `Outline`, `Script`, `Scene Plans`, `Scenes`, `Final Video`, `Reshuffle` | RunPage.tsx:109 via config/stages.ts:13-20 | Step labels (also stage h2, approval bar, Next notices) | Rail | Name stages | Pipeline order | Click | frontend config | functional |
| B14 | `Open Console` | RunPage.tsx:111 | Button | Non-problem run | Open console drawer | Talk to Claude | Click | frontend hardcoded | functional |
| B15 | `Request a Change` | RunPage.tsx:112 | Button | Open stage not in NO_REQUESTS | Open ChangeModal | Ask for change | Click | frontend hardcoded | functional (button silently absent on Template/Requirements/Reshuffle with no explanation) |
| B16 | `Optional` | RunPage.tsx:139 | Badge | step.optional (Reshuffle) | Mark optional stage | Not required | None | frontend hardcoded | functional |
| B17 | status pill label (`Approved`, `Done`, `In Progress`, `Being Revised`, `Waiting for You`, `Failed`, `Not Started`) | RunPage.tsx:139 via config/status.tsx:11-17 | StatusPill | Not waiting and not approved; fallback "pending" | Stage state | State | None | frontend config | functional |
| B18 | `<step.label> Is Waiting for Your Decision` | RunPage.tsx:143 | Approval bar (role=status) | waitingIn && tab !== waitingIn | Prompt for approval | Checkpoint pending | Click Decide | dynamic | functional (grammar odd for "Scenes Is Waiting", "Scene Plans Is Waiting") |
| B19 | `Decide` | RunPage.tsx:144 | Button | Approval bar | Go to checkpoint tab | -- | Click | frontend hardcoded | functional |
| B20 | `This Run Cannot Be Read Right Now` | RunPage.tsx:132 | SystemMessage title (unsupported) | `run.problem` starts with "This run cannot be read" | Unreadable run | Temporary/format issue | Wait/retry | frontend hardcoded (branches on backend string prefix) | functional (fragile coupling to backend wording) |
| B21 | `This Run Was Made by an Older Version` | RunPage.tsx:132 | SystemMessage title | Any other `run.problem` | Old-format run | Final video only | Watch video | frontend hardcoded | misleading (every other problem is labelled "older version") |
| B22 | `{run.problem}` | RunPage.tsx:132 | SystemMessage body via WithCode | `run.problem` | Detail | Reason | Read | backend API (run.problem) | functional |
| B23 | `Final Video: ${name}` | RunPage.tsx:133 | VideoPreview label | problem run | Video label | -- | Play | dynamic | functional |
| B24 | `No Final Video` | RunPage.tsx:133 | VideoPreview empty | problem run, no final | Empty state | -- | None | frontend hardcoded | inconsistent (Final stage says "No Final Video Yet") |
| B25 | `Not Up to Date` | RunPage.tsx:124 | SystemMessage title (offline) | Refresh/poll failed with data shown | Stale data | Poll failed | Try Again | frontend hardcoded | functional |
| B26 | `Console` | RunPage.tsx:153 | Drawer title | consoleOpen | Name drawer | -- | -- | frontend hardcoded | functional |
| B27 | Notice text passed to `refresh(message)` | RunPage.tsx:62-65,122 | Notice (polite live) | After any write | Outcome | Whatever caller passed | Read | dynamic (see rows B60, B72, B73, B83, B108, B199, B215) | functional (never cleared; see Finding 6) |

### context.tsx

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| B28 | `useRun outside a run page` | context.tsx:21 | Thrown Error (developer-only) | Misuse | Dev guard | -- | None | frontend hardcoded | functional (not user-visible unless bug) |

### Overview.tsx

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| B29 | `At a Glance` | Overview.tsx:58 | Chips label | Always | Group name | Summary chips | None | frontend hardcoded | functional |
| B30 | `Approach` + value approachName() | Overview.tsx:59 | Chip | run.approach | Show approach | -- | None | frontend hardcoded label; backend API (run.approach) value | functional |
| B31 | `Length` + `${run.minutes} Min` | Overview.tsx:60 | Chip | run.minutes | Show length | -- | None | dynamic | inconsistent (`Min` here, `min` in Requirements B140) |
| B32 | `Scenes` + count | Overview.tsx:61 | Chip | Always | Scene count | -- | None | dynamic | functional |
| B33 | `Open Requests` + count | Overview.tsx:62 | Chip | open > 0 | Open change requests | Unfinished requests | None | frontend hardcoded | inconsistent (elsewhere "Change Requests"/"Changes") |
| B34 | `Started` + run.summary.created | Overview.tsx:63 | Chip | Always | Creation time | -- | None | frontend hardcoded label; backend API (summary.created) raw value | functional (raw format unverified) |
| B35 | `Clips per Scene` | Overview.tsx:22 | Chart title | scenes exist | Chart name | -- | None | frontend hardcoded | functional |
| B36 | Legend `Done` / `In Progress` / `Waiting for You` / `Failed` / `Not Started` | Overview.tsx:24 via config/status.tsx:21-27 | Legend items | Present buckets only | Explain fills | -- | None | frontend config | functional (bucket "Done" merges Approved and Done) |
| B37 | `Scene N` (sceneName) | Overview.tsx:14,34 | Row label | Each scene | Name scene | s03 becomes "Scene 3" | None | dynamic | inconsistent (ChangeModal shows "Scene s03", B65) |
| B38 | `${scene}, ${titleCase(title)}: ${summary \|\| "no clips planned"}` | Overview.tsx:33 | aria-label on row | Each scene | SR summary | e.g. "Scene 2, Title: Done: 2, Not Started: 1" | SR users read | dynamic | inconsistent (lowercase "no clips planned" vs Title Case) |
| B39 | `title={titleCase(scene.title)}` | Overview.tsx:34 | Tooltip | Hover | Full title | -- | None | backend API (scene.title) | functional |
| B40 | `${scene} · ${title} — ${bucket.label}: ${n} of ${total}` | Overview.tsx:40 | Segment tooltip | Hover | Detail | -- | None | dynamic | functional (tooltip-only, not keyboard reachable) |
| B41 | `${scene}: no clips planned` | Overview.tsx:41 | Tooltip | scene.clips empty | Empty bar | -- | None | dynamic | inconsistent (lowercase) |
| B42 | `${done}/${clips.length}` | Overview.tsx:44 | Count text | Each scene | Done clips | -- | None | dynamic | functional |

### CheckpointPanel.tsx

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| B43 | `Decisions` | CheckpointPanel.tsx:33 | h3 | decisions exist | History heading | Past decisions | Read | frontend hardcoded | functional |
| B44 | `${titleCase(decision.decision)}${forced ? " (Accepted With Open Problems)" : ""}` | CheckpointPanel.tsx:37 | List item | each decision | History | e.g. "Approved (Accepted With Open Problems)" | Read | backend API (decision.decision) + frontend hardcoded suffix | functional |
| B45 | `${decided_at with T->space}${ · by}` | CheckpointPanel.tsx:38 | Meta | each decision | Timestamp, author | raw ISO-ish string | Read | backend API (decided_at, by) | functional (unformatted timestamp, no timezone) |
| B46 | `{decision.notes}` | CheckpointPanel.tsx:39 | Markdown | notes present | User notes | -- | Read | backend API (notes) | functional |
| B47 | `You Approved This Checkpoint` / `Changing What It Covers Asks You Again` | CheckpointPanel.tsx:49 | SystemMessage success | no awaiting checkpoint and stage approved | Status | Approved | None | frontend hardcoded | functional (also shows on scene "start:" tabs where "approved" is read from stage not scene) |
| B48 | `Nothing to Decide Yet` / `Claude Asks When This Stage Is Ready` (+ Said "Wake me, when you need me.") | CheckpointPanel.tsx:50 | SystemMessage pending | no checkpoint, not approved | Empty state | Nothing to approve now | Wait | frontend hardcoded + frontend config (voice.nothingToDecide) | functional (also shown after Claude finished with nothing to ask, no next step) |
| B49 | `${checkpoint.label}` | CheckpointPanel.tsx:69 | h3 | checkpoint present | Name checkpoint | -- | Read | backend API (awaiting[].label) | functional |
| B50 | `Open Problems` | CheckpointPanel.tsx:72 | Subhead p | problems.length | Heading | -- | Read | frontend hardcoded | functional (a `<p>` styled as heading, not a heading element) |
| B51 | `{problem}` list | CheckpointPanel.tsx:73 | List via WithCode | problems | List problems | -- | Read | backend API (awaiting[].problems) | functional |
| B52 | `Approve with Open Problems` | CheckpointPanel.tsx:74 | Checkbox label | blocked | Explicit override | -- | Tick | frontend hardcoded | inconsistent (title case drops "with" lowercase OK; but sentence-ish) |
| B53 | `Approving Records These as Open` | CheckpointPanel.tsx:74 | Checkbox hint | blocked | Explain consequence | Problems saved with decision | Read | frontend hardcoded | functional |
| B54 | `Nothing Blocks This Checkpoint` | CheckpointPanel.tsx:76 | Note | no problems | Reassure | -- | Approve | frontend hardcoded | functional |
| B55 | `Notes (Optional)` | CheckpointPanel.tsx:77 | MarkdownField label | Always | Notes | -- | Type | frontend hardcoded | functional (no placeholder/hint) |
| B56 | `Approve & Continue` | CheckpointPanel.tsx:79 | Button | Always (disabled while busy, already sent, or blocked && !accepted) | Approve | Approves, moves on | Click | frontend hardcoded | misleading on scene "start:" and "scenes"-final checkpoints where nothing follows (stays on the tab) |
| B57 | `Request a Change` | CheckpointPanel.tsx:80 | Button | target not in NO_REQUESTS | Open modal for this checkpoint | -- | Click | frontend hardcoded | functional |
| B58 | `Tick Approve with Open Problems to Approve Anyway, or Ask Claude in the Console` / `... or Request a Change` | CheckpointPanel.tsx:82 | Note, aria-describedby target of disabled Approve | blocked && !accepted | Explain why disabled | -- | Tick or ask | frontend hardcoded | functional (no end punctuation; "Console" is a drawer opened elsewhere, not linked) |
| B59 | `Approving…` | CheckpointPanel.tsx:57 | Working notice | Approve clicked | Progress | -- | Wait | frontend hardcoded | functional |
| B60 | `${checkpoint.label} Approved${forced ? " With Its Open Problems" : ""}${after ? `: Next, ${after.label}` : ""}` | CheckpointPanel.tsx:63 | refresh() notice | After approve succeeds | Success | e.g. "Outline Approved: Next, Script" | Continue | dynamic (backend label) | misleading for `final` ("Next, Reshuffle" is optional and not required) and for scene checkpoints (no "next") |
| B61 | Error text from failed approve | CheckpointPanel.tsx:83 via useAction | Notice (assertive) | Request fails | Failure | -- | Retry | backend API (error) / shared errorText | functional (no retained form guidance) |

### ChangeModal.tsx

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| B62 | `Request a Change` | ChangeModal.tsx:68 | Modal title | ask != null | Title | -- | -- | frontend hardcoded | functional |
| B63 | `Any Stage, Scene or Clip: Claude Applies It and Marks It Done` | ChangeModal.tsx:68 | Modal description | Open | Explain | Claude will apply it | Read | frontend hardcoded | misleading (modal is not reachable for Template/Requirements/Reshuffle; "Marks It Done" is not guaranteed) |
| B64 | `What Should Change` | ChangeModal.tsx:73 | Select label | Open | Pick target | -- | Choose | frontend hardcoded | functional |
| B65 | Target options: `The Outline`, `The Script`, `All Scene Plans`, `All Scenes`, `Scene ${scene_id}: ${title}`, `Clip ${clip_id}: ${objective}`, `The Final Video` | ChangeModal.tsx:28-33 | Select options | Open | Targets | -- | Choose | frontend hardcoded + backend API (scene_id, title, clip_id, objective) | inconsistent (raw ids "Scene s03" vs "Scene 3"; "The ..." prefix vs stage names; titles not title-cased here) |
| B66 | `Kind of Change` | ChangeModal.tsx:74 | Select label | Open | Pick kind | -- | Choose | frontend hardcoded | functional |
| B67 | Kind options: `Wording: What Is Said`, `Visuals: What Is Shown`, `Audio Timing`, `Accuracy: a Claim Is Wrong`, `Structure: Order or Scenes`, `Style: Look or Tone`, `Something Else` | ChangeModal.tsx:15-18 | Select options | Open | Categories | -- | Choose | frontend hardcoded | inconsistent (`a` lowercase mid-title is house Title Case OK; "Audio Timing" and "Something Else" lack explanation unlike the others; "Visuals" label vs id "visual"; "Style: Look or Tone" overlaps Template stage which cannot request) |
| B68 | `Describe the Change` | ChangeModal.tsx:75 | MarkdownField label (required) | Open | Free text | -- | Type | frontend hardcoded | functional (no hint about 3-character minimum) |
| B69 | `Cancel` | ChangeModal.tsx:70 | Button | Open | Close | -- | Click | frontend hardcoded | functional |
| B70 | `Send Request` | ChangeModal.tsx:71 | Button | Disabled while busy or text < 3 chars | Submit | -- | Click | frontend hardcoded | functional (disabled with no reason given) |
| B71 | `Sending…` | ChangeModal.tsx:51 | Working notice | Submit | Progress | -- | Wait | frontend hardcoded | functional (modal closes in the middle of the action, so later notice states show inside a closed modal) |
| B72 | `Change Request ${request.id} Recorded: Claude Applies It After the Step It Is On` | ChangeModal.tsx:59 | refresh() notice | console busy after recording | Success | Running turn will pick it up | Wait | dynamic (backend request.id) | depends on unverified claim: busy turn picks up request (comment M20) |
| B73 | `Change Request ${request.id} Recorded: Claude Is Applying It` | ChangeModal.tsx:64 | refresh() notice | console idle, new turn fired | Success | Turn started | Wait | dynamic | misleading when the fire-and-forget turn fails to start (error swallowed at :63) |
| B74 | `I asked for a change: ${id} (${target}, ${kind}). Apply it, then carry on.` | ChangeModal.tsx:62 | User message sent to Claude; appears in console as "you" line | Idle | Trigger turn | -- | Read in console | dynamic | functional (English, raw ids/kinds shown to user) |
| B75 | Errors from send()/load() | ChangeModal.tsx:76 | Notice | Failure | Failure | -- | Retry | backend API / shared errorText | misleading: after `onClose()` at :55 the modal closes, a later failure of `load(console)` lands in a closed modal's Notice and nowhere visible while the request is already recorded |

### ClaudePanel.tsx

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| B76 | `Could Not Load Claude's Messages` + error message | ClaudePanel.tsx:41 | SystemMessage unavailable | view.error | Failure | -- | Wait/reload | frontend hardcoded + backend API (error) | functional (no retry button) |
| B77 | (nothing) | ClaudePanel.tsx:42 | Loading state returns null | view loading | -- | -- | -- | n/a | no feedback while loading |
| B78 | `Claude Is Working` / `Its Reply Appears Here When It Ends` | ClaudePanel.tsx:61 | SystemMessage processing | view.data.busy && !turn.busy (turn started elsewhere) | Waiting | -- | Wait | frontend hardcoded | functional (hides reply box, option buttons, and Notice while busy) |
| B79 | `Ready to Begin` (+ Said readyToBegin: "This is only the beginning." / "let us make an experiment or two.") | ClaudePanel.tsx:69-70 | h2 + quote | no entries and not live | Idle intro | -- | Click Start | frontend hardcoded + frontend config | functional |
| B80 | `Claude` | ClaudePanel.tsx:66,77 | aria-label on sections | Always | Landmark | -- | -- | frontend hardcoded | functional |
| B81 | `Start Production` | ClaudePanel.tsx:72 | Button | idle | Sends backend kickoff text | Start turn | Click | frontend hardcoded; message sent is backend API (kickoff) | functional (Console button for same action says `Start`) |
| B82 | `Claude Is Working: Renders and Voice Can Take Minutes` | ClaudePanel.tsx:48 | Working notice | send() | Progress | -- | Wait | frontend hardcoded | functional |
| B83 | `Claude Finished` | ClaudePanel.tsx:51 | refresh() notice | streamTurn promise resolves | Completion | -- | Read | frontend hardcoded | misleading (see Finding 2): fires on any clean stream end, incl. stream cut or error entries |
| B84 | h2 `Claude Is Working` / `Claude Asks` / `Claude Says` | ClaudePanel.tsx:81 | Heading | turn.busy / asks / default | State label | -- | Read | frontend hardcoded | inconsistent (same "Claude Is Working" appears as B78 for a different state) |
| B85 | Said asks: "Help me, Obi-Wan Kenobi. You're my only hope." | ClaudePanel.tsx:82 | Note quote | asks | Voice line | Claude waits for you | Answer | frontend config (voice.asks) | functional (quote attributes to Star Wars; does not tell what to do) |
| B86 | `{entry.text}` Markdown | ClaudePanel.tsx:88 | Content | said entries | Claude's words | -- | Read | backend API (console entry.text) | functional |
| B87 | `{option}` buttons | ClaudePanel.tsx:91 | Buttons | entry.options | One-click answers | -- | Click | backend API (entry.options) | functional |
| B88 | `Waiting for Claude` / `No Reply` | ClaudePanel.tsx:95 | Note | said empty; busy / not | Empty state | -- | Wait | frontend hardcoded | functional ("No Reply" ambiguous: reads like Claude refused) |
| B89 | `Your Answer` / `Reply to Claude` | ClaudePanel.tsx:98 | Field label | asks / not | Label | -- | Type | frontend hardcoded | functional |
| B90 | `Your Answer` / `Message Claude` | ClaudePanel.tsx:99 | Placeholder | asks / not | Hint | -- | Type | frontend hardcoded | redundant (placeholder equals label when asking) |
| B91 | `Send` | ClaudePanel.tsx:100 | Submit button | Disabled while busy/empty | Send reply | -- | Click | frontend hardcoded | functional |
| B92 | error text from failed turn | ClaudePanel.tsx:102 | Notice | Failure | Failure | -- | Retry | backend API / shared errorText | functional (typed reply restored at :55; option answers not) |
| B93 | `aria-live="polite"` on whole section | ClaudePanel.tsx:77 | a11y | Always | Announce | -- | -- | frontend hardcoded | potential noise: streaming entries and a nested Notice live region are both announced |

### Console.tsx

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| B94 | `Could Not Load the Console` + message | Console.tsx:36 | SystemMessage unavailable | view.error | Failure | -- | Close/reopen | frontend hardcoded + backend API (error) | functional (no retry) |
| B95 | `Connecting` | Console.tsx:37 | SystemMessage loading | Loading | Wait | -- | Wait | frontend hardcoded | functional |
| B96 | `claude code` | Console.tsx:66 | Terminal bar | Always | Terminal title | -- | -- | frontend hardcoded | inconsistent (lowercase; product name "Claude Code" elsewhere "Claude") |
| B97 | `{id}` | Console.tsx:66 | Terminal bar | Always | Run id | -- | -- | backend API (summary.id) | functional |
| B98 | `Conversation with Claude` | Console.tsx:67 | aria-label on log (aria-live polite) | Always | Name log | -- | -- | frontend hardcoded | functional |
| B99 | `No Messages Yet` | Console.tsx:77 | Empty li | no lines | Empty state | -- | Start | frontend hardcoded | functional |
| B100 | entry text per role (claude/question/you markdown; tool/error raw) | Console.tsx:73 | Content | each entry | Transcript | -- | Read | backend API (entries) | functional (speaker only given by CSS class; no text/SR label for who spoke) |
| B101 | `Choices: ${options.join(" · ")}` | Console.tsx:74 | Span | entry.options | Show choices | -- | Type an answer | dynamic | functional (not clickable here, unlike ClaudePanel) |
| B102 | `Message to Claude` | Console.tsx:81 | aria-label textarea | Always | Label | -- | -- | frontend hardcoded | functional |
| B103 | `Message Claude` / `${kickoff}` | Console.tsx:82 | Placeholder | started / not | Hint | before start the placeholder is the whole backend kickoff prompt | Type or press Start | frontend hardcoded / backend API (kickoff) | misleading (looks like a hint but it is the message that will be sent; long) |
| B104 | `Send` / `Start` | Console.tsx:84 | Submit button | started / not | Send | -- | Click | frontend hardcoded | inconsistent (ClaudePanel says "Start Production") |
| B105 | `Enter Sends · Shift+Enter for a New Line` | Console.tsx:86 | Hint (aria-describedby) | Always | Keys | -- | Read | frontend hardcoded | functional |
| B106 | `Claude Is Still Replying: Its Messages Appear Here as It Works` | Console.tsx:88 | Note | view.busy && !turn.busy | Waiting | -- | Wait | frontend hardcoded | functional (textarea becomes read-only without a visible reason except this note) |
| B107 | `Claude Is Working: Renders and Voice Can Take Minutes` | Console.tsx:49 | Working notice | submit | Progress | -- | Wait | frontend hardcoded | duplicate of B82 |
| B108 | `Claude Finished` | Console.tsx:51 | refresh() notice | stream ends | Completion | -- | -- | frontend hardcoded | misleading (see Finding 2) and not visible: goes to the run page Notice behind the open Drawer; console shows nothing when work ends |
| B109 | error text | Console.tsx:89 | Notice | Failure | Failure | -- | Retry | backend API / shared errorText | functional |

### review.tsx

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| B110 | `Claude's Next Step` + count badge | review.tsx:22 | Disclosure toggle | batchStage matches stage and actions exist | Show upcoming work | -- | Expand | frontend hardcoded | inconsistent (singular title, count of steps; panel lists many "steps") |
| B111 | `{titleCase(action.agent)}` | review.tsx:29 | Badge | action.agent | Which agent | -- | Read | backend API (next.actions[].agent) | functional |
| B112 | `${action.target}: ` | review.tsx:30 | Id span | action.target | Target | -- | Read | backend API (target) | functional |
| B113 | `{action.what}` | review.tsx:31 | WithCode | each action | Instruction text | workflow's instruction to Claude | Read | backend API (next.actions[].what) | functional (written for Claude, not for users) |
| B114 | `Change Requests` | review.tsx:44 | Section title | Changes tab | Heading | -- | -- | frontend hardcoded | inconsistent with tab `Changes` and chip `Open Requests` |
| B115 | `Request a Change` | review.tsx:45 | Button | Changes tab | Open modal | -- | Click | frontend hardcoded | functional |
| B116 | `${id} · ${kind} on ${target} · ${status}${note ? ` (${note})` : ""}` | review.tsx:51 | List meta | each request | Request status | e.g. "r01 · wording on outline · open" | Read | backend API (id, kind, target, status, note) | inconsistent (raw lowercase ids/kinds/status, not Title Case or the labels from KINDS) |
| B117 | `{request.text}` | review.tsx:50 | Markdown | each request | Request | -- | Read | backend API (text) | functional |
| B118 | `No Changes Requested` (+ Said "Mostly harmless") | review.tsx:55 | SystemMessage empty | no requests | Empty state | -- | -- | frontend hardcoded + frontend config (voice.noChanges) | functional |
| B119 | `Round ${index + 1}` | review.tsx:70 | h4 | each round | Round title | -- | Read | dynamic | functional |
| B120 | `${titleCase(round.verdict)}` | review.tsx:71 | Badge | each round | Verdict | -- | Read | backend API (verdict) | functional |
| B121 | `${score}/100` | review.tsx:72 | Score | score != null | Score | -- | Read | backend API (score) | functional |
| B122 | `{round.summary}` | review.tsx:74 | p | summary | Summary | -- | Read | backend API (summary) | functional |
| B123 | `Keeps: ${strengths.join(" · ")}` | review.tsx:75 | Note | strengths | Strengths | -- | Read | frontend hardcoded prefix + backend API (strengths) | ambiguous ("Keeps" unclear; means "Strengths kept") |
| B124 | `Table (scrolls sideways on small screens)` | review.tsx:77,104 | aria-label on scroll region | tables | SR name | -- | -- | frontend hardcoded | ambiguous (every table has the same name; says nothing about contents) |
| B125 | Headers `Rule`, `Where`, `Problem`, `Fix` | review.tsx:79 | th | critique issues | Table headers | -- | Read | frontend hardcoded | functional |
| B126 | `{criterion}` `{tier}` / `{target}` / `{problem}` `{evidence}` / `{fix}` | review.tsx:83-86 | Cells | each issue | Data | -- | Read | backend API (Issue fields) | functional (raw, no title case) |
| B127 | `No Accuracy Problems` | review.tsx:102 | SystemMessage success | findings empty | Success | -- | -- | frontend hardcoded | functional |
| B128 | Headers `Severity`, `Where`, `Quote`, `Why`, `Fix` | review.tsx:106 | th | findings | Headers | -- | Read | frontend hardcoded | functional |
| B129 | `${titleCase(`${severity} ${kind}`)}` | review.tsx:110 | Badge | each finding | Severity | -- | Read | backend API (severity, kind) | functional |
| B130 | `“{quote}”`, `{why}`, `{fix}`, `{target}` | review.tsx:111 | Cells | each finding | Data | -- | Read | backend API | functional |
| B131 | `No ${what} Yet` | review.tsx:122 | SystemMessage missing title (NotYet) | file absent | Empty | -- | Wait | dynamic (what from callers) | functional |
| B132 | `Claude Writes It When the Run Gets Here` | review.tsx:122 | NotYet default body | no children | Explain | -- | Wait | frontend hardcoded | functional (wrong for "Media Checks" B183 and "Accuracy Review", which Claude "writes" differently) |

### stages/StageTabs.tsx

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| B133 | `label` prop of each stage (see rows below) | stages/StageTabs.tsx:14 | Tabs aria label | Always | Name tab list | -- | -- | frontend hardcoded (by caller) | functional |
| B134 | tab `count` badges (waiting() = 1 or 0; error counts; check counts) | stages/StageTabs.tsx:17 | Tab badge | Per stage | Attention markers | -- | Open tab | dynamic | ambiguous (a bare number; meaning (decisions waiting vs errors) differs per tab and is not named) |

### stages/Requirements.tsx

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| B135 | `Requirements` | Requirements.tsx:15 | Tabs label | Always | Name | -- | -- | frontend hardcoded | functional |
| B136 | Tabs `Brief`, `Topics`, `Content`, `Checkpoint` | Requirements.tsx:16,24-26 | Tab labels | Always | Navigate | -- | Click | frontend hardcoded | functional |
| B137 | Facts `Explain`, `Objectives`, `Approach`, `Length` | Requirements.tsx:18-21 | dt | Brief tab | Labels | -- | Read | frontend hardcoded | ambiguous ("Explain" is the topic; elsewhere "Topic"/"Question") |
| B138 | `{run.summary.topic}`, objectives, approachName(run.approach) | Requirements.tsx:18-20 | dd | Brief | Data | -- | Read | backend API (topic, objectives, approach) | functional |
| B139 | `Not Set Yet: Claude Proposes Them With You` | Requirements.tsx:19 | dd fallback | no objectives | Empty | -- | Wait / talk to Claude | frontend hardcoded | functional |
| B140 | `${run.minutes} min` | Requirements.tsx:21 | dd | Always | Length | -- | Read | dynamic | inconsistent (`Min` in Overview B31; renders "undefined min"/"0 min" if missing) |
| B141 | `No Topic List Yet` + `Claude Writes It When the Run Gets Here` | Requirements.tsx:24 | NotYet | no topics.md | Empty | -- | Wait | dynamic + frontend hardcoded | functional |
| B142 | `No Content Yet` + same body | Requirements.tsx:25 | NotYet | no content.md | Empty | -- | Wait | dynamic | ambiguous (title "No Content Yet" reads as a generic empty message) |
| B143 | topics.md / content.md body | Requirements.tsx:24-25 | Markdown | present | Documents | -- | Read | backend API (media file) | functional |

### stages/Writing.tsx (Outline and Script)

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| B144 | `Outline` (tabs label and tab) | Writing.tsx:15-16 | Tabs | Always | Name | -- | -- | frontend hardcoded | redundant (tab "Outline" inside stage "Outline") |
| B145 | `Changes`, `Checkpoint` tabs | Writing.tsx:27-28,65-66 | Tabs | Always | Navigate | -- | Click | frontend hardcoded | functional |
| B146 | `{segment.scene_id}`, `{segment.title}`, `titleCase(segment_type)`, `${duration_seconds} s`, talking points | Writing.tsx:20-21 | Card contents | Each outline segment | Outline | -- | Read | backend API (outline.json) | functional (raw number id, title not title-cased unlike Script) |
| B147 | `Picture: ${segment.visual_plan}` | Writing.tsx:22 | Note | Each segment | Visual plan | -- | Read | frontend hardcoded prefix + backend API | inconsistent ("Picture" vs "Visuals" elsewhere) |
| B148 | `No Outline Yet` + default body | Writing.tsx:26 | NotYet | no outline | Empty | -- | Wait | dynamic | functional |
| B149 | `Script` (tabs label, tab) | Writing.tsx:41-42 | Tabs | Always | Name | -- | -- | frontend hardcoded | redundant |
| B150 | `${duration_seconds} s · ${words} words` | Writing.tsx:49 | Meta | Each scene | Info | -- | Read | dynamic | functional ("1 words" grammar; word count of empty narration is 1) |
| B151 | scene role badge, `titleCase(title)`, objective, bridge_in, narration | Writing.tsx:48-55 | Text | Each scene | Script | -- | Read | backend API (script.json) | functional |
| B152 | `No Script Yet` | Writing.tsx:60 | NotYet | no script | Empty | -- | Wait | dynamic | functional |
| B153 | Tabs `Accuracy` (+ error count), `Critique` | Writing.tsx:61,63 | Tabs | Always | Navigate | -- | Click | frontend hardcoded | inconsistent (`Accuracy` vs `Accuracy Review` in NotYet) |
| B154 | `No Accuracy Review Yet` | Writing.tsx:62 | NotYet | no review | Empty | -- | Wait | dynamic | functional |
| B155 | `No Script Critique Yet` / `Critiqued When You Request a Change at Its Checkpoint` | Writing.tsx:64 | NotYet with custom body | no critique file | Explain | -- | Request a change? | frontend hardcoded | ambiguous/possibly outdated (claims critique only runs on change request; verify with backend workflow; Reads as an instruction) |

### stages/Production.tsx

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| B156 | `Loading the Execution Plan of ${sceneName}` | Production.tsx:23 | SystemMessage loading | file loading | Loading | -- | Wait | dynamic | functional |
| B157 | `No Execution Plan for ${sceneName}` | Production.tsx:24 | SystemMessage missing | no execution_plan | Empty | -- | Wait | dynamic | functional (also shown on fetch failure) |
| B158 | `Execution Plan` (h3) + scene badge | Production.tsx:30 | Heading | present | Title | -- | Read | frontend hardcoded | functional |
| B159 | Section headings derived from tags, e.g. `### ${titleCase(TAG)}` | Production.tsx:27 | Markdown headings | execution_plan text | Show tagged sections | -- | Read | backend API (execution_plan) transformed | functional |
| B160 | `Scene Code`, `Manim code of ${sceneName}` | Production.tsx:44,46 | h3, aria-label | scene_code.py exists | Show code | -- | Read | frontend hardcoded | functional (card silently absent when file missing) |
| B161 | CHANGES.md body | Production.tsx:45 | Markdown | present | Builder notes | -- | Read | backend API (media file) | functional |
| B162 | `Loading the Plan of ${sceneName}` | Production.tsx:54 | SystemMessage loading | loading | Loading | -- | Wait | dynamic | functional (renders nothing if load failed) |
| B163 | `Opens With: ${transition_in}` | Production.tsx:59 | Note | transition_in | Transition | -- | Read | frontend hardcoded + backend API | functional |
| B164 | Headers `Clip`, `What It Shows`, `Beats`, `Seconds` | Production.tsx:62 | th | PlanCard | Headers | -- | Read | frontend hardcoded | functional |
| B165 | `No ${titleCase(kind)} Critique for ${sceneName} Yet` | Production.tsx:82 | SystemMessage pending | no critique file | Empty | -- | Wait | dynamic | functional |
| B166 | `${sceneName} · ${titleCase(kind)} Critique` | Production.tsx:83 | h3 title | present | Title | -- | Read | dynamic | functional |
| B167 | `No Scene Plans Yet` / `Written After You Approve the Script` | Production.tsx:89 | NotYet | no scenes | Explain | -- | Approve script | dynamic + frontend hardcoded | potentially misleading (relies on assumption that scenes are created exactly when script approved) |
| B168 | `Scene Plans` (tabs label); tabs `Plans`, `Execution Plans`, `Critiques`, `Accuracy`, `Checkpoint` | Production.tsx:91-96 | Tabs | Always | Navigate | -- | Click | frontend hardcoded | functional |
| B169 | `No Accuracy Review Yet` | Production.tsx:95 | NotYet | no plan_review.json | Empty | -- | Wait | dynamic | functional (Accuracy tab here has no error count unlike Script) |
| B170 | `No Scenes Yet` / `Built After the Scene Plans Are Approved` | Production.tsx:103 | NotYet | no scenes | Explain | -- | Approve plans | dynamic + frontend hardcoded | contradicts B167: scenes (and thus the Plans UI) exist when scenes is non-empty, so this message can show only before plans exist |
| B171 | `Approve All Scenes` | Production.tsx:106 | Tab label | Scenes stage | Aggregate approval | -- | Click | frontend hardcoded | functional |
| B172 | Facts `Scenes`, `Ready`, `Still Building`, `Failed` | Production.tsx:110-113 | dt | approval tab | Counts | -- | Read | frontend hardcoded | inconsistent (`Failed` vs statuses; `Ready` vs "Waiting for You") |
| B173 | `Scenes` (tabs label), `sceneName` tab labels | Production.tsx:120,124 | Tabs | Always | Navigate | -- | Click | dynamic | functional |
| B174 | `Preview of ${scene.title}` | Production.tsx:127 | VideoPreview label | each scene | Label | -- | Play | dynamic | inconsistent (title not title-cased) |
| B175 | `No Preview Yet` / `Appears Once the Scene's Code Is Built` | Production.tsx:127 | VideoPreview empty/hint | no preview | Empty | -- | Wait | frontend hardcoded | functional |
| B176 | `Clips Built` / `${built} of ${total}` | Production.tsx:130 | ProgressBar | each scene | Progress | -- | Read | frontend hardcoded + dynamic | functional |
| B177 | Headers `Clip`, `What It Shows`, `Status` | Production.tsx:133 | th | scene tab | Headers | -- | Read | frontend hardcoded | functional |
| B178 | `{scene.sync_problems}` | Production.tsx:137 | List, no heading | present | Show sync problems | -- | Read | backend API (sync_problems) | ambiguous (raw list with no title or severity) |
| B179 | `Final Video` (tabs label); tabs `Video`, `Media Checks`, `Checkpoint` | Production.tsx:154-155,161,171 | Tabs | Always | Navigate | -- | Click | frontend hardcoded | functional |
| B180 | Said complete: "This was a triumph." / "We're made of star-stuff..." / "Even the smallest person can change the course of the future." | Production.tsx:157 | Note quote | final video exists | Celebrate | -- | -- | frontend config (voice.complete) | functional |
| B181 | `Final Video: ${runTitle(topic)}` | Production.tsx:158 | VideoPreview label | Always | Label | -- | Play | dynamic | inconsistent (RunPage uses summary.name first) |
| B182 | `No Final Video Yet` / `Rendered at 2560 × 1440 Once Every Scene Is Approved` | Production.tsx:158 | VideoPreview empty/hint | no video | Empty | -- | Wait | frontend hardcoded | functional (hardcoded resolution) |
| B183 | `No Media Checks Yet` | Production.tsx:161 | NotYet | no final video | Empty | -- | Wait | dynamic | functional |
| B184 | Headers `Severity`, `Check`; badge `Error`/`Warning` | Production.tsx:164,166 | th, badge | checks | Report | -- | Read | frontend hardcoded | functional |
| B185 | `${code lowercased with spaces}: ${message}` | Production.tsx:166 | Cell | each check | Check text | -- | Read | backend API (code, message) | inconsistent (lowercase code prefix breaks house style) |
| B186 | `Every Check Passed` / `No Media Checks Recorded` | Production.tsx:170 | SystemMessage success/pending | no check rows | Empty | -- | -- | frontend hardcoded | functional |

### stages/Reshuffle.tsx

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| B187 | `Choose a Template First` / `A Reshuffle Starts From the Run's Approved Template` / `Open Template` | Reshuffle.tsx:45-47 | SystemMessage pending + button | template not approved | Gate | -- | Approve template | frontend hardcoded | misleading (title says choose, body says approve) |
| B188 | `Reshuffle the Look` / `Colors, Fonts and Backgrounds Change; Layouts Never Do` | Reshuffle.tsx:76-77 | Section | Always | Heading | -- | Read | frontend hardcoded | functional |
| B189 | `What to Reshuffle` | Reshuffle.tsx:81 | legend | Always | Group label | -- | -- | frontend hardcoded | functional |
| B190 | `Colors & Palettes` / `Primary, Secondary and Accent Palettes`; `Fonts` / `Text and Math Fonts`; `Background` / `Type and Color`; `Grid` / `Type, Color and Opacity`; `Border` / `Style and Color` | Reshuffle.tsx:25-29 | Checkbox label/hint | Always | Options | -- | Tick | frontend hardcoded | functional (no message if none ticked) |
| B191 | `Seed` / `The Same Seed Always Gives the Same Look` | Reshuffle.tsx:87 | Field label/hint | Always | Seed | -- | Type | frontend hardcoded | functional (invalid seeds: no message) |
| B192 | `New Seed` | Reshuffle.tsx:89 | Button | Always | Random seed | -- | Click | frontend hardcoded | functional |
| B193 | `Preview` | Reshuffle.tsx:92 | Button | disabled if invalid/busy | Preview | -- | Click | frontend hardcoded | functional (disabled with no reason) |
| B194 | `Apply Reshuffle` | Reshuffle.tsx:93,118 | Buttons (form and modal confirm) | disabled w/o changes | Apply | -- | Click | frontend hardcoded | functional (disabled w/o reason) |
| B195 | `Reshuffling, Then Rendering One Frame…` | Reshuffle.tsx:61 | Working notice | Preview | Progress | -- | Wait | frontend hardcoded | functional |
| B196 | `Nothing Changes With This Seed: Try Another` | Reshuffle.tsx:64 | Done notice | zero changes | Result | -- | Click New Seed | frontend hardcoded | functional |
| B197 | `${n} Elements Change` | Reshuffle.tsx:66 | Done notice | changes | Result | -- | Read | dynamic | grammar: "1 Elements Change" |
| B198 | `Recoloring Every Built Clip…` | Reshuffle.tsx:68 | Working notice | Apply | Progress | -- | Wait | frontend hardcoded | misleading placement: Notice is behind the confirm modal |
| B199 | `Reshuffle Applied (Seed ${seed}): Send Any Message in the Console and Claude Renders the Previews and Final Video Again` | Reshuffle.tsx:72 | refresh() notice | Apply succeeds | Result | -- | Open Console, send | dynamic | misleading vs B202 ("Then Renders ... Again" implies automatic); requires manual step |
| B200 | `Reshuffled Look (Seed ${seed})` / `One Frame at 2560 × 1440, as Every Clip Would Get It` | Reshuffle.tsx:98 | Image alt / caption | still | Preview | -- | Look | dynamic | functional |
| B201 | `No Preview Yet` | Reshuffle.tsx:99 | SystemMessage empty | no still | Empty | -- | Click Preview | frontend hardcoded | functional |
| B202 | `Apply This Reshuffle?` / `Recolors Every Built Clip, Then Renders the Previews and Final Video Again. The Current Final Video Is Kept; Every Scene Needs Approval Again.` | Reshuffle.tsx:114-115 | Modal | confirming | Confirm | -- | Apply/Cancel | frontend hardcoded | misleading (see B199); `Cancel` button also here |
| B203 | `What changes (scrolls sideways on small screens)` | Reshuffle.tsx:101 | aria-label | changes table | SR name | -- | -- | frontend hardcoded | functional |
| B204 | Headers `Element`, `Now`, `After`; cells titleCase(element/before/after) | Reshuffle.tsx:103-106 | Table | changes | Diff | -- | Read | frontend hardcoded + backend API (changes) | functional |
| B205 | `Cancel` | Reshuffle.tsx:117 | Button | Modal | Close | -- | Click | frontend hardcoded | functional |
| B206 | Error text | Reshuffle.tsx:95 | Notice | failed preview/apply | Failure | -- | Retry | backend API / errorText | misleading placement: failed Apply leaves the modal open and the error is hidden behind it |

### stages/look/LookSound.tsx

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| B207 | `Could Not Load the Template` + message | LookSound.tsx:31 | SystemMessage unavailable | any load error | Failure | -- | Reload | frontend hardcoded + backend API | functional (no retry button) |
| B208 | `Loading Options` | LookSound.tsx:33 | SystemMessage loading | Loading | Wait | -- | Wait | frontend hardcoded | functional |
| B209 | `Synthesizing a Few Seconds…` | LookSound.tsx:45 | Working notice | Hear voice | Progress | -- | Wait | frontend hardcoded | functional |
| B210 | `Voice Sample Ready` | LookSound.tsx:47 | Done notice | Sample generated | Result | -- | Play | frontend hardcoded | functional |
| B211 | `Hear the Voice` | LookSound.tsx:51 | Button | Sound tab | Synthesize | -- | Click | frontend hardcoded | functional |
| B212 | `Voice Sample` | LookSound.tsx:59 | AudioPreview label | audio | Label | -- | Play | frontend hardcoded | functional |
| B213 | `Saving…` | LookSound.tsx:53 | Working notice | Save | Progress | -- | Wait | frontend hardcoded | functional |
| B214 | `Saved` | LookSound.tsx:56 | Done notice | Save | Result | -- | -- | frontend hardcoded | redundant (immediately replaced/duplicated by page notice B215 visible at once) |
| B215 | `Template Saved: Approve It in the Checkpoint Tab, Then the Requirements Come Next` | LookSound.tsx:55 | refresh() notice | Save | Result | -- | Go to Checkpoint | frontend hardcoded | functional (persistent on page after navigation) |
| B216 | `Starter: ${titleCase(choice.template)}` | LookSound.tsx:64 | Badge | Always | Base template | -- | -- | dynamic | functional |
| B217 | `Save Template` | LookSound.tsx:65 | Button | Always | Save | -- | Click | frontend hardcoded | functional (no unsaved-changes indicator) |
| B218 | `Template` | LookSound.tsx:62 | Tabs label | Always | Name | -- | -- | frontend hardcoded | functional |
| B219 | `Checkpoint` | LookSound.tsx:67 | Tab | Always | Navigate | -- | Click | frontend hardcoded | functional |
| B220 | `Showing Defaults: The Video Uses These Until You Save` | LookSound.tsx:69 | Note | !saved | Warn | -- | Save | frontend hardcoded | functional (disappears once saved, but edits after saving are not flagged) |
| B221 | `{editor.note}` = `Could Not Render the ${titleCase(element)} Options in Your Look` | LookSound.tsx:71 via useTemplateEditor.tsx:62 | Note role=status | option preview request fails | Failure | -- | Retry (reopen element) | dynamic | stale: never cleared |

### stages/look/useTemplateEditor.tsx

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| B222 | `Starter Templates` (tab and section title) | useTemplateEditor.tsx:87,90 | Tab, Section | Always | Gallery | -- | -- | frontend hardcoded | redundant (tab == title) |
| B223 | Said chooseLook: "See how beautifully these are coloured" | useTemplateEditor.tsx:90 | Section description | Always | Voice | -- | Pick | frontend config (voice.chooseLook) | inconsistent ("coloured" vs US "Color" in UI; it is a verbatim quote) |
| B224 | `Dark or Light Templates` | useTemplateEditor.tsx:91 | aria-label of switch | Always | Name | -- | -- | frontend hardcoded | functional |
| B225 | `Dark`, `Light` | useTemplateEditor.tsx:96-97 | Toggle options | Always | Mode | -- | Click | frontend hardcoded | functional |
| B226 | `${titleCase(view)} Starter Templates` | useTemplateEditor.tsx:100 | RadioCards label | Always | Name | -- | -- | dynamic | functional |
| B227 | starter `titleCase(template.name)`, srLabel/alt `${name}: ${description}` | useTemplateEditor.tsx:102-103 | Card label, SR, alt | Each starter | Show | -- | Pick | backend API (templates[].name, description) | functional |
| B228 | `Want to Make It Your Own?` | useTemplateEditor.tsx:106 | Span | Always | Prompt | -- | -- | frontend hardcoded | functional |
| B229 | `Build Your Own` | useTemplateEditor.tsx:107,141 | Button, Drawer title | Always | Open custom pane | -- | Click | frontend hardcoded | functional |
| B230 | `Audio & Subtitles` (tab and section) | useTemplateEditor.tsx:114-115 | Tab, Section | Always | Sound options | -- | -- | frontend hardcoded | redundant (tab == title) |
| B231 | `Subtitles` / `Previewed Now; Burned Into the Video in a Later Version` | useTemplateEditor.tsx:116 | Toggle label/hint | Always | Subtitle option | -- | Toggle | frontend hardcoded | potentially outdated/ambiguous ("later version" is not actionable; check whether subtitles are burned in yet) |
| B232 | `Whole Look` (tab and section) | useTemplateEditor.tsx:121-122 | Tab, Section | Always | Full frame preview | -- | -- | frontend hardcoded | redundant |
| B233 | `One Frame at 2560 × 1440, as Every Clip Will Look` | useTemplateEditor.tsx:122 | Description | Always | Explain | -- | Read | frontend hardcoded | inconsistent (Reshuffle says "Would Get It") |
| B234 | `Render the Whole Look` | useTemplateEditor.tsx:123 | Button | Always | Render still | -- | Click | frontend hardcoded | functional |
| B235 | `Rendering the Whole Look…` | useTemplateEditor.tsx:73 | Working notice | Render | Progress | -- | Wait | frontend hardcoded | functional |
| B236 | `Whole Look Ready` or `${answer.note}` | useTemplateEditor.tsx:76 | Done notice | Render done | Result | -- | Look | frontend hardcoded / backend API (note) | functional |
| B237 | `Whole Look` (alt) / `Backdrop, Grid, Border, Colors, Font and Sizes at Delivery Size` | useTemplateEditor.tsx:124 | Image alt, caption | still | Preview | -- | -- | frontend hardcoded | ambiguous (alt only repeats the heading, does not describe the image) |
| B238 | `Nothing Rendered Yet` | useTemplateEditor.tsx:125 | SystemMessage empty | no still | Empty | -- | Click Render | frontend hardcoded | functional |
| B239 | `Starting From ${titleCase(template)}, ${titleCase(mode)}` | useTemplateEditor.tsx:142 | Drawer description | Build pane | Context | -- | -- | dynamic | functional |
| B240 | `Done` | useTemplateEditor.tsx:143 | Button | Build pane | Close | -- | Click | frontend hardcoded | functional |

### stages/look/LookTree.tsx

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| B241 | Group names `Mode`, `Background`, `Grid`, `Color`, `Type`, `Border`, `Narration`, `Subtitles` (else titleCase(group)) | LookTree.tsx:11-12,44 | Summary | Each group | Headings | -- | Expand | frontend hardcoded | functional (`Subtitles` group appears unused since subtitles element is filtered out at useTemplateEditor.tsx:79) |
| B242 | `${titleCase(element.label)}` | LookTree.tsx:63 | Summary | Each element | Name | -- | Expand | backend API (look catalogue label) | functional |
| B243 | `{custom \|\| titleCase(chosen?.label ?? "")}` | LookTree.tsx:64 | Value | Each element | Current choice | -- | Read | backend API / user value | functional (raw custom value) |
| B244 | `Changed` / `Custom` (badge) | LookTree.tsx:65 | Badge | not default | State | -- | Read | frontend hardcoded via titleCase(mark) | functional |
| B245 | `{element.description}` | LookTree.tsx:69 | Note | open | Help | -- | Read | backend API (element.description) | functional |
| B246 | RadioCards label `{element.label}` | LookTree.tsx:71 | SR group label | open | Name | -- | -- | backend API | inconsistent (not title-cased, unlike every other use) |
| B247 | option labels titleCase(option.label), hint option.detail | LookTree.tsx:77 | Radio options | open | Choices | -- | Pick | backend API (options[].label, detail) | functional |
| B248 | `Default` | LookTree.tsx:78 | Badge | default option | Mark | -- | -- | frontend hardcoded | functional |
| B249 | `Custom` / `Your own ${element.custom}` / `Your Value` | LookTree.tsx:82-83 | Option label/hint/alt label | element.custom | Custom option | e.g. "Your own color or gradient" | Click | frontend hardcoded + backend API (element.custom) | inconsistent (hint sentence case, not Title Case; `Your Value` only in alt) |
| B250 | `Preview Unavailable` | LookTree.tsx:53 | Placeholder | render failed | Failure | -- | Retry | frontend hardcoded | functional (no retry action) |
| B251 | `Rendering in Your Look…` | LookTree.tsx:54 | Placeholder (loading) | loading | Wait | -- | Wait | frontend hardcoded | functional |
| B252 | `Unreadable Text in This Look` | LookTree.tsx:56 | Placeholder | option returned without url | Warn | Text contrast fails | Pick another | frontend hardcoded | ambiguous |
| B253 | `Choose a Value to See It` | LookTree.tsx:56,83 | Placeholder | no picture | Hint | -- | Click Custom | frontend hardcoded | ambiguous (also used when an option simply has no picture) |
| B254 | `${titleCase(label)}: ${option} (${titleCase(mode)} Mode)` | LookTree.tsx:57 | Image alt | ready | Alt | -- | -- | dynamic | functional |

### stages/look/CustomEditor.tsx

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| B255 | `Your Own ${titleCase(element.label)}` | CustomEditor.tsx:45 | Modal title | editing | Title | -- | -- | dynamic | functional |
| B256 | `{element.description}` | CustomEditor.tsx:45 | Modal description | editing | Help | -- | Read | backend API | functional |
| B257 | `Color or Gradient`, `Solid`, `Gradient` | CustomEditor.tsx:28,35-36 | Tabs | color or gradient element | Switch | -- | Pick | frontend hardcoded | functional |
| B258 | `${titleCase(element.label)}` (ColorPicker/Field label), `{element.custom ?? ""}` hint | CustomEditor.tsx:24,40 | Labels, hint | editing | Input | hint is lowercase backend text | Type | dynamic / backend API (element.custom) | inconsistent (lowercase hint, no validation message for bad font/rate; speaking speed bounds 0.8 to 1.2 shown only as input attributes) |
| B259 | `Cancel`, `Apply` | CustomEditor.tsx:47-48 | Buttons | editing | Close/accept | -- | Click | frontend hardcoded | functional (`Apply` disabled when empty with no reason) |

### Findings (B)

Ranked by user impact. Row references are above.

1. **Notice messages that nobody sees, or that are stale.** Rows B27, B71, B75, B198, B206, B108. (a) `ChangeModal.tsx:55` closes the modal before the follow-up `load(console)` and `streamTurn`; a failure of `load` is written to a Notice inside the closed modal and the user is told nothing, even though the request has already been recorded. (b) `Reshuffle.tsx:61-72,95`: the `Recoloring Every Built Clip…` working text and any error from Apply render in the card behind the confirm modal, which stays open on failure with no error shown inside it. (c) `Console.tsx:51` hands `Claude Finished` to the page-level Notice (`RunPage.tsx:122`) which is behind the console Drawer. When a turn ends nothing visible changes in the console. (d) Page-level notices (`Template Saved…`, `Claude Finished`, `X Approved: Next…`) are never cleared (`RunPage.tsx:55,62-65`), so they persist across stage navigation and long after they stop being true. Recommendation: render the error inside the modal, keep the modal open on failure, clear the notice on stage change or after a timeout, and show a completion line inside the console.
2. **"Claude Finished" is not tied to a real completion.** B83, B108. `ClaudePanel.tsx:49-51`, `Console.tsx:50-51`. `streamTurn` (`services/http.ts:57-86`) resolves on any clean end of the body, including a connection closed early or a stream containing only an `error` entry, so the text shows after partial or failed turns. Aborts (page left) correctly skip it. Recommendation: have the server send an explicit terminal event, and show `Claude Stopped` or the entry's error when the last entry is role `error`.
3. **"Claude Is Applying It" can be false.** B73. `ChangeModal.tsx:63-64` fires `streamTurn(...).catch(() => undefined)` and announces success before the turn has started; a 409 (turn already running, race with the earlier busy check), network failure or auth failure are silently dropped. B72's claim that a running turn picks the request up is an assumption of the frontend (comment M20), not verified in this scope. Recommendation: await the first response, or on catch call `refresh` with a failure text such as `Request Recorded, but Claude Could Not Start: Send Any Message in the Console`.
4. **Reshuffle apply wording contradicts what happens.** B199, B202, B198. The modal says Claude `Renders the Previews and Final Video Again`; the post-apply notice says the user must `Send Any Message in the Console`. Pick one statement; ideally the confirm modal states the manual step too. Also B187 title `Choose a Template First` while the body demands approval.
5. **Disabled controls give no reason.** B70 (Send Request needs 3+ chars), B193/B194 (Preview/Apply disabled with invalid seed, no groups, no changes), B259 (Apply), B56 (Approve disabled, only this one has a described-by hint), B15 (button absent on Template/Requirements/Reshuffle). Recommendation: inline validation hints, e.g. `Pick at Least One Group`, `Seed Must Be a Whole Number up to 999999999`, `Describe the Change in at Least 3 Characters`.
6. **Misleading success text on approve.** B60, B56. `final` approval announces `Next, Reshuffle` (an optional stage, which also `navigate`s there at `CheckpointPanel.tsx:62-64`); scene-level checkpoints say `Approve & Continue` and give no `Next`. Recommendation: for the optional step say `Optional Next Step: Reshuffle`; for scene start checkpoints use `Approve` / `Start This Scene`.
7. **No feedback on silent failures and loading.** B77 (ClaudePanel returns null while loading), B157/B162/B160 (plan card and scene code vanish on a failed fetch; "No Execution Plan" also shown on fetch failure), B76/B94/B207 (error messages with no retry button; Notice on RunPage has `Try Again` only for the stale banner), B250 (no retry on preview failure), B221 (error never cleared). Recommendation: reuse the `Try Again` pattern and show a failure state distinct from "missing".
8. **Run problem classification is fragile and misleading.** B20, B21, B22. `RunPage.tsx:132` decides the title by `run.problem.startsWith("This run cannot be read")`; any other problem is called `Made by an Older Version`. Recommendation: a structured `problem_kind` from the backend, with a neutral fallback title.
9. **Terminology inconsistency.** B33/B114/B145 (`Open Requests` / `Change Requests` / `Changes` / `Request a Change`); B104 vs B81 (`Start` vs `Start Production`); B107 duplicate of B82; B137 (`Explain` for topic); B147 (`Picture` vs `Visuals`); B24/B182 (`No Final Video` vs `No Final Video Yet`); B153/B154/B169 (`Accuracy` vs `Accuracy Review`); B4 (`All Runs` vs `Ongoing`/`Previous Runs`); B31/B140 (`Min` vs `min`); B84 vs B78 (identical title for different states); B222/B230/B232 tab names duplicated as section titles; B144/B149 tab named same as stage.
10. **Scene/clip naming and raw ids.** B37 vs B65: Overview and Production use `Scene 3`, the ChangeModal target list shows `Scene s03: ...` and `Clip c0301: ...`; B116 shows raw `r01 · wording on outline · open` (lowercase, ids, no use of the KINDS labels); B185 `code lowercased`; B45 raw ISO-like timestamps; B34 raw `created`. Recommendation: one formatter (`sceneName`, kind labels) reused everywhere; format dates with the locale.
11. **Change requests for plan, scenes, final, scene and clip targets are not visible.** B65, B114. `<Changes>` is only mounted in Outline and Script (`Writing.tsx:27,65`), yet the modal can target All Scene Plans, All Scenes, a scene, a clip and the Final Video (`ChangeModal.tsx:28-33`). Only the count appears (Overview `Open Requests`). Users cannot see the status of such requests. Add a Changes tab to those stages.
12. **Accessibility gaps.** B9 (aside labelled just `Run`), B100 (console/ClaudePanel speakers identified only by CSS class: no visible or SR label for you/claude/tool/error), B93 (whole ClaudePanel is `aria-live` plus a nested Notice, so streaming content is announced repeatedly), B124 (identical `Table (scrolls sideways...)` name for every table), B237 (`alt="Whole Look"` does not describe the image), B40/B41 (hover-only chart tooltips; the row aria-label covers SR but not keyboard sighted users), B134 (bare count badges on tabs), B50 (`Open Problems` is a styled `<p>`, not a heading), B18 (approval bar `role=status` re-announces whenever the tab changes), B106/B103 (textarea turns read-only with the reason only in a separate note; placeholder is the whole kickoff prompt).
13. **Grammar and Title Case.** B197 `1 Elements Change`; B150 `1 words`; B18 `Scenes Is Waiting for Your Decision` / `Scene Plans Is Waiting...`; B38/B41 lowercase `no clips planned`; B96 `claude code` lowercase; B249/B258 lowercase hints from backend (`Your own color or gradient`); B58 no terminal punctuation (fine under house style) but `Tick ... to Approve Anyway, or Request a Change` is a run-on; B246 un-title-cased aria label; B223 `coloured` (quote, UK spelling).
14. **Ambiguous or possibly outdated.** B155 (`Critiqued When You Request a Change at Its Checkpoint`), B231 (`Burned Into the Video in a Later Version`; the `Subtitles` group in B241 is filtered out so is probably unused), B252/B253 (`Unreadable Text in This Look`, `Choose a Value to See It` reused for different situations), B167 vs B170 (the two NotYet explanations cannot both be true given that `Plans` renders as soon as scenes exist), B88 (`No Reply`), B123 (`Keeps:`), B132 (default NotYet wording used for files written by different agents).
15. **Duplicate texts.** `Claude Is Working: Renders and Voice Can Take Minutes` (B82, B107), `Claude Finished` (B83, B108), `Request a Change` (B15, B57, B62, B115), `Table (scrolls sideways on small screens)` (B124 x3), `No Preview Yet` (B175, B201 in two stages with different hints), `Saved` plus `Template Saved: ...` (B214, B215) shown together. Extract shared constants for the turn notices (one source of wording) and drop B214.
16. **Unused/unreachable.** `GROUP_NAMES.subtitles` (B241) is likely unreachable since the `subtitles` element is excluded; `lastTurn` is exported only for ClaudePanel (no external use, grep verified); `Choices:` in the Console (B101) is display-only.


# Part 3 — Backend text that reaches people: API, run views, checkpoint problems, console, Look catalogue, CLI, session-relayed, hooks (rows C1–C300)
Scope: backend/app/web, run_views/approvals/validation/critiques/production/checkpoints/status, driver/change_requests, hook_command, cli and commands, look and sound catalogue. Audit only; nothing in the repo was changed. File:line are in the source files as of this audit. 'Site' = shown on the website (verified in frontend/src: CheckpointPanel.tsx:73, review.tsx:31, Home.tsx:106-109, Production.tsx:137/165, LookTree.tsx:69, CustomEditor.tsx:45, RunList.tsx:88, RunPage.tsx:132).

### 1. API errors (backend/app/web)
Every ApiProblem becomes `{error, problems}` JSON; the frontend shows `error` through SystemMessage/Notice (`error.message`).

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| C1 | changes come only from this page | app/web/app.py:166 | HTTP 403 error | Write request whose Origin header differs from Host | Same-origin protection | Request refused as cross-site | Reload the page; rarely user-visible | backend API | functional |
| C2 | send JSON | app/web/app.py:170 | HTTP 415 error | Write with a body that is not application/json | Protocol guard | Wrong content type | None possible for a person (a bug if seen) | backend API | inconsistent: developer-facing text; lower-case fragment unlike other messages |
| C3 | <field>: <pydantic message> (e.g. requirement: Field required; objectives.0: String should have at least 1 character) | app/web/app.py:185-186 | HTTP 400 error (dynamic) | Request body fails FastAPI validation | Report invalid input | Raw pydantic field path and message joined with '; ' | Correct the field | dynamic | misleading: raw library wording and dotted field paths, field names are API names not form labels |
| C4 | <field>: <pydantic message> (contract validation) | app/web/app.py:190-192 | HTTP 400 error (dynamic) | A pydantic ValidationError escapes a handler (e.g. Brief.model_validate in start_run) | Report invalid input | Same raw format via format_validation_errors | Correct the field | dynamic | misleading: raw pydantic text |
| C5 | <ExceptionType>: <message> (e.g. KeyError: 'x') | app/web/app.py:197 | HTTP 500 error (dynamic) | Any unhandled exception | Name the cause instead of a bare 500 | Raw Python class and message | Retry; report if repeated | dynamic | misleading: Python exception text reaches the user |
| C6 | sign in first | app/web/app.py:203 | HTTP 401 error | No or expired session cookie on any protected route | Require sign-in | Not signed in (also the case after server restart or 24 h expiry) | Sign in again | backend API | inconsistent: lower-case fragment; does not say why the session ended |
| C7 | no run {run} | app/web/app.py:209 | HTTP 404 error (dynamic) | Run folder id invalid or missing (also used for traversal) | Unknown run | The run does not exist (folder id shown, not the run's name) | Go back to the run list | dynamic | inconsistent: exposes folder id (e.g. 20261124-101500-topic), not the display name |
| C8 | Open the sign-in link `text-2-shorts serve` printed in its terminal. | app/web/app.py:252 | HTTP 403 error | POST /api/session with wrong or missing X-Faraday-Token | Stop other local programs from signing in (H6) | Token missing | Open the full link from the terminal where serve runs | backend API | inconsistent: only sentence-case message with period + backticks; uses CLI jargon, product name 'text-2-shorts' |
| C9 | Claude Code on this machine is not signed in. Run `claude auth login` in a terminal, sign in on claude.ai, then continue here. | app/web/app.py:257-258 | HTTP 401 error | Sign-in while `claude auth status` reports no account (or claude missing/timeout) | Explain sign-in prerequisite | Claude Code has no account | Run the command, sign in, retry | backend API | misleading: same text when claude is not installed or the status call timed out (auth.py:27) |
| C10 | the run could not be set up, so it was not kept: {error} | app/web/app.py:134 | HTTP 500 error (dynamic) | Any exception or SystemExit while finishing a new/duplicated run | Explain no half-made run remains | Setup failed; run folder removed; raw cause appended | Retry; read the cause | dynamic | misleading: appends raw exception/SystemExit text; 'kept' is internal |
| C11 | no starter template {name} | app/web/app.py:314, 572, 590, 611 | HTTP 404 error (dynamic) | Start a Run / still / starter picture / option pictures with an unknown template name | Unknown starter | The template name does not exist | Pick another template | dynamic | redundant: four copies of one text; uses 'starter template' while the site says 'template' |
| C12 | this look and sound cannot be used yet | app/web/app.py:316, 493, 500, 574 | HTTP 409 error + problems list | Chosen look fails video_settings.problems / template_problems | Block an unusable look | Look has problems (listed below it) | Fix the listed problems | backend API | redundant: four copies; the list under it is raw (see the checkpoint-problem section) |
| C13 | {RunNotCreated text} (Preflight failed: claude CLI not found, latex missing, ...; AWS credentials not found for Polly ...; Google credentials not found ...) | app/web/app.py:320, 345 | HTTP 409 error (dynamic) | create_run refuses: preflight problems or missing voice credentials | Explain why a run cannot start | See run_workspace.py texts in the CLI section | Install the tool or sign in to the voice provider | dynamic | functional |
| C14 | this run has no readable brief to copy | app/web/app.py:341 | HTTP 409 error | Duplicate a run whose brief.json is missing or invalid | Block duplicate | Source run unreadable | None in the UI; fix the source run | backend API | inconsistent: 'brief' is internal; the site says Requirements |
| C15 | Claude is working on this run: wait for the turn to end | app/web/app.py:362 | HTTP 409 error | Delete a run while a console turn holds the lock | Protect a running turn | A Claude Code turn is running | Wait, then delete again | backend API | inconsistent: 'turn' is jargon; differs from the 409 on POST console ('Claude is still working on the previous message') |
| C16 | no draft {draft} | app/web/app.py:396 | HTTP 404 error (dynamic) | Draft id is not a UUID | Unknown draft | Draft does not exist | None | dynamic | potentially unused: the UI always sends valid ids; shows internal id |
| C17 | Claude is still working on the previous message | app/web/app.py:427 | HTTP 409 error | Console message sent while a turn is running | Serialise turns | Previous message still running | Wait for Claude to finish | backend API | functional |
| C18 | {ApprovalBlocked text}: cannot approve {target} yet: {problem}; {problem}... | app/web/app.py:449; app/workflow/approvals.py:98 | HTTP 409 error (dynamic) | Approve while problems exist, or fingerprint changed | Refuse approval with reasons | Checkpoint has open problems; target is the ledger key (plan, scenes, scene:s01, start:s02) | Fix problems or accept with force | dynamic | misleading: ledger keys and the joined problem string are shown; problems also shown separately (duplicated) |
| C19 | {SystemExit text from a workflow gate} | app/web/app.py:451 | HTTP 409 error (dynamic) | A workflow function stops with sys.exit while approving (checkpoints.py:34 'require_approval') | Convert CLI exit into API error | See section 3 texts | As given | dynamic | misleading: CLI-worded text (e.g. 'get the outline checkpoint first') shown on the website |
| C20 | no change request {id} | app/web/app.py:472; app/workflow/change_requests.py:65 | HTTP 404 error (dynamic) | Resolve with an unknown request id (e.g. r007) | Unknown request | Request does not exist | None | dynamic | functional: internal id r007 shown |
| C21 | no template {name}: choose one of obsidian, paper, ... | app/web/app.py:488; app/workflow/templates.py:207 | HTTP 404 error (dynamic) | chosen_template ValueError | Unknown template | List of valid names | Pick one | dynamic | redundant: same fact as 'no starter template {name}' with a different wording and status path |
| C22 | choose the look and sound first: there is nothing to reshuffle | app/web/app.py:537 | HTTP 409 error | Reshuffle before template.json exists | Block reshuffle | No saved look | Save a look first | backend API | functional |
| C23 | this reshuffle cannot be used | app/web/app.py:540 | HTTP 409 error + problems | Applied reshuffle fails template checks | Block bad reshuffle | Result would be invalid | Try another seed/groups | backend API | functional |
| C24 | the voice could not be synthesised: {failed} | app/web/app.py:512 | HTTP 502 error (dynamic) | Voice sample fails (credentials, network, unknown voice id) | Explain voice sample failure | Provider error text appended raw | Check credentials/network | dynamic | misleading: raw provider exception (boto/google) text; British spelling 'synthesised' |
| C25 | the still could not be rendered: {failed} | app/web/app.py:526, 582 | HTTP 502 error (dynamic) | Look still render failed (RuntimeError last 1500 chars of stderr, OSError, timeout) | Explain render failure | Raw Manim/subprocess output appended | Retry; report | dynamic | misleading: up to 1500 chars of traceback/stderr |
| C26 | the starter could not be rendered: {failed} | app/web/app.py:596 | HTTP 502 error (dynamic) | Starter preview render failed | Explain render failure | As above | Retry | dynamic | redundant: fourth variant of 'could not be rendered' |
| C27 | the previews could not be rendered: {failed} | app/web/app.py:638 | HTTP 502 error (dynamic) | Batch option previews failed | As above | As above | Retry | dynamic | redundant |
| C28 | the preview could not be rendered: {failed} | app/web/app.py:653 | HTTP 502 error (dynamic) | Full-size option preview failed | As above | As above | Retry | dynamic | redundant |
| C29 | {element} has no picture | app/web/app.py:605 | HTTP 404 error (dynamic) | Option pictures asked for an element not in PREVIEWED (e.g. voice, subtitles, theme_mode) | Unknown element | Element id shown (e.g. theme_mode) | None | dynamic | potentially unused: the UI only asks for previewed elements; shows internal element id |
| C30 | no such preview | app/web/app.py:647, 655 | HTTP 404 error | Preview file name malformed or file absent | Missing preview | Image not found | Reload | backend API | functional |
| C31 | no such file in this run | app/web/app.py:663 | HTTP 404 error | /media path outside run or missing | Missing media | File absent | Reload (video not made yet) | backend API | functional |
| C32 | no such file | app/web/app.py:682 | HTTP 404 error | Frontend asset missing or bad name | Missing asset | Stale cached page | Hard-reload | backend API | redundant: near-duplicate of 'no such file in this run' |
| C33 | The website is not built yet: run `npm ci && npm run build` in frontend/, then reload. | app/web/app.py:672 | HTTP 503 plain text | GET / with no frontend/dist/index.html | Tell the developer to build | Frontend not built | Run the build | backend API | functional: developer-facing, only seen on a fresh clone |
| C34 | Here is how your narrator will sound. Square the short sides, add them, and you get the long side squared. | app/web/app.py:106-108 | Constant (voice sample sentence) | Defined but never referenced in app.py; the real sample text is duplicated in templates/generate_preview.py:221 | Voice sample sentence | Pythagorean joke the user hears | Listen | backend config data | potentially unused: grep VOICE_SAMPLE finds only its definition; duplicate of generate_preview.py:221-222 |
| C35 | Text-2-Shorts (FastAPI title) | app/web/app.py:140 | App title | Not exposed (docs/openapi disabled) | Internal title | Product name | None | backend config data | potentially unused: never shown; product is called Faraday on the site |

#### Sign-in, session and usage (web/auth.py, web/usage.py)

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| C36 | (no user text) email, organization, plan, method from `claude auth status --json` | app/web/auth.py:31-36 | Account fields | Sign in | Show whose account is used | Values copied from Claude Code | None | dynamic | functional |
| C37 | {window.id} e.g. five_hour, seven_day; used_percent; resets_at; status 'allowed' | app/web/usage.py:313-320 | Usage window fields (dynamic) | GET/POST /api/usage | Show Claude usage limits on Home | Raw Claude Code window ids/status strings pass through | Check whether the frontend maps them | dynamic | misleading: raw window ids and status strings are not user wording unless mapped (frontend not in my scope) |

### 2. Run views (backend/app/workflow/run_views.py)

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| C38 | completed / failed / configuring / awaiting_approval / in_progress | app/workflow/run_views.py:50-56 | Run status code | Computed per run summary | Run list status | Machine status words (snake_case) | Read via the site's own labels | backend config data | functional (frontend maps them) |
| C39 | made by an older version | app/workflow/run_views.py:62 | Run stage text | Brief missing or invalid | Mark an unreadable run | Run lacks a valid brief | None | backend API | misleading: the same flag is shown as 'Older Version: Final Video Only' even when the cause is a damaged brief.json (RunList.tsx:88) |
| C40 | cannot be read: {ExceptionType}: {message[:200]} | app/workflow/run_views.py:73 | Run stage text (dynamic) | next_actions/compute_statuses raise ValidationError/ValueError/KeyError | Mark a run that failed to load | Raw Python error text | Fix or remove the file | dynamic | misleading: RunList shows 'Older Version: Final Video Only' for these runs because readable=false; the stage text only reaches RunPage |
| C41 | This run cannot be read: {type}: {msg}. Fix or remove that file and the page comes back. | app/workflow/run_views.py:148-150 (prefix 'This run' + stage) | Run page message (dynamic) | Detail of a run whose summary stage starts with 'cannot be read' | Explain unreadable run | Run files damaged; 'that file' is not named | Open the run folder | dynamic | ambiguous: 'that file' is undefined (the exception text may or may not name it); string-prefix coupling to the stage text |
| C42 | Made by an older version of Faraday: only its final video can be shown. | app/workflow/run_views.py:150 | Run page message | Run has no brief | Explain old run format | Older workflow format | Use the final video only | backend API | functional |
| C43 | Requirements / Template / Outline / Script / Scene Plans / Final Video | app/workflow/run_views.py:105-112 | Checkpoint labels | awaiting checkpoints | Names for decisions | Stage names | Decide on the stage | backend config data | inconsistent: 'Template' here, 'Look & sound' in the stage tree and in API errors; 'Scene Plans' vs 'plan' in CLI/problem texts |
| C44 | Start Scene {N} | app/workflow/run_views.py:117 | Checkpoint label (dynamic) | Target 'start:sNN' when confirm_each_scene is set | Ask permission to start a scene | Per-scene go-ahead | Approve to start | dynamic | functional |
| C45 | All Scenes | app/workflow/run_views.py:119 | Checkpoint label | Target 'scenes' (CP3) | Label for the combined scene approval | Every scene approved together | Approve all | backend API | functional |
| C46 | Scene {N} | app/workflow/run_views.py:120 | Checkpoint label (dynamic) | Target sNN | Per-scene label | One scene | None | dynamic | functional |
| C47 | {target}  (fallback: raw target id, e.g. scene:s01) | app/workflow/run_views.py:120 | Checkpoint label fallback | Unmapped target | Fallback | Raw ledger key | None | dynamic | potentially unused: all targets are mapped today |
| C48 | {Name} — {Mon D, YYYY} (default run name; 'Untitled Run' when empty) | app/workflow/run_views.py:95-102 | Run name (dynamic) | Run has no name set | Default display name | Topic plus start date; long topics cut with an ellipsis | None | dynamic | functional |
| C49 | {YYYY-MM-DD HH:MM} created / updated | app/workflow/run_views.py:30-45 | Timestamp text | Run summary | Show times | Local time, no seconds or timezone | None | dynamic | functional |
| C50 | {stage} e.g. '1 template', '1 requirements', '2 outline', '3 script', '4 plans', '5 production', 'final', 'change requests', 'done' | app/workflow/run_views.py:66; app/workflow/driver.py:179-513 | Stage code (dynamic) | Every run summary | Machine stage key | Mapped by the frontend (stages.tsx BATCH_NAMES) | None | dynamic | inconsistent: numbered codes duplicate 'requirements' under stage 1 and call stage 4 'plans' while the UI says 'Scene Plans'; unmapped values would show raw |

### 3. Checkpoint problems (shown in the site's checkpoint panel, run page problems list and as 409 problems)
Shown through CheckpointPanel.tsx:73 (WithCode) and Home.tsx:106-107 as `{label}: {problem}`. Many are written for Claude, not for the user.

#### 3a. Approval gates (approvals.py, checkpoints.py, change_requests.py)

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| C51 | {target} changed since you opened it: reload the page to see it as it is now | app/workflow/approvals.py:139 | Checkpoint problem (dynamic) | Fingerprint the page showed differs from current | Tell the user what blocks this checkpoint | Approving would bind to a version the user never saw | Reload and re-review | dynamic | misleading: {target} is a ledger key (plan, scenes, scene:s01, start:s02) not a label; 'opened' fits the page not the file |
| C52 | cannot approve {target} yet: {problems joined by '; '} | app/workflow/approvals.py:98 | Checkpoint problem (dynamic) | ApprovalBlocked.__str__ | Tell the user what blocks this checkpoint | Same blockers as the list | See list | dynamic | redundant: duplicates the problems list in the same 409 response |
| C53 | {checkpoint} is not approved, or changed since it was approved: get {short} first | app/workflow/checkpoints.py:29 | Checkpoint problem (dynamic) | A prerequisite stage is not approved for the current inputs | Tell the user what blocks this checkpoint | E.g. 'the template checkpoint (template.json) is not approved, or changed ... get the template checkpoint first'; 'CP0 (the outline) ... get CP0 first' | Approve the earlier stage | dynamic | misleading: CP0/CP1/CP2 jargon; file name template.json; the site has no 'CP' vocabulary |
| C54 | the requirements checkpoint (brief, topics, content) | app/workflow/checkpoints.py:11 | Checkpoint name | Fragment inside the line above | Tell the user what blocks this checkpoint | Requirements stage | Approve requirements | backend config data | inconsistent: 'checkpoint' prose vs CPn naming of the next three |
| C55 | the template checkpoint (template.json) | app/workflow/checkpoints.py:12 | Checkpoint name | as above | Tell the user what blocks this checkpoint | Look & sound stage | Approve template | backend config data | misleading: internal file name |
| C56 | CP0 (the outline) | app/workflow/checkpoints.py:13 | Checkpoint name | as above | Tell the user what blocks this checkpoint | Outline stage | Approve outline | backend config data | misleading: CP0 jargon |
| C57 | CP1 (the complete script) | app/workflow/checkpoints.py:14 | Checkpoint name | as above | Tell the user what blocks this checkpoint | Script stage | Approve script | backend config data | misleading: CP1 jargon |
| C58 | CP2 (the scene visual plans) | app/workflow/checkpoints.py:15 | Checkpoint name | as above | Tell the user what blocks this checkpoint | Scene Plans stage | Approve plans | backend config data | misleading: CP2 jargon; the site calls it Scene Plans |
| C59 | open change request {id} ({target}, {kind}): {text} — apply or decline it first | app/workflow/change_requests.py:112 | Checkpoint problem (dynamic) | Open change request blocks a checkpoint | Tell the user what blocks this checkpoint | Request r001 must be applied or declined | Wait for Claude, or decline it | dynamic | misleading: asks the user to 'apply' a request, which only Claude/CLI can do; ids r001 and kind codes (audio-timing) leak |
| C60 | script: changes were requested at CP1 — run the script-critic (round {n} of {m}) | app/workflow/critiques.py:112 | Checkpoint problem (dynamic) | Script changes requested but critic round missing | Tell the user what blocks this checkpoint | Claude's next job, not the user's | None (Claude will do it) | dynamic | misleading: CP1, 'script-critic' subagent name; the user cannot run it |
| C61 | no scene plans yet | app/workflow/approvals.py:74 | Checkpoint problem (dynamic) | Approve 'scenes' with no plans | Tell the user what blocks this checkpoint | Nothing to approve | Wait for plans | dynamic | functional |
| C62 | {scene_id}: {plan error}  (one per scene, prefix e.g. 's01: ') | app/workflow/approvals.py:59 | Checkpoint problem (dynamic) | Plan checkpoint | Tell the user what blocks this checkpoint | Per-scene plan problems prefixed with the scene id | Wait for Claude | dynamic | inconsistent: 's01' vs 'Scene 1' labels elsewhere |
| C63 | {sNN}: has a plan but is not a scene of the script — delete it | app/workflow/approvals.py:67 | Checkpoint problem (dynamic) | A plans folder exists for a scene not in the script | Tell the user what blocks this checkpoint | Stale scene folder | Delete scenes/sNN/ | dynamic | misleading: asks the user to delete a file they cannot reach from the site |
| C64 | final.mp4 is missing or out of date | app/workflow/approvals.py:79 | Checkpoint problem (dynamic) | Final checkpoint with no matching final_report | Tell the user what blocks this checkpoint | Final video not (re)rendered | Wait for Claude to render | dynamic | misleading: file name; 'out of date' not explained; also part of UNFORCEABLE matching |
| C65 | media check {CODE}: {message} | app/workflow/approvals.py:80 | Checkpoint problem (dynamic) | Final report has ERROR findings (e.g. media check RESOLUTION: 1920x1080) | Tell the user what blocks this checkpoint | A delivery check failed | Ask Claude to re-render, or accept | dynamic | misleading: raw code names (DECODE_ERRORS, FRAME_RATE) and technical messages |
| C66 | {sNN}: no valid plan | app/workflow/approvals.py:84 | Checkpoint problem (dynamic) | Scene checkpoint whose plan fails to load | Tell the user what blocks this checkpoint | Plan missing/invalid | Wait for plans | dynamic | redundant: same text as the CLI 'no valid plan' (preview, scene_code) |
| C67 | {sNN}: {clipId} is not built from its current inputs | app/workflow/approvals.py:87 | Checkpoint problem (dynamic) | Scene approval while a clip is stale | Tell the user what blocks this checkpoint | Clip out of date versus plan/audio | Wait for rebuild | dynamic | misleading: 'inputs' is jargon; clip ids sNNcMM |
| C68 | is not built from its current inputs / preview missing or out of date / final.mp4 is missing or out (the UNFORCEABLE substrings) | app/workflow/approvals.py:112 | Matching list (not shown) | Force refused when the matching problem is present | Tell the user what blocks this checkpoint | Cannot force-approve what the user has not seen | Wait | backend config data | misleading: fragile substring match on problem wording; if a message is edited force silently works |

#### 3b. Stage validation (validation.py)

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| C69 | brief.json does not exist | app/workflow/validation.py:43 | Checkpoint problem (dynamic) | Requirements check | Tell the user what blocks this checkpoint | File missing | Wait for Claude | dynamic | misleading: file name; site says Requirements |
| C70 | topics.md does not exist / content.md does not exist / outline.json does not exist / script.json does not exist | app/workflow/validation.py:52, 64, 90, 140 | Checkpoint problem (dynamic) | Stage file missing | Tell the user what blocks this checkpoint | Artifact not written yet | Wait for Claude | dynamic | misleading: file names, four texts of one pattern |
| C71 | topics.md must be a numbered list (1., 2., 3., …) with one topic per line and nothing else | app/workflow/validation.py:56 | Checkpoint problem (dynamic) | Topic list malformed | Tell the user what blocks this checkpoint | Format rule for Claude | Wait | dynamic | misleading: format rule shown to user |
| C72 | content.md has no '## {topic}' section | app/workflow/validation.py:68 | Checkpoint problem (dynamic) | Content missing a topic | Tell the user what blocks this checkpoint | Missing section | Wait | dynamic | misleading: markdown syntax and file name |
| C73 | content.md sections must follow the topic list's order | app/workflow/validation.py:70 | Checkpoint problem (dynamic) | Order mismatch | Tell the user what blocks this checkpoint | Order rule | Wait | dynamic | misleading: file name |
| C74 | content.md section '{heading}' is empty | app/workflow/validation.py:73 | Checkpoint problem (dynamic) | Empty section | Tell the user what blocks this checkpoint | Empty section | Wait | dynamic | misleading: file name |
| C75 | {loc}: {pydantic msg} (brief.json / outline.json / script.json / plan.json validation errors) | app/workflow/validation.py:45, 92, 142, 196; app/utilities.py:97 | Checkpoint problem (dynamic) | Schema validation of an artifact | Tell the user what blocks this checkpoint | Field path and library message e.g. scenes.0.duration_seconds: Input should be greater than 0 | Wait | dynamic | misleading: raw pydantic text with JSON paths |
| C76 | segment scene_id values must be 1, 2, 3, … in order | app/workflow/validation.py:95 | Checkpoint problem (dynamic) | Outline numbering wrong | Tell the user what blocks this checkpoint | Rule text | Wait | dynamic | inconsistent: 'segment' vs 'scene' on the site; field name scene_id |
| C77 | segment {n}: {kind} is not a stage of the {approach} approach ({a → b → c}) | app/workflow/validation.py:100 | Checkpoint problem (dynamic) | Outline stage type outside the approach | Tell the user what blocks this checkpoint | Approach order rule | Wait | dynamic | misleading: approach id (visual_intuition) and stage ids |
| C78 | segments break the {approach} order (A2): {order} | app/workflow/validation.py:106 | Checkpoint problem (dynamic) | Outline order wrong | Tell the user what blocks this checkpoint | Rule A2 | Wait | dynamic | misleading: criterion code A2 leaks |
| C79 | every stage appears at least once (A2); missing: {list} | app/workflow/validation.py:108 | Checkpoint problem (dynamic) | Approach stage missing | Tell the user what blocks this checkpoint | Rule A2 | Wait | dynamic | misleading: criterion code |
| C80 | the video opens with {x} and closes with {y} (A3) | app/workflow/validation.py:110 | Checkpoint problem (dynamic) | First/last segment type wrong | Tell the user what blocks this checkpoint | Rule A3 | Wait | dynamic | misleading: criterion code |
| C81 | segment {n}: {secs}s — every segment is 10–120 s (G2) | app/workflow/validation.py:114 | Checkpoint problem (dynamic) | Segment length out of range | Tell the user what blocks this checkpoint | Rule G2 | Wait | dynamic | misleading: criterion code |
| C82 | segment {n}: transition_to_next is null only on the last segment (S13) | app/workflow/validation.py:116 | Checkpoint problem (dynamic) | Transition rule | Tell the user what blocks this checkpoint | Rule S13 | Wait | dynamic | misleading: field name and code |
| C83 | segment {n}: visual_plan has {a} sentences, needs at least {b} (VP2) | app/workflow/validation.py:121 | Checkpoint problem (dynamic) | Visual plan too short | Tell the user what blocks this checkpoint | Rule VP2 | Wait | dynamic | misleading: field name and code |
| C84 | segment {n}: visual_plan's first sentence describes the empty canvas (VP3) | app/workflow/validation.py:123 | Checkpoint problem (dynamic) | First sentence rule | Tell the user what blocks this checkpoint | Rule VP3 | Wait | dynamic | misleading: code |
| C85 | segment {n}: visual_plan's last sentence must begin 'The scene ends with' (VP4) | app/workflow/validation.py:125 | Checkpoint problem (dynamic) | Last sentence rule | Tell the user what blocks this checkpoint | Rule VP4 | Wait | dynamic | misleading: code |
| C86 | segment {n}: visual_plan uses double quotes; on-screen text goes in single quotes (VP5) | app/workflow/validation.py:127 | Checkpoint problem (dynamic) | Quote rule | Tell the user what blocks this checkpoint | Rule VP5 | Wait | dynamic | misleading: code |
| C87 | outline_segment: the scenes after the index must narrate outline segments {ids} once each, in order; got {ids} (none on {ids}) | app/workflow/validation.py:149-151 | Checkpoint problem (dynamic) | Script scene mapping wrong | Tell the user what blocks this checkpoint | Mapping rule with Python lists printed | Wait | dynamic | misleading: field name and list reprs |
| C88 | objective {n} is not covered by any scene: '{objective}' | app/workflow/validation.py:157 | Checkpoint problem (dynamic) | Script misses an objective | Tell the user what blocks this checkpoint | Objective uncovered; repr quotes | Wait or ask for a change | dynamic | functional: Python repr quoting |
| C89 | brief objective missing from the script's objectives: '{objective}' | app/workflow/validation.py:162 | Checkpoint problem (dynamic) | Script drops a brief objective | Tell the user what blocks this checkpoint | As stated | Wait | dynamic | functional |
| C90 | {sNN} has {a} spoken words, but {b}s at {wpm} wpm needs about {c} (±25%): rewrite the narration or change duration_seconds | app/workflow/validation.py:171-173 | Checkpoint problem (dynamic) | Narration length off its budget | Tell the user what blocks this checkpoint | Word budget | Wait | dynamic | misleading: field name; ±25% hard-coded duplicating WORD_BUDGET_TOLERANCE (config.py:70) |
| C91 | scenes total {a}s but the target is {b}s (±20%): rescale duration_seconds, drop or merge scenes | app/workflow/validation.py:179-180 | Checkpoint problem (dynamic) | Total length off | Tell the user what blocks this checkpoint | Length target | Wait | dynamic | misleading: field name |
| C92 | scenes/{sNN}/plan.json does not exist | app/workflow/validation.py:194 | Checkpoint problem (dynamic) | Plan file missing | Tell the user what blocks this checkpoint | Missing plan | Wait | dynamic | misleading: file path |
| C93 | scene_id is {a}, expected {b} | app/workflow/validation.py:197 | Checkpoint problem (dynamic) | Plan scene id mismatch | Tell the user what blocks this checkpoint | Inconsistent id | Wait | dynamic | misleading: field name |
| C94 | {sNN} execution_plan is empty: run `text-2-shorts plan-task . --scene {sNN}` and write the Scene Execution Plan into plan.json first, then derive the other fields from it | app/workflow/validation.py:200-201 | Checkpoint problem (dynamic) | Plan lacks execution plan | Tell the user what blocks this checkpoint | Instruction to Claude with a CLI command | Wait | dynamic | misleading: CLI command and jargon shown to a website user |
| C95 | {sNN} execution_plan: {visual-director problem} | app/workflow/validation.py:205-206 | Checkpoint problem (dynamic) | Execution plan rule broken | Tell the user what blocks this checkpoint | Rule text from visual_director | Wait | dynamic | misleading: internal rule text |
| C96 | {sNN} is not a scene of the approved script | app/workflow/validation.py:211 | Checkpoint problem (dynamic) | Plan for unknown scene | Tell the user what blocks this checkpoint | Orphan plan | Wait | dynamic | functional |
| C97 | {sNN}: the clips' narration must be the script's spoken text for this scene (bridge_in, then narration), word for word and in order; to change what is said, edit script.json and get CP1 again | app/workflow/validation.py:215-216 | Checkpoint problem (dynamic) | Narration differs from script | Tell the user what blocks this checkpoint | Narration must match | Wait | dynamic | misleading: field names, CP1 |
| C98 | {sNN}: the script's on-screen text '{text}' appears in no clip (visual_intent, beats or on_screen_math) | app/workflow/validation.py:221-222 | Checkpoint problem (dynamic) | On-screen text missing from clips | Tell the user what blocks this checkpoint | Field names | Wait | dynamic | misleading: field names |
| C99 | {clipId}: sound effect {file} not found (the user's own file, relative to the run) | app/workflow/validation.py:226 | Checkpoint problem (dynamic) | Sound-effect file missing | Tell the user what blocks this checkpoint | User file not found | Upload/fix the file | dynamic | functional (path in message) |
| C100 | {clipId} entry: add {names} to entry.descriptions (type, text or LaTeX, colour) — a clip re-creates what it takes over when it runs alone | app/workflow/validation.py:234-235 | Checkpoint problem (dynamic) | Persistent objects undescribed | Tell the user what blocks this checkpoint | Instruction to Claude | Wait | dynamic | misleading: field names, Python list repr |
| C101 | {clipId} ssml: not well-formed SSML: {xml error} / SSML must be one <speak>…</speak> element / unsupported SSML tags {...}; use only {...} | app/workflow/validation.py:238; app/narration.py:188-191 | Checkpoint problem (dynamic) | SSML invalid | Tell the user what blocks this checkpoint | XML/SSML problem | Wait | dynamic | misleading: raw XML parser text, Python set reprs |
| C102 | {clipId} ssml must speak exactly the clip's narration (add tags, never change words) | app/workflow/validation.py:243 | Checkpoint problem (dynamic) | SSML words differ | Tell the user what blocks this checkpoint | Rule | Wait | dynamic | misleading: SSML jargon |
| C103 | {sNN} transition_in is empty: describe how it opens from the previous scene's final image | app/workflow/validation.py:247 | Checkpoint problem (dynamic) | Missing transition | Tell the user what blocks this checkpoint | Field empty | Wait | dynamic | misleading: field name |
| C104 | {clipId} entry must be empty (scenes start on an empty frame) / {clipId} exit must be empty (scenes end with everything faded out) | app/workflow/validation.py:29, 31 | Checkpoint problem (dynamic) | Scene boundary objects present | Tell the user what blocks this checkpoint | Boundary rule | Wait | dynamic | functional (two texts) |
| C105 | `{symbol}` is {colour} here but {colour} in {sNN}: one colour per symbol | app/workflow/validation.py:252 | Checkpoint problem (dynamic) | Colour roles disagree between scenes | Tell the user what blocks this checkpoint | Consistency rule | Wait | dynamic | functional; British 'colour' vs the site's 'Color' |
| C106 | {file} does not exist: run the accuracy-reviewer subagent | app/workflow/validation.py:265 | Checkpoint problem (dynamic) | script_review.json/plan_review.json absent | Tell the user what blocks this checkpoint | Review not made | Wait | dynamic | misleading: subagent name and file name shown to the user |
| C107 | {file} reviewed an older version of the {script\|plans}: run the accuracy-reviewer again | app/workflow/validation.py:270 | Checkpoint problem (dynamic) | Review is stale | Tell the user what blocks this checkpoint | Needs re-review | Wait | dynamic | misleading: same |
| C108 | {file}: unknown target {target} | app/workflow/validation.py:276 | Checkpoint problem (dynamic) | Review finding targets nothing | Tell the user what blocks this checkpoint | Bad id | Wait | dynamic | misleading: file name |
| C109 | accuracy ERROR in {target}: {why} | app/workflow/critiques.py:216 | Checkpoint problem (dynamic) | Accuracy review ERROR finding | Tell the user what blocks this checkpoint | Content problem found by reviewer | Fix or accept (force) | dynamic | functional: 'ERROR' capitalised, target is raw id |

#### 3c. Critique, preview and template problems (critiques.py, production.py, templates.py, video_settings.py)

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| C110 | {file} does not exist: run the {script\|plan\|video}-critic subagent | app/workflow/critiques.py:56 | Checkpoint problem (dynamic) | Critique file missing | Tell the user what blocks this checkpoint | Critic not run | Wait | dynamic | misleading: subagent names |
| C111 | {file}: {pydantic error} | app/workflow/critiques.py:58 | Checkpoint problem (dynamic) | Critique file malformed | Tell the user what blocks this checkpoint | Raw schema error | Wait | dynamic | misleading: raw pydantic |
| C112 | {file} has {n} rounds: one critique round per change request raised at CP1 ({k} so far) | app/workflow/critiques.py:62-63 | Checkpoint problem (dynamic) | Too many script critique rounds | Tell the user what blocks this checkpoint | Round limit | Wait | dynamic | misleading: CP1, internals |
| C113 | {file} has {n} rounds: the loop stops after {max} rounds | app/workflow/critiques.py:66 | Checkpoint problem (dynamic) | Too many critique rounds | Tell the user what blocks this checkpoint | Round limit | Wait | dynamic | misleading: 'loop' |
| C114 | {file} round {n}: score {s}[ against the quality threshold {t}][ with a basic need open] means verdict pass\|revise | app/workflow/critiques.py:74-77 | Checkpoint problem (dynamic) | Verdict inconsistent with score | Tell the user what blocks this checkpoint | Scoring rule | Wait | dynamic | misleading: scoring internals; grammar is awkward |
| C115 | {file}: {criterion} is not a {kind} criterion ({X}-…) | app/workflow/critiques.py:80 | Checkpoint problem (dynamic) | Critic used the wrong criterion code | Tell the user what blocks this checkpoint | Rubric prefix | Wait | dynamic | misleading: criterion codes |
| C116 | {file}: aspect {a} is not one of {list} | app/workflow/critiques.py:82 | Checkpoint problem (dynamic) | Unknown aspect | Tell the user what blocks this checkpoint | Rubric | Wait | dynamic | misleading |
| C117 | {file}: unknown target {target} | app/workflow/critiques.py:90 | Checkpoint problem (dynamic) | Critique targets nothing | Tell the user what blocks this checkpoint | Bad id | Wait | dynamic | redundant: same text as review texts |
| C118 | {sNN}: record the refactor of iteration {n} in scenes/{sNN}/changes.json (what changed, files, rendering, audio timing, sync, validation) | app/workflow/critiques.py:132-133 | Checkpoint problem (dynamic) | Refactor not recorded | Tell the user what blocks this checkpoint | Instruction to Claude | Wait | dynamic | misleading: file path and field list |
| C119 | {sNN}: the {kind} changed since the last critique round — run the {critic} ({round n of m}) | app/workflow/critiques.py:142 | Checkpoint problem (dynamic) | Critic is stale | Tell the user what blocks this checkpoint | Re-critique needed | Wait | dynamic | misleading: subagent names |
| C120 | {sNN}: {kind} critique round {n} asks for changes — refactor, then {round n of m} | app/workflow/critiques.py:144 | Checkpoint problem (dynamic) | Critique says revise | Tell the user what blocks this checkpoint | Another round needed | Wait | dynamic | functional |
| C121 | {sNN}: REQUIRES ATTENTION — {m} critique rounds with issues left; open issues for the user to accept (approve --force) or fix: {target criterion (tier): problem; ...} | app/workflow/critiques.py:147-149 | Checkpoint problem (dynamic) | Critique rounds exhausted | Tell the user what blocks this checkpoint | The user's decision | Read issues; accept or ask for fixes | dynamic | misleading: shouting 'REQUIRES ATTENTION', `approve --force` CLI flag, criterion codes and tier names inline |
| C122 | ... the last {kind} change was not critiqued | app/workflow/critiques.py:149 | Checkpoint problem (dynamic) | Fallback when no issue text | Tell the user what blocks this checkpoint | Gap | Wait | dynamic | functional |
| C123 | scenes/{sNN}/changes.json: {target} is not scene {sNN} or one of its clips | app/workflow/critiques.py:164 | Checkpoint problem (dynamic) | Refactor log targets wrong scene | Tell the user what blocks this checkpoint | Bad id | Wait | dynamic | misleading: file path |
| C124 | {sNN}: preview missing or out of date (text-2-shorts preview <run> {sNN}) | app/workflow/production.py:194 | Checkpoint problem (dynamic) | Scene preview stale | Tell the user what blocks this checkpoint | Preview needed | Wait | dynamic | misleading: CLI command shown on the site; part of UNFORCEABLE |
| C125 | {sNN} out of sync — {clip} beat {n}: shown {x}s {after\|before} the voice says it (audio-refactorer) | app/workflow/production.py:195,161 | Checkpoint problem (dynamic) | Voice and animation misaligned | Tell the user what blocks this checkpoint | Sync problem; also shown per scene via sync_problems (Production.tsx:137) | Wait for retiming, or accept | dynamic | misleading: '(audio-refactorer)' agent name; duplicated with the sync_problems text which omits the suffix |
| C126 | {clip}: the voice ({x}s with lead-in) runs past its animation ({y}s) | app/workflow/production.py:168-169 | Checkpoint problem (dynamic) | Audio longer than video | Tell the user what blocks this checkpoint | Sync problem | Wait | dynamic | functional: 'lead-in' jargon |
| C127 | {clip}: no beat timings from the voice, so its beats were not checked | app/workflow/production.py:150 | Checkpoint problem (dynamic) | Voice gave no word timings | Tell the user what blocks this checkpoint | Warning only | None | dynamic | functional (Google/Polly generative voices) |
| C128 | {CLIP_IDS} (MISSING_CLIPS) / {w}x{h} (RESOLUTION) / {fps} fps (expected {n}) (FRAME_RATE) / {w}x{h} is not 16:9 / no audio stream / {n} LUFS (target -16) / {x} dBTP (clipping risk > -1) / {n} silence(s) ≥ 2.5 s / {first ffmpeg error line} / {n} black stretch(es) ≥ 1 s / {x}s against {y}s scripted | app/workflow/production.py:202-282 | Checkpoint problem (dynamic) | Final media check findings; Home.tsx:109 shows only the message | Tell the user what blocks this checkpoint | Delivery check result | Check pass/warn | dynamic | misleading: on Home only the message is shown without its code (e.g. just 's01c01, s01c02'); 'silence(s)' 'stretch(es)' plural hedging; the code UPPER_SNAKE leaks until lower-cased |
| C129 | template.json does not exist: choose one on the website (Look & sound) or `template . <name>` | app/workflow/templates.py:60 | Checkpoint problem (dynamic) | No template yet | Tell the user what blocks this checkpoint | Prompt to choose the look | Choose a look | dynamic | misleading: file name and CLI syntax shown on the website |
| C130 | template.json is not JSON: {JSON error} | app/workflow/templates.py:64 | Checkpoint problem (dynamic) | Damaged template.json | Tell the user what blocks this checkpoint | Raw parse error | Re-save the look | dynamic | misleading: raw JSON error |
| C131 | music {file} not found: the user's own file, relative to the run folder | app/workflow/templates.py:54 | Checkpoint problem (dynamic) | Template music path invalid | Tell the user what blocks this checkpoint | Missing file | Provide the file | dynamic | functional (no UI to add music) |
| C132 | unknown element {name} | backend/templates/video_settings.py:120 | Checkpoint problem (dynamic) | Template contains unknown element | Tell the user what blocks this checkpoint | Bad template | Re-save | dynamic | functional: internal id |
| C133 | {name}: not set | backend/templates/video_settings.py:121 | Checkpoint problem (dynamic) | Element missing | Tell the user what blocks this checkpoint | Incomplete template | Re-save | dynamic | misleading: element id (e.g. word_highlighting) instead of the label |
| C134 | {name}: {value} is not one of {variants} | backend/templates/video_settings.py:123-125 | Checkpoint problem (dynamic) | Unknown variant id | Tell the user what blocks this checkpoint | Bad choice | Re-pick | dynamic | misleading: ids not labels |
| C135 | {name}: no custom value allowed (custom: background_color, accent_color, text_font) | backend/templates/video_settings.py:129 | Checkpoint problem (dynamic) | Override on a non-customisable element | Tell the user what blocks this checkpoint | Bad custom | None | dynamic | functional (should be unreachable from the UI) |
| C136 | {name}: a custom colour is #RRGGBB | backend/templates/video_settings.py:133 | Checkpoint problem (dynamic) | Custom colour not hex | Tell the user what blocks this checkpoint | Format rule | Enter #RRGGBB | dynamic | inconsistent: 'colour' vs 'Color' on the site |
| C137 | speaking_speed: a custom rate is 0.8–1.2 | backend/templates/video_settings.py:135 | Checkpoint problem (dynamic) | Legacy custom speed | Tell the user what blocks this checkpoint | Legacy rule | None | dynamic | potentially unused: LEGACY_CUSTOM, no UI offers custom speed (video_settings.py:48 comment) |
| C138 | {role} {#hex} has {x}:1 contrast on the background (needs 4.5:1) | backend/templates/video_settings.py:140 | Checkpoint problem (dynamic) | Text colour fails contrast | Tell the user what blocks this checkpoint | Accessibility rule | Choose another colour | dynamic | misleading: role id 'text' (always) and raw hex; 'role' jargon |
| C139 | {loc}: {pydantic message} (VideoTemplate validation) | app/workflow/templates.py:50 | Checkpoint problem (dynamic) | Template fails its schema | Tell the user what blocks this checkpoint | Raw pydantic | Re-save | dynamic | misleading: raw pydantic |

### 4. Console (backend/app/web/console.py)
Each ConsoleEntry is shown in the run page console / Claude panel.

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| C140 | Turn finished. | app/web/console.py:95 | Console system line | Claude Code result event without error | End-of-turn marker | Claude finished replying | Read the reply | backend API | inconsistent: 'Turn' is jargon; the API 409s say 'working' / 'previous message' |
| C141 | {result text or subtype} (e.g. error_max_turns) | app/web/console.py:94 | Console error line (dynamic) | result event with is_error | Show Claude Code's failure | Raw Claude Code result string or subtype id | Retry | dynamic | misleading: raw subtype like error_during_execution |
| C142 | Claude Code stopped (exit {code}). {last 600 chars of stderr} | app/web/console.py:197 | Console error line (dynamic) | Claude Code process exits non-zero | Report abnormal stop | Process crashed; raw stderr appended | Retry; check log | dynamic | misleading: raw stderr tail, exit code |
| C143 | {Tool} {file name \| command \| description}[:200] (e.g. 'Bash text-2-shorts approve . plan', 'Edit script.json') | app/web/console.py:64-66 | Console tool line (dynamic) | Claude calls a tool | Show what Claude is doing | Raw tool name + file/command | None | dynamic | misleading: internal tool names and raw shell commands incl. CLI syntax |
| C144 | **{header}** — {question} (+ options) | app/web/console.py:76-78 | Console question line (dynamic) | Claude calls AskUserQuestion | Let the user answer on the site | A question from Claude; markdown ** kept in text | Choose an option | dynamic | functional: depends on frontend rendering the ** markers |
| C145 | {Claude text} | app/web/console.py:73 | Console claude line | Assistant text part | Show Claude's words | Whatever Claude wrote | Read | dynamic | functional |
| C146 | {user message} | app/web/console.py:157 | Console you line | User sends a message | Echo the user's message | Sent text (includes the kickoff prompt) | None | dynamic | functional |
| C147 | Produce this video: follow the text-2-shorts-produce skill from the current state. | app/sandbox.py:130; app/web/app.py:420 | Console kickoff message | Start Production button sends it as a user message | Start the session | The user's 'message' that starts production | Press Start Production | backend (relayed by the Claude session) | misleading: shown as if the user typed it; mentions a skill name |

### 5. Look and sound catalogue (shown in the website's Look & sound tree and Start a Run)
Source `GET /api/look` (templates.py:150-176) built from elements.json and templates/*.json. 21 elements are shown (frame is hidden, templates.py:147); 136 option labels in total. Grouped rows first, then one row per text with a problem.

#### 5a. Grouped rows

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| C148 | Element labels (21), generated by code from ids: Theme mode, Background type, Background color, Grid type, Grid color, Grid opacity, Primary palette, Secondary palette, Accent color, Text font, Math font, Typography, Border style, Border color, Voice, Speaking speed, Narration tone, Subtitles, Subtitle style, Caption position, Word highlighting | app/workflow/templates.py:162 | Element label (21) | Look tree row titles (frontend title-cases) | Let the user pick a look or sound | Names each setting | None | backend config data | functional: derived by `name.replace('_',' ').capitalize()`, not authored; 'Primary/Secondary palette' and 'Typography' are not self-explanatory |
| C149 | Group ids mode, canvas, background, grid, colour, type, border, narration, subtitles (site names: Mode, Background, Grid, Color, Type, Border, Narration, Subtitles) | backend/templates/template_kit/elements.json ('group'); frontend LookTree.tsx:10 | Group label (9) | Tree branches | Let the user pick a look or sound | Groups settings | None | backend config data | inconsistent: backend id 'colour' (British) vs site label 'Color'; 'canvas' is only the hidden frame group |
| C150 | Template names (12): arctic, aurora, cosmic, graphite, ivory, lavender, midnight, monochrome, obsidian, paper, peach, sage | backend/templates/template_kit/templates/*.json ('name') | Starter template names (12) | Start a Run gallery, Look & sound | Let the user pick a look or sound | Starter looks | Pick one | backend config data | functional: lower-case ids title-cased by the frontend |
| C151 | Template descriptions (12), e.g. 'Icy blue on an isometric grid, colour-blind-safe palette, clean sans.' / 'Near-black charcoal, warm cream type, gold accents, one hairline frame.' / 'Slate drafting table: graph paper, technical type, sans maths, corner brackets.' | backend/templates/template_kit/templates/*.json ('description') | Template descriptions (12) | Gallery card alt text and caption | Let the user pick a look or sound | Describes a starter | Read | backend config data | inconsistent: British 'colour', 'maths' vs 'Color' on the site; 'hyperlegible', 'sans maths' are jargon |
| C152 | Custom-value hints: 'color or gradient', 'color', 'font family' | backend/templates/video_settings.py:46-50 | Field hints (3) | Custom editor hint | Let the user pick a look or sound | Tells what a custom value is | Enter a value | backend config data | inconsistent: lower-case fragments, 'color' American here |
| C153 | theme_mode options (2): Dark, Light | backend/templates/template_kit/elements.json elements.theme_mode.variants[].label | Option labels (2) | Option list of the element | Let the user pick a look or sound | One choice per label | Choose | backend config data | functional |
| C154 | background_type options (7): Plain, Plain + grid, Gradient, Centre glow | backend/templates/template_kit/elements.json elements.background_type.variants[].label | Option labels (7) | Option list of the element | Let the user pick a look or sound | One choice per label | Choose | backend config data | functional; British 'Colour'/'Centre' spellings |
| C155 | background_color options (13): Slate, Deep teal, Board green, Warm paper, Peach | backend/templates/template_kit/elements.json elements.background_color.variants[].label | Option labels (13) | Option list of the element | Let the user pick a look or sound | One choice per label | Choose | backend config data | functional |
| C156 | grid_type options (7): Dot grid, Graph paper, Coordinate plane, Isometric | backend/templates/template_kit/elements.json elements.grid_type.variants[].label | Option labels (7) | Option list of the element | Let the user pick a look or sound | One choice per label | Choose | backend config data | functional |
| C157 | grid_color options (5): Secondary palette, Outline, Accent | backend/templates/template_kit/elements.json elements.grid_color.variants[].label | Option labels (5) | Option list of the element | Let the user pick a look or sound | One choice per label | Choose | backend config data | functional |
| C158 | grid_opacity options (5): Whisper, Faint, Subtle, Soft, Visible | backend/templates/template_kit/elements.json elements.grid_opacity.variants[].label | Option labels (5) | Option list of the element | Let the user pick a look or sound | One choice per label | Choose | backend config data | functional |
| C159 | primary_palette options (7): Classic, Chalk pastel, Ink, Neon, Earth | backend/templates/template_kit/elements.json elements.primary_palette.variants[].label | Option labels (7) | Option list of the element | Let the user pick a look or sound | One choice per label | Choose | backend config data | functional; British 'Colour'/'Centre' spellings |
| C160 | secondary_palette options (7): Neutral grey, Cool slate, Sage, Plum | backend/templates/template_kit/elements.json elements.secondary_palette.variants[].label | Option labels (7) | Option list of the element | Let the user pick a look or sound | One choice per label | Choose | backend config data | functional |
| C161 | accent_color options (7): Amber, Coral, Violet, Teal, Lime | backend/templates/template_kit/elements.json elements.accent_color.variants[].label | Option labels (7) | Option list of the element | Let the user pick a look or sound | One choice per label | Choose | backend config data | functional |
| C162 | text_font options (11): Inter, Source Sans 3, Merriweather, Lora | backend/templates/template_kit/elements.json elements.text_font.variants[].label | Option labels (11) | Option list of the element | Let the user pick a look or sound | One choice per label | Choose | backend config data | functional |
| C163 | math_font options (7): Latin Modern, Palatino, CM Bright | backend/templates/template_kit/elements.json elements.math_font.variants[].label | Option labels (7) | Option list of the element | Let the user pick a look or sound | One choice per label | Choose | backend config data | functional |
| C164 | typography options (5): Compact, Standard, Comfortable, Large | backend/templates/template_kit/elements.json elements.typography.variants[].label | Option labels (5) | Option list of the element | Let the user pick a look or sound | One choice per label | Choose | backend config data | functional |
| C165 | border_style options (7): None, Hairline frame, Double frame, Rounded inset, Corner brackets | backend/templates/template_kit/elements.json elements.border_style.variants[].label | Option labels (7) | Option list of the element | Let the user pick a look or sound | One choice per label | Choose | backend config data | functional |
| C166 | border_color options (5): Outline, Secondary, Accent, Focus | backend/templates/template_kit/elements.json elements.border_color.variants[].label | Option labels (5) | Option list of the element | Let the user pick a look or sound | One choice per label | Choose | backend config data | functional |
| C167 | voice options (7): US female, warm / US male, steady / British female / Indian English female | backend/templates/template_kit/elements.json elements.voice.variants[].label | Option labels (7) | Option list of the element | Let the user pick a look or sound | One choice per label | Choose | backend config data | functional |
| C168 | speaking_speed options (5): Slow, Relaxed, Natural, Brisk, Fast | backend/templates/template_kit/elements.json elements.speaking_speed.variants[].label | Option labels (5) | Option list of the element | Let the user pick a look or sound | One choice per label | Choose | backend config data | functional |
| C169 | narration_tone options (7): Friendly teacher, Calm documentary, Energetic, Storyteller | backend/templates/template_kit/elements.json elements.narration_tone.variants[].label | Option labels (7) | Option list of the element | Let the user pick a look or sound | One choice per label | Choose | backend config data | functional |
| C170 | subtitles options (2): On, Off | backend/templates/template_kit/elements.json elements.subtitles.variants[].label | Option labels (2) | Option list of the element | Let the user pick a look or sound | One choice per label | Choose | backend config data | functional |
| C171 | subtitle_style options (7): Clean bar, Outlined, Rounded pill, Minimal, Bold social, High contrast | backend/templates/template_kit/elements.json elements.subtitle_style.variants[].label | Option labels (7) | Option list of the element | Let the user pick a look or sound | One choice per label | Choose | backend config data | functional |
| C172 | caption_position options (6): Bottom centre, Top centre, Lower-left third | backend/templates/template_kit/elements.json elements.caption_position.variants[].label | Option labels (6) | Option list of the element | Let the user pick a look or sound | One choice per label | Choose | backend config data | functional; British 'Colour'/'Centre' spellings |
| C173 | word_highlighting options (7): None, Karaoke fill, Underline current, Progressive reveal | backend/templates/template_kit/elements.json elements.word_highlighting.variants[].label | Option labels (7) | Option list of the element | Let the user pick a look or sound | One choice per label | Choose | backend config data | functional |

#### 5b. Element descriptions (shown as a note under each element, LookTree.tsx:69, CustomEditor.tsx:45)
These are written for the developer who builds the kit, not for the user.

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| C174 | Dark or light. Every colour element below carries a value for both modes. | backend/templates/template_kit/elements.json elements.theme_mode.description | Element description | Note under theme_mode | Let the user pick a look or sound | What the element does | Read | backend config data | functional; 'colour' British |
| C175 | How the backdrop is built from Manim primitives. fill: solid (camera background), linear (gradient Rectangle), radial (stacked translucent Ellipses). texture: random Dots, light on dark and dark on light. | backend/templates/template_kit/elements.json elements.background_type.description | Element description | Note under background_type | Let the user pick a look or sound | What the element does | Read | backend config data | misleading: Manim class names and internal terms 'fill/texture' shown to users |
| C176 | Base colour, gradient end (shade) and centre glow, for each mode. | backend/templates/template_kit/elements.json elements.background_color.description | Element description | Note under background_color | Let the user pick a look or sound | What the element does | Read | backend config data | functional; jargon 'shade' |
| C177 | Grid geometry (Manim Lines/Dots/NumberPlane). Drawn only when the background type includes a grid. | backend/templates/template_kit/elements.json elements.grid_type.description | Element description | Note under grid_type | Let the user pick a look or sound | What the element does | Read | backend config data | misleading: Manim class names; useful rule at the end |
| C178 | Grid line colour, taken from the active mode's palette. | backend/templates/template_kit/elements.json elements.grid_color.description | Element description | Note under grid_color | Let the user pick a look or sound | What the element does | Read | backend config data | functional |
| C179 | Line/dot opacity; graph-paper minor lines and plane axes scale from it. | backend/templates/template_kit/elements.json elements.grid_opacity.description | Element description | Note under grid_opacity | Let the user pick a look or sound | What the element does | Read | backend config data | misleading: 'graph-paper minor lines and plane axes' is implementation detail |
| C180 | Content roles: text, focus (what is discussed now), given (inputs), derived (results), warning. Each variant has a dark and a light set; theme_mode picks one. | backend/templates/template_kit/elements.json elements.primary_palette.description | Element description | Note under primary_palette | Let the user pick a look or sound | What the element does | Read | backend config data | misleading: role names and the id 'theme_mode' |
| C181 | Supporting roles: secondary (labels, notes), surface (panel fill, used at low opacity), outline (dividers, panel borders), dim (de-emphasised items). | backend/templates/template_kit/elements.json elements.secondary_palette.description | Element description | Note under secondary_palette | Let the user pick a look or sound | What the element does | Read | backend config data | misleading: role jargon |
| C182 | One brand/highlight colour (role 'accent'), also used for word highlighting unless the subtitle style says otherwise. | backend/templates/template_kit/elements.json elements.accent_color.description | Element description | Note under accent_color | Let the user pick a look or sound | What the element does | Read | backend config data | misleading: 'role', 'brand' |
| C183 | Google Fonts family rendered by Pango (Manim Text). install_fonts.py downloads all of them. | backend/templates/template_kit/elements.json elements.text_font.description | Element description | Note under text_font | Let the user pick a look or sound | What the element does | Read | backend config data | misleading: Pango, Manim and a script file name shown to users |
| C184 | LaTeX preamble for MathTex/Tex. The kit test-compiles the chosen one at startup. | backend/templates/template_kit/elements.json elements.math_font.description | Element description | Note under math_font | Let the user pick a look or sound | What the element does | Read | backend config data | misleading: LaTeX preamble, class names, 'the kit' |
| C185 | Type scale in Manim font_size units. | backend/templates/template_kit/elements.json elements.typography.description | Element description | Note under typography | Let the user pick a look or sound | What the element does | Read | backend config data | misleading: Manim units |
| C186 | Frame border drawn from Manim primitives; inset is how far content must stay inside it (Manim units). | backend/templates/template_kit/elements.json elements.border_style.description | Element description | Note under border_style | Let the user pick a look or sound | What the element does | Read | backend config data | misleading: Manim primitives/units |
| C187 | Palette role used for the border (letterbox bars use it as a fill). | backend/templates/template_kit/elements.json elements.border_color.description | Element description | Note under border_color | Let the user pick a look or sound | What the element does | Read | backend config data | misleading: 'palette role' |
| C188 | English narrator: the same person-type on both providers. Polly neural and Google Neural2 return exact word timings; Polly generative and Google Chirp 3 HD sound richer but highlighting is estimated. | backend/templates/template_kit/elements.json elements.voice.description | Element description | Note under voice | Let the user pick a look or sound | What the element does | Read | backend config data | misleading: provider engine names; true but unexplained consequence |
| C189 | Rate (Polly prosody %, Google speaking_rate) and pause after each sentence. | backend/templates/template_kit/elements.json elements.speaking_speed.description | Element description | Note under speaking_speed | Let the user pick a look or sound | What the element does | Read | backend config data | misleading: API parameter names |
| C190 | How the script is written (rules for the script model; sentence length is enforced). Documentary/formal use Polly's newscaster style on voices that have it. | backend/templates/template_kit/elements.json elements.narration_tone.description | Element description | Note under narration_tone | Let the user pick a look or sound | What the element does | Read | backend config data | misleading: 'script model', 'newscaster style' |
| C191 | Burned-in subtitles on or off. An .srt sidecar is always written. | backend/templates/template_kit/elements.json elements.subtitles.description | Element description | Note under subtitles | Let the user pick a look or sound | What the element does | Read | backend config data | misleading: '.srt sidecar' file term |
| C192 | Burned-in subtitle look. text_color 'auto' = the palette's text colour for the mode; outline 'auto' = black under light text, white under dark text. Boxes are fixed fills so they read on either mode. | backend/templates/template_kit/elements.json elements.subtitle_style.description | Element description | Note under subtitle_style | Let the user pick a look or sound | What the element does | Read | backend config data | misleading: field names text_color/outline |
| C193 | Where burned-in subtitles sit. reserve = fraction of frame height kept clear of content. | backend/templates/template_kit/elements.json elements.caption_position.description | Element description | Note under caption_position | Let the user pick a look or sound | What the element does | Read | backend config data | misleading: field name 'reserve' |
| C194 | How the spoken word is tracked in burned-in subtitles. | backend/templates/template_kit/elements.json elements.word_highlighting.description | Element description | Note under word_highlighting | Let the user pick a look or sound | What the element does | Read | backend config data | functional |

#### 5c. Individual option labels and details with a problem

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| C195 | Auto (white on dark, black on light) | backend/templates/template_kit/elements.json grid_color.auto | Option label | grid_color list | Let the user pick a look or sound | Automatic colour | Choose | backend config data | functional |
| C196 | Primary (given) | backend/templates/template_kit/elements.json grid_color.given | Option label | grid_color list | Let the user pick a look or sound | Uses the 'given' role colour | Choose | backend config data | misleading: 'given' is an internal role name |
| C197 | Off (sidecar .srt only) | backend/templates/template_kit/elements.json subtitles.off | Option label | subtitles list | Let the user pick a look or sound | Subtitles not burned in, a file is still written | Choose | backend config data | misleading: '.srt' file term |
| C198 | Textured (chalk/paper) | backend/templates/template_kit/elements.json background_type.textured | Option label | background_type list | Let the user pick a look or sound | Grainy background | Choose | backend config data | functional: slash reads awkwardly |
| C199 | Colour-blind safe (Okabe-Ito) | backend/templates/template_kit/elements.json primary_palette.okabe_ito | Option label | palette list | Let the user pick a look or sound | Accessible palette named for its authors | Choose | backend config data | inconsistent: British 'Colour'; 'Okabe-Ito' is jargon |
| C200 | Computer Modern (default) / Latin Modern / Palatino / Times (mathptmx) / Utopia (Fourier) / Euler (hand-drawn feel) / CM Bright (sans maths) | backend/templates/template_kit/elements.json math_font | Option labels (7) | math_font list | Let the user pick a look or sound | Maths typefaces | Choose | backend config data | misleading: LaTeX package names (mathptmx, Fourier); 'maths' British; '(default)' marks a default that the starters override |
| C201 | Bottom, raised (player-safe) / Adaptive (avoid content) | backend/templates/template_kit/elements.json caption_position | Option labels | caption_position list | Let the user pick a look or sound | Subtitle position | Choose | backend config data | functional: 'player-safe' needs explaining |
| C202 | Lecture XL | backend/templates/template_kit/elements.json typography.lecture_xl | Option label | typography list | Let the user pick a look or sound | Very large text | Choose | backend config data | functional: 'XL' abbreviation |
| C203 | Background shade | backend/templates/template_kit/elements.json border_color.background_shade | Option label | border_color list | Let the user pick a look or sound | Border uses the gradient's end colour | Choose | backend config data | misleading: 'shade' unexplained |
| C204 | Draft 480p 15fps / HD 720p 30fps / Full HD 1080p 30fps / Full HD 1080p 60fps / 4K 30fps | backend/templates/template_kit/elements.json frame.variants[].label | Option labels (5) | Never shown: frame is HIDDEN (templates.py:147) | Let the user pick a look or sound | Delivery resolution | None | backend config data | potentially unused: HIDDEN element; the delivery is always 2560x1440 120 fps |
| C205 | Polly {voice_id} · Google {neural2 id} (e.g. Polly Joanna · Google en-US-Neural2-F) | app/workflow/templates.py:182 | Voice option detail (dynamic) | voice list | Let the user pick a look or sound | Maps the voice to providers | Choose | backend config data | misleading: provider ids shown although only one provider is used per run (brief.tts) |
| C206 | {N}% · about {W} words a minute (e.g. 90% · about 135 words a minute) | app/workflow/templates.py:184 | Speed option detail (dynamic) | speaking_speed list | Let the user pick a look or sound | Speed in numbers | Choose | dynamic | functional |
| C207 | {script_rules} e.g. 'Speak to one learner as 'you'; use 'we' when working things out. One idea per sentence. Name what is on screen before explaining it.' | app/workflow/templates.py:186; backend/templates/template_kit/elements.json narration_tone.script_rules | Tone option detail (7) | narration_tone list | Let the user pick a look or sound | Rules for the script writer | Choose | backend config data | misleading: written as instructions to Claude, shown as option detail; only the first sentence describes the sound for a viewer |
| C208 | The font {family} is not available, so a default font is shown. Fetch the template fonts with `uv run python backend/templates/generate_preview.py fonts`. | backend/templates/generate_preview.py:206-209 | Still note (dynamic) | Look still rendered with an uninstalled font (Notice, LookSound.tsx:70, NewRun.tsx:52) | misleading: a shell command with repo paths shown to website users | Warn about font fallback | Preview uses another font | backend API | Run the command |
| C209 | Colours / Fonts / Background / Grid / Border (reshuffle groups: colours, fonts, background, grid, border) | backend/templates/video_settings.py:53-59 | Reshuffle group ids (5) | Reshuffle stage (Reshuffle.tsx) | Let the user pick a look or sound | Which parts to shuffle | Tick groups | backend config data | inconsistent: ids use British 'colours'; the frontend owns the shown labels |

### 6. Command line (backend/app/cli.py, backend/app/commands/**, workflow modules they call)

#### 6a. Argparse help and argument errors

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| C210 | a video is {3}–{20} minutes of teaching | app/cli.py:46 | argparse error | --minutes outside MINUTES (3, 20) | Tell the terminal user | Range of --minutes | Fix the value | backend CLI | functional |
| C211 | what the viewer should be able to do or explain afterwards (repeat for several) | app/cli.py:60 | argparse help (--objective) | --help | Tell the terminal user | Explains the flag | Read | backend CLI | functional |
| C212 | explanation style and tone | app/cli.py:62 | argparse help (--style) | --help | Tell the terminal user | Explains the flag | Read | backend CLI | functional |
| C213 | how the topic is taught: {key} ({name}, {form}), ... | app/cli.py:67-68 | argparse help (--approach, dynamic) | --help | Tell the terminal user | Lists approaches | Choose | dynamic | functional |
| C214 | teaching narration, 3–20 (intro, bridges, closing extra) | app/cli.py:71 | argparse help (--minutes) | --help | Tell the terminal user | Explains the flag | Read | backend CLI | redundant: 3–20 hard-coded twice (also line 46 and MINUTES) |
| C215 | narration provider: AWS Polly or Google Cloud Text-to-Speech (voice, speed and look: the template) | app/cli.py:80 | argparse help (--tts) | --help | Tell the terminal user | Explains the flag | Read | backend CLI | inconsistent: 'the template' vs the site's 'Look & sound' |
| C216 | -- CMD…: run CMD instead of claude in the jail (debugging) | app/cli.py:87 | argparse help (open) | --help | Tell the terminal user | Debug option | Read | backend CLI | functional |
| C217 | comma-separated scene numbers / comma-separated clip ids to rebuild, e.g. s01c02 | app/cli.py:122, 124 | argparse help (--scenes, --clips) | --help | Tell the terminal user | Flags | Read | backend CLI | potentially unused: add_subcommand is never called with scenes=True or clips=True or feedback=True |
| C218 | the web view: follow runs, approve checkpoints, ask for changes (this machine) | app/cli.py:134 | argparse help (serve) | --help | Tell the terminal user | Describes serve | Read | backend CLI | functional |
| C219 | the starter templates | app/cli.py:138 | argparse help (templates) | --help | Tell the terminal user | Describes templates | Read | backend CLI | functional |
| C220 | element=variant · custom.element=value · key=value, e.g. accent_color=coral, custom.text_font=Lato | app/cli.py:151 | argparse help (--set) | --help | Tell the terminal user | Syntax | Read | backend CLI | functional |
| C221 | what each agent gets wrong, over every run → artifacts/reports/mistakes.json and .md | app/cli.py:157 | argparse help (mistakes) | --help | Tell the terminal user | Describes mistakes | Read | backend CLI | functional |
| C222 | the runs folder to read / where to write the report | app/cli.py:159-160 | argparse help (--runs, --out) | --help | Tell the terminal user | Flags | Read | backend CLI | functional |
| C223 | Claude Code hook entry point (reads the hook JSON on stdin) | app/cli.py:164 | argparse help (hook) | --help | Tell the terminal user | Describes hook | Read | backend CLI | functional |
| C224 | sNN / sNN (plan: default every scene; critiques: required) / script \| plans \| sNN | app/cli.py:170,190,200 | argparse help (--scene, scene) | --help | Tell the terminal user | Argument formats | Read | backend CLI | inconsistent: three different notations for a scene argument |
| C225 | Manim API cards by name, e.g. MathTex,Axes.plot | app/cli.py:191 | argparse help (doc) | --help | Tell the terminal user | Describes doc | Read | backend CLI | functional |
| C226 | reference files, e.g. manim-vocabulary,manim-common-mistakes | app/cli.py:193 | argparse help (--topics) | --help | Tell the terminal user | Flag | Read | backend CLI | functional |
| C227 | requirements \| template \| outline \| script \| plan \| sNN \| final \| start:sNN | app/cli.py:211 | argparse help (approve target) | --help | Tell the terminal user | Valid targets | Read | backend CLI | inconsistent: omits 'scenes' (valid, used by CP3 text); 'plan' here, 'Scene Plans' on the site |
| C228 | the user's notes with the approval | app/cli.py:213 | argparse help (--notes) | --help | Tell the terminal user | Flag | Read | backend CLI | functional |
| C229 | outline \| script \| plan \| final \| sNN \| sNNcMM | app/cli.py:215 | argparse help (feedback target) | --help | Tell the terminal user | Valid targets | Read | backend CLI | functional |
| C230 | the user's request, in their words | app/cli.py:221 | argparse help (--text) | --help | Tell the terminal user | Flag | Read | backend CLI | functional |
| C231 | the checkpoint it was raised at (records 'changes requested') | app/cli.py:222 | argparse help (--checkpoint) | --help | Tell the terminal user | Flag | Read | backend CLI | functional |
| C232 | r001, r002, … | app/cli.py:224 | argparse help (resolve id) | --help | Tell the terminal user | Id format | Read | backend CLI | functional |
| C233 | (no help text) new, open, voice, template, final, status, report, validate, next, preview, hash, task, accept, usage-ok, resolve | app/cli.py:54, 84, 120+ | Missing help | --help | Tell the terminal user | Several subcommands have no description | None | backend CLI | inconsistent: only serve, templates, mistakes, hook, doc have help; the other 15 print none |

#### 6b. Command output and exit messages

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| C234 | Invalid requirements: {pydantic error} | app/commands/run_commands.py:20 | sys.exit | `new` with invalid brief | Tell the terminal user | Reject input | Fix flags | backend CLI | misleading: raw pydantic multi-line error |
| C235 | {RunNotCreated text}: Preflight failed: claude CLI not found, manim X installed, project pinned to Y, latex missing, ...; AWS credentials not found for Polly — run `aws configure` or set AWS_PROFILE (or use Google); Google credentials not found — run `gcloud auth application-default login` or set GOOGLE_APPLICATION_CREDENTIALS (or use Polly) | app/workflow/run_workspace.py:79,81,60,68; backend/tools/preflight.py:67-78 | sys.exit / API error (dynamic) | new or Start a Run on a machine missing tools or credentials | Tell the terminal user | Env problems: 'claude CLI not found', 'Claude Code {v} < {need} required for {flag}', 'manim {v} installed, project pinned to {pin}', '{tool} missing' (latex, dvisvgm, ffmpeg, bwrap, socat) | Install the tool / sign in | dynamic | inconsistent: problems are joined with ', ' (hard to scan) and '{tool} missing' gives no install hint; shown raw on the website too |
| C236 | {run relative path} next: text-2-shorts serve (the website), or text-2-shorts open {path}   (Claude Code in this run's isolated workspace) | app/commands/run_commands.py:23-27 | print | `new` succeeded | Tell the terminal user | Next steps | Open serve or open | backend CLI | functional: three spaces before the parenthesis |
| C237 | {run} is not a run workspace (no brief.json) — create one with text-2-shorts new | app/commands/run_commands.py:35 | sys.exit | `open` on a folder without brief.json | Tell the terminal user | Reject | Create a run | backend CLI | functional |
| C238 | Text-2-Shorts: http://127.0.0.1:{port}/#/signin?token={token} | app/commands/serve_command.py:14 | print (serve banner) | `serve` starts | Tell the terminal user | Sign-in link with a one-time token | Open the link | backend CLI | inconsistent: product name 'Text-2-Shorts' vs 'Faraday' on the site |
| C239 |   open that link to sign in with Claude Code's account (valid until serve stops; Ctrl+C to stop) | app/commands/serve_command.py:15 | print (serve banner) | `serve` starts | Tell the terminal user | Explain the link | Open it | backend CLI | functional: 'serve' and 'sign in with Claude Code's account' fine |
| C240 | {name}: {description} (one line per starter template) | app/cli.py:139-141 | print | `templates` | Tell the terminal user | List templates | Pick one | backend CLI | functional |
| C241 | no template {name}: choose one of {a, b, c} | app/workflow/templates.py:107 | sys.exit | `template` with an unknown name | Tell the terminal user | Reject | Pick a listed name | backend CLI | redundant: equals the ValueError at templates.py:207 and the API 404 |
| C242 | {name} has no custom value: choose one of its options | app/workflow/templates.py:113 | sys.exit | `template --set custom.X=` for non-custom X | Tell the terminal user | Reject | Use a listed option | backend CLI | misleading: says 'choose one of its options' but lists none |
| C243 | template.json would be invalid: {problems} | app/workflow/templates.py:123 | sys.exit | `template` result fails checks | Tell the terminal user | Explain | Fix --set values | backend CLI | functional |
| C244 | {template.json path} (printed by `template`) | app/cli.py:144 | print | `template` success | Tell the terminal user | Echo the file | None | backend CLI | functional: no confirmation wording |
| C245 | invalid change request: {pydantic errors} | app/commands/workflow_commands.py:45 | sys.exit | `feedback` invalid kind/target/text | Tell the terminal user | Reject | Fix | backend CLI | misleading: raw pydantic text |
| C246 | {id} recorded for {target} ({kind}). Apply it: {route}; then `text-2-shorts resolve <run> {id} applied`. | app/commands/workflow_commands.py:47-48 | print | `feedback` succeeded | Tell the terminal user | Next step with route text (e.g. 'change what is said in script.json (CP1 again, then the affected plans and CP2)') | Apply the change, then resolve | backend CLI | misleading: route text uses CP1/CP2 jargon; `<run>` placeholder while other messages use `.` |
| C247 | {id}: {applied\|declined} | app/commands/workflow_commands.py:57 | print | `resolve` | Tell the terminal user | Echo | None | backend CLI | functional |
| C248 | no change request {id} | app/workflow/change_requests.py:65 | sys.exit | `resolve` unknown id | Tell the terminal user | Reject | Check id | backend CLI | redundant: also the API 404 |
| C249 | go-ahead for this step only: {stage} | app/commands/workflow_commands.py:65 | print | `usage-ok` | Tell the terminal user | Confirm the usage-gate go-ahead for one batch | None | backend CLI | functional: stage is the code '3 script', not words |
| C250 | cannot approve {target} yet:   - {problem}   - {problem} (use --force only if the user explicitly accepts these) | app/commands/workflow_commands.py:75-77 | sys.exit | `approve` blocked | Tell the terminal user | Explain blockers | Fix or --force with the user's consent | backend CLI | inconsistent: 'cannot approve X yet' text repeated in ApprovalBlocked.__str__ (approvals.py:98) |
| C251 | approved {target}[ (forced)] | app/commands/workflow_commands.py:79 | print | `approve` success | Tell the terminal user | Confirm | None | backend CLI | functional |
| C252 | Claude Code sessions: {n} model responses · input {t} tokens (net {n}, cache read {n}, cache write {n}, {p}% read from cache) · output {n} tokens   {model}: {n} responses · input {n} · cache read {n} · cache write {n} · output {n} | app/commands/workflow_commands.py:91-96 | print | `report` | Tell the terminal user | Token totals | Read | dynamic | functional: jargon (cache read/write) for developers |
| C253 | {error lines}  or '{what}: OK' | app/commands/workflow_commands.py:125 | print + exit 1/0 | `validate` | Tell the terminal user | Validation output | Fix | dynamic | misleading: raw validation texts (see section 3) |
| C254 | {doc cards, or stderr} | app/commands/workflow_commands.py:148 | print | `doc` | Tell the terminal user | Manim API cards | Read | backend CLI | functional |
| C255 | {hash}  or  missing | app/commands/workflow_commands.py:157 | print | `hash` | Tell the terminal user | Version id for critics | Use in a critique file | backend CLI | functional |
| C256 | {clip} {path} summary: {clip}: {secs}s ... total narration: {x}s | app/commands/production_commands.py:73, 79 | print | `voice` per clip and total | Tell the terminal user | Progress | None | backend CLI | functional |
| C257 | brief.json is missing or invalid: `text-2-shorts validate . brief` | app/commands/production_commands.py:43; app/workflow/production.py:42 | sys.exit | `voice`/hash key without a valid brief | Tell the terminal user | Reject | Run validate | backend CLI | redundant: two identical texts |
| C258 | {clipId}: the voice provider failed — {error}. Run voice again to go on from here. | app/commands/production_commands.py:64 | sys.exit | Polly/Google call raises | Tell the terminal user | Explain and resume | Retry | backend CLI | misleading: raw provider exception text |
| C259 | Not built, or built from an older plan or request: {['s01c01', ...]}. Build them first (task, accept). | app/commands/production_commands.py:98 | sys.exit | `final` with unbuilt clips | Tell the terminal user | Explain | Build the clips | backend CLI | inconsistent: Python list repr; '(task, accept)' unexplained |
| C260 | audio missing or outdated for {['s01c01']}: text-2-shorts voice <run> | app/commands/production_commands.py:100, 164; app/workflow/status.py:78 (without list repr) | sys.exit | `final` / `preview` with stale audio | Tell the terminal user | Explain | Run voice | backend CLI | redundant: three nearly identical texts; Python list repr; `<run>` placeholder |
| C261 | Scene previews not approved (CP3): {['s01']} — `approve <run> scenes` (or --force). | app/commands/production_commands.py:107 | sys.exit | `final` before scenes approved | Tell the terminal user | Explain | Approve scenes | backend CLI | misleading: CP3 jargon; list repr |
| C262 | TEXT_2_SHORTS_FPS={n}: must be 60–120 | app/commands/production_commands.py:109 | sys.exit | Bad env var | Tell the terminal user | Explain | Fix env var | dynamic | functional |
| C263 | Final render failed: {json of scene → stderr tail[:3000]} | app/commands/production_commands.py:120 | sys.exit | Any scene render fails | Tell the terminal user | Explain | Read the tail | dynamic | misleading: raw JSON/stderr dump |
| C264 | {run}/final.mp4 duration: {x}s · clips: {n} {SEVERITY} {CODE}: {message} | app/commands/production_commands.py:138-140 | print | `final` success | Tell the terminal user | Report and checks | Read | dynamic | functional |
| C265 | {sNN}: no valid plan | app/commands/production_commands.py:155; app/workflow/scene_code.py:112 | sys.exit / SystemExit | `preview`/`task` for an unknown scene | Tell the terminal user | Reject | Check the scene id | backend CLI | redundant: also a checkpoint problem |
| C266 | build the scene first (text-2-shorts task . {sNN}): {[ids]} not built | app/commands/production_commands.py:162 | sys.exit | `preview` with unbuilt clips | Tell the terminal user | Explain | Run task and the scene-builder | backend CLI | misleading: list repr; command pointing to a step normally done by Claude |
| C267 | preview render failed: {stderr tail} | app/commands/production_commands.py:167 | sys.exit | Preview render error | Tell the terminal user | Explain | Read | dynamic | misleading: raw stderr |
| C268 | {path}/preview.mp4 (720p30) · sync: in sync \|    {problem}...   not checked — {note} | app/commands/production_commands.py:203-205 | print | `preview` done | Tell the terminal user | Report | Read | dynamic | functional |
| C269 | {sNN}: {READY\|FAILED} — {open findings} (e.g. 's01: FAILED — layout_gate: OVERLAP') | app/commands/production_commands.py:212-213; app/workflow/scene_code.py:211 | print + exit 0/1 | `accept` | Tell the terminal user | Report the gates | Rebuild if failed | dynamic | misleading: gate finding codes |
| C270 | gates: crashed (exit {n}) — {stderr tail} | app/workflow/scene_code.py:217 | finding text (dynamic) | Scene gates crash | Tell the terminal user | Say how | Report | dynamic | misleading: raw stderr |
| C271 | No audio for {ids}: run voice first (`text-2-shorts voice .`) | app/workflow/scene_code.py:133 | SystemExit | `task` before audio exists | Tell the terminal user | Explain | Run voice | backend CLI | inconsistent: Capital 'No' + backticks; other messages lower-case |
| C272 | {what} failed (exit {n}): {stderr tail 1500} | app/utilities.py:52 | SystemExit (dynamic) | A helper tool fails (wrapping scene_code, Manim API index) | Tell the terminal user | Explain which tool | Read | dynamic | misleading: raw stderr tail |
| C273 | the render timed out after 7200 s | app/workflow/production.py:108 | finding text (dynamic) | Scene render exceeds 2 h | Tell the terminal user | Explain | Retry | dynamic | functional: seconds not hours |
| C274 | {scene_id} is not a scene of the approved script | app/workflow/visual_director.py:132 | SystemExit | `plan-task` unknown scene | Tell the terminal user | Reject | Check id | backend CLI | redundant: near-duplicate of the plan-validation text 'is not a scene of the approved script' |

### 7. Text the Claude session relays to the user (driver ask_user, change requests)
The driver's `what` texts go to Claude (via `text-2-shorts next`, the SessionStart hook) and are also shown on the site as 'Claude's Next Step' (review.tsx:31). They are written as instructions to Claude, so the site shows instructions addressed to someone else.

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| C275 | Claude usage is at {N}% of the {window id} window (resets {Day HH:MM}; read {time or 'at an unknown time'}). Next would be: {step}. Ask the user whether to go on; on yes run `text-2-shorts usage-ok .`, then `text-2-shorts next .` again. | app/workflow/driver.py:62-65 | ask_user text (usage gate) | A usage window >= 85% (USAGE_GATE_PERCENT) and the next batch is not an ask | Instruct Claude what to ask the user | Usage gate | Say yes or no to continue | dynamic | misleading: raw window ids (five_hour), no date in 'resets Mon 14:00', instructions to Claude shown to the user; 'read ...' is the stored time text; ambiguous 'step' list like 'script-writer script' |
| C276 | the user chooses the look and sound in the website's Look & sound tree (a starter template; anything left alone keeps its default) — or, if they ask you, `text-2-shorts template . <name> [--set element=variant \| custom.element=value]` — {first template problem} | app/workflow/driver.py:183-185 | ask_user text | No valid template.json | Instruct Claude what to ask the user | Prompt: pick the look | Choose on the site | backend (relayed by the Claude session) | misleading: 'if they ask you' and CLI syntax shown to the user; ends with a file-name problem text |
| C277 | template checkpoint: show template.json (starter, changed elements, custom values); on approval `text-2-shorts approve . template` | app/workflow/driver.py:195-196 | ask_user text | Template saved but not approved | Instruct Claude what to ask the user | Ask the user to approve the look | Approve or change | backend (relayed by the Claude session) | misleading: file name and CLI command |
| C278 | complete and confirm the requirements: {brief errors} | app/workflow/driver.py:208 | ask_user text | brief.json invalid | Instruct Claude what to ask the user | Confirm brief | Answer Claude | backend (relayed by the Claude session) | misleading: raw pydantic errors |
| C279 | requirements checkpoint: show brief.json (approach = script type, length, audience, detail level, depth, complexity, visual and audio expectations), topics.md and content.md; on approval `text-2-shorts approve . requirements` | app/workflow/driver.py:260-262 | ask_user text | Requirements ready | Instruct Claude what to ask the user | Approve requirements | Approve | backend (relayed by the Claude session) | misleading: file names and CLI command |
| C280 | CP0: show the outline (segments, timing, visual plans); on approval `text-2-shorts approve . outline` | app/workflow/driver.py:290-291 | ask_user text | Outline ready | Instruct Claude what to ask the user | Approve outline | Approve | backend (relayed by the Claude session) | misleading: CP0 jargon; 'segments' vs site 'Outline' |
| C281 | CP1: show the scene table, the full narration and the accuracy findings; on approval `text-2-shorts approve . script` | app/workflow/driver.py:323-324 | ask_user text | Script ready | Instruct Claude what to ask the user | Approve script | Approve | backend (relayed by the Claude session) | misleading: CP1 jargon |
| C282 | CP2: show each scene's composition, transition_in, clip table and last critique round; on approval `text-2-shorts approve . plan` | app/workflow/driver.py:366-367 | ask_user text | Plans ready | Instruct Claude what to ask the user | Approve plans | Approve | backend (relayed by the Claude session) | misleading: CP2, field name transition_in |
| C283 | the user asked to confirm each scene: start {sNN} now? on yes `text-2-shorts approve . start:{sNN}` | app/workflow/driver.py:387-389 | ask_user text | confirm_each_scene preference on | Instruct Claude what to ask the user | Per-scene go-ahead | Answer yes/no | backend (relayed by the Claude session) | misleading: 'start:s02' target string |
| C284 | {sNN} failed accept {N} times ({findings or 'no gate findings'}): show the user the findings and ask for a hint, then record it with `text-2-shorts feedback . {clipId} visual "<hint>"`, which lets the scene-builder try again | app/workflow/driver.py:421-423 | ask_user text | A scene failed the gates MAX_ATTEMPTS times | Instruct Claude what to ask the user | Ask for a hint | Give a hint or tell Claude to retry | dynamic | misleading: gate codes and CLI |
| C285 | CP3: every scene is built, previewed and critiqued; give the user each scene's preview.mp4, sync summary and last critique round, all together; on approval `text-2-shorts approve . scenes` | app/workflow/driver.py:490-492 | ask_user text | All scenes built | Instruct Claude what to ask the user | Approve scenes | Approve | backend (relayed by the Claude session) | misleading: CP3, file name |
| C286 | CP4: give the user final.mp4 and the media checks; on approval `text-2-shorts approve . final` | app/workflow/driver.py:508-509 | ask_user text | Final ready | Instruct Claude what to ask the user | Approve final | Approve | backend (relayed by the Claude session) | misleading: CP4, file name |
| C287 | which scenes should change? apply {id} ({kind}, {target}): {text} — then `text-2-shorts resolve . {id} applied` (or declined, with the user's agreement) | app/workflow/change_requests.py:122-123,143 | ask_user text | Request targets all scenes | Instruct Claude what to ask the user | Ask which scenes | Name scenes | dynamic | misleading: CLI and request ids; the id text 'r001' leaks |
| C288 | apply {id} ({kind}, {target}): {text} — then `text-2-shorts resolve . {id} applied` (or declined, with the user's agreement) | app/workflow/change_requests.py:122-123,152 | ask_user text | Other/style requests | Instruct Claude what to ask the user | Claude's instruction | Answer | dynamic | misleading: same |
| C289 | {mode} mode — … (subagent instruction texts: 'outline refactor mode — …', 'script refactor mode — …', 'request mode — …', 'one critique round → script_critique.json', 'write mode — run `text-2-shorts plan-task …`', '720p30 scene preview + sync.json', '2560×1440, 120 fps delivery render', 'narration audio from the planned SSML') | app/workflow/driver.py:87-513 | Action text (not a question) | Subagent/command action texts | Instruct Claude what to ask the user | Claude's work order, shown as 'Claude's Next Step' | Wait | backend (relayed by the Claude session) | misleading: internal file names and subagent names; spelled arrow/em-dash punctuation |
| C290 | done: the video is approved. | app/workflow/driver.py:527 | CLI output (format_actions) | `next` when no actions are left | Instruct Claude what to ask the user | Finish message | None | backend CLI | functional |
| C291 | stage {stage}[ — run these in parallel]:   - [{do}] {who}[ · {target}] — {what}[ (first `x`, then `y`)]       read: {paths} | app/workflow/driver.py:517-526 | CLI output | Formatted batch (CLI and SessionStart) | Instruct Claude what to ask the user | Command output | Read | backend CLI | functional: file paths of reference docs are absolute |

### 8. Hook messages (backend/app/commands/hook_command.py)
SessionStart/PostToolUse `systemMessage` appears in the Claude Code terminal (and in the console's session); stderr with exit 2 is fed back to Claude.

| # | Exact Text | Location (file:line) | Element Type | Trigger / Condition | Purpose | Meaning | Expected User Action | Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| C292 | Text-2-Shorts run {run} {status_text}  NEXT BATCH {format_actions} | app/commands/hook_command.py:78 | systemMessage + additionalContext | SessionStart inside a run | Give Claude and the user the run's state | Status table, open requests and next actions | Read | backend (relayed by the Claude session) | redundant: status_text already ends with 'next:' + the same format_actions, so the next batch appears twice (status.py:193) |
| C293 | approved: {names or 'nothing yet'} status: {name}: {value} · ... open change requests: ... \| clip \| status \| open findings \| | app/workflow/status.py:178-189 | status text | `status` and SessionStart | Run overview | Which stages are approved | Read | backend CLI | misleading: values such as requires_user_approval, 'not built'; lower-case 'approved:' fragment |
| C294 | next: {format_actions} | app/workflow/status.py:193 | status text | status | Show the next batch | As above | Read | backend CLI | redundant: duplicated by hook_command.py:78 |
| C295 | text-2-shorts · {tool} {path} — valid \| {tool} {path} \| subagent {agent}: {detail} \| {tool}: {detail} | app/commands/hook_command.py:112,116,118,136 | systemMessage | PostToolUse after any tool | Terminal status line per tool call | What Claude just did | None | backend (relayed by the Claude session) | functional: 'valid' appears only for validated files |
| C296 |  — changes.txt updated | app/commands/hook_command.py:114 | systemMessage suffix | changes.json written and valid | Tell that changes.txt was regenerated | Log refreshed | None | backend (relayed by the Claude session) | functional |
| C297 |  — INVALID: {errors joined by '; '} | app/commands/hook_command.py:119 | log/shown text | Validation errors | Show why a file is invalid | Same texts as section 3 | None | backend (relayed by the Claude session) | misleading: raw validation texts (section 3) |
| C298 | {file} is invalid — fix it: {error lines} | app/commands/hook_command.py:126 | stderr (exit 2) | Validation errors after a Write/Edit | Feed errors back to Claude | Claude must fix the file | None for the user | backend (relayed by the Claude session) | functional |
| C299 | The Text-2-Shorts hook crashed ({Type}: {error}), so this was not validated. Check the file with `text-2-shorts validate`. | app/commands/hook_command.py:48-52 | stderr (exit 2) | Hook raises | Never wave a file through unvalidated | Validator crashed | Check the file | backend (relayed by the Claude session) | inconsistent: product 'Text-2-Shorts' vs Faraday; raw exception |
| C300 | Only the user approves a checkpoint or going on past the usage gate. Finish your task and report back; the session asks the user. | app/commands/hook_command.py:62-64 | stderr (exit 2) | A subagent runs `text-2-shorts approve\|usage-ok` | Stop subagents approving (M31) | Agent blocked | None | backend (relayed by the Claude session) | functional: addressed to Claude; the user only sees it if the terminal shows hook stderr |

### Internal logs (not user-facing)
Counts of `log.*` calls found in each module (info/warning/error/exception/debug); all go to log files, not the UI.

| Module | Count |
|---|---|
| app/web/app.py | 6 (request log, 'run list: skipped', 'run {x} removed...', 'run {x} moved to...', problem handler) |
| app/web/console.py | 4 |
| app/web/usage.py | 3 |
| app/workflow/approvals.py | 4 |
| app/commands/hook_command.py | 2 |
| app/commands/production_commands.py | 1 |
| app/cli.py | 3 |
| app/utilities.py | 2 |
| app/narration.py | 2 |
| app/workflow/run_workspace.py | 2 |
| app/workflow/scene_code.py | 1 |
| app/workflow/templates.py | 1 |
| app/workflow/reshuffle.py | 1 |
| backend/templates/generate_preview.py | 3 |

Logs that are shown to users somewhere: (1) console.py:197 `Claude Code stopped (exit N). {stderr}` is also sent as a visible console line (C row in section 4); (2) app.py:179 request-log problem text is not shown, but the same `ApiProblem` text is returned to the page; (3) utilities.py:52 `run_or_explain` logs the same stderr tail it raises as a SystemExit that reaches the CLI or the site (409). No other log text reaches users.




### Findings (C)

Ranked by user impact (high to low). Line numbers refer to the files at audit time.

#### F1. Developer jargon in the Look & sound element descriptions (high)
- Rows: C174-C194 (notably C175, C177, C183, C184, C185, C186, C189, C190, C191, C192, C193).
- Evidence: backend/templates/template_kit/elements.json `elements.*.description`; passed to the UI unchanged at app/workflow/templates.py:165 and rendered at frontend LookTree.tsx:69 and CustomEditor.tsx:45. Examples: "Manim primitives", "Pango (Manim Text). install_fonts.py downloads all of them", "LaTeX preamble for MathTex/Tex", "Type scale in Manim font_size units", "An .srt sidecar is always written", "text_color 'auto'", "reserve = fraction of frame height".
- Why: 20 of 21 notes under the tree speak to the kit developer; a first-time user sees library names and a script name.
- Recommendation: add a separate user-facing `summary` field in elements.json (one plain sentence) and send that; keep `description` for developers. Also drop role names (given, derived, surface) from C180-C182, C187 and C196.

#### F2. Checkpoint jargon CP0-CP4 and CLI commands reach the website (high)
- Rows: C53, C56-C58, C60, C112, C246, C261, C280-C282, C285-C286 (and C97, C60).
- Evidence: app/workflow/checkpoints.py:11-15 (`"CP0 (the outline)"`, `"CP1 (the complete script)"`), :29 (`get {short} first`); critiques.py:62, :112; validation.py:216, driver.py:290, 323, 366, 490, 508 ("CP0:/CP1:..."). The site shows these through CheckpointPanel.tsx:73, Home.tsx:107 and review.tsx:31 ("Claude's Next Step").
- Why: the site names the stages Requirements, Look & sound, Outline, Script, Scene Plans, All Scenes, Final Video (run_views.py:105-120); "CP2" appears nowhere in the UI, so "get CP2 (the scene visual plans) first" cannot be matched to a screen.
- Recommendation: one display-name map (reuse LABELS from run_views.py:105) used by checkpoints.py and driver.py for any text that reaches the site; keep "CPn" only in Claude-facing prompts.

#### F3. Instructions written for Claude are shown to the user as checkpoint problems or next steps (high)
- Rows: C94, C97, C100, C101, C106, C110, C118, C119, C121, C124, C125, C275-C289.
- Evidence: validation.py:200-201 ("run `text-2-shorts plan-task . --scene s01` and write the Scene Execution Plan into plan.json"), :265 ("run the accuracy-reviewer subagent"); critiques.py:56, :132-133, :142, :147-149; production.py:194 ("text-2-shorts preview <run> s01"), :195 ("(audio-refactorer)"); driver.py:62-65 ("Ask the user whether to go on; on yes run `text-2-shorts usage-ok .`"), :183-185 ("if they ask you, `text-2-shorts template ...`").
- Why: the user is told to run subagents, edit scenes/s01/changes.json, or is the object of "Ask the user ..." sentences. They cannot act on any of it, and it makes the blocker look like their job.
- Recommendation: split each problem into `{user_text, claude_text}` (or add a field on CheckpointView) and show only `user_text` on the site; the usage-gate message (C275) should show "Claude usage is at 87% (five-hour limit, resets Mon 14:00). Continue?" on the site.

#### F4. Raw Python / pydantic / stderr text reaches users (high)
- Rows: C3, C4, C5, C10, C24-C28, C40, C41, C75, C111, C130, C139, C141, C142, C234, C245, C258, C263, C267, C270, C272.
- Evidence: app.py:185-186 (`{loc}: {msg}` straight from pydantic), :197 (`f"{type(error).__name__}: {error}"`), :134 (`{error}` appended), :512, :526, :582, :596, :638, :653 (`{failed}` includes up to 1500 chars of Manim stderr, generate_preview.py:193); run_views.py:73 (`cannot be read: KeyError: 'x'`); utilities.py:97 (`scenes.0.duration_seconds: Input should be greater than 0`); console.py:197 (stderr tail).
- Why: messages like "the still could not be rendered: Traceback ..." or "KeyError: 's01'" are alarming and unactionable; field paths use API names rather than form labels.
- Recommendation: map known failures to plain sentences ("The preview could not be drawn. Try again; if it keeps failing, see the log file named X."), keep the raw detail in the log only (the logs already hold it), and translate the first-level pydantic path through a field-label table.

#### F5. An unreadable run is labelled "made by an older version" (medium-high)
- Rows: C39-C42, C50.
- Evidence: run_views.py:62 sets stage "made by an older version" when brief is missing; :73 sets "cannot be read: ..." and status "failed" with readable=False; RunList.tsx:88 prints "Older Version: Final Video Only" for every `readable == false` run, so a damaged run is described as an old one. RunPage.tsx:132 decides the title by string prefix "This run cannot be read" (coupled to run_views.py:148).
- Also: "Fix or remove that file" (C41) does not say which file; the exception text (first 200 chars) may not name it.
- Recommendation: add a `reason: "older" | "damaged"` field to RunSummary instead of reading the stage text; name the file in the problem text.

#### F6. Product name and stage vocabulary are inconsistent with the site (medium)
- Rows: C8, C35, C238, C292, C299, C42, C43, C50, C148-C152, C224, C227, C229.
- Evidence: the site and C42 say "Faraday"; serve banner "Text-2-Shorts: http://..." (serve_command.py:14), hook "The Text-2-Shorts hook crashed" (hook_command.py:48), error "Open the sign-in link `text-2-shorts serve` ..." (app.py:252). Stage words: Template (run_views.py:107) vs "Look & sound" (site) vs "the look and sound" (app.py:316) vs "starter template" (app.py:314); "Scene Plans" (label) vs "plan" (CLI target, validation texts, argparse C227) vs "plans" (driver stage "4 plans"); "segment" (validation.py:95-127) vs "scene" (everything else); "brief" (C14, C69) vs "Requirements"; "turn" (C15, C140) vs "message"; British colour/centre/maths in backend vs "Color" in the site (C149, C151, C152, C136, C105).
- Recommendation: one glossary (product Faraday; Look & sound; Scene Plans; Requirements) applied to anything that reaches the site; leave CLI target ids as they are but add the display name in help text.

#### F7. Internal ids and file names in user-visible text (medium)
- Rows: C7, C16, C20, C29, C51, C59, C62-C67, C69-C74, C92, C93, C132-C134, C138, C204.
- Evidence: "no run 20261124-101500-keplers-laws" (app.py:209), "scene:s01 changed since you opened it" (approvals.py:139 uses the ledger key), "open change request r001 (audio-timing)", "brief.json does not exist", "scenes/s01/plan.json does not exist", "theme_mode has no picture", "word_highlighting: not set", rule codes (A2, A3, G2, S13, VP2-VP5, O4) in validation.py:106-127 and criterion/tier codes in critiques.py:145-149.
- Why: ids and rule codes carry no meaning for a reader; the same blocker already carries a human label on the page (checkpoint label C43-C46).
- Recommendation: format problems with the checkpoint label (`checkpoint_label()` in run_views.py:115) instead of the ledger key; strip rule codes from the user copy.

#### F8. Message duplicated or contradictory across channels (medium)
- Rows: C11/C21/C241 (unknown template, three wordings, two status codes); C12 (four copies); C25-C28 (five "could not be rendered" variants); C30/C31/C32 (no such file/preview); C52/C250 (cannot approve ... yet, once as exception, once as CLI); C124/C260/C259 (stale preview/audio texts, three CLI variants with and without Python list repr); C64/C68 (UNFORCEABLE substring match on message text, approvals.py:112); C292/C294 (the next batch is printed twice in the SessionStart message, hook_command.py:78 plus status.py:193); C15/C17 (two different 409s for the same busy state).
- Recommendation: centralise common texts as constants (`NO_STARTER = "..."`), and match UNFORCEABLE by a code returned with the problem, not by substring. The substring coupling means rewording C64 or C124 silently lets "force" approve an unseen video.

#### F9. Usage-gate message is unclear for people (medium)
- Row: C275 (and C249).
- Evidence: driver.py:62-65: raw window id (`five_hour`/`seven_day`), time as `%a %H:%M` with no date or time zone ("resets Mon 14:00"), "read {read_at}" prints the stored `now_text()` string or "at an unknown time", the step list is raw `agent target` pairs ("script-writer script"); the sentence ends in an instruction to Claude. `usage-ok` prints "go-ahead for this step only: 3 script" (workflow_commands.py:65) with a raw stage code.
- Recommendation: send a typed object (percent, window label, reset time) and let the frontend word it; map window ids to "5-hour limit / weekly limit" in one place (usage.py:313 passes the raw id to the site, C37).

#### F10. Sign-in and protection errors are terse or ambiguous (medium)
- Rows: C1, C2, C6, C8, C9.
- Evidence: "sign in first" (app.py:203, lower-case fragment, same text after the 24 h expiry or a server restart), "send JSON" (:170), "changes come only from this page" (:166); C9 is used both when Claude Code is signed out and when the `claude` binary is missing or the status call times out (auth.py:27 returns None for FileNotFoundError and TimeoutExpired); C8 mixes a sentence ending in a period with backticks while other errors are lower-case fragments.
- Recommendation: separate "Claude Code is not installed", "Claude Code did not answer", "Claude Code is not signed in"; capitalise and punctuate every user-visible API error the same way.

#### F11. Media check messages lack context (medium-low)
- Row: C128; see also C65.
- Evidence: production.py:202-282 produce messages like "s01c01, s01c02", "1920x1080", "no audio stream", "-18.4 LUFS (target -16)", "3 silence(s) >= 2.5 s". Home.tsx:109 shows only `finding.message` with no code; Production.tsx:165 prefixes the lower-cased code ("missing clips: ..."). Approvals.py:80 renders "media check RESOLUTION: 1920x1080" with the upper-case code.
- Recommendation: one `title` + `detail` pair per finding ("Wrong resolution: 1920x1080, expected 2560x1440"), used by all three places; replace "silence(s)", "stretch(es)".

#### F12. Look catalogue wording problems (medium-low)
- Rows: C148-C152, C195-C209.
- Evidence: element labels are generated by `name.replace("_"," ").capitalize()` (templates.py:162) giving "Primary palette", "Secondary palette", "Typography", "Math font"; option labels with internal terms ("Primary (given)", "Background shade", "Okabe-Ito", "Times (mathptmx)", "Utopia (Fourier)", "Off (sidecar .srt only)"); `narration_tone` detail is the writer's rule text (C207, "One idea per sentence. Name what is on screen before explaining it."); voice detail shows two provider voice ids (C205) though only one provider is used per run; frame labels (C204) are never shown (HIDDEN) and could be removed or kept out of the catalogue; the font warning (C208) tells a website user to run `uv run python backend/templates/generate_preview.py fonts`.
- Recommendation: author labels in elements.json; give tone a short listener-facing description; show only the provider the brief uses; move the font command to the log and say "Install the template fonts (see the README)".

#### F13. Terminal message style is inconsistent (low-medium)
- Rows: C210-C233, C257-C262, C271.
- Evidence: mixed case ("No audio for ..." vs "audio missing or outdated for ..."), Python list repr in output (`['s01c01']`, production_commands.py:98, 100, 107, 162), placeholder `<run>` in some texts but `.` in others (production_commands.py:100, 107 vs driver.py usage `approve . plan`), "approve <run> scenes" without the `text-2-shorts` prefix (production_commands.py:107), `add_subcommand` flags `--scenes`, `--clips`, `--feedback` never used (cli.py:121-126, potentially unused help), 15 subcommands with no help (C233), `approve --help` omits the valid target `scenes` (C227) although CP3 uses it.
- Recommendation: add `help=` to every subcommand; format id lists with ", ".join; one placeholder style.

#### F14. Console wording (low-medium)
- Rows: C140-C147.
- Evidence: "Turn finished." (console.py:95) uses "turn"; error lines pass the raw Claude Code result subtype (console.py:94); tool lines print raw tool names and shell commands (console.py:64-66), including approval commands (`Bash text-2-shorts approve . plan`) that a user never types; the kickoff prompt (C147) appears as the user's own message ("Produce this video: follow the text-2-shorts-produce skill ...").
- Recommendation: "Claude finished." / "Claude could not finish: ..."; show tool lines as friendly verbs ("Writing script.json") or hide them behind a toggle.

#### F15. Dead or duplicated constants (low)
- Rows: C34, C35, C204, C217.
- Evidence: `VOICE_SAMPLE` (app.py:106-108) is never referenced (grep) and duplicates the phrase hard-coded in generate_preview.py:221-222; FastAPI title "Text-2-Shorts" (app.py:140) never displayed; `add_subcommand` flags (cli.py:121-130) unused; LEGACY_CUSTOM text (C137) unreachable from the UI; "minutes 3-20" hard-coded in cli.py:46 and :71 as well as MINUTES; "±25%" in validation.py:173 duplicates WORD_BUDGET_TOLERANCE (config.py:70) so changing the constant would leave the text wrong.
- Recommendation: delete VOICE_SAMPLE or use it from generate_preview; build the texts from the constants.

#### F16. Missing messages (low)
- No message tells the user *which* Claude Code step failed when the console turn ends with exit 0 but did nothing (console.py:249-250 logs only).
- `DELETE /api/runs/{run}` returns 204 with no copy that the run is recoverable from .trash/ (app.py:358 comment only); the UI must say it.
- `PUT /api/drafts/{id}` and `GET /api/drafts` raise a bare 500 through on_unexpected (C5) when a draft file is unreadable (app.py:401, `model_validate_json` on every file, no try/except), unlike `runs()` which skips unreadable items (app.py:296).
- Sign-in with a valid token but no `claude` binary yields the generic C9 text.
- `usage.check()` failures only log (usage.py:339-341); the Home page then shows stale numbers with no note.

#### Counts
- Rows: 300 (C1-C300).
- Findings: 16 (F1-F16).
