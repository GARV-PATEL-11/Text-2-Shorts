// Faraday's voice: every line the interface borrows, with where it comes from. Michael Faraday's own words (public
// domain), and short, well-known lines from films, books and games, each checked word for word against the page linked
// (2026-11-24). Labels and buttons stay plain; these lines give state messages, step introductions and empty states a
// voice. "Curiosity, Illustrated." is the brand line and is never replaced. docs/DESIGN_REFERENCE.md explains the picks.
export interface Line { text: string; source?: string; url?: string }

const candle = (lecture: string) => `https://en.wikisource.org/wiki/The_Chemical_History_of_a_Candle/Lecture_${lecture}`;
const CANDLE = "Michael Faraday, The Chemical History of a Candle";

const LINES = {
  openDoor: { text: "There is no better, there is no more open door by which you can enter into the study of natural philosophy, than by considering the physical phenomena of a candle.", source: `${CANDLE}, Lecture I (1860)`, url: candle("I") },
  juvenile: { text: "I claim the privilege of speaking to juveniles as a juvenile myself.", source: `${CANDLE}, Lecture I`, url: candle("I") },
  cause: { text: "What is the cause? Why does it occur?", source: `${CANDLE}, Lecture I`, url: candle("I") },
  philosophers: { text: "We come here to be philosophers", source: `${CANDLE}, Lecture I`, url: candle("I") },
  coloured: { text: "See how beautifully these are coloured", source: `${CANDLE}, Lecture I`, url: candle("I") },
  experiment: { text: "let us make an experiment or two.", source: `${CANDLE}, Lecture IV`, url: candle("IV") },
  points: { text: "We have now some very interesting points to study.", source: `${CANDLE}, Lecture II`, url: candle("II") },
  waiting: { text: "This waiting is a curious and wonderful thing.", source: `${CANDLE}, Lecture VI`, url: candle("VI") },
  wait: { text: "It is curious to see how different substances wait", source: `${CANDLE}, Lecture VI`, url: candle("VI") },
  proved: { text: "Yes! We have proved it by combustion", source: `${CANDLE}, Lecture V`, url: candle("V") },
  wonder: { text: "Nothing is too wonderful to be true, if it be consistent with the laws of nature", source: "Michael Faraday, laboratory journal, 19 March 1849", url: "https://archive.org/stream/lifelettersoffar02joneiala#page/248/mode/2up/search/wonderful" },
  houston: { text: "Houston, we have a problem.", source: "Apollo 13 (1995), Jim Lovell", url: "https://en.wikiquote.org/wiki/Apollo_13_(film)" },
  failure: { text: "Failure is not an option!", source: "Apollo 13 (1995), Gene Kranz", url: "https://en.wikiquote.org/wiki/Apollo_13_(film)" },
  dave: { text: "I'm sorry, Dave. I'm afraid I can't do that.", source: "2001: A Space Odyssey (1968), HAL 9000", url: "https://en.wikiquote.org/wiki/2001:_A_Space_Odyssey_(film)" },
  panic: { text: "DON'T PANIC", source: "The Hitchhiker's Guide to the Galaxy (1979), on the Guide's cover", url: "https://en.wikiquote.org/wiki/The_Hitchhiker%27s_Guide_to_the_Galaxy" },
  harmless: { text: "Mostly harmless", source: "The Hitchhiker's Guide to the Galaxy (1979)", url: "https://en.wikiquote.org/wiki/The_Hitchhiker%27s_Guide_to_the_Galaxy" },
  tears: { text: "All those moments will be lost in time, like tears in rain.", source: "Blade Runner (1982), Roy Batty", url: "https://en.wikiquote.org/wiki/Blade_Runner" },
  beginning: { text: "This is only the beginning.", source: "Dune (2021), Chani", url: "https://en.wikiquote.org/wiki/Dune_(2021_film)" },
  nextProblem: { text: "You solve one problem... and you solve the next one... and then the next.", source: "The Martian (2015), Mark Watney", url: "https://en.wikiquote.org/wiki/The_Martian_(film)" },
  aperture: { text: "Hello and, again, welcome to the Aperture Science computer-aided enrichment center.", source: "Portal (2007), GLaDOS", url: "https://en.wikiquote.org/wiki/Portal_(game)" },
  triumph: { text: "This was a triumph.", source: "Portal (2007), \u201cStill Alive\u201d", url: "https://en.wikiquote.org/wiki/Portal_(game)" },
  doingWell: { text: "You're doing very well.", source: "Portal (2007), GLaDOS", url: "https://en.wikiquote.org/wiki/Portal_(game)" },
  impossible: { text: "The Enrichment Center regrets to inform you that this next test is impossible.", source: "Portal (2007), GLaDOS", url: "https://en.wikiquote.org/wiki/Portal_(game)" },
  whyNot: { text: "Science isn't about why, it's about why not.", source: "Portal 2 (2011), Cave Johnson", url: "https://en.wikiquote.org/wiki/Portal_2" },
  alone: { text: "It's dangerous to go alone! Take this.", source: "The Legend of Zelda (1986)", url: "https://en.wikiquote.org/wiki/The_Legend_of_Zelda_(video_game)" },
  wakeMe: { text: "Wake me, when you need me.", source: "Halo 3 (2007), Master Chief", url: "https://en.wikiquote.org/wiki/Halo_3" },
  awake: { text: "Hey, you. You're finally awake.", source: "The Elder Scrolls V: Skyrim (2011), Ralof", url: "https://en.wikiquote.org/wiki/The_Elder_Scrolls_V:_Skyrim" },
  doItAll: { text: "Do it all, everything!", source: "Minecraft, splash text", url: "https://en.wikiquote.org/wiki/Minecraft_(game)" },
  decide: { text: "All we have to decide is what to do with the time that is given to us.", source: "The Lord of the Rings: The Fellowship of the Ring (2001), Gandalf", url: "https://en.wikiquote.org/wiki/The_Lord_of_the_Rings:_The_Fellowship_of_the_Ring" },
  smallest: { text: "Even the smallest person can change the course of the future.", source: "The Lord of the Rings: The Fellowship of the Ring (2001), Galadriel", url: "https://en.wikiquote.org/wiki/The_Lord_of_the_Rings:_The_Fellowship_of_the_Ring" },
  wizard: { text: "A wizard is never late, Frodo Baggins. Nor is he early; he arrives precisely when he means to.", source: "The Lord of the Rings: The Fellowship of the Ring (2001), Gandalf", url: "https://en.wikiquote.org/wiki/The_Lord_of_the_Rings:_The_Fellowship_of_the_Ring" },
  notPass: { text: "You shall not pass!", source: "The Lord of the Rings: The Fellowship of the Ring (2001), Gandalf", url: "https://en.wikiquote.org/wiki/The_Lord_of_the_Rings:_The_Fellowship_of_the_Ring" },
  onlyHope: { text: "Help me, Obi-Wan Kenobi. You're my only hope.", source: "Star Wars (1977), Leia", url: "https://en.wikiquote.org/wiki/Star_Wars_(film)" },
  badFeeling: { text: "I have a very bad feeling about this.", source: "Star Wars (1977)", url: "https://en.wikiquote.org/wiki/Star_Wars_(film)" },
  starStuff: { text: "We're made of star-stuff. We are a way for the cosmos to know itself.", source: "Carl Sagan, Cosmos (1980)", url: "https://en.wikiquote.org/wiki/Carl_Sagan" },
} satisfies Record<string, Line>;

