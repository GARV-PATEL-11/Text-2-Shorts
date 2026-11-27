# Critic 03 – Frontend Engineering (Voice Studio)
Run: `tsc --noEmit` clean; `npm test` 16/16 pass (all pure voice.ts logic; zero tests for hook/orb/player/studio).
Paths: F=frontend/src. P=F/components/voice/usePreviewPlayer.ts, S=F/pages/run/stages/look/VoiceStudio.tsx, O=VoiceOrb.tsx, C=F/styles/components.css

E1 HIGH – Audio keeps playing while UI says nothing is. 
 Evidence: S:`set()` (row pick, speed/tone/engine) never calls player.stop (stop() is never called anywhere: grep). `stale` then hides waveform/duration (AudioPlayer passes duration 0), orb is forced to "idle" (S orb state prop), rows show "Preview" (playingId null), yet the element still plays and `position` advances -> "00:03 / 00:00", orb aria-pressed=false while audible.
 Why: UI states audio is idle while sound plays; no way to pause except pressing orb (which restarts a new preview). Core "never fake state" violation in the inverse direction.
 Fix: in set(), if player.state is playing/paused and key changes, call player.stop() (or pause) ; or keep orb "playing" until audio ends.
 Validate: play A, click row B / move slider; assert element.paused and state idle (hook test with fake Audio).

E2 HIGH – Regression: `.player` class collision with existing video player. C:259-267 (`.player`, `.player--empty`, `__empty-title`) used by components/media/VideoPreview.tsx:31; new `.player` at C:664 (later, same specificity) overrides border (kills `.player--empty` dashed), background, radius, and adds a 5-col grid + padding/gap to the empty video placeholder. 
 Why: Start a Run / run page video empty state visually changes; unrelated component broken. Fix: rename to `.vplayer`/`.voice-player` (AudioPlayer, VoiceRow glyph class). Validate: screenshot empty video preview before/after; grep `\.player` for single owner.

E3 HIGH – Crash on missing catalogue options. S: `settled = {speed: speed.id, tone: style.id}` and `speed.label`, `style.id` are unguarded while `speed?.detail` elsewhere is guarded; if catalogue lacks speaking_speed/narration_tone (speeds=[] -> speeds[0] undefined) the stage throws and white-screens Start a Run/Template. Fix: guard (render note) or default. Validate: test with empty elements.

E4 MED – Orb render loop cost. O:41-110: rAF runs at 60fps continuously even when idle/paused (breathing/floating) while visible; each frame re-creates a radialGradient and sets shadowBlur 24–74px on a 220px*DPR canvas (software-blur is the most expensive 2D op; ~2-4ms on weak GPUs, scales with DPR 2-3). No setState in the loop (good). 
 Fix: cache the gradient (re-create only when y changes) or draw shadow via CSS filter/pre-rendered glow; drop idle loop to ~30fps or CSS animation; cap DPR at 2. Validate: Chrome Performance panel, frame time idle vs playing.

E5 MED – Playhead choppy and whole studio re-renders 4x/s. P:55 `ontimeupdate` (~4Hz) -> setPosition in hook living inside VoiceStudio -> re-renders all of S including 35 VoiceRow (no React.memo, inline closures at S list), the three fieldsets, the 96 wave spans. Progress is stepped at 250ms, not smooth (animation-quality gap vs the smooth orb). 
 Fix: memo VoiceRow (stable callbacks), split `position` into a sub-component/ref + rAF reading element.currentTime only inside Waveform/time; CSS transform for played overlay instead of 96 class toggles. Validate: React Profiler commits/sec during play.

E6 MED – Unhandled rejections / race gaps in hook. P:76-81 same-key branch: not in try/catch (play() NotAllowed/closed context rejects unhandled, state stuck "idle/paused"), not tied to a controller. P:95 `void waveform(blob).then` has no catch (decodeAudioData failure -> unhandled rejection, no fallback). P:109,116 toggle/replay chains have no catch and no state recovery; toggle during resume can desync. No `pause`/`error`/`waiting` listeners: OS media-key/headset pause leaves state "playing"; orb keeps "playing" with a silent analyser. 
 Fix: wrap all in one try, listen to pause/play/error events as the source of truth for state. Validate: hook tests with stubbed Audio rejecting play().

E7 MED – Stale peaks shown for the wrong voice. P: peaks never cleared on new load; after loadedKey changes, hasAudio true and AudioPlayer passes old `player.peaks` until decode finishes (and indefinitely if decode fails or OfflineAudioContext absent... then [] -> placeholder flat bars, honest). Brief flash of previous voice's real waveform labelled as new. Fix: setPeaks([]) in release()/before load. Validate: switch voices, assert peaks empty until decoded.

