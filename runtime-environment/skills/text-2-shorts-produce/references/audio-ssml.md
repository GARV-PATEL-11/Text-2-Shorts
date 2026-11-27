# Audio planning: SSML per clip (read with scene-visual-planning.md)

Each clip's `ssml` is its audio plan: exactly the clip's narration words (the gate compares them), wrapped in SSML
that gives the picture the time it needs and makes the voice sound like a person explaining it live, at a board, to
one viewer. Plan it together with the beats: what is said and what is shown must line up.

## Tags

AWS Polly and Google both understand these. Anything else is rejected.

- `<speak>` around everything.
- `<p>` for a thought and `<s>` for each sentence. Every sentence goes in its own `<s>`; a clip that moves to a new
  idea starts a new `<p>`.
- `<break time="400ms"/>`. `[pause]` also works and becomes the template's pause, 600 ms by default.
- `<prosody rate="92%" volume="+2dB">…</prosody>`. Rate is 85–110%. Volume is −6 to +6 dB. No `pitch`: only the
  oldest voices speak it.
- `<emphasis level="strong|moderate|reduced">…</emphasis>`. Voices that lack it (most of them) get the same words
  slightly louder or softer instead, so mark the stress where a speaker would put it and never rely on it alone.
- `<sub alias="spoken">written</sub>`.
- `<say-as interpret-as="characters|cardinal|ordinal|digits|fraction|unit|date|time">…</say-as>`.

Symbols stay in backticks inside the text (`` `M` ``): the voice step speaks them by name. Escape `&` as `&amp;`.
The voice step adapts the markup to the chosen voice; write it once, for a listener.

## Sounding like someone explaining live

Markup cannot add words: the voice says only the narration. These are how a good explainer's delivery is written down.

1. **Sentences and thoughts.** One `<s>` per sentence and one `<p>` per thought, so the voice drops and resets at
   each end instead of reading on in one breath.
2. **Breathing room.** Commas pause on their own. Add a short break, 150–250 ms, where a speaker would gather the
   next idea: before "so", "which means", "but", or after a setup clause ("If you double the radius, <break/> …").
3. **Questions land.** After a question the viewer is meant to think about, break for 400–700 ms before the answer.
4. **Stress the new word.** One emphasis per sentence at most, on the word carrying the new information: the term
   being defined, the surprising number, the contrast ("not the area, but the <emphasis>rate</emphasis>").
   `strong` only for the clip's key result. `reduced` for an aside.
5. **Slow down for what matters.** Rate 90–95% for a definition, a formula being read, or the key result. Normal
   pace (no prosody) for connective talk. A quick aside can be 103–106%. Change rate at phrase boundaries, never
   inside a word group.
6. **Numbers and letters said right.** `say-as cardinal` for a big number ("1,250,000"), `ordinal` for "3rd",
   `fraction` for "3/4", `characters` for an acronym spoken letter by letter ("DNA"), `unit` for "5 kg". Use `sub` when
   the written form and the spoken form differ ("<sub alias="pi">π</sub>", "<sub alias="versus">vs</sub>").
7. **Don't over-mark.** Most words carry no markup. More than one emphasis, or more than three breaks, in one short
   sentence sounds robotic, not human.

Example (narration: "So what is a derivative, really? It is the slope of a curve, at one single point."):

```xml
<speak><p><s>So what is a derivative, really?</s> <break time="500ms"/>
<s>It is the <emphasis level="strong">slope</emphasis> of a curve, <break time="200ms"/> at one single point.</s></p></speak>
```

## Sync rules

1. Every beat quotes the phrase it starts on; the picture change starts when the voice says it (within 0.35 s).
2. Waits: when an animation must finish before the voice moves on (a formula being written, a curve drawing), put a
   `<break>` after the phrase, sized to the animation (Write/Create 0.8–1.5 s, Transform 0.8–1.2 s).
3. Pointing out: "this", "here", "notice that…" land on the beat that highlights that object, and take its stress.
4. Pauses: one longer break (600–900 ms) after each clip's key result, while nothing moves.
5. Lead-in and hold are added automatically (picture 0.3 s before the voice, ≥ 0.8 s after it): no breaks for them.
6. Breaks lengthen the clip: keep each clip at 4–20 s of audio.

After a scene is built and previewed, the audio-refactorer re-times this SSML to the real animation (`sync.json`).
