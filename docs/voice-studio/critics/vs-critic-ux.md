# Critic 02 — UX and Interaction (Voice Studio)

Scope: blueprint 4,7-10,12; screenshots vs1/01-06; VoiceStudio.tsx, AudioPlayer, VoiceOrb, Waveform, usePreviewPlayer, useTemplateEditor, e2e/audio.e2e.mjs, components.css. The ‹ › autoplay deviation is accepted and not scored.

## Findings

**U1 High - Main player button says "Pause" but restarts a new preview when stale.**
Evidence: AudioPlayer label uses `state === "playing"` only; `main()` calls `onPlay()` when `stale`. After changing speed/style/voice mid-playback, the old audio keeps playing, the button reads "Pause <name>", and pressing it generates and plays a different preview. The orb handles this case (`playing && !stale`); the player does not.
Why: the control lies about what it does, and the old audio keeps playing beside a "Settings Changed" message.
Improvement: derive one `effectiveState`. When stale, the label is "Play <name> with new settings" and the old audio is paused or stopped when a setting changes (`player.stop()` in `set`).
Validation: e2e - play, move the slider, assert the button name is not "Pause" and the old audio is paused.

**U2 High - On tablet/phone, list previews give no visible feedback.**
Evidence: 05/06 stack list -> orb -> player. List max-height is 280px (css:690) and the player is about 900-1100px below the list. A row's play button starts loading, errors or plays out of sight. Rows show no loading or error state, and the row Play button is not disabled while loading.
Why: the error alert and "Generating..." text are off-screen, so the preview looks dead.
Improvement: per-row loading spinner and error icon; on narrow widths, a sticky mini-player; or put the hero above the list.
Validation: 390px e2e - press a row preview with a 503, assert a visible error in the viewport.

**U3 High - Browse vs select is blurred.**
Evidence: the narrator is marked by a small tick beside the name (06, "Arthur ✓"), and the browsed row only by a subtle background and dot. `selected` requires voice+engine+speed+tone, so changing speed on the narrator voice makes the "Your Narrator" badge vanish and the button revert to "Select Voice" while the list tick stays. Nothing says "browsing X, narrator is Y" when they differ. "Selected" is also disabled-grey, which reads as unavailable.
Why: users can't tell what will be used or what pressing Select changes.
Improvement: a persistent "Narrator: Arthur - Neural - Slow" line near Select; label the action "Use This Voice" / "Update Narrator" when only settings differ; a distinct "Previewing" tag on the browsed row.
Validation: usability check, plus e2e assertion of badge text after a speed change.

**U4 Medium - Select Voice does not persist; Save Template is far away.**
Evidence: e2e requires a separate "Save Template" click before a reload (lines 119-140). In 01 Save sits in the tab header above the Voice Studio, and "Selected" appears immediately. No unsaved indicator near the voice.
Why: leaving the page after "Selected" loses the choice.
Improvement: a "Not saved yet - Save Template" hint or dirty dot beside Selected, or a sticky save bar.
Validation: select, navigate away, assert a confirm or indicator.

**U5 Medium - Voice change makes the message say "Settings Changed" and the old voice keeps playing.**
Evidence: picking a row calls `set` and does not stop playback; the message is a fixed "Settings Changed: Play to Hear Them". Stale audio of the previous voice continues. The blueprint asks for no overlap or stale playback on switching.
Improvement: stop on any browse change; name what changed ("Voice changed", "Speed changed").
Validation: e2e - pick a row while playing, assert paused.

**U6 Medium - Floating UI covers content.**
Evidence: 01 - the Console launcher overlaps the preview line text ("powered by An..."); 05 - the sticky "Waiting for You: Template" banner covers the orb/name; 06 - Console covers the Amy row's play button. These are shell elements, but they collide with Voice Studio controls.
Improvement: reserve bottom padding; make the banner non-sticky or collapse it; keep the Console launcher clear of interactive rows.
Validation: screenshot diff at 3 sizes.

**U7 Medium - ‹ › arrows are tiny and give no context.**
Evidence: 01/06 glyphs are about 8px and faint on a 124px orb. There is no indication of next/previous voice name or position (e.g. "5 of 35"). `move` when the browsed voice is not in the filtered list: index falls back to 0, so "next" skips pool[0].
Why: low discoverability for the chief browse action; autoplay on each press fires a Polly request with no debounce.
Improvement: 44px buttons with larger chevrons and "Arthur 5/35"; handle the not-in-pool case; debounce or abort-aware requests.

