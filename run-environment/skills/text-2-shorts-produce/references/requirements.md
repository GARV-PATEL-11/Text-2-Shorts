# Stage 1 — Requirements (read when a run starts)

Goal: an agreed `brief.json` before any script is written. `text-2-shorts new` wrote it from the user's request;
make it complete and confirm it with the user. Schema: `Brief` (repo `schemas/json/Brief.schema.json`).

| Field | Meaning |
|---|---|
| requirement | the topic and request in the user's words |
| objectives | 1–5 statements of what the viewer can explain or do afterwards ("explain why…", "compute…") |
| audience | who watches and what they already know |
| style | explanation style and tone (default ELI5 / Feynman, see standards.md) |
| approach | narrative structure: zoom · arc · linear (fixed) · creative (designed for the topic, or the user's own) |
| minutes, pace | length (any value > 0) and speaking pace (slow 130 · medium 150 · fast 170 words/min) |
| notes | constraints: must include / must avoid, notation, examples, terms, language level |
| tts, voice, engine, font | voice provider and look (set by `new`) |

Steps
1. Read `brief.json` and what the user said. Keep what is decided; never re-ask it.
2. Fill the gaps: propose objectives from the requirement when none were given; name the prior knowledge you will
   assume; note constraints the user mentioned in passing.
3. Ask only about what is missing or ambiguous, in one round, with your proposal as the default.
4. Write the agreed values into `brief.json` (the hook validates it) and state the expected outcome in one
   sentence: "After N minutes, <audience> can <objectives>."

Done when `text-2-shorts validate . brief` passes and the user agreed to objectives, audience, style, length and
constraints. A request the product cannot do (another output format, another voice vendor) → say so and offer
the closest supported option.
