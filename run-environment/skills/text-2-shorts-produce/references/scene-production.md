# Stage 4 — Clips, scene preview and the video loop (read after CP2)

`text-2-shorts next .` hands out each step. Scenes are produced one after another (a scene starts after the
previous one's CP3); the clips of the current scene are built in parallel, each on its own.

1. Voice: `text-2-shorts voice .` (only clips whose SSML changed) — audio from the planned SSML; word timings give
   each beat's time.
2. Clips, all at once: for every clip of the scene `text-2-shorts task . sNNcMM` → **clip-builder** subagent,
   given only that folder's path → `text-2-shorts accept . sNNcMM`; dispatch them in one message. Each clip takes
   the objects it inherits with `self.entry(name, make)` (built from the plan's description when it runs alone;
   the previous clip's real object in the scene). Drafts render at 720p30. A clip that fails accept twice: show the user the
   findings and ask for a hint.
3. Preview: `text-2-shorts preview . sNN` → `scenes/sNN/preview.mp4` (the whole scene with its opening transition,
   720p30, with audio), `sync.json` (the changes-made document: per beat when it is said vs shown, whether each
   clip's audio fits, each clip's CHANGES.md) and `preview_sheet_*.png`.
4. Audio sync: while `sync.json` lists problems → **audio-refactorer** subagent (re-times the SSML, re-voices,
   previews again). A problem timing cannot fix (wrong or missing animation) → `text-2-shorts feedback . sNNcMM
   --text "…"` and rebuild that clip, then preview again.
5. Video critic loop — at most 3 rounds: **video-critic** subagent appends a round to `scenes/sNN/video_critique.json`.
   On "revise", route each issue (sync → audio-refactorer; plan-match, render, design → feedback + clip rebuild),
   preview again, then the next round. After round 3, whatever is still open goes to the user at CP3.
6. CP3: give the user the `preview.mp4` path, the sync summary and the last critique round;
   `text-2-shorts approve . sNN` (`--force` only when the user accepts open issues).

Then the next scene starts at step 1. After the last CP3: `text-2-shorts final .` renders the
delivery video at 2560×1440, 120 fps → CP4.
