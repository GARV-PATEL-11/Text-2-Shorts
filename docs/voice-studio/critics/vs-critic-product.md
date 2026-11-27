# Critic 04 — Product Experience: Voice Studio (vs1 screenshots + VoiceStudio.tsx)

Verdict in one line: a competent, coherent, well-behaved voice picker with a real orb and player, but it still reads as a settings page with a nice hero. The reference board's calm "one stage" (orb, name, play, 4 controls, Back/Continue) has been replaced by a 3-zone dashboard where facts repeat and the primary action is ambiguous.

## Findings

### P1 (High) Voice name/attributes stated 4-5 times
- Evidence: 01-studio-desktop. "Raveena" appears in the list row, the H3 identity, the "Voice" group dl (Voice: Raveena), the preview line ("Hello! I'm Raveena"), the player label ("Play to Hear Raveena"), plus the Delivery hint ("Only the Engines Raveena Has..."). Language "en-IN" and "Indian Accent" appear in identity meta AND the Voice group (Language/Accent rows). Code L174-178 vs L188-192.
- Why: the Voice group is a read-only dl that duplicates the identity block directly above it; it looks editable (fieldset+legend, same chrome as Delivery/Provider) but has no control. Blueprint 9A says Voice = voice selection/language/accent, but the user selects those in the list/filters, so a group for them is redundant. Violates "removing everything that doesn't deserve to be there".
- Improve: delete the Voice fieldset entirely (identity block already carries it); fold language_code into identity meta only. Two groups (Delivery, Engine) remain, in one row beside/below the player.
- Validate: screenshot shows each fact once; count occurrences of voice name in the stage region <= 3 (list, identity, player aria).

