# Faraday design reference

The approved decisions of the frontend councils: design system, icons, words, quotations.

- **First council** (2026-11-24): design system architect, iconography, UX writing, cultural references, critical reviewer.
- **Second council** (2026-11-25): design director, UX architect, typography and content, frontend engineering lead,
  independent critic. Goal: minimal, flat, proportionate, consistent. Approved after three critic rounds (two 390px
  overflows found and fixed).

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
| Borrowed lines (Faraday, films, books, games) | `frontend/src/config/voice.ts` (text, source, link, moments) |

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

**Icon boxes:** one `.icon-box`, two sizes. No component draws its own.
- `.icon-box--sm`: 24px. Used for chips.
- `.icon-box--md`: 32px. Used for everything else: messages, Claude, the modal, steps and the journey.
- The 28px and 40px sizes are gone.
- `--halo` (3px) marks the current stage, and nothing else.

**Corner radii:**

| Radius | Value | Used for |
|---|---|---|
| sm | 4px | inside containers, chips' icon boxes, swatches, chart ends |
| md | 6px | controls, icon boxes, journey steps, pictures inside cards |
| lg | 8px | cards, media, players, Claude, the journey, the clips chart |
| xl | 12px | the modal only |
| pill | | badges and status pills only |

**Badges and status pills:** one recipe at `--h-xs` (24px). `Pill` (StatusPill.tsx) for any named state, `StatusPill` for the
status vocabulary.

**Chips** (`components/ui/Chip.tsx`): a 24px icon box, a value, a label. No box of their own.

**Buttons:** two heights, 32 (sm) and 40 (md); icons 16 and 20px. The 48px size is gone.

**Padding:** cards and messages 16px (`--card-pad`); compact messages 12px.

**No box inside a box:** the journey inside a card has no border; facts tables keep only their row hairlines.

**Borders:**
- `--rule`: every container.
- `--check-line`: anything interactive, or a marker you must see.
- Dashed: "not there yet" (empty, missing, pending, optional) and nothing else.
- 2px white: "needs you" (and errors), and only that.

**Shadows:** the popover only (`--elev-pop`), and the full-screen picture.

**Disabled:** always the `not-allowed` cursor.

**Motion:** fades and colour changes. The spinner and the working icon are the only rotations, and both stop under reduced motion.
Chevrons swap icons rather than rotate.

**Type:**
- **Geist** is the one interface family.
- **Fraunces**: "Curiosity, Illustrated." and quotations only.
- **Fira Code**: code, ids, times and the console only.
- **Sizes**: display, h1 (26–32), h2 20, body 16, small 14, note 13. Weight, not size, makes a heading: 600 for titles, 500 for labels, 400 for text.
- **Spacing and case**: one letter-spacing (`--ls-tight`, display and page titles). No uppercase labels.

**Mobile:** one-column grids are `minmax(0, 1fr)`, so no line widens the page. Start a Run's Back and Continue stick
to the bottom.

## Words

**House rules:**
- Title Case (Chicago) for every word the interface authors: labels, headings, buttons, tabs, badges, states, hints,
  placeholders, empty and error messages, and the few short sentences that remain (no full stop). The owner asked for
  Title Case throughout (second council).
- Not Title Cased: quotations (verbatim), "Curiosity, Illustrated.", your words, Claude's words, server error details,
  code and ids.
- Cut what the title already says: an empty state is its title; an explanation stays only when it carries real
  information (a size, a consequence, a time).
- American spelling, to match the template kit's own labels.
- No "please", "sorry" or "oops".
- No "System" or "Resource".
- No checkpoint codes such as CP0 to CP4 in the interface.

**Tone by moment.** One voice throughout: a lecturer at the demonstration table, plain, exact and a little warm.

| Moment | Register | Example |
|---|---|---|
| Welcome | invitational, brief | "Faraday uses the Claude account already on this computer." |
| Loading | calm noun | "Loading Your Runs" |
| Processing | present tense, the mechanism | "Claude Is Working: Renders and Voice Can Take Minutes" |
| Rendering | honest about time | a quoted line beside the spinner |
| Done | plain fact | "Script Approved: Next, Scene Plans" |
| Failure | what failed, what to do | "Full Size Did Not Render: Showing the Preview"; load errors are "Could Not Load X" |
| Critical | sober, cause first | "Claude Code Is Not Signed In" |
| Empty | the title alone | "No Changes Requested" |

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

## Quotations: Faraday's voice

The owner asked for as much of the interface's prose as possible to come from real references: Faraday, films, books
and games. "Curiosity, Illustrated." is never replaced.

The catalogue lives in `frontend/src/config/voice.ts`. Each line keeps its words, its source and the page it was
checked against, and each moment lists the lines it may show. `components/ui/Said.tsx` shows one line per visit, like a
game's splash text, followed by a quiet credit.

**Where lines go:**
- every non-compact system message, through its kind;
- the Home lead;
- the empty Home and empty run list;
- the Start a Run steps;
- Claude's Ready to Begin and Asks states;
- the full-screen render note;
- the finished final video;
- an empty checkpoint;
- empty change requests.

Buttons, labels and stage names stay plain.

**Splash lines** (`splash()` in `voice.ts`): Faraday's own words in the manner of Minecraft's title-screen splash text,
mixed now and then into loading, pending and rendering.

**Checking:** every line was checked word for word (2026-11-24).
- **Faraday:** *The Chemical History of a Candle* via the Wikisource API (the lecture numbers in `voice.ts`), and his 1849 journal via *Life and Letters*.
- **Films, books, games:** Wikiquote raw wikitext, linked per line.

**Copyright:** the films, books and games are short, credited quotations of famous lines. Faraday's words are public domain.

**Rejected, not verifiable on any fetched page:**
- **Dark Souls and Elden Ring screen messages** ("YOU DIED", "BONFIRE LIT", "Site of Grace Discovered").
- **Lines that don't match their pages:**
  - "I'm doing Science and I'm still alive";
  - "Let's work the problem, people";
  - Interstellar's "look up at the sky";
  - "My God, it's full of stars" (it is from the novel, not the film).
- **Lines with an unverified source:**
  - "The important thing is to know how to take all things quietly";
  - the "you may tax it" anecdote.

**Rejected for fit:** anything grim, profane or long (for example "Time to die", "science the shit out of this").

## Decided by the owner, kept against council suggestions

- **The journey strip showing every stage on Start a Run.** The council suggested removing it; it is kept.
- **The clips-per-scene chart.** It is kept, fixed rather than removed: bar length follows each scene's clip count, the legend shows only states present, and Failed has its own fill.
- **A rendered preview for every option, even near-identical ones.** These keep colours exact.
- **Home's sections** (second council kept them): hero with quick actions, Live Run, Usage Limits, closing line.

## Deferred by the second council

- A two-column run page from 1500px (the stage on the left; Claude, Next Step and the checkpoint on the right).
- Start a Run's "Your Run" summary on every step (the template steps need the width for previews).
- A fade at the edge of the scrolling strips (header nav, journey) on phones.
