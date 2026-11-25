/** How the topic is taught (backend/schemas/outline_models/approaches.py): seven presets and Custom; `minutes` is
 * the length a pick suggests, which the user may change. */
export const APPROACHES = [
  { id: "eli5", label: "ELI5", hint: "Everyday Analogies and Simple Shapes · 3–5 Min", minutes: 4 },
  { id: "visual_intuition", label: "Visual Intuition", hint: "See It Happen: Graphs, Vectors, Transformations · 3–5 Min", minutes: 4 },
  { id: "story_driven", label: "Story-Driven", hint: "A Mystery, Failed Attempts, Then the Discovery · 4–6 Min", minutes: 5 },
  { id: "step_by_step", label: "Step-by-Step Breakdown", hint: "Build It Part by Part Into the Whole System · 4–6 Min", minutes: 5 },
  { id: "feynman", label: "Feynman Deep Dive", hint: "From First Principles, Misconceptions Included · 8–10 Min", minutes: 9 },
  { id: "technical", label: "Mathematical & Technical", hint: "Derivations, Worked Numbers, Verification · 8–10 Min", minutes: 9 },
  { id: "case_study", label: "Real-World Case Study", hint: "One Real Problem, Analysed, Simulated, Solved · 8–10 Min", minutes: 9 },
  { id: "custom", label: "Custom", hint: "Your Own Teaching Style, Depth and Structure · 3–20 Min", minutes: 5 },
];

/** An approach's name as the website shows it ("eli5" → "ELI5"); unknown ids as they are. */
export const approachName = (id: string | null | undefined) => APPROACHES.find((approach) => approach.id === id)?.label ?? id ?? "";
