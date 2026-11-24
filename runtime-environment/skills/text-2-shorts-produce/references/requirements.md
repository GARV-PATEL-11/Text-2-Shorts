# Stage 1 — Requirements (read when a run starts)

Goal: an agreed `brief.json`, topic list and content before the outline is written. `text-2-shorts new` wrote it from the user's request;
make it complete and confirm it with the user. Schema: `Brief` (repo `backend/schemas/json/Brief.schema.json`).

| Field | Meaning |
|---|---|
| requirement | the topic and request in the user's words |
| objectives | 1–5 statements of what the viewer can explain or do afterwards ("explain why…", "compute…") |
| audience | who watches and what they already know |
| style | explanation style and tone (default ELI5 / Feynman, see standards.md) |
| approach | narrative structure: zoom · arc · linear (fixed) · creative (designed for the topic, or the user's own) |
| minutes, pace | length (any value > 0) and speaking pace (slow 130 · medium 150 · fast 170 words/min) |
| notes | constraints: must include / must avoid, notation, examples, terms, language level |
| detail_level | overview · standard · detailed |
| explanation_depth | intuitive · conceptual · rigorous |
| technical_complexity | beginner · intermediate · advanced |
| visual_expectations, audio_expectations | what the user expects to see and hear (style, diagrams, voice, music) |
| tts, voice, engine, font | voice provider and look (set by `new`) |

Steps
1. Read `brief.json` and what the user said. Keep what is decided; never re-ask it.
2. Fill the gaps: propose objectives from the requirement when none were given; name the prior knowledge you will
   assume; note constraints the user mentioned in passing.
3. Ask only about what is missing or ambiguous, in one round, with your proposal as the default.
4. Write the agreed values into `brief.json` (the hook validates it) and state the expected outcome in one
   sentence: "After N minutes, <audience> can <objectives>."

5. Topics and content (topic-list.md): apply the request-modifier prompt to the request → `topics.md` (a numbered
   list), confirm it with the user, then write `content.md` — one `## <topic>` section per topic, in order, with
   correct educational content for the audience. This is the outline's `raw_content`.
6. Standing preferences: if the user states a lasting preference (tone, pause length, confirm each scene, quality
   threshold), write it to `preferences.json` (schema `Preferences`). Colours, fonts, voice and speed are the
   template's (step 8).

7. Requirements checkpoint: show the user the brief (approach = the script type, length, audience, detail,
   depth, complexity, expectations), topics.md and content.md; on approval `text-2-shorts approve . requirements`.
8. Template (look and sound) — the run's first stage, chosen before the requirements: the user picks it on the
   website's Template stage (a gallery of starters, or Build Your Own): a starter template (7, from
   `runtime-environment/template_kit/`), then any element changed (background, grid, palettes, accent, fonts, type
   sizes, border, voice, speaking speed, narration tone, subtitles), five of them to their own value (background
   colour, accent colour, text font, voice, speed). Untouched elements keep the starter's default; each element
   shows every option rendered, and the voice can be heard before saving. If they ask you instead:
   `text-2-shorts template . <name> --set accent_color=coral --set custom.text_font=Lato --set music=assets/song.mp3`.
   Music and sound effects are the user's own files in the run folder (e.g. `assets/`). On approval
   `text-2-shorts approve . template`.

Done when `text-2-shorts validate . brief`, `… topics` and `… content` pass, the user agreed to objectives,
audience, style, length and constraints, and both checkpoints (template first, then requirements) are approved. A request the product cannot do (another output format, another voice vendor) → say so and offer
the closest supported option.
