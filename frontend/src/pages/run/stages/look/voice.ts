// The narrator choice, without React: which Polly voice and engine a look speaks with, how a choice is stored (one of
// the template's voice options, or a custom "Voice:engine"), the preview sentence, and the speed steps. Unit-tested.
import type { LookChoice, PollyVoice } from "../../../../types/api";

export const ENGINE_LABEL: Record<string, string> = { generative: "Generative", "long-form": "Long-Form", neural: "Neural", standard: "Standard" };
export const ENGINE_ORDER = ["generative", "long-form", "neural", "standard"];

/** The voice and engine a look speaks with: its custom voice, else its voice option's Polly voice. */
export function spokenBy(choice: LookChoice, curated: Record<string, string>): { voice: string; engine: string } | null {
  const custom = choice.custom.voice;
  if (custom) {
    const [voice, engine = "neural"] = custom.split(":");
    return { voice, engine };
  }
  const found = Object.entries(curated).find(([, option]) => option === choice.elements.voice);
  if (!found) return null;
  const [voice, engine] = found[0].split(":");
  return { voice, engine };
}

/** The look with this voice and engine: the template's own option when it is one of them, else a custom voice. */
export function withVoice(choice: LookChoice, voice: string, engine: string, curated: Record<string, string>): LookChoice {
  const custom = { ...choice.custom };
  delete custom.voice;
  const option = curated[`${voice}:${engine}`];
  if (option) return { ...choice, elements: { ...choice.elements, voice: option }, custom };
  return { ...choice, custom: { ...custom, voice: `${voice}:${engine}` } };
}

/** The engine to use for a voice: the one asked for if it has it, else its best (generative, long-form, neural…). */
export const engineFor = (voice: PollyVoice, wanted: string) =>
  voice.engines.includes(wanted) ? wanted : ENGINE_ORDER.find((engine) => voice.engines.includes(engine)) ?? voice.engines[0];

const titled = (text: string) => text.replace(/\b\w/g, (letter) => letter.toUpperCase());

/** The preview sentence, as the server speaks it (its template, filled). */
export function previewLine(template: string, parts: { agent: string; tone: string; speed: string; provider: string; engine: string }): string {
  return template.replace(/\{(\w+)\}/g, (whole, key: string) =>
    key in parts ? (key === "tone" || key === "speed" ? titled(parts[key as keyof typeof parts]) : key === "engine" ? ENGINE_LABEL[parts.engine] ?? parts.engine : parts[key as keyof typeof parts]) : whole);
}

/** One step slower (-1) or faster (+1) through the speed options, staying at the ends. */
export function stepSpeed(options: string[], current: string, direction: -1 | 1): string {
  const at = Math.max(0, options.indexOf(current));
  return options[Math.min(options.length - 1, Math.max(0, at + direction))];
}

/** The rate a speed option's label shows: "1.08×". */
export const rateLabel = (rate: number) => `${rate.toFixed(2).replace(/0$/, "")}×`;

/** "Singaporean English" → "Singaporean Accent"; "US English" → "US Accent". */
export const accentLabel = (language: string) => language.replace(/\s*English$/, "") + " Accent";

/** "Natural · 1.0×". */
export const speedText = (label: string, rate: number) => `${label} · ${rateLabel(rate)}`;

/** Voices matching a name search, a gender (as Polly gives it) and an accent (its language); "" means any. */
export function filterVoices<T extends { name: string; gender: string; language: string }>(voices: T[], query: string, gender: string, accent: string): T[] {
  const wanted = query.trim().toLowerCase();
  return voices.filter((voice) => (!wanted || voice.name.toLowerCase().includes(wanted))
    && (!gender || voice.gender === gender) && (!accent || voice.language === accent));
}
