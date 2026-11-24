# Audio planning: SSML per clip (read with scene-visual-planning.md)

Each clip's `ssml` is its audio plan: exactly the clip's narration words (the gate compares them), wrapped in SSML
that gives the picture the time it needs. Plan it together with the beats — what is said and what is shown must line
up.

Tags (AWS Polly and Google both understand these; anything else is rejected):
`<speak>` around everything · `<break time="400ms"/>` · `<prosody rate="92%">…</prosody>` · `<emphasis>…</emphasis>`
(Polly neural and generative voices drop it — never rely on it alone) · `<s>`, `<p>` · `<sub alias="spoken">written</sub>` ·
`<say-as interpret-as="characters|cardinal|date">…</say-as>`. Symbols stay in backticks inside the text (`` `M` ``);
the voice step speaks them by name. `[pause]` is allowed and becomes a 600 ms break. Escape `&` as `&amp;`.

Sync rules
1. Every beat quotes the phrase it starts on; the picture change starts when the voice says it (within 0.35 s).
2. Waits: when an animation must finish before the voice moves on (a formula being written, a curve drawing), put a
   `<break>` after the phrase, sized to the animation (Write/Create 0.8–1.5 s, Transform 0.8–1.2 s).
3. Pointing out: "this", "here", "notice that…" land on the beat that highlights that object.
4. Explanations: slow down (rate 90–95%) for a definition or the key result; normal pace for connective talk; never
   below 85% or above 110%.
5. Pauses: one longer break (600–900 ms) after each clip's key result, while nothing moves.
6. Lead-in and hold are added automatically (picture 0.3 s before the voice, ≥ 0.8 s after it): no breaks for them.
7. Breaks lengthen the clip: keep each clip at 4–20 s of audio.

After a scene is built and previewed, the audio-refactorer re-times this SSML to the real animation (`sync.json`).