### P2 (High) Provider/engine shown 3x, provider group has one non-control
- Evidence: identity "Engine: Standard"; Provider group "Provider: Amazon Polly" dl row; Voice Engine select; preview line "powered by Amazon Polly's Standard engine"; provider segmented control at the top of the studio says Amazon Polly again. Hint "Only the Engines Raveena Has in This Region." is filler and, with one engine, the select is a one-option dropdown.
- Why: Amazon Polly is stated three times above the fold; a select with a single option is a dead control.
- Improve: remove identity "Engine:" line (or remove the select's duplicate and show engine as a chip in identity); drop the Provider dl row; render the engine control only when voice.engines.length > 1, otherwise a quiet chip; delete the hint or make it a title/tooltip. Collapse to a "Delivery" group: Style, Speed, Engine (if choice exists).
- Validate: voice with 1 engine shows no select; with 3 shows select; "Amazon Polly" appears once.

### P3 (High) "Your Narrator" badge vs "Selected" button vs "Select Voice": three states for one fact
- Evidence: 01-studio: badge "Your Narrator" next to the name AND a disabled button "Selected" under it; list row also gets a tick (aria "Your Narrator"); 03-speaking: no badge, button "Select Voice"; mobile shows "Arthur ✓" tick in the list.
- Why: two words ("Selected", "Your Narrator") for one state, shown simultaneously; the disabled grey "Selected" button is the most dead-looking element on the page. Also vocabulary conflicts with the page-level "Save Template" and "Decide": it's unclear whether Select Voice commits, or Save Template does. Users will click Select Voice then wonder if they must also Save Template (and the approval bar "Decide").
- Improve: one state word. Keep the badge ("Your Narrator") and when selected replace the button with nothing (or a text-style "Change" is not needed); keep the button only when the browsed voice differs. Better: label button "Use as Narrator". Explicitly show a dirty state ("Not saved to template yet") near Save Template.
- Validate: only one indicator per state; usability test: 5 users asked "is Raveena your narrator now?" and "what saves it?"

### P4 (High) Three competing primary actions/stacked chrome above the studio push the studio below the fold
- Evidence: 01-studio: studio heading is at y=567 of a 1440x~1650 page. Above it: breadcrumb, H1, metadata row (Custom/1 Min/0 Scenes/Started), "Ready to Begin / Start Production" bar (white CTA), "Template" H2, "Waiting for You: Template / Decide" (white CTA with heavy white border), "Claude's Next Step 1", tab row with "Starter: Obsidian" chip and "Save Template" (white CTA). Four white-filled buttons on one screen: Start Production, Decide, Save Template, Select Voice.
- Why: the reference board has a single Continue; here the user cannot tell which to press. "Ready to Begin" says begin production while Template stage is "Waiting for You" and 0/7 approved: contradictory. At 1440x1000 (03-speaking) the studio hero is cut off after the identity block, orb partly beneath. Heading "Template" H2 then "Voice Studio" H3 then name H3: three heading tiers in 300px.
- Improve (page-level, affects the studio): demote Start Production to secondary while stage 0/7; merge "Waiting for You: Template / Decide" into the sticky footer action; fold "Claude's Next Step" into a one-line row (it already is collapsed; fine) but move it below the studio or into the rail; remove the redundant "Voice Studio" H3 inside a tab already labelled Voice Studio (a 2-3 sentence blueprint item 4 "avoid repeating navigation"). Single persistent footer: Back / Save Template.
- Validate: studio top at y<=380 on 1440x900; one filled-white button visible at a time except the focus action.

### P5 (Medium-High) Voice list is the largest visual mass and is a plain table; the orb is detached from it
- Evidence: 35 rows, each with a grey ball (dot), name, meta, a tiny grey triangle. 9 rows are visible, 57px each, 580px tall — taller than the hero. The row "dot" is a grey sphere pretending to be the orb, reading as clutter. The play glyphs are unicode "▶"/"❚❚" (mixed font rendering, light grey at low contrast, 16px) versus the Icon set used elsewhere (Check, header icons).
- Why: reference has a single list row with a selected check and a play icon, compact; here dots + glyphs + meta line double-line every row. A list that can't show more than 9 of 35 and no grouping/favourites means scanning is slow; search/filter exists but there is no sort or "Recommended" for a creator who wants a narrator for an explainer.
- Improve: single-line rows (name · accent, gender as tiny meta), replace sphere dot with a 2px left rail for current, use the app's Icon set for play/pause, use a compact density; surface 3-5 "Recommended for explainers" on top (data from `curated`; already in data.curated) so most creators never scroll 35.
- Validate: >=14 rows visible in the same height; time-to-pick task.

### P6 (Medium) Orb hero is lonely: arrows are 9px glyphs, name block floats right, no visual relationship
- Evidence: 01-studio: orb at x~815 with "‹" and "›" at 676 and 952 (tiny, ~10px, tertiary buttons with no visible target; effectively invisible). Identity is a separate column at x=996, so orb and name don't centre as in the reference (orb left, name beside, button below is similar, but the reference ties player waveform to the same row). The "‹ ›" invisibility means the "next voice and play" feature (a strong creator affordance) is undiscoverable; only the aria label explains it. On mobile the orb sits below the list, i.e. 12 voices-worth scroll before the hero, and "Selected" etc. follow; the stage is last on mobile (06-mobile: list y=1010-1240, orb y=1300).
- Improve: bigger circular chevron buttons with hover state; a short caption "Press the orb to hear a sample"; on mobile place hero first (task order per blueprint: "stack in task order"? blueprint puts discovery before stage, but reference places the stage first and a drawer/sheet for the list). Consider collapsing the list into a "Change voice" popover/sheet on mobile.
- Validate: first-time user finds the next-voice control within 5 seconds.

### P7 (Medium) Player: strong on function, weak on emptiness/typography
- Evidence: empty state 01: dotted line baseline, "00:00 / 00:00", a greyed "Replay" button and "1.15x" pill before any audio exists. Monospace timer + serif italic preview line + Inter UI + monospace "Ctrl `" Console chip = four type voices. Replay disabled-looking before playback is noise (blueprint 8 asks for empty state, which exists, but disabled Replay is not an empty state). 04-error: "Amazon Polly Did Not Answer..." is OK but speed pill still shows 0.9x and the timer 00:00/00:00.
- Improve: before first play show only the play button, the dotted line and "Play to hear Raveena"; hide Replay/time until audio loaded; keep error recovery. The speed pill duplicates the slider's value (Speed Fast 1.15x) in the group below: show it once (the player pill is more useful since it reflects the previewed audio; then drop the "Fast · 1.15x" from slider label or vice versa).
- Validate: empty state screenshot has <=3 elements.

### P8 (Medium) "Preview line" blockquote is unexplained decoration and collides with the floating Console chip
- Evidence: 01-studio: the italic serif quote "Hello! I'm Raveena. I'm speaking in a Storyteller tone, at Fast speed, powered by An[...]" is truncated at x=1215 by the fixed "Console Ctrl `" button overlaying the content (also in 03-speaking, y=945). At desktop the Console overlap hides text in every default state.
- Why: this is the actual sentence the voice will say; showing it is good (transparency) but it states settings the user just set (tone, speed, provider, engine: a fifth repetition) and the Console button obscures it. Console is a developer tool in a creator surface.
- Improve: set the preview line to a neutral sentence (or the run's actual first narration line, which is far more useful to a creator: "hear your script's opening"); move/auto-hide Console on this tab or give the page bottom padding so it never overlaps.
- Validate: no overlap at 1440 and 1024 widths; preview line pulls script line if present.

### P9 (Medium) Subtitles block is "complexity not hidden"
- Evidence: 01/04/06: Subtitles H2 + toggle "Show Subtitles" ON by default, helper copy "Shown With the Narration; Burned Into the Video in a Later Version" (admits the feature isn't implemented), then a nested tree: "Subtitles" disclosure containing three more disclosures (Style/Position/Word Highlighting) that look like labelled rows but are collapsed accordions. Heading "Subtitles" appears twice in a row (section title + tree root).
- Why: blueprint 10: compact status row when off, reveal when on. Here it's on, with 3 chevrons, and the copy tells the user it does not burn in yet: shipping a promise. Chevron-heavy nesting contradicts "avoid excessive nesting".
- Improve: a single row: "Subtitles — On · Clean Bar · Bottom Centre · Current-word colour [Edit]"; reveal editors inline on Edit. Remove the duplicate "Subtitles" root node. If burn-in isn't shipped, say so once in a tooltip.
- Validate: collapsed state <= 56px tall.

### P10 (Medium) Identity with Faraday: monochrome mostly holds, editorial voice is mixed with title case and glyphs
- Evidence: "Curiosity, Illustrated." only in footer; Title Case on every sentence ("Shown With the Narration; Burned Into..." "Only the Engines Raveena Has in This Region.") is the app's convention but reads shouty for body copy and is inconsistent with the sentence-case "Play to Hear Raveena" vs "Ready to Begin". The orb is a glossy 3D grey sphere with a drop glow: closest to skeuomorphic, whereas the reference orb is a flat-lit disc with ring; blueprint 5 says "no unnecessary glow". Provider tabs: "Google Cloud TTS | Coming Soon" shown disabled: advertising a non-feature (blueprint 9C says only if implemented).
- Improve: sentence case for helper copy; decide: either remove Google tab or keep a tiny "More providers soon" text; flatten orb highlight to a radial gradient with rim light; use an editorial serif for the name H3 (the quote already uses a serif; so serif for voice name creates the "studio" identity).
- Validate: design review against token sheet.

### P11 (Low-Medium) Layout coherence on tablet/mobile
- Evidence: 06-mobile: top nav clips ("Previous" cut off), the tab row wraps to two lines with the Console icon button floating beside "Voice Studio" tab; "Save Template" and "Starter: Obsidian" sit between tabs and studio, pushing studio down; the studio begins at y~950 of 2994. Orb appears after the whole list; the list has no max-height so the user scrolls 5+ rows then orb; "Selected" ghost button persists. Groups stack at full width (3 big boxes, 340px) where a 2-col or an accordion would do.
- Improve: on mobile hero first, then list inside a bottom sheet ("Change voice, 35"), Delivery as one compact card; sticky bottom bar (Back / Save Template).

### P12 (Low) Creator workflow gaps
- No Back/Continue footer inside the studio (blueprint 4 item 9, reference "Back / Continue"); the stage commit lives in the page header far above.
- No indication of unsaved selection: Select Voice sets look, but Save Template is separate; no toast or inline "Saved to template".
- No favourite/recent; acceptable per blueprint (no persistence model) but "Recommended" from curated is cheap.
- Selecting a row doesn't play (good, per blueprint 7), but the row's play button, orb and player play all exist: three play affordances for one preview. Orb + list row play are justified; the player's own big play adds a third. The player's play is the standard accessible one; consider making the orb the only hero play and the player the scrubber.

## What works (keep)
- Selecting a voice never autoplays; stale preview state is signalled; real audio-reactive orb and real waveform (blueprint 14).
- Provider segmented control, discovery search+filters are compact and consistent with blueprint 7; counts update; empty-search recovery exists.
- Error state (04) has a clear recovery action.
- Monochrome palette respected; focus rings visible; white active states match the reference.

## Comparison with the reference board
Reference: one centred stage (orb + name + verified tick + 1 line meta + play + waveform + time), a single row of four compact controls (Style, Speed, Engine, Subtitles) and Back/Continue. Faraday now: three columns, list first, nine rows of voices as the heaviest element, three fieldsets of which one is read-only facts, subtitles a separate section of its own. It is richer in function (list, filters, error states) but fails the "removing everything that doesn't deserve to be there" principle: roughly 30% of visible text is repeats.

## Overall weighted score (blueprint table)

| Area | Weight | Score /100 | Weighted |
|---|---:|---:|---:|
| Visual hierarchy | 15 | 62 | 9.3 |
| Typography | 10 | 70 | 7.0 |
| Spacing and alignment | 10 | 74 | 7.4 |
| Monochrome consistency | 10 | 82 | 8.2 |
| Interaction and usability | 15 | 68 | 10.2 |
| Animation quality | 10 | 80 | 8.0 |
| Responsive behavior | 10 | 62 | 6.2 |
| Accessibility | 10 | 78 | 7.8 |
| Component consistency | 5 | 72 | 3.6 |
| Performance | 5 | 80 | 4.0 |
| **Total** | 100 | | **71.7 / 100** |

Below the 90 release bar. Highest-yield fixes: P1+P2+P3 (delete redundancy), P4 (one primary action, studio above the fold), P9 (collapsed subtitles row), P6/P11 (mobile order and discoverable next/prev).

Counts: High 4 (P1-P4), Medium-High 1 (P5), Medium 5 (P6-P10), Low/Low-Medium 2 (P11-P12); Critical 0.
