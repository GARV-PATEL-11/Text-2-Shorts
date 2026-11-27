# TTS, Audio, Subtitles and Frontend Refinement (2026-11-27)

Phase by phase, as asked. Screenshots: `tts-refinement-2026-11-27/`. Nothing committed.

## 01 · Existing TTS implementation and UI (inspected)

- Provider: `brief.tts` (polly | google), chosen on its own step in Start a Run (two radio cards); fixed for a run.
- Voice: the `voice` element, 7 curated options ("US Female, Warm" …), each one Polly voice + engine and one Google
  voice, shown as large radio cards. Speed: 5 options (0.9–1.15×). Tone: 7 options. Custom voices were removed in 0.36.
- Hearing a voice: a "Hear the Voice" button on the run page only, one fixed sentence.
- Subtitles: an on/off switch, but its style, position and highlighting were always shown.
- Start a Run: "All Changes Saved · 15:32" had a row of its own.

## 02 · AWS credentials and Polly access (verified, no secret shown)

| Check | Result |
|---|---|
| Where the app reads credentials | `.env` (loaded by `app/config.py`), updated today 15:08; keys in the environment win over profiles |
| `~/.aws` default profile | **No usable credentials** (last changed 15 Oct): everything relies on `.env` |
| Authentication (STS) | OK: an IAM user, region `us-east-1` |
| `polly:DescribeVoices` | OK: 119 voices; standard 60, neural 63, generative 55, long-form 6; 35 English |
| `polly:SynthesizeSpeech` | OK for every engine (Matthew, Ruth, Joanna, Kajal: 11 samples, valid MP3s) |
| SSML `prosody rate` on generative | OK (what speed uses) |
| Word speech marks | OK (what subtitles time from) |
| Playback in the site | OK: real previews played in Chrome (e2e) |
| Errors | missing credentials, refused credentials, missing `polly:DescribeVoices` / `polly:SynthesizeSpeech` and no network each give their own plain sentence (tests) |

Finding to decide on (not changed): the server passes the `.env` AWS keys into the run's Claude Code session
through its environment, so anything that session runs can read them with `env`. It predates this work.

## 03 · Polly voices, engines and settings (audited)

35 English voices across 9 Englishes (US, British, Australian, Indian, Irish, New Zealand, Singaporean, South African,
Welsh), each with only the engines Polly gives it in `us-east-1`. Live from Polly, kept for the server's lifetime.

## 04 · Provider selection

The Audio & Subtitles header holds the switch: **Amazon Polly** (on) and **Google Cloud TTS** behind frosted glass,
dashed, dimmed, "Coming Soon", not focusable or pressable. Start a Run's provider step is gone. A run or draft set up
for Google says it speaks with Polly for now.

## 05 · Dynamic previews

One template on the server (`app/web/voices.py`): "Hello! I'm {agent}. I'm speaking in a {tone} tone, at {speed} speed,
powered by {provider}'s {engine} engine." Filled with the chosen voice, tone, speed and engine, spoken through the
narration's own Polly path, cached on disk per combination. The page shows the same filled line, plus the voice's
name, gender, language and engine. No sentence is written per voice.

## 06–07 · Character selection, speed, auto-play

The voice cards are replaced by one voice at a time: a monochrome sphere whose glow follows the voice's loudness,
‹ › (and ← → keys) to move, the name, speed − 1.08× Brisk + right under it, then engine and tone. Moving to a voice,
or changing speed, tone or engine, plays it; the previous preview stops first (one audio element). Any English voice
and engine can be saved: the template's own option when it is one, else a custom `Voice:engine`
(validated: a Polly voice name and a real engine, nothing else).

## 08 · Conditional subtitles

Style, position and highlighting roll down only while Subtitles is on and roll up to nothing when it is off. Their
values are kept and come back.

## 09 · Space

"All Changes Saved" sits on the steps line; its row is gone. Run pages keep room so the console dock never covers
their last line.

## 10 · Console

A Console button docked bottom-right on every run page; Ctrl+` opens and closes it from anywhere on the page; Home's
live run has "Open Console", which lands on the run with the console open.

## 11 · Standardisation

- Typography and sizes: almost everything was already on the design tokens; 10 leftover literals now use tokens
  (1–4 px changes).
- Title Case: about 90 interface strings, every quotation (rendered in Title Case), the console's own wording and its
  server notes ("Turn Finished.", "Stopped by You. …").
- Unchanged on purpose: Claude's and tools' words, file names, commands, user text, voice names.
- Nothing was removed as bluff: nothing was clearly redundant.

## 12 · Tests

| Suite | Result |
|---|---|
| Python (`uv run pytest -q`) | **265 passed** (new: `tests/test_voices.py`, 8 tests) |
| Frontend unit (`npm test`) | **14 passed** (new: `voice.test.ts`) |
| Console e2e | **passed**, 18 states (Ctrl+` added) |
| Audio e2e with real Polly (`e2e/audio.e2e.mjs`) | **passed**: provider lock, 35 voices, auto-play, one at a time, speed, tone, engines, subtitles roll, voice saved and shown after reload |
| ruff, format, tsc, build | clean |

