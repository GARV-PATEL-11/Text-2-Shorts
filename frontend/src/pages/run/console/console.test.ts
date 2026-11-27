// node --test (TypeScript type stripping, no dependency): the console's pure logic.
import { test } from "node:test";
import assert from "node:assert/strict";
import type { ConsoleEntry } from "../../../types/api";
import { contextShare, fold, openPrompts, summaryLine, toolTitle } from "./fold.ts";
import { diffSummary, editDiff, lineDiff } from "./diff.ts";
import { AT_DRAFT, promptHistory, search, step } from "./history.ts";
import { commandList, matchCommands, parseCommand } from "./commands.ts";
import { keyAction, type KeyContext } from "./keys.ts";

const at = "2026-11-27T10:00:00";
const e = (role: ConsoleEntry["role"], text: string, more: Partial<ConsoleEntry> = {}): ConsoleEntry => ({ at, role, text, ...more });
const stats = { model: "m", cost_usd: 0.0041, duration_ms: 1835, context_tokens: 31597, context_window: 1_000_000, output_tokens: 144, tools: 1 };

test("a tool call, its permission, answer and result fold into one block", () => {
  const blocks = fold([
    e("you", "go"),
    e("partial", "Run"), e("partial", "ning"),
    e("tool", "Bash date", { id: "t1", tool: "Bash", input: { command: "date" } }),
    e("permission", "Run a shell command", { id: "t1", tool: "Bash", rule: "Bash(date *)" }),
    e("answer", "Allowed Once.", { id: "t1" }),
    e("result", "2026", { id: "t1", tool: "Bash", duration_ms: 40 }),
    e("claude", "Done."),
    e("system", "Turn Finished.", { stats }),
  ], false);
  assert.deepEqual(blocks.map((block) => block.kind), ["prompt", "tool", "text", "summary"]);  // streamed text replaced
  const tool = blocks[1];
  assert.ok(tool.kind === "tool");
  assert.equal(tool.title, "Bash(date)");
  assert.equal(tool.status, "done");
  assert.equal(tool.output, "2026");
  assert.equal(tool.permission?.answer, "Allowed Once.");
});

test("a waiting prompt is open; a denied call is denied; a stopped turn leaves its calls stopped", () => {
  const waiting = fold([e("tool", "x", { id: "a", tool: "Write", input: { file_path: "/r/notes.md" } }),
    e("permission", "Create notes.md", { id: "a", tool: "Write", rule: "Write" })], true);
  assert.deepEqual(openPrompts(waiting, true).map((prompt) => prompt.id), ["a"]);
  assert.deepEqual(openPrompts(fold([e("permission", "p", { id: "z", tool: "Bash" })], false), false), []);  // the turn is over
  assert.equal(waiting[0].kind === "tool" && waiting[0].status, "awaiting");
  const denied = fold([e("tool", "x", { id: "a", tool: "Bash", input: { command: "rm x" } }),
    e("permission", "p", { id: "a", tool: "Bash" }), e("answer", "Denied. no", { id: "a" }),
    e("result", "The user denied this.", { id: "a", is_error: true })], false);
  assert.equal(denied[0].kind === "tool" && denied[0].status, "denied");
  const stopped = fold([e("tool", "x", { id: "a", tool: "Read", input: { file_path: "a" } }), e("system", "Stopped by You.")], false);
  assert.equal(stopped[0].kind === "tool" && stopped[0].status, "stopped");
  const cut = fold([e("you", "go"), e("tool", "x", { id: "b", tool: "Read", input: {} })], false);  // the server restarted
  assert.equal(cut.at(-1)?.kind, "note");
});

test("streamed text with no message after it stays visible; thinking shows only while it is the latest", () => {
  assert.deepEqual(fold([e("you", "a"), e("partial", "half a sen")], false).map((block) => block.kind), ["prompt", "live"]);
  assert.equal(fold([e("thinking", "Thinking…")], true)[0].kind, "thinking");
  assert.equal(fold([e("thinking", "Thinking…"), e("claude", "x")], true).length, 1);
});

test("tool titles read like Claude Code's", () => {
  assert.equal(toolTitle("Edit", { file_path: "/run/scenes/s01/code.py" }), "Update(s01/code.py)");
  assert.equal(toolTitle("Grep", { pattern: "TODO", path: "/run/src" }), "Search(TODO in run/src)");
  assert.equal(toolTitle("mcp__faraday__permission", {}), "faraday · permission");
});

test("turn summary and context share", () => {
  assert.equal(summaryLine(stats), "1.8 s · $0.0041 · 1 Tool");
  assert.equal(summaryLine({ ...stats, duration_ms: 125_000, tools: 3 }), "2 min 5 s · $0.0041 · 3 Tools");
  assert.equal(contextShare(stats), 3);
  assert.equal(contextShare(null), 0);
});

