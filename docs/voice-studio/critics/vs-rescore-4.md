# Round-4 re-score (tsc clean; npm test 16/16 pass)
## Round-3 items
- P9 subtitles: RESOLVED. 01/07 show Toggle On + one summary line "Clean Bar - Bottom Centre - Current Word Colour" + Edit.
- U2 row error near list: RESOLVED in code (VoiceStudio.tsx:61 role=alert message under row). Not visually captured: 04 is cropped at 1000px and shows only the player error, so the row message is unverified in pixels.
- Redundant play+Try Again: RESOLVED (04: single "Try ... Again" retry glyph + message, no second button).
- Clipped list affordance: RESOLVED desktop (01 Joanna fades out). Mobile list now shows 8 rows then Subtitles, fine.
- U4 unsaved cue: RESOLVED and verified (05 "Unsaved Changes" pill beside Save Template).
- V1 dock: unchanged; desktop fine. Mobile (07): console icon sits in the tab row and forces "Whole Look/Checkpoint" to wrap onto a 2nd line - new Low.
- V3 white CTAs: OWNER DECISION (run page). Studio-owned whites: Play, Save pill. 01 still has Start Production, Decide, Save Template, Play.
- P4 studio starts low: OWNER DECISION (run page). Heading y567 desktop; mobile ~y955.
- Hook tests / peaks cache: still OPEN (Low). Only voice.test.ts exists; no player/orb tests.
## New issues (none Critical/High)
- Low: mobile tab row wraps because of console icon (07).
- Low: tablet hero height / desktop hero y-jiggle not re-verified.
- Low: row-error state not captured in any screenshot.
## Scores
Visual hierarchy 83 | Typography 81 | Spacing 84 | Monochrome 88 | Interaction 89 | Animation 84 | Responsive 82 | Accessibility 85 | Component consistency 85 | Performance 83
Weighted: 15*.83+10*.81+10*.84+10*.88+15*.89+10*.84+10*.82+10*.85+5*.85+5*.83 = 85.0 (rounded; 12.45+8.1+8.4+8.8+13.35+8.4+8.2+8.5+4.25+4.15=84.6)
## Release verdict
Studio scope: no Critical/High open; remaining Lows only. Score ~85 vs 90 target -> NOT met numerically; gap is hierarchy/responsive polish and missing tests, not defects.
Run-page scope (owner must rule): V3 (white CTAs outside the studio) and P4 (studio begins below header, approval bar, Next Step). If owner accepts both as out of scope, studio-scope release = acceptable with Lows tracked (mobile tab wrap, hook tests, peaks cache, capture row-error shot). If not accepted, not met.
