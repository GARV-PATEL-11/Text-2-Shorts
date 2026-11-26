# Stage 4 — Scene code, scene preview and the video loop (read after CP2)

`text-2-shorts next .` hands out each step. Scenes are produced one after another, steps 1-5 for each, then CP3
approves them all at once (never scene by scene); each scene is ONE Python file, `scene_code.py`, whose clips are its
sections.

1. Voice: `text-2-shorts voice .` (only clips whose SSML changed) — audio from the planned SSML; word timings give
   each beat's time.
2. Scene code: `text-2-shorts task . sNN` (prints the task: the execution plan, the TEMPLATE, each clip's real
   length from the voice) → **scene-builder** subagent writes `scenes/sNN/work/scene_code.py`
   (`references/codegen-system.md`: one class, a `_clip_N` method per clip) and runs `./check all` →
   `text-2-shorts accept . sNN` re-checks it in a jail and installs it as `scenes/sNN/scene_code.py`. Drafts render
   at 720p30. A scene that fails accept 3 times from the same inputs: `next` says so; show the user the findings
   and record their hint as a visual change request on one of its clips, which lets the scene-builder try again.
   Likewise 3 out-of-sync previews in a row, or 3 accuracy reviews in a row that still find an ERROR, stop the
   loop: the checkpoint shows what is left, and the user accepts it or asks for a change.
3. Preview: `text-2-shorts preview . sNN` → `scenes/sNN/preview.mp4` (the whole scene with its opening transition,
   720p30, with audio), `sync.json` (the changes-made document: per beat when it is said vs shown, whether each
   clip's audio fits, each clip's CHANGES.md) and `preview_sheet_*.png`.
4. Audio sync: while `sync.json` lists problems → **audio-refactorer** subagent (re-times the SSML, re-voices,
   previews again). A problem timing cannot fix (wrong or missing animation) → `text-2-shorts feedback . sNNcMM
   --text "…"` and rebuild the scene (it starts from the accepted file), then preview again.
5. Video critic loop — at most 3 rounds, each scored 0–100 against `quality_threshold` (preferences.json, 85 by
   default; tiers, scoring and routing: critique-protocol.md): **video-critic** subagent appends a round to `scenes/sNN/video_critique.json`. On "revise", route each
   issue (sync → audio-refactorer; plan-match, render, design → feedback + scene rebuild), preview again, and append
   a ChangeRecord for the iteration to `scenes/sNN/changes.json` (issue, findings, modification, files, rendering,
   audio timing, sync, validation, score) — the hook writes the run's `changes.txt` from it; then the next round.
   After round 3 below the threshold the scene REQUIRES ATTENTION: the user accepts the open issues
   (`approve --force`, recorded) or asks for changes — never approve it silently.
Then the next scene starts at step 1.
6. CP3, once every scene is through step 5: give the user every scene's `preview.mp4` path, sync summary and last
   critique round together; `text-2-shorts approve . scenes` (`--force` only when the user accepts open issues).

After CP3: `text-2-shorts final .` renders the delivery video at
2560×1440, 120 fps; assembly checks every part's stream parameters, joins the scenes with the template's transition
(cut, fade or crossfade), mixes clip sound effects and the template's music (the user's own files), normalises
loudness, then checks resolution, 16:9, frame rate, audio, loudness, true peak, silences, black frames, decoding,
duration against the script and that every clip is present → CP4.
