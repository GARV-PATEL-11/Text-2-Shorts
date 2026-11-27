# Critic 01 - Visual Design: Voice Studio (screens vs1/*.png, before/*.png)

Screenshot names: 01 desktop, 02 filtered, 03 speaking, 04 error, 05 tablet 820, 06 mobile 390.
CSS refs: frontend/src/styles/components.css (CC), tokens.css (T).

## Findings

**V1 - Console dock covers content (High)**
- Observed: the fixed "Console Ctrl `" button (x1214-1404) sits on the sample line in 01 ("powered by An..." is cut off) and 03 (line cut at "Amaz"). In 05 it sits on the row play button for Amy. In 06 it is an icon beside the tabs.
- Evidence: CC:703 only reserves bottom padding at the end of the page (`.page:has(.console-dock)`). CC:704 is `position: fixed`, so the dock overlaps whatever scrolls under it. The `.studio__line` text runs the full width, so it always hits the dock's right edge.
- Why it matters: it hides real content mid-scroll and looks like a layout bug. The old screen had the same defect (before/01 covers the Voice Engine select); the redesign did not fix it.
- Fix: make the dock a 40px icon-only button at the viewport corner, or dock it into the footer or header. Alternatively cap `.studio__line` and the player at `calc(100% - 200px)` on the right. The simplest option is to move Console into the sticky header, which also removes the z-index fight with V2.
- Validate: scroll to each section at 1440, 820 and 390. No element's bounding box should intersect the dock box. Add a Playwright intersection check.

**V2 - The sticky "Waiting for You" bar hides the hero (High)**
- Observed: in 04 the 2px white-bordered Decision banner is pinned at y=60-120 and covers the top of the page. The tab strip and the voice name ("Arthur" is cut in half) and the top of the orb are hidden behind it. The orb and name are the studio's identity, and they are clipped.
- Evidence: 04-error.png, y 60-120.
- Why it matters: the most prominent object on the page (the strongest border, a white button) is the one that hides the content it is asking about. It is also not the same height as the in-flow version in 01.
- Fix: shrink the sticky state to a 40px slim bar with a 1px border, or only pin it once the studio is below the fold. Add `scroll-margin-top` to the studio sections.
- Validate: screenshot after anchor scroll. The voice name must be fully visible below the bar.

**V3 - Too many competing white-fill elements; hierarchy is inverted (High)**
- Observed: in 01 there are 5 solid-white primaries (Start Production, Decide, Save Template, Play, plus Select Voice in 03). The 2px white-outline Waiting banner is the loudest box on the page. The studio's own title, "Voice Studio", is a small ~16px heading (y567), much smaller than the 32px voice name or the 32px page title. The blueprint says white is used selectively.
- Evidence: 01 and 03. The Play button (40px white square) is not the visual focal point of the studio.
- Why it matters: the eye lands on the run chrome (banner, Start Production), not on the voice preview, which is the job of this screen.
- Fix: inside the studio, make Play/Select the only filled-white elements. Demote Save Template to an outline button. Reduce the banner border to 1px `--check-line`. Give the Play button more size, such as 48px.
- Validate: squint test (blur the screenshot and check that the orb and Play remain the brightest masses). Count `.btn--primary` elements per viewport (target <=2).

**V4 - The orb is under-scaled and flat, and the speaking state is not distinguishable (High)**
- Observed: the sphere is about 125px in a column 300px wide, with `<` `>` arrows floating ~140px away on each side (x676 and x952). It has a static gradient and no visible ambient glow, rings or halo. The speaking screenshot (03) shows an orb identical to idle (01) with no ripple, glow or ring. The only difference between states is in the player waveform.
- Evidence: VoiceOrb.tsx:11 `size=220` and :32 `radius = size*0.28`, so the sphere is ~123px and the remaining canvas is empty padding, which pushes the arrows apart. 01 vs 03 orb region (x750-880, y655-780).
- Why it matters: blueprint section 6 calls it the "signature visual identity". It reads as a stock gradient circle, and the states (previewing, error, processing) are not visible in stills.
- Fix: draw the sphere at ~0.36*size, or use size=260 and a radius of 0.34. Add a thin 1px ring (`--field-line`) at rest, and make previewing show a bright ring plus amplitude-driven stroke. Error: a dashed ring (a monochrome error cue). Pull the arrows in, to ~16px from the sphere.
- Validate: capture orb crops at idle, speaking (mid-playback), paused, processing and error. Each must be recognizable without a caption. Check with `prefers-reduced-motion`.

