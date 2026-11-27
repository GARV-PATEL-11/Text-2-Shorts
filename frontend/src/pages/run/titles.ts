// Plain wordings that mean exactly the same thing, one shown per visit (usePick). The first is the original wording.
// Never errors, labels, buttons or anything a user acts on. "{step}" and "{scene}" are filled in by the caller.
/** "No Script Yet" | "Script Not Made Yet" | "Script: Not Made Yet" (verb "Run" for checks). */
export const notYet = (what: string, verb = "Made") => [`No ${what} Yet`, `${what} Not ${verb} Yet`, `${what}: Not ${verb} Yet`] as const;
export const fill = (text: string, values: Record<string, string>) => text.replace(/\{(\w+)\}/g, (whole, key: string) => values[key] ?? whole);

export const TITLES = {
  openingRun: ["Opening the Run", "Loading This Run", "Opening Your Run", "Setting Out the Run"],
  decision: ["Decision Needed: {step}", "{step}: Waiting for Your Decision", "Your Decision Is Needed on {step}", "Waiting for You: {step}"],
  noFinalVideo: ["No Final Video Yet", "Final Video Not Made Yet", "Final Video: Not Made Yet"],
  noFinalRendered: ["No Final Video Yet", "Final Video Not Made Yet", "Final Video: Not Rendered Yet"],
  stale: ["Not Up to Date", "This Page May Be Out of Date", "Showing the Last Version Received"],
  noDecision: ["Nothing to Decide Yet", "No Decision Due Yet", "Not Ready for a Decision"],
  noDecisionBody: ["Claude Asks When This Stage Is Ready", "Claude Will Ask You When This Stage Is Ready", "Your Decision Is Asked For When This Stage Is Ready"],
  loadingMessages: ["Loading Claude's Messages", "Opening the Conversation", "Connecting"],
  waitingForClaude: ["Waiting for Claude", "Claude Has Not Replied Yet"],
  noReply: ["No Reply", "No Reply Yet"],
  working: [
    "Claude Is Working: Renders and Voice Can Take Minutes", "Claude Is Working: Renders and Voice Take Minutes",
    "Claude Is at Work: Expect Minutes for Renders and Voice", "Claude Is Working: Long Renders and Voice Take a While",
  ],
  connecting: ["Connecting", "Connecting to Claude", "Opening the Console"],
  noMessages: ["No Messages Yet", "Nothing Said Yet", "No Messages in This Run Yet"],
  stillReplying: [
    "Claude Is Still Replying: Its Messages Appear Here as It Works", "Claude Is Still Replying: Watch Its Messages Appear Here",
    "Claude Is Mid-Reply: Its Messages Arrive Here as It Works",
  ],
  notYetBody: [
    "Claude Writes It When the Run Gets Here", "Claude Writes It When the Run Reaches This Stage",
    "Written When the Run Reaches This Stage", "Claude Makes It Once the Run Gets Here",
  ],
  critiqueBody: ["Critiqued When You Request a Change at Its Checkpoint", "Critique Runs When You Request a Change at Its Checkpoint"],
  objectivesUnset: ["Not Set Yet: Claude Proposes Them With You", "Not Set Yet: You and Claude Settle Them Together", "Not Made Yet: Claude Proposes Them With You"],
  loadingExecution: ["Loading the Execution Plan for {scene}", "Opening the Execution Plan of {scene}", "Loading {scene}'s Execution Plan"],
  loadingPlan: ["Loading the Plan for {scene}", "Opening the Plan of {scene}", "Loading {scene}'s Plan"],
  noPreview: ["No Preview Yet", "Preview Not Made Yet", "Nothing to Preview Yet"],
  previewSeed: ["No Preview Yet", "Preview Not Made Yet", "Preview a Seed to See It"],
  reshufflePreviewing: ["Reshuffling, Then Rendering One Frame…", "Reshuffling the Look, Then Rendering One Frame…", "Drawing One Frame of the New Look…"],
  recoloring: ["Recoloring Every Built Clip…", "Recoloring the Built Clips…", "Recoloring Clip by Clip…"],
  loadingOptions: ["Loading Options", "Loading Looks and Sounds", "Gathering the Options"],
  voiceSample: ["Synthesizing a Few Seconds…", "Making a Few Seconds of Voice…", "Recording a Short Voice Sample…", "Generating a Few Seconds of Voice…"],
  renderingLook: ["Rendering the Whole Look…", "Rendering One Full-Size Frame…", "Drawing the Whole Look…"],
  nothingRendered: ["Nothing Rendered Yet", "Not Rendered Yet", "Whole Look Not Rendered Yet"],
  renderingOption: ["Rendering in Your Look…", "Rendering This Option…", "Drawing This Option in Your Look…"],
} as const;
