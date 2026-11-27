// Slash commands: what Faraday does itself (local), what goes to Claude Code (claude: its built-ins that work headless,
// probed on 2.1.332, and the session's own skills and commands), and what has no equivalent here (unavailable, with
// the reason). Pure; unit-tested.
import type { ConsoleSession } from "../../../types/api";

export interface Command { name: string; args?: string; description: string; kind: "local" | "claude" | "unavailable"; reason?: string }

export const LOCAL: Command[] = [
  { name: "help", description: "Commands and Keyboard Shortcuts", kind: "local" },
  { name: "clear", description: "Start a New Conversation (a New Claude Code Session for This Run)", kind: "local" },
  { name: "model", args: "[haiku|sonnet|opus]", description: "Choose the Model for the Next Messages", kind: "local" },
  { name: "plan", description: "Switch Plan Mode On or Off (Claude Plans, Edits Nothing)", kind: "local" },
  { name: "permissions", description: "What Claude May Do Without Asking, and This Session's Allowances", kind: "local" },
  { name: "status", description: "Model, Mode, Session and Working Folder", kind: "local" },
  { name: "diff", description: "Files Changed in This Conversation, with Their Edits", kind: "local" },
  { name: "skills", description: "Skills This Session Can Use", kind: "local" },
  { name: "agents", description: "Subagents This Session Can Use", kind: "local" },
  { name: "stop", description: "Stop Claude (Esc)", kind: "local" },
];
const CLAUDE: Command[] = [
  { name: "compact", args: "[instructions]", description: "Summarise the Conversation to Free Context", kind: "claude" },
  { name: "context", description: "How the Context Window Is Used", kind: "claude" },
  { name: "cost", description: "Usage and Limits of This Claude Account", kind: "claude" },
];
const UNAVAILABLE: Command[] = [
  ["resume", "Each Run Has One Conversation; /clear Starts a New One"],
  ["rewind", "Not Available Headless; Ask Claude to Undo a Change Instead"],
  ["fork", "Each Run Has One Conversation"],
  ["config", "A Run's Settings Are Fixed by Faraday"],
  ["hooks", "A Run's Hooks Are Fixed by Faraday"],
  ["mcp", "A Run's Tools Are Fixed by Faraday"],
  ["memory", "A Run Has No CLAUDE.md Memory of Its Own"],
  ["init", "A Run Is Not a Code Project"],
  ["add-dir", "A Run Only Sees Its Own Folder"],
  ["login", "Sign In Through Claude Code on This Computer"],
  ["logout", "Sign Out Through Claude Code on This Computer"],
].map(([name, reason]) => ({ name, description: reason, kind: "unavailable" as const, reason }));

/** Every command, local first, then Claude Code's, the session's skills and commands, then the unavailable ones. */
export function commandList(session?: ConsoleSession | null): Command[] {
  const known = new Set([...LOCAL, ...CLAUDE, ...UNAVAILABLE].map((command) => command.name));
  const own = [...new Set([...(session?.skills ?? []), ...(session?.slash_commands ?? [])])]
    .filter((name) => !known.has(name))
    .map((name) => ({ name, description: "Skill or Command of This Run's Session", kind: "claude" as const }));
  return [...LOCAL, ...CLAUDE, ...own, ...UNAVAILABLE];
}

/** Commands matching what follows the "/": names starting with it first, then names containing it. */
export function matchCommands(commands: Command[], typed: string): Command[] {
  const wanted = typed.toLowerCase();
  const starts = commands.filter((command) => command.name.toLowerCase().startsWith(wanted));
  return [...starts, ...commands.filter((command) => !starts.includes(command) && command.name.toLowerCase().includes(wanted))];
}

/** "/model sonnet" → { name: "model", args: "sonnet" }; null when the text is not a command. */
export function parseCommand(text: string): { name: string; args: string } | null {
  const found = text.trim().match(/^\/([\w:.-]+)(?:\s+([\s\S]*))?$/);
  return found ? { name: found[1], args: (found[2] ?? "").trim() } : null;
}
