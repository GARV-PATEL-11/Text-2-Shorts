// Equal-meaning plain wordings for titles of waits and empty states (never errors, labels, buttons or anything a user
// acts on). The current wording comes first; usePick (components/ui/Said.tsx) shows one per visit.
export const TITLES = {
  opening: ["Opening Your Workspace…", "Lighting the Candle…", "Setting Up the Table…", "Preparing the Demonstration Table…", "Arranging the Apparatus…"],
  openingText: ["Checking Which Claude Account This Computer Uses", "Checking Your Sign-In", "Looking for Your Claude Account"],
  signingIn: ["Checking Your Sign-In…", "Looking for Your Claude Account…", "Checking This Computer…"],
  loadingRuns: ["Loading Your Runs", "Gathering Your Runs", "Laying Out Your Runs", "Fetching Your Runs", "Opening the Ledger"],
  nothingInProgress: ["Nothing in Progress", "No Run Under Way", "The Table Is Clear"],
  loadingRun: ["Loading This Run", "Opening This Run", "Bringing Up This Run"],
  loadingUsage: ["Loading Usage", "Reading the Meters", "Checking Your Limits"],
  asking: ["Asking Claude Code", "Putting the Question to Claude Code"],
  notChecked: ["Not Checked Yet", "Not Measured Yet"],
  copying: ["Checking This Computer, Then Copying the Run…", "Copying the Run…", "Making a Copy of the Run…"],
  noMatches: ["No Matches", "Nothing Found", "No Run Matches That"],
  loadingTemplates: ["Loading Templates", "Laying Out the Templates", "Setting Out the Templates", "Opening the Template Shelf"],
  startingRun: [
    "Checking Manim, LaTeX, ffmpeg and Voice Credentials, Then Creating the Run…",
    "Checking the Tools, Then Creating the Run…",
    "Checking Your Setup, Then Starting the Run…",
  ],
  sharpening: ["Sharpening…", "Bringing It Into Focus…"],  // "Rendering Full Size…" is the spinner's line, so not repeated here
} as const;
