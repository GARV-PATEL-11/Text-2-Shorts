// Prompt history: Up/Down walk through this run's earlier prompts (the draft comes back at the end), Ctrl+R searches
// them. Pure; unit-tested.
import type { ConsoleEntry } from "../../../types/api";

export interface HistoryPosition { index: number; draft: string }  // index -1: the draft being written
export const AT_DRAFT: HistoryPosition = { index: -1, draft: "" };

/** Earlier prompts, oldest first, without repeats next to each other. */
export function promptHistory(entries: ConsoleEntry[]): string[] {
  return entries.filter((entry) => entry.role === "you").map((entry) => entry.text)
    .filter((text, index, all) => index === 0 || text !== all[index - 1]);
}

/** One step older (-1) or newer (+1) → the new position and the text to show; null when there is nowhere to go. */
export function step(history: string[], at: HistoryPosition, direction: -1 | 1, current: string): { at: HistoryPosition; text: string } | null {
  if (!history.length) return null;
  if (direction === -1) {
    if (at.index === 0) return null;
    const index = at.index === -1 ? history.length - 1 : at.index - 1;
    return { at: { index, draft: at.index === -1 ? current : at.draft }, text: history[index] };
  }
  if (at.index === -1) return null;
  if (at.index === history.length - 1) return { at: { index: -1, draft: "" }, text: at.draft };
  return { at: { index: at.index + 1, draft: at.draft }, text: history[at.index + 1] };
}

/** Ctrl+R: earlier prompts containing the query, newest first. */
export function search(history: string[], query: string, limit = 8): string[] {
  const wanted = query.trim().toLowerCase();
  return [...new Set([...history].reverse())].filter((text) => text.toLowerCase().includes(wanted)).slice(0, limit);
}