test("line diff keeps common lines and marks the rest", () => {
  assert.deepEqual(lineDiff("a\nb\nc", "a\nB\nc"), [{ op: " ", text: "a" }, { op: "-", text: "b" }, { op: "+", text: "B" }, { op: " ", text: "c" }]);
  assert.deepEqual(editDiff("Write", { content: "x\ny" })?.map((line) => line.op), ["+", "+"]);
  assert.equal(editDiff("Bash", { command: "ls" }), null);
  assert.equal(diffSummary(lineDiff("a\nb", "a\nc\nd")), "Added 2 Lines, Removed 1 Line");
  assert.equal(lineDiff("x\n".repeat(500), "y").length, 502);  // too long for the table: whole sides
});

test("history walks back through prompts and returns the draft", () => {
  const history = promptHistory([e("you", "one"), e("claude", "x"), e("you", "two"), e("you", "two")]);
  assert.deepEqual(history, ["one", "two"]);
  const back = step(history, AT_DRAFT, -1, "draft")!;
  assert.equal(back.text, "two");
  const further = step(history, back.at, -1, "two")!;
  assert.equal(further.text, "one");
  assert.equal(step(history, further.at, -1, "one"), null);
  const forward = step(history, step(history, further.at, 1, "one")!.at, 1, "two")!;
  assert.equal(forward.text, "draft");
  assert.deepEqual(search(["make it blue", "shorter", "blue again"], "blue"), ["blue again", "make it blue"]);
});

test("slash commands: local, Claude Code's, the session's own, unavailable", () => {
  const list = commandList({ session_id: "", model: "", cwd: "", permission_mode: "", slash_commands: ["compact", "text-2-shorts-produce"], skills: [], agents: [], tools: [] });
  const named = (name: string) => list.find((command) => command.name === name);
  assert.equal(named("model")?.kind, "local");
  assert.equal(named("compact")?.kind, "claude");
  assert.equal(named("text-2-shorts-produce")?.kind, "claude");
  assert.equal(named("resume")?.kind, "unavailable");
  assert.equal(list.filter((command) => command.name === "compact").length, 1);
  assert.deepEqual(matchCommands(list, "co").slice(0, 2).map((command) => command.name), ["compact", "context"]);
  assert.deepEqual(parseCommand("/model  sonnet "), { name: "model", args: "sonnet" });
  assert.deepEqual(parseCommand("/compact keep the scene list\nand the voice"), { name: "compact", args: "keep the scene list\nand the voice" });
  assert.equal(parseCommand("not a command"), null);
});

test("keys: Enter sends, Shift/Alt+Enter and Ctrl+J add a line, Esc stops a turn, Shift+Tab cycles modes", () => {
  const idle: KeyContext = { menuOpen: false, busy: false, empty: false, onFirstLine: true, onLastLine: true, selecting: false };
  assert.equal(keyAction({ key: "Enter" }, idle), "submit");
  assert.equal(keyAction({ key: "Enter", shift: true }, idle), "newline");
  assert.equal(keyAction({ key: "Enter", alt: true }, idle), "newline");
  assert.equal(keyAction({ key: "j", ctrl: true }, idle), "newline");
  assert.equal(keyAction({ key: "Enter" }, { ...idle, menuOpen: true }), "menu-accept");
  assert.equal(keyAction({ key: "Escape" }, { ...idle, busy: true }), "stop");
  assert.equal(keyAction({ key: "Escape" }, { ...idle, menuOpen: true, busy: true }), "menu-close");
  assert.equal(keyAction({ key: "Tab", shift: true }, idle), "cycle-mode");
  assert.equal(keyAction({ key: "ArrowUp" }, idle), "history-older");
  assert.equal(keyAction({ key: "ArrowUp" }, { ...idle, onFirstLine: false }), "none");
  assert.equal(keyAction({ key: "c", ctrl: true }, { ...idle, busy: true }), "stop");
  assert.equal(keyAction({ key: "c", ctrl: true }, { ...idle, selecting: true }), "none");  // copy stays copy
  assert.equal(keyAction({ key: "?" }, { ...idle, empty: true }), "toggle-help");
  assert.equal(keyAction({ key: "?" }, idle), "none");
  assert.equal(keyAction({ key: "o", ctrl: true }, idle), "toggle-detail");
  assert.equal(keyAction({ key: "r", ctrl: true }, idle), "search-history");
  assert.equal(keyAction({ key: "Escape" }, { ...idle, busy: true, searching: true }), "menu-close");  // leaves search, never stops
  assert.equal(keyAction({ key: "Enter" }, { ...idle, searching: true }), "none");  // no match: nothing is sent
  assert.equal(keyAction({ key: "Escape" }, { ...idle, empty: true, helpOpen: true }), "toggle-help");
});
