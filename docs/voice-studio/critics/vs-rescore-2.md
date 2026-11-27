# Round-2 re-score (tsc clean, npm test 16/16; no hook/orb/player tests still)

## Round-1 High findings
- V1 dock covers content: PARTIAL. Now an icon (x1370-1424) but still fixed over the list: in 01/03/04 it sits on Brian's row play button (y944-984, play glyph at x1388); mobile 06 it overlaps the "Claude's Next Step" row edge; tablet 05 floats beside the orb. Sample line no longer clipped.
- V2 sticky bar hides hero: RESOLVED in scope (04 shows banner in flow, name fully visible; sticky bar declared out of scope).
- V3 too many white fills: PARTIAL. Studio itself is better (Play + Select), but Start Production, Decide, Save Template still white (5 on 01); Subtitles etc untouched.
- V4 orb under-scaled/flat: RESOLVED. size 248, sphere ~150px, speaking shows a deformed bright blob (03), error a dashed ring (04), idle matte sphere; states distinguishable in stills.
- U1 Pause lies when stale: RESOLVED. AudioPlayer derives `ready=loadedKey && !stale`; label "Play X" when stale, and set() calls player.stop() when key changes.
- U2 list preview feedback on phone: PARTIAL. Hero now precedes list on mobile (06) and rows have loading/playing/error glyphs, but the error text/Try Again lives in the player ~500px above the list.
- U3 browse vs select: MOSTLY RESOLVED. Badge + "Select Voice"/"Update Narrator", button hidden when identical, tick + current row. No "Narrator: X" line when browsing another voice (03) -> minor.
- U4 Select doesn't persist / Save Template far: OPEN. select() only calls setChoice; no dirty/"not saved" hint near Select or Save Template (01/03).
- U10 a11y semantics: PARTIAL. Fixed: sr-only "Position", aria-live announce, focus to heading after Select. Still: main/orb button isDisabled while loading (focus drop), Google tab aria-disabled (now reachable as button, explained via aria-label, ok), orb ArrowLeft/Right non-standard but intentional.
- E1 audio plays while UI idle: RESOLVED (stop() in set(); test only by reading, no hook test).
- E2 `.player` collision: RESOLVED. Studio uses `.aplayer`; VideoPreview keeps `.player` (C:259-267) with no later override.
- E3 crash on missing catalogue: RESOLVED. Guard returns an alert when speeds/styles empty before use.
- P1 voice stated 4-5x: RESOLVED (Voice group removed; name now list/identity/player/line).
- P2 provider/engine 3x + dead select: RESOLVED (engine select only if >1; provider only in tabs + line).
- P3 three states for one fact: RESOLVED (badge + conditional button).
- P4 stacked chrome pushes studio below fold: OPEN (studio heading still y567; page-level, declared out of scope but unresolved for the release bar).
- P5-P8 mediums: P6 improved (arrows 40px beside orb), P7 improved (fixed-height player, error/empty states in-line), P8 improved (dock smaller).
- P9 subtitles not hidden: OPEN (01/06 unchanged: toggle ON, three chevron rows, "Burned Into the Video in a Later Version").
Medium engineering: E5 fixed (100ms interval only while playing, VoiceRow memo'd); E7 fixed (setPeaks([]) on load); E6 PARTIAL (same-key path now try/caught; `waveform().then` still has no .catch -> unhandled rejection on decode failure); E8, E9 (no blob cache) unchanged.

## New issues in round 2
- Low: stop() leaves loadedKey set, so after changing a setting then reverting, player shows "ready" with a stopped, position-0 waveform; acceptable but Replay/Play behavior is implicit.
- Low: `waveform()` unhandled rejection (above), now more reachable.
- Low: hear() on rapid ‹ › spam issues one aborted fetch per press (abort works, but request storm possible; no debounce).
- Low: desktop 03 hero collapses in height (identity block gains Select button, orb region shifts) - layout minor jiggle between 01 and 03 (name y717 vs y689).
- Low: tablet 05 hero is a very tall centered block (~330px) before the player; list pushed below delivery controls.
No new Critical/High.

## Scores
| Area | W | Score | Note |
|---|---:|---:|---|
| Visual hierarchy | 15 | 74 | orb/Play now the studio focus; page chrome white CTAs and heading at y567 still compete |
| Typography | 10 | 78 | clean name/meta/player scale; Title Case + 3 families remain |
| Spacing/alignment | 10 | 76 | fixed-height player, aligned hero; dead column when filtered (02) and hero jiggle |
| Monochrome | 10 | 86 | strictly neutral tokens, orb grayscale states |
| Interaction/usability | 15 | 80 | find-hear-tune-select loop honest and stop-on-change; no unsaved cue (U4) |
| Animation | 10 | 82 | real-audio-driven orb, no scale(), distinct states; no reduced-motion reactivity (unverified) |
| Responsive | 10 | 78 | no overflow at 390/820, hero first; dock overlap, tablet hero tall, error far from list |
| Accessibility | 10 | 78 | live announce, focus mgmt, sr labels; focus drop on loading disable |
| Component consistency | 5 | 82 | .aplayer/.studio isolated, collision gone |
| Performance | 5 | 82 | memo rows, 100ms ticker; no decode cache, orb rAF not re-audited |
**Weighted overall: ~79 / 100** (round 1 ~70). Below the 90 bar.

## Open High (release criteria: score does not override)
V1 (dock over row play button, partial), U4 (no dirty/save cue), P4 (page chrome above studio), P9 (subtitles block), V3 partial.

## Top 3 remaining improvements
1. Move the console dock into the header (or inset the list/rows from it) and add a "Not saved to template yet" cue + one primary action near Select/Save.
2. Collapse Subtitles to a single status row and demote Start Production/Decide so the studio starts above ~y380.
3. Add `.catch` on waveform(), cache blobs/peaks per key, and add hook tests (stop-on-change, stale label, abort race); surface list-row errors near the list on narrow screens.
