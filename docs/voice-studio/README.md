# Voice Studio — redesign record (2026-11-27)

Built from `Faraday_Voice_Studio_UX_Blueprint.md` and its reference board. Screenshots: `before/`, `round-1/`,
`round-2/`, `after/`. Critic and re-score reports: `critics/`. Nothing committed.

## 1. Audit (before)

- Component inventory:
  - `VoiceStudio` (one big component).
  - `VoiceOrb` (canvas, AnalyserNode).
  - `Waveform`, and `usePreviewPlayer` (one audio element, fetch, decode).
  - Backend: `/api/voices` (Polly `describe_voices`, English) and `/api/voices/preview` (one template, cached MP3).
- Flow: an accent chip row → orb with ‹ › → name and speed → preview card → one control row (voice, speed, style,
  engine, provider) → Select Voice → Save Template.
- Findings that held up:
  - Settings were crammed into one row.
  - Accent chips took a whole row; there was no search.
  - The orb and voice were visually isolated.
  - The player had no time, replay or error state.
  - Subtitles always took space.

## 2. Component hierarchy (after)

```
VoiceStudio (pages/run/stages/look) — state: browse (what is heard) vs choice (the narrator)
├─ ProviderTabs                      Amazon Polly · Google Cloud TTS (frosted, Coming Soon, reachable, not choosable)
├─ main
│  ├─ VoiceOrb (components/voice)    idle · loading (turning arcs) · playing (real frequencies) · paused · error
│  ├─ identity                       name · Your Narrator badge · gender · accent · engine · Select Voice / Update Narrator
│  ├─ AudioPlayer (components/voice) play/pause/try again · real waveform + seek · time · replay · speed
│  ├─ the sentence it speaks         one template, filled
│  └─ delivery                       speed (slider, min/max) · voice engine (only if > 1)
└─ discover                          search · gender · accent · 35 voices (pick = no playback; ▶ = preview)
Subtitles (useTemplateEditor)        On/Off; when on: one summary line, Edit opens style · position · highlighting
```

Reusable: `components/voice/{usePreviewPlayer, VoiceOrb, Waveform, AudioPlayer}` (voice-agnostic).

## 3. Decisions log

| Decision | Why |
|---|---|
| ‹ › play the next voice; list picks and setting changes never play | The owner asked earlier that moving to a voice plays it; the blueprint says selecting must not. Settings changes stop the audio and mark the preview out of date. |
| Keep the existing neutral tokens, not the blueprint's suggested hexes | The blueprint calls them starting points; a test enforces the current neutral set. |
| Canvas orb, no Three.js/WebGL | Same effect with no new dependency. |
| No CSS `scale()` animations | The motion contract (tested) forbids them; the canvas draws rings and deformation. |
| Console: in the run's side panel on wide screens, a small icon on narrow ones | A floating button covered content (V1). |
| Run header, sticky approval bar, Start Production / Decide | Run-page scope, not changed here: **owner decision (V3, P4).** |
| Speaking Style hidden (owner, 2026-11-27) | Removed from the studio and the preview sentence for now; the look keeps its tone for the script writer, and the preview API still accepts a tone, so it can return as one control. |
| No "Recommended" group, no favourites | No product need or persistence model (blueprint §7). |

## 4. Critic rounds

| Round | Overall (weighted, blueprint §11) | What changed |
|---|---|---|
| 1 (4 critics) | ≈70 | First redesign. |
| 2 | ≈79 | Video-player style collision fixed; audio stops when settings change; repeated info removed; one narrator marker; voice before list; per-row states; steady player; accessibility. |
| 3 | ≈83 | Console out of the content; Unsaved Changes cue; subtitles flattened; focus kept while loading. |
| 4 | **≈85** | Subtitles as one summary line; Try Again in place; row errors under the row; list fade. |

Release verdict:
- **Studio scope:** no Critical or High open; only Lows remain (no hook/orb unit tests; no client cache of
  previews).
- **Numerically:** 85 is below 90. The remaining gap is mostly V3 and P4, which are run-page scope and await the
  owner's call.

## 5. Validation

- `e2e/audio.e2e.mjs` with real Polly covers:
  - the provider lock;
  - search and filters, including the empty result and clearing it;
  - picking without playing;
  - the orb playing with a real waveform and time;
  - the out-of-date preview after a setting changes, then playing again;
  - replay without a new request;
  - ‹ › playing the next voice;
  - the engines offered;
  - the error state (a forced 503) and Try Again;
  - Select Voice, the narrator markers and the Unsaved Changes cue;
  - subtitles on, off and on again with their values kept;
  - saving and seeing the voice after a reload;
  - tablet and phone widths.
- Console e2e: 18 states. Python: 265 passed. Frontend unit: 16 passed. ruff, format, tsc, build: clean.
- Reduced motion: still orb, no rings or breathing. Keyboard: list, filters, orb (← →), player, Edit, provider tabs.
- Performance:
  - The orb runs at 30 fps when idle and pauses when off screen.
  - The playhead updates at 10 Hz while playing.
  - Each preview is generated once per combination on the server.