**V5 - Player idle/disabled state is almost invisible (Medium)**
- Observed: in 01 the waveform is a 1px dotted line at y877 with no visible bars. "Replay" is a grey ghost button with disabled-grade contrast. "00:00 / 00:00" is mono mute. The Play button (white) is the only readable element. In 03 the bar fills the full width with bright bars and Replay brightens, so the idle and speaking states differ in density, brightness and height: the card is ~82px tall in 01 and ~66px in 03/04, and the white Play button jumps from y869-909 to y861-901.
- Evidence: CC:664-674, 01 vs 03 vs 04 region y848-930. Time and speed pill column x shifts (1137 in 01, 1128 in 04) because the auto grid columns resize with the Replay/Try Again label.
- Why it matters: the card jumps when state changes, and an empty player looks broken. The speed pill "1.15x" is a non-interactive pill that looks like a button and repeats the slider's value.
- Fix: fix the card height (`min-height`) and give the idle waveform a synthetic flat bar row at `--field-line` rather than dots. Give the time/Replay/speed columns fixed widths (`grid-template-columns: 40px 1fr 96px 88px 56px`). Show the speed as plain mute text, or drop it.
- Validate: record the Play button's bounding box in the idle, loading, playing and error states; the delta must be 0 px.

**V6 - Voice and Provider cards repeat information and are unbalanced (Medium)**
- Observed: the "Voice" fieldset (Voice/Language/Accent) repeats the identity block directly above it (name, "Female · Indian Accent · en-IN"). It is a read-only list in a bordered card, half empty (bottom 70px blank in 01), next to the two interactive cards. "Provider: Amazon Polly" repeats the provider switcher at the top. In 05, facts are right-aligned ~600px away from their labels.
- Evidence: 01 y1020-1205; 05 y1723-1830; CC:676-681.
- Why it matters: the blueprint asks for "avoid excessive card nesting and unnecessary containers". 3 bordered cards x 3 legend-cut borders is a heavy frame for a small amount of content, and the static card gives it the same weight as controls.
- Fix: merge Voice and Provider into one "Voice" card with facts on a single line or drop it, and keep Delivery as the only interactive card. Left-align the facts (dt/dd in a 2-col grid, label width 96px).
- Validate: compare the information count against the hero block; the cards should have no duplicated strings.

**V7 - Heading and legend inconsistency (Medium)**
- Observed: section headings use an h2 with a bottom rule ("Voice Studio", "Subtitles"), while the three cards use `<legend>` tabs that cut through the border at 14px/600. Title Case is applied to sentences ("Only the Engines Raveena Has in This Region.", "Play to Hear Raveena", "Shown With the Narration; Burned Into the Video in a Later Version"). The Subtitles section has a "Subtitles" disclosure nested inside a "Subtitles" section (01, y1265 and y1362). Labels there are all bold.
- Evidence: CC:678, 01 y1265-1500; blueprint: "avoid making every label bold".
- Why it matters: it reads as three typographic systems, and the Title Case sentences look machine-generated.
- Fix: use one pattern (an uppercase 12px mute eyebrow label above each card, or the h2 pattern). Sentence case for sentences and Title Case only for short labels. Remove the duplicated "Subtitles" disclosure row (this is pre-existing, so it can be deferred). Use 500 weight for row labels and keep 600 only for headings.
- Validate: grep the rendered DOM text for 3+ capitalized words ending in a period.

**V8 - Spacing rhythm and alignment of the hero (Medium)**
- Observed: the identity column starts at x996 while the player and cards start at x656, so there is a ~340px dead zone left of the name, and the orb is not aligned to either edge (the left arrow at x676 does align to the 656 edge by accident). The gap between the hero and the player is 52px (y795 to 848), while player to line is 12px, line to cards 24px, and cards to Subtitles 60px: four gaps at four values, where `--s-5` is intended (CC:620 gap 20px, but heading margins vary). The list column ends at y1237 and the cards at y1205, so the bottoms don't align.
- Evidence: 01 coordinates above.
- Why it matters: the hero feels like two floating islands instead of one composition.
- Fix: make the hero a 2-col grid with the orb column sized to its canvas (e.g. `grid-template-columns: 220px 1fr`) so identity starts ~24px after the orb. Normalize the gaps to 24px.
- Validate: overlay a grid. Left edges of the orb block, player and cards must coincide.

**V9 - Contrast of low-emphasis and disabled elements (Medium)**
- Observed: "Google Cloud TTS / Coming Soon" is `--mute` at opacity 0.7 on a veil with a dashed border, about 4:1 or below (CC:624). The sidebar "Optional" and "Reshuffle" mutes are similar. The list's meta (13px `--mute` #a3a5ad) is acceptable (8:1). The `<` `>` arrows are ~10px glyphs at mute. The range scale ("0.9x ... 1.15x", 13px mono mute) is small. The disabled-looking "Selected" button (grey on grey border) doubles as a status, so a state indicator looks disabled.
- Evidence: 01 x1030-1400 y560; x996-1117 y756-795.
- Why it matters: WCAG 4.5:1 for text is not met by the `.studio__provider--soon` at 0.7 opacity.
- Fix: drop the opacity and use `--mute` directly (8:1) with the dashed border to signal unavailability. Render "Selected" as a check badge (outline, `--fg`), not as a disabled button. Make the arrows 28x28 icon buttons.
- Validate: axe color-contrast run on the page; manual contrast calculation for each text token pair.

