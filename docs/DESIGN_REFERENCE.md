# Faraday design reference

The approved decisions of the frontend council: design system, icons, words, quotations.

**Members:** design system architect, iconography, UX writing, cultural references, critical reviewer.

**Approved:** 2026-11-24.

The code is the source of truth. This page says where each decision lives and why it was taken. Change the module,
then this page.

## Where decisions live

| Decision | Source of truth |
|---|---|
| Colours, spacing, type, radii, icon boxes, motion | `frontend/src/styles/tokens.css` (`--box-*`, `--h-xs`, `--halo`), `motion.css` |
| Icon for each meaning | `frontend/src/components/ui/icons.tsx` (one meaning per glyph) |
| States: word, icon, chart fill | `frontend/src/config/status.tsx` (`STATES`, `BUCKETS`) |
| System message kinds | `frontend/src/components/feedback/SystemMessage.tsx` (`KINDS`) |
| Stages: names, hints, icons | `frontend/src/config/stages.tsx` |
| Quotations | `frontend/src/config/quotes.ts` (text, source, link) |

## Icons

**Library:** Untitled UI Icons, `@untitledui/icons` 0.0.23.

- **One family:** 24px grid, a single line weight.
- **Licence:** the bundled LICENSE allows personal and commercial use and forbids redistributing the icons themselves. `package.json` says MIT, but the LICENSE text is the stricter one; follow it.

**Rules:**
- One meaning per glyph.
- Status icons always sit beside their word, never alone.
- An icon-only button always has an `aria-label`.
- Glyphs are half their box: 24 → 14, 32 → 16, 40 → 20.

**Meanings that used to collide and are now separated:**
- **Claude:** `MessageChatCircle`, used for Claude and nothing else.
- **Request a Change:** `MessagePlusCircle`.
- **Console:** `Terminal`, used for the console and nothing else.
- **Preview:** `Eye`.
- **Whole Look:** `Image01`.
- **Ticks:** `Check` is a control's tick; `CheckCircle` is the Done state.
- **Time and dates:**
  - `Clock` means Pending.
  - `ClockStopwatch` means a length.
  - `Calendar` means a date.
- **Problems:**
  - `Bell01` means Waiting for You.
  - `XCircle` means Failed.
  - `AlertTriangle` means Warning.
  - `AlertCircle` means Error.
- **Missing or blocked content:**
  - `Inbox01` means Nothing Here.
  - `SlashCircle01` means Unavailable.
  - `MinusCircle` means Not Supported.
  - `Lock01` means Access Restricted.

**Rejected alternatives:**
- **Lucide or Tabler:** an equivalent set, so switching costs a re-audit and fixes nothing.
- **Phosphor:** six weights invite drift.
- **Material Symbols:** a font, and a different voice.
- **A second family just for states:** mixed strokes would show plainly in a black-and-white interface.
- **The sparkle (`Stars02`):** a generic "AI" mark that carries no meaning.

## Design system

**Icon boxes:**
- `.icon-box--sm`: 24px. Used for chips.
- `.icon-box--md`: 32px. Used for steps, the journey and compact messages.
- `.icon-box--lg`: 40px. Used for messages and Claude.
- The 28px size is gone.
- `--halo` is the one ring for "current" and "asks".

**Corner radii:**

| Radius | Used for |
|---|---|
| sm | inside containers |
| md | controls, icon boxes, pictures inside cards |
| lg | cards, media and players |
| xl | modals and the two hero panels |
| pill | badges, status pills and journey steps |

**Badges and status pills:** one recipe at `--h-xs` (24px).

**Button icons:** scale with the button, at 16, 20 or 24px.

**Borders:**
- `--rule`: containers.
- `--check-line`: anything interactive, or a marker you must see.
- 2px white: "needs you", and only that.

**Disabled:** always the `not-allowed` cursor.

**Motion:** fades and colour changes. The spinner and the working icon are the only rotations, and both stop under reduced motion.

## Words

**House rules:**
- Title Case (Chicago) for labels, headings, buttons, tabs, badges and states.
- Sentence case, ending with a full stop, for sentences.
- American spelling, to match the template kit's own labels.
- No "please", "sorry" or "oops".
- No "System" or "Resource".
- No checkpoint codes such as CP0 to CP4 in the interface.

**Tone by moment.** One voice throughout: a lecturer at the demonstration table, plain, exact and a little warm.

| Moment | Register | Example |
|---|---|---|
| Welcome | invitational, brief | "Faraday uses the Claude account already on this computer." |
| Loading | calm noun | "Loading Your Runs" |
| Processing | present tense, the mechanism | "Claude is working. Renders and voice can take minutes." |
| Rendering | honest about time | "Rendering at 2560 × 1440. Thank you for your patience." (the owner asked for this line) |
| Done | plain fact | "Script approved. Next: Scene Plans." |
| Failure | what failed, what to do | "Full size did not render. Showing the preview." |
| Critical | sober, cause first | "Claude Code Is Not Signed In" |
| Empty | invite, one line | "No runs yet. Ask your first question." |

**One term per concept:**

| Concept | Term |
|---|---|
| What you make | a **run** |
| What the run produces | a **video** |
| A unit of the story | a **scene** |
| A rendered piece of a scene | a **clip** |
| Your decision on a stage | **Approve** (the checkbox is "Approve with Open Problems") |
| Asking for something different | **Request a Change** (sends a request) |
| The full conversation | the **Console** ("Open Console") |
| A state with nothing yet | **Nothing Here** when no data exists; **Not Made Yet** when it will be made later in the run |
| A state the server refused | **Unavailable** when the server answered with an error; **Connection Lost** when there was no answer |
| Finished work | **Done**, everywhere |
| A scene's name in the interface | **Scene 1**, never "s01" |

## Quotations

Only Michael Faraday's own words are used. They are public domain, checked word for word, and never shown on waiting, failure or error states.

| Where | Text | Source |
|---|---|---|
| Sign-in | "There is no better, there is no more open door by which you can enter into the study of natural philosophy, than by considering the physical phenomena of a candle." | *The Chemical History of a Candle*, Lecture I (1860); [Wikisource](https://en.wikisource.org/wiki/The_Chemical_History_of_a_Candle/Lecture_I) |
| Home, nothing in progress | "Nothing is too wonderful to be true, if it be consistent with the laws of nature" | Laboratory journal #10,040, 19 March 1849, in Bence Jones, *Life and Letters of Faraday* (1870), vol. II, p. 248; [Archive.org](https://archive.org/stream/lifelettersoffar02joneiala#page/248/mode/2up/search/wonderful) |

**Rejected:**
- **Game and film lines** (Minecraft, Portal, Dark Souls and others): none were verified against a primary source, short quotes from commercial works in product copy carry copyright and trademark risk, and they would read as in-jokes against this tone.
- **"The important thing is to know how to take all things quietly"** (attributed to Faraday): its source is unverified.
- **The "you may tax it" anecdote:** probably invented.
- **A quote in the footer:** it would add text to every page.

## Decided by the owner, kept against council suggestions

- **The journey strip showing every stage on Start a Run.** The council suggested removing it; it is kept.
- **The clips-per-scene chart.** It is kept, fixed rather than removed: bar length follows each scene's clip count, the legend shows only states present, and Failed has its own fill.
- **A rendered preview for every option, even near-identical ones.** These keep colours exact.
- **"Thank you for your patience"** in the full-screen waiting note.
