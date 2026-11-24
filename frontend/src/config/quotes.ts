// The only quotations the interface uses: Michael Faraday's own words, public domain, checked word for word against the
// sources below (2026-11-24). Used sparingly: never on waiting, failure or error. docs/DESIGN_REFERENCE.md says where.
export interface Quote { text: string; source: string; url: string }

export const QUOTES = {
  /** Sign-in: the opening of his Christmas lectures, on why a humble thing leads into all of science. */
  welcome: {
    text: "There is no better, there is no more open door by which you can enter into the study of natural philosophy, than by considering the physical phenomena of a candle.",
    source: "Michael Faraday, The Chemical History of a Candle, Lecture I (1860)",
    url: "https://en.wikisource.org/wiki/The_Chemical_History_of_a_Candle/Lecture_I",
  },
  /** Home with nothing in progress: a note to himself about testing a surprising idea. */
  wonder: {
    text: "Nothing is too wonderful to be true, if it be consistent with the laws of nature",
    source: "Michael Faraday, laboratory journal, 19 March 1849",
    url: "https://archive.org/stream/lifelettersoffar02joneiala#page/248/mode/2up/search/wonderful",
  },
} satisfies Record<string, Quote>;
