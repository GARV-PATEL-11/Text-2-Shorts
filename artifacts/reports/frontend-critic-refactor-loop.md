# Frontend critic refactor loop — Faraday (2026-11-24, version 0.16.0)

Pages reviewed in a real browser (headless Chrome, 1440 px and 390 px): sign-in, run list, a run waiting at a
checkpoint (CP1), a run making its scenes, and a run made by an older version. Constraints kept: black and white only,
no motion (the user's earlier instruction), no fabricated figures, no backend change except one truthful flag.

## Issue register

| # | Pri | Page / component | Issue | Change | Validated |
|---|---|---|---|---|---|
| 1 | Critical | Run page, stage strip | Scene production had no stage: with plans approved and scenes being built, the strip read "Final video: Not started" and nothing else | A 7th stage, Scenes, derived from the real scene statuses (done only when every scene is approved) | i1-run: "6 Scenes, In progress" |
| 13 | Critical | Final video, media checks | "Every check passed" shown for videos that were never checked (older runs have no report) | `RunDetail.final_checked`; the page says "No media checks were recorded" otherwise (test added) | i2-old |
| 14 | High | Final video caption | "2560×1440, as delivered" claimed for unchecked videos | The size is named only when the checks ran | i3-old: "As delivered." |
| 2 | High | Every page | Blank page while data loads | A static "Loading…" where the content will appear (`aria-busy`), no animation | code path; instant locally |
| 3 | High | Run list, What happens next | Internal labels ("5 production", "change requests") | Plain stage names ("Making the scenes", "Applying your changes") | i2-home, i1-run |
| 4 | High | Run page | ~3,400 px for a nearly empty run: 112 px section padding, 52 px headings everywhere, empty 16:9 boxes | Tighter section rhythm, section headings at h3 size, one-line empty states | i2-run: ~2,400 px with more content above the fold |
| 5 | Medium | Run header | Progress only visible after scrolling | Four figures from the run's files (stages approved, scenes approved, clips built, open requests) and the stage strip under the title | i1-run |
| 6 | Medium | Stage strip | Current stage not identified | "now" marker and a white rule on the first stage not yet approved | i2-run |
| 7 | Medium | Status pills | Meaning carried by fill alone | Glyphs: ✓ approved/done, ! waiting for you, ◐ in progress, ↻ being fixed, ✕ failed, ○ not started | i1-run |
| 9 | Medium | Stage strip | "6 · now" middle-dot label | Number plus a separate "now" marker | i2-run |
| 10 | Medium | Scene card | Empty preview box stretched to the card's height | Aligned to the top | i2-run |
| 11 | Medium | Final video | Empty "Media checks" card and a repeated sentence before any video | One line until there is a video | i2-run |
| 12 | Medium | Stage strip, mobile | 7 stages in 2 columns, the last stranded | One row per stage below 900 px | i2-mobile |
| 15 | Low | Notices, next actions | Literal backticks | Backtick spans rendered as code (text nodes only) | i3-old |
| 16 | Low | Run at a checkpoint | "What happens next" repeated the approval panel | Hidden when every action is a checkpoint the panel offers | i4-cp1 |
| 8 | Low | Brand | Old name | Faraday, "Curiosity, Illustrated" (title, bar, sign-in, home, footer, README) | i2-home, i3-signin |

## Decided against (with reasons)
- **Charts**: the runs hold counts, not series or distributions; a chart would be decoration. Counts are shown as figures.
- **Semantic colours** (green, red, amber): the brief is black and white; state is shown by glyph, fill and border, always with a word.
- **Spinners, skeleton shimmer, animated running indicators**: the user asked for no motion; loading is a static message.
- **Renaming the CLI, package and plugin** to Faraday: about 300 references and the tests, no visible effect. Ask to do it.

## Acceptance
Visual consistency, layout, hierarchy, figures (all from run files), truthful workflow states, no fabricated progress,
functional integrity (125 tests, including approve / change / resolve through the API), responsive (1440 and 390 px),
accessibility (native buttons, visible focus, `aria-current` on the current stage, `aria-busy` while loading, live
status messages, contrast ≥ 7:1 for body text), performance (no new requests or dependencies; static files).

## Outstanding
- No in-browser click test of approve / ask / resolve (covered by API tests, not by a browser driver).
- Empty Scenes section before plans exist still takes a section (one line of copy); merge into the strip if it bothers.
