# Round-3 re-score (tsc clean; npm test 16/16 pass)
## Round-2 open items
- V1 console dock: RESOLVED on desktop (01/04: Console button in the rail, nothing over the list). Mobile/tablet: small floating icon (06 at y~808 beside tabs, 05 right of orb) - no content covered in stills; stays fixed on scroll (Low).
- V3 white CTAs: PARTIAL. 01 still has Start Production, Decide, Save Template, Play (+Select when browsing) = 4-5 white fills; studio-owned ones are Play/Select only; rest declared run-page scope.
- U2 row errors on mobile: PARTIAL. Row now shows "!" glyph/"Try X Again" label (VoiceStudio.tsx:49-50) but the message + Try Again live in the player above the list (04); on 390px the list is ~400px below it.
- U4 unsaved cue: RESOLVED in code (LookSound.tsx:47,64 "Unsaved Changes" solid badge next to Save Template, cleared on save). Not captured in any vs3 screenshot (no post-Select shot) -> unverified visually.
- U10 focus loss while loading: RESOLVED. AudioPlayer.tsx:23-24 no isDisabled; onPress guard + aria-busy.
- P4 studio starts low: OPEN (heading y567 desktop, y975 mobile, y794 tablet); page chrome, declared out of scope but real.
- P9 subtitles block: OPEN (Medium). Toggle On + 3 chevron rows unchanged in 01/05/06.
- E6 waveform unhandled rejection: RESOLVED (.catch -> setPeaks([]), usePreviewPlayer.ts:106).
## New issues
- Low: mobile/tablet list is a clipped scroll box ending mid-row ("Daniel..." cut, 05/06) directly above Subtitles; reads as a bug, no fade/affordance.
- Low: desktop 03/01 hero y-jiggle and tablet hero ~330px tall remain.
- Low: no hook/orb/player tests (usePreviewPlayer stop-on-change/abort untested); no blob/peaks cache.
- Low: Google tab "Coming Soon" fine; error state (04) player shows play glyph + Try Again twice-able (play and Try Again both) - redundant.
No new Critical/High.
## Scores
Visual hierarchy 80 (orb/name/Play clear; chrome above, white CTAs) | Typography 80 | Spacing 78 (clipped list, tall tablet hero) | Monochrome 88 | Interaction 86 (unsaved cue, honest Select) | Animation 84 | Responsive 80 (no overflow, icon dock fine; list clip, error far) | Accessibility 84 | Component consistency 84 | Performance 83.
Weighted: 15*.80+10*.80+10*.78+10*.88+15*.86+10*.84+10*.80+10*.84+5*.84+5*.83 = 83.0
## Release criteria
NOT met. Score 83 <90. No Critical open; High-class items remaining: P4 (studio starts below ~560px), P9 (subtitles block) - Medium/High by round-2 rating, not explicitly accepted; V3 partial.
Remaining: (1) collapse Subtitles to one status row/expand-on-demand; (2) pull studio higher (compact run header/approval banner above it, or owner documents acceptance of P4/V3); (3) show list-row error text near the list on mobile; (4) capture post-Select screenshot proving Unsaved badge; (5) fade/affordance on clipped list; (6) hook tests + peaks cache.