## Critic review and outcome

A fresh reviewer: 0 Critical, 1 High, 10 Medium, 12 Low, 1 Enhancement.

- **Fixed:**
  - G1 High: my comment on one line had swallowed the draft's notes and save time. Restored.
  - Missing or unsupported saved voice or engine is now shown, not swapped silently.
  - Atomic preview cache.
  - Plain Polly permission messages.
  - Audio URLs released.
  - Inner buttons keep their keys.
  - Honest toggle buttons instead of fake radios.
  - Speed under the name.
  - Google-set runs told.
- **Deferred:**
  - G6, preview rate limit: every combination is cached once and there are a fixed number of them.
  - Low items.

## Remaining

- The `.env` keys reach the run session (above).
- `~/.aws` default profile is empty: anything that runs without `.env` (outside the server) has no AWS access.
- Google Cloud TTS stays in the backend and the CLI (`--tts google`); only the website locks it.

## Voice Studio redesign (same day, from the mockups)

Voice as an experience, one reusable studio (`components/voice/`: `usePreviewPlayer`, `VoiceOrb`, `Waveform`; the
studio itself in `pages/run/stages/look/VoiceStudio.tsx`, used by Start a Run and the run's Template stage).

- **Living orb:** a monochrome blob drawn on a canvas and fed by the Web Audio AnalyserNode, so it moves with the real
  voice. It breathes when idle, spreads rings while a preview loads, deforms with six frequency bands while speaking,
  floats when paused and brightens on hover. It is the play and pause button. With reduced motion it is a still sphere.
- **Layout:**
  - Accent chips at the top; the orb with ‹ › beside it.
  - The voice's name, "Selected" badge, "Female · Singaporean Accent", and speed "− Natural · 1.0× +".
  - The preview card: the real waveform decoded from the MP3, seekable, with Preview Voice / Pause / Resume.
  - The sentence the voice speaks.
  - One control panel: Voice, Speed slider, Speaking Style, Voice Engine, Provider, Select Voice.
- **Browsing versus choosing:** moving between voices plays them; only **Select Voice** makes one the narrator.
- **Wording as asked:**
  - Audio & Subtitles → Voice Studio; Tone → Speaking Style; the engine → Voice Engine.
  - Play Sample → Preview Voice; Use This Voice → Select Voice.
  - "Natural · 1.0×"; "Singaporean Accent".
  - Subtitles have their own section with a Show Subtitles switch.
- **Deliberately not taken from the mockups:**
  - Three.js or WebGL: a 2D canvas does it with no dependency.
  - Green accents: monochrome only.
  - The handwritten "Listen to your selected voice" arrow and the "Natural, Expressive Voice ✓" checklist: no bluff.
  - CSS-scaled rings: the motion contract forbids scale(); the canvas draws them.
- **Tests:**
  - `e2e/audio.e2e.mjs` with real Polly: provider lock, accents, orb play with a decoded waveform, move-plays, speed
    and style replay, engines, Select Voice, subtitles roll, saved after reload, phone width.
  - Frontend unit tests: 15. Python: all pass. Console e2e: passes.
- **Review:** this round had no independent critic pass; I checked it in the screenshots and tests only.

## Delivery SSML (same day)

What each Polly engine accepts (probed live in us-east-1 with Joanna, Matthew, Danielle and Ruth):

| Markup | Standard | Neural | Long-Form | Generative |
|---|---|---|---|---|
| `s`, `p`, `break`, prosody rate/volume, `say-as`, `sub`, `lang`, `phoneme`, `w`, `mark` | yes | yes | yes | yes |
| `emphasis`, prosody pitch, breaths, soft/whispered, max-duration | yes | no | no | no |
| `amazon:effect name="drc"` | yes | yes | yes | no |
| `amazon:domain` (conversational, news) | no | some voices only | no | no |
| Word speech marks | yes | yes | yes | **no** (beats are not timed on generative) |

- **Before:** neural and generative dropped `<emphasis>`. A clip with `pitch` was rejected and read as plain text,
  so all its pauses were lost.
- **Now:** `narration.polly_ssml` adapts each clip to its engine.
  - Standard keeps everything and breathes between phrases (`amazon:auto-breaths`).
  - Other engines get stressed words slightly louder (`prosody volume`, strong +4 dB, moderate +2 dB, reduced −3 dB)
    and pitch removed. Sentences, breaks and rate are kept.
  - All four engines accepted the adapted SSML live.
- **Planner guide:** `audio-ssml.md` now has delivery rules for sounding like someone explaining live:
  - one `<s>` per sentence and one `<p>` per thought;
  - short breaks before "so" or "but";
  - a pause after a question;
  - one stress per sentence, on the new word;
  - slower for definitions and the key result;
  - `say-as` and `sub` for numbers, acronyms and symbols;
  - no over-marking.

  The plan-critic checks it (P-G6).
- **Voice previews:** the same line, now one sentence at a time, with a beat after "Hello!", the name stressed and a
  breath at the comma. Samples of each engine are in the session scratchpad (`ssml-samples/`).
