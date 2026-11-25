// Faraday's voice: every line the interface borrows, with where it comes from. Michael Faraday's own words (public
// domain), and short, well-known lines from films, books and games, each checked word for word against the page linked
// (2026-11-24). Only two places quote: Sign In and the homepage's closing line; every other message stays plain.
// "Curiosity, Illustrated." is the brand line and is never replaced. docs/DESIGN_REFERENCE.md explains the picks.
export interface Line { text: string; source?: string; url?: string }

const candle = (lecture: string) => `https://en.wikisource.org/wiki/The_Chemical_History_of_a_Candle/Lecture_${lecture}`;
const CANDLE = "Michael Faraday, The Chemical History of a Candle";

const LINES = {
  openDoor: { text: "There is no better, there is no more open door by which you can enter into the study of natural philosophy, than by considering the physical phenomena of a candle.", source: `${CANDLE}, Lecture I (1860)`, url: candle("I") },
  aperture: { text: "Hello and, again, welcome to the Aperture Science computer-aided enrichment center.", source: "Portal (2007), GLaDOS", url: "https://en.wikiquote.org/wiki/Portal_(game)" },
  starStuff: { text: "We're made of star-stuff. We are a way for the cosmos to know itself.", source: "Carl Sagan, Cosmos (1980)", url: "https://en.wikiquote.org/wiki/Carl_Sagan" },
} satisfies Record<string, Line>;

/** Each moment of the interface and the lines it may show (one per visit, chosen at random when several). */
export const VOICE = {
  welcome: [LINES.openDoor, LINES.aperture],
  closing: [LINES.openDoor, LINES.starStuff],
} satisfies Record<string, Line[]>;
export type Moment = keyof typeof VOICE;