**V10 - Off-token literals and `backdrop-filter` in a monochrome system (Low)**
- Observed: `.studio__dot` uses hard-coded hex (#ffffff, #a3a5ad, #3a3b42) at CC:643 rather than `--fg`, `--mute`, `--field-line`. The Coming Soon pill uses `backdrop-filter: blur(6px)` (CC:624) over a flat background, which has no visible effect. 24 identical sphere dots in the list repeat the orb at a smaller size and add noise (every voice looks the same).
- Why it matters: the tokens are the single source of truth, and a test enforces the palette. The dots carry no information.
- Fix: use var() tokens. Use a dot only to mark the current or playing row (filled vs hollow ring), or encode gender with a letter. Drop the blur.
- Validate: grep CC for `#[0-9a-f]{3,6}` in the studio blocks (expect 0).

**V11 - Filtered state leaves a dead column and loses the current-voice context (Medium)**
- Observed: in 02 the filter "Female + British Accent" returns 2 rows, and the left column collapses to y836 while the right column keeps going, leaving a ~400px empty area under the list. The current narrator (Raveena, Indian) is not in the filtered list, so there is no highlighted row, and nothing says why the hero shows a voice not in the list. The filter row (All/Female/Male + accent select) has two different control styles: a segmented pill (r-md) next to a native select with an OS chevron.
- Evidence: 02-filtered.png x332-632 y836-1000; CC:629,633.
- Why it matters: the state change looks broken, and the native select breaks the monochrome theme (its popup is OS-styled).
- Fix: pin the current voice as a row above the list ("Current") when it is filtered out. Add an empty-state min-height or place a "Clear filters" link. Style the select with a custom chevron (`appearance:none` + an SVG background).
- Validate: filter to 0, 2 and 35 results, and compare the column heights; the current voice must always be visible.

**V12 - Tablet/mobile: the list is placed before the hero, and the tablet capture looks truncated (Medium)**
- Observed: at 820 (05) and 390 (06) the order is the filters, then 5 list rows, then the orb. The hero appears ~1180px down, so the first thing a user sees is a list. At 820 the cards stack full width with labels and values ~600px apart. In 05 the page content ends mid-Delivery card ("0.9x ... 1.15x" is clipped at y1990) followed by ~500px of blank canvas, with Provider and Subtitles missing. This may be a screenshot artifact or a real clipping bug, so it needs verification. The mobile header nav is truncated ("Previous") and the tab row wraps into two lines with the Console icon floating at the right.
- Evidence: 05-tablet.png y1150-2000; 06-mobile.png y1300 and y2000.
- Fix: on <=900px put the hero (orb, name, Play) first and the list after it (or in a collapsible "Choose a voice" section). At 820 use a 2-col grid for the cards (the 1180px breakpoint at CC:688 is too eager). Confirm the clipped render.
- Validate: re-capture at 820 with a full-page scroll and check that the DOM height equals the screenshot height.

**V13 - Misc polish (Low)**
- Row play glyphs are text "▶" in mute (x616) while the player uses an SVG icon and a pause glyph is rendered as "❚❚" (03 x616 y922): mixed icon styles and sizes. The sample line is Fraunces italic 14px in `--fg-2`, a third family beside Geist and Fira Code; it is legible but the left rule (2px `--rule`) is nearly invisible. Mono time at 13px beside the Geist 14px adds a baseline mismatch. The row's `is-current` fill (`--veil-1`, 6% white) is too subtle to see in 03 against the rest.
- Fix: use the shared icon set, and raise the current-row indicator to a 2px left bar in `--fg`.

## What is better than before
The before screenshots had a pill-chip accent bar, an unbalanced wide hero with the orb floating far from the name, a text-only play button and a cramped 6-field toolbar with truncated selects ("Patrick · US Accen"). The redesign adds a searchable list, a clear 3-card layout, tidy fields and a clearer player. Core hierarchy is improved (name 32px, meta 14px mute), and there is no color anywhere.

## Scores (0-100)
- Visual hierarchy: 62 - the voice name is strong, but the white CTAs, the sticky banner and the dock compete with, or cover, the studio, and the orb is under-scaled.
- Typography: 70 - a clean Geist scale with sensible sizes, but Title Case sentences, three families, a bold-everything Subtitles block and small 13px mono scales.
- Spacing and alignment: 58 - four different vertical gaps, the hero's islands are misaligned, a dead column when filtered, the dock overlap, and the player's width changes.
- Monochrome consistency: 80 - strictly neutral, with only a few off-token literals, a no-op blur and a 0.7 opacity that breaks the contrast.
- Component consistency: 60 - the player jumps between states, the legend cards and h2 headings use different patterns, a native select next to custom controls, mixed icon styles, and a status shown as a disabled button.

## Counts
Critical 0, High 4 (V1, V2, V3, V4), Medium 7 (V5, V6, V7, V8, V9, V11, V12), Low 2 (V10, V13).