/** Splash text in the manner of Minecraft's title screen (Faraday's own words), now and then while something waits. */
const splash = (text: string): Line => ({ text });

/** Each moment of the interface and the lines it may show (one per visit, chosen at random when several). */
export const VOICE = {
  welcome: [LINES.openDoor, LINES.aperture],
  homeLead: [LINES.cause],
  nothingInProgress: [LINES.wonder, LINES.doItAll],
  noRuns: [LINES.alone, LINES.beginning],
  chooseLook: [LINES.coloured],
  question: [LINES.philosophers, LINES.whyNot],
  audience: [LINES.juvenile],
  review: [LINES.experiment, LINES.decide],
  readyToBegin: [LINES.beginning, LINES.experiment],
  openingRun: [LINES.points, LINES.awake],
  loading: [LINES.waiting, LINES.wait, splash("Vectors included!")],
  processing: [LINES.nextProblem],
  pending: [LINES.wait, LINES.wizard, splash("Ask why. Then ask again!")],
  rendering: [LINES.waiting, LINES.wizard, splash("Every frame is code!")],
  asks: [LINES.onlyHope],
  nothingToDecide: [LINES.wakeMe],
  approved: [LINES.proved, LINES.doingWell],
  complete: [LINES.triumph, LINES.starStuff, LINES.smallest],
  noChanges: [LINES.harmless],
  failed: [LINES.houston, LINES.failure, LINES.badFeeling],
  renderFailed: [LINES.impossible, LINES.houston],
  offline: [LINES.panic],
  restricted: [LINES.dave, LINES.notPass],
  lost: [LINES.tears],
  closing: [LINES.openDoor, LINES.starStuff],
} satisfies Record<string, Line[]>;
export type Moment = keyof typeof VOICE;