**U8 Medium - Error state outlives its cause.**
Evidence: `state==="error"` persists after the user picks another voice or changes a setting; the player still shows the old error and "Try Again" for a voice no longer shown. The orb in the error state has no recovery hint.
Improvement: clear the error on `set`/voice change.

**U9 Medium - Redundant, read-only Voice/Provider groups.**
Evidence: name, language and accent appear in the hero meta and again in the "Voice" fieldset (a `<dl>` in a fieldset with no controls); Provider is shown in the tab and the Provider group; engine appears in the hero and the Provider group. The blueprint puts selection/language/accent in group A as controls, not repeats.
Why: cognitive load and misuse of fieldset semantics (SR announces a group with no inputs).
Improvement: drop the Voice group (or make it the filter controls); use plain headings instead of fieldsets for read-only data.

**U10 Medium - Accessibility semantics.**
- Orb: `aria-pressed` plus a changing "Play/Pause" label gives a double state; the label is a long sentence with key instructions (VoiceOrb:118; VoiceStudio).
- `aria-label="Position"` on the time `<span>` has no role, so it is ignored by AT.
- No live region announces the new voice after ‹ › or the arrow keys; the name `<h3>` changes silently while focus stays on the orb. ArrowLeft/Right on the orb is an undocumented, non-standard key mapping that also autoplays.
- Disabled-on-press: the main Play button gets `isDisabled` during loading, so keyboard focus is dropped; the "Selected" button is disabled the instant it is pressed, which also drops focus.
- Google provider: `aria-disabled` with `tabIndex=-1` is unreachable by keyboard and its explanation lives only in `title`; the group is outside the studio section and is not a tablist.
- Waveform slider: `tabIndex=-1` and valuemax 0 before audio; only +/-10% arrows, no Home/End; it stays interactive on stale audio (duration is kept) while the bars are blank.
- Speed slider accessible name includes the value and `aria-valuetext` repeats it; the range has 5 stops with no ticks or presets despite a text scale.
Improvement: use `aria-disabled` plus focusable for loading; add `aria-live=polite` voice announcement; fix names/roles; keep Home/End.
Validation: axe plus a screen-reader pass (NVDA/VoiceOver) and a keyboard-only e2e walk.

**U11 Low-Medium - Filtering edge cases.**
Evidence: filtering can hide the browsed voice; the hero still shows it with no row highlighted and no explanation. "35 Voices" is a status live region that re-announces on every keystroke. No empty-state advice beyond "Clear the Search" (fine). No match highlighting, no favorites (acceptable per blueprint).

**U12 Low - Subtitles.**
Disabled state shows the compact note and the body is `inert`/`aria-hidden` (good; values kept, e2e verified). But the rollout body probably still reserves layout until the transition ends, and the note text "Burned Into the Video in a Later Version" implies a promised feature in a control that does nothing visible, which the blueprint says not to present as functional. The tree headers ("Subtitles" nested under the "Subtitles" section) repeat. When off there is no summary of the current style (e.g. "Clean Bar, Bottom Centre") for reference. The toggle is in the section header and its label is clear.

**U13 Low - Loading and empty states.**
"Loading the Voices..." is bare text with no skeleton; layout jumps on load. The empty-preview state ("Play to Hear X") is good. Row "Preview" icons are ▶ glyphs; the label includes the name (good).

**U14 Low - Responsive.**
01 desktop fine. 05 tablet and 06 mobile: the 35-voice list is a nested scroll box (280px) that traps scroll on touch; the hero and settings stack well; a 3-up groups layout collapses properly. Mobile tab bar wraps to two rows with the Console button beside it (06). The tablet shot is truncated at "Speed" (capture artifact; unverified below).

## Strengths
Real audio-driven waveform/progress, a stale-preview concept, a clear error with Try Again (alert role), empty player copy, 7 engines driven from data, search/gender/accent filters, subtitles inert when off with values kept, e2e coverage of all main flows at three viewports.

## Scores
- Interaction and usability: 72 - the core flow works and is e2e-covered, but U1 (lying Pause), U3 (browse vs narrator) and U4 (unsaved) hurt the find->hear->tune->select->save loop.
- Accessibility: 64 - good labels on rows, slider valuetext and alert/status roles, but focus loss on disabled buttons, a silent voice change, an ignored time label, an unreachable Google tab and a double-state orb.
- Responsive behavior: 70 - stacks cleanly with no horizontal scroll, but the player/feedback sits far from the list previews, the nested scroll list, tiny ‹ › and floating overlays.