E8 MED – Browse state never re-syncs with the draft. S effect only seeds `browse` once (`if(!data||browse) return`). If the look/template or draft choice changes externally (reset to template, switching template, drafts restore), the studio keeps browsing the old voice; "Your Narrator" badge is computed from choice (correct) but the studio view is detached. Also effect deps include `styles` (new [] each render when catalogue lacks element) – harmless only because of the guard. Fix: key <VoiceStudio key={choice-id}> or reseed on external change. Validate: change template via draft restore in Template stage.

E9 MED – decode + fetch not cached. P:128 every first play of a (voice,engine,speed,tone) key re-fetches (the server's `Cache-Control` on a POST (voices.py/app.py:~535) is ignored by browsers, so the "max-age=86400" comment is misleading) and re-decodes the whole MP3 via a new OfflineAudioContext; switching back to a voice heard 10 s ago repeats both. Decode cost small (~5s clip) but unbounded repeated; Fix: Map<key, {blob,peaks}> LRU (≈8) in hook; or GET with query for HTTP cache. Validate: network panel on A->B->A.

E10 LOW – Reduced motion handled once, not reactively. O:26 `matchMedia` read once at effect time; toggling the OS setting while open does nothing, no listener. In still mode, MutationObserver redraw rAF (O:112) is not cancelled on cleanup. Still-mode path otherwise correct (draws once, redraws on class change; MutationObserver targets the button whose class is orb--state: correct). IntersectionObserver logic correct (restarts loop; first frame can draw once while hidden). Hardcoded white/grey canvas colours ignore design tokens/light theme; DPR change (zoom, monitor move) not handled.

E11 LOW – Reusability is partial. Orb (generic), hook (generic: play(load,key)), AudioPlayer (needs whole PreviewPlayer + `stale/speed/name` props, voice wording "Play to Hear {name}", "Settings Changed") live in components/voice – ok. But Browse/keyOf/previewBlob endpoint, ProviderTabs, VoiceRow, stale logic, orb keyboard handling all in a 225-line S monolith in pages/run/stages/look; hook returns a fresh object every render (no memoisation of consumers). Single consumer in useTemplateEditor.tsx:123 (shared by Start a Run + Template stage – one path, so regression surface is shared; good). Glyphs "❚❚/▶" are text, not the icon set. Zero tests on components; only voice.ts pure fns.

E12 LOW – Responsive. Breakpoints 1180/900 exist (C:688-694). Gaps: no <=520px rules: `.studio__hero` orb 220px + two nav buttons in a flex row (C:654) ≈ 220+2*btn+gaps can exceed 360px viewport -> horizontal overflow; player grid at <=900 drops time/speed (loses the "speed it was made at" info on mobile); list max-height 280 inner scroll nested in page scroll; `.studio__discover` sticky ignores tall content. Not verified in a browser (no live run). Validate at 360/390px.

E13 LOW – StrictMode: lazy audio creation makes the double effect safe (cleanup before any element exists). But cleanup closes the AudioContext without nulling graph.current/element.current: any code path re-using the hook instance after cleanup (HMR, StrictMode in future when audio is created eagerly) hits closed context -> resume() rejects. Cheap fix: null refs in cleanup. Object URL revocation is correct (revoked on next load and unmount); createMediaElementSource once per element: correct; one AudioContext per hook instance, closed on unmount: correct.

E14 LOW – Faking check: no fake waveform/playback found. Orb reacts to AnalyserNode only in "playing"; waveform is decoded from real MP3; when no decode, flat 0.08 placeholder bars (labelled as no audio). Caveat: breathing/float/loading arcs are decorative state animation (acceptable, tied to real state). Exception is E1 (orb says idle while audio plays).

Positives: no per-frame setState in orb; abort of superseded fetch + aborted checks after await; blob URL hygiene; keyboard slider semantic; findings above are the delta.

## Scores
Animation quality: 66 – orb is honestly audio-driven and well-state-mapped, but playhead steps at 4Hz, orb/state desync on E1, loading-state is plain arcs, reduced motion not reactive.
Performance: 58 – no setState-per-frame, but unthrottled 60fps shadowBlur canvas when idle, 4Hz full-studio re-render with unmemoised rows, uncached fetch+decode per preview.

Counts: HIGH 3, MED 6, LOW 5 (E1-E14).
