# Stage 4 — Clips, scene preview and the video loop (read after CP2)

`text-2-shorts next .` hands out each step. Scenes are produced one after another (a scene starts after the
previous one's CP3); the clips of a scene are built one at a time, in order: the next starts only after the
current one passed `accept`.

1. Voice: `text-2-shorts voice .` (only clips whose SSML changed) — audio from the planned SSML; word timings give
   each beat's time.
2. Clips, one at a time: `text-2-shorts task . sNNcMM` → **clip-builder** subagent, given only that folder's
   path → `text-2-shorts accept . sNNcMM`, then the next clip. The task folder holds the accepted earlier clips
   (scene/clips/), so the clip starts from their real end state; it takes inherited objects with
   `self.entry(name, make)`. TASK.md carries the template's rules (colour roles, font, text sizes, safe area). Drafts render at 720p30. A clip that fails accept twice: show the user the
   findings and ask for a hint.
3. Preview: `text-2-shorts preview . sNN` → `scenes/sNN/preview.mp4` (the whole scene with its opening transition,
   720p30, with audio), `sync.json` (the changes-made document: per beat when it is said vs shown, whether each
   clip's audio fits, each clip's CHANGES.md) and `preview_sheet_*.png`.
4. Audio sync: while `sync.json` lists problems → **audio-refactorer** subagent (re-times the SSML, re-voices,
   previews again). A problem timing cannot fix (wrong or missing animation) → `text-2-shorts feedback . sNNcMM
   --text "…"` and rebuild that clip, then preview again.
5. Video critic loop — at most 3 rounds, each scored 0–100 against `quality_threshold` (preferences.json, 85 by
   default; tiers, scoring and routing: critique-protocol.md): **video-critic** subagent appends a round to `scenes/sNN/video_critique.json`. On "revise", route each
   issue (sync → audio-refactorer; plan-match, render, design → feedback + clip rebuild), preview again, and append
   a ChangeRecord for the iteration to `scenes/sNN/changes.json` (issue, findings, modification, files, rendering,
   audio timing, sync, validation, score) — the hook writes the run's `changes.txt` from it; then the next round.
   After round 3 below the threshold the scene REQUIRES ATTENTION: the user accepts the open issues
   (`approve --force`, recorded) or asks for changes — never approve it silently.
6. CP3: give the user the `preview.mp4` path, the sync summary and the last critique round;
   `text-2-shorts approve . sNN` (`--force` only when the user accepts open issues).

Then the next scene starts at step 1. After the last CP3: `text-2-shorts final .` renders the delivery video at
2560×1440, 120 fps; assembly checks every part's stream parameters, joins the scenes with the template's transition
(cut, fade or crossfade), mixes clip sound effects and the template's music (the user's own files), normalises
loudness, then checks resolution, 16:9, frame rate, audio, loudness, true peak, silences, black frames, decoding,
duration against the script and that every clip is present → CP4.
