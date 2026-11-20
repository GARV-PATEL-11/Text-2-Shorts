# Video standards and explanation style (apply to every scene and clip)

VIDEO STANDARDS — identical for every scene and clip
Frame: 16:9, 2560×1440 (Manim frame 14.2 × 8 units); keep 0.5 units clear of every edge. One background for the whole
video (#0e2733, set by the harness — never set it in clip code).
Palette roles (Manim colour constants): text WHITE · current focus/highlight YELLOW ·
given quantities BLUE · derived results GREEN · mistakes/warnings RED ·
secondary/dimmed GREY_B. Each math symbol keeps ONE colour for the whole video (SYMBOL COLORS).
Type scale (font_size): title 48 · body 34 · label 28 · caption 24, never smaller. MathTex: main formula 44, inline 34.
Zones: top_center = title or the running formula · center = main diagram · left_half/right_half = comparisons ·
bottom_center = one-line caption. At most 2 text blocks and 1 diagram on screen at once.
Timing: Write/Create 0.8–1.5 s · FadeIn/FadeOut 0.4–0.6 s · Transform 0.8–1.2 s · hold ≥ 0.8 s after a key result.
Nothing moves during a [pause]: that is when the viewer looks.
Clip rhythm: the picture starts 0.3 s before the voice; the final frame holds ≥ 0.8 s after the voice ends.
Scenes: every scene starts on an empty frame and ends with its objects faded out (last beat of the last clip).
Narration text: plain spoken English for a voice. Write math symbols in backticks (`a`, `M`, `v_1`, `θ`) so the voice
says their names; write [pause] where the viewer needs a moment to look (after a key result, before a new step);
write units and abbreviations as words when in doubt ("meters per second", "astronomical units"). If one letter is used
in both cases (M and m), say the difference in words the first time ("big `M`, the Sun's mass").

EXPLANATION STYLE — ELI5 / Feynman
- Start from something the viewer already knows (an everyday object or experience), then name the idea.
- One new idea per sentence; short sentences; every term gets a plain-words meaning where it first appears.
- Concrete before abstract: a picture or a worked number first, the general rule after.
- Show why it is true, not only that it is true: give the step the viewer would otherwise have to take on trust.
- After each key step, a one-line plain recap ("So: …").
- Talk to one curious person ("you"), warm and direct; no filler, no hype.
