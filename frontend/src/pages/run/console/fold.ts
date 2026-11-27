// Console entries (append-only, as the server sends them) → the blocks the transcript shows: a tool call with its
// permission prompt, decision and result in one block, streamed text gathered until Claude's message replaces it.
// Every block's key is the index of its first entry, so other lines (command output) can be placed between them.
// Pure: no React, unit-tested with `node --test`.
import type { ConsoleEntry, TurnStats } from "../../../types/api";

export type ToolStatus = "running" | "awaiting" | "done" | "failed" | "denied" | "stopped";
export interface ToolBlock {
  kind: "tool"; key: string; id: string; tool: string; title: string; input: Record<string, unknown>; at: string;
  status: ToolStatus; output?: string; isError?: boolean; durationMs?: number | null;
  permission?: { id: string; text: string; rule?: string | null; answer?: string };
}
export type Block =
  | { kind: "prompt"; key: string; text: string; at: string }
  | { kind: "text"; key: string; text: string; at: string }
  | { kind: "live"; key: string; text: string }
  | { kind: "thinking"; key: string; text: string }
  | { kind: "question"; key: string; text: string; options: string[]; at: string }
  | { kind: "permission"; key: string; id: string; tool: string; text: string; input: Record<string, unknown>; rule?: string | null; answer?: string; at: string }
  | { kind: "note"; key: string; text: string; at: string }
  | { kind: "error"; key: string; text: string; at: string; stats?: TurnStats | null }
  | { kind: "summary"; key: string; text: string; at: string; stats: TurnStats }
  | ToolBlock;

const short = (value: unknown, length = 80) => {
  const text = String(value ?? "").replace(/\s+/g, " ").trim();
  return text.length > length ? `${text.slice(0, length - 1)}…` : text;
};
const base = (path: unknown) => String(path ?? "").split("/").filter(Boolean).slice(-2).join("/");

/** How Claude Code names a call: Bash(command), Read(file), Update(file), Write(file), Search(pattern), Fetch(url)… */
export function toolTitle(tool: string, input: Record<string, unknown>): string {
  const named: Record<string, () => string> = {
    Bash: () => `Bash(${short(input.command)})`,
    Read: () => `Read(${base(input.file_path)})`,
    Edit: () => `Update(${base(input.file_path)})`,
    MultiEdit: () => `Update(${base(input.file_path)})`,
    Write: () => `Write(${base(input.file_path)})`,
    NotebookEdit: () => `Update(${base(input.notebook_path)})`,
    Glob: () => `Search(${short(input.pattern)})`,
    Grep: () => `Search(${short(input.pattern)}${input.path ? ` in ${base(input.path)}` : ""})`,
    WebFetch: () => `Fetch(${short(input.url)})`,
    WebSearch: () => `Web Search(${short(input.query)})`,
    Task: () => `Task(${short(input.description ?? input.subagent_type)})`,
    Agent: () => `Agent(${short(input.description ?? input.subagent_type)})`,
    TodoWrite: () => "Update Todos",
    Skill: () => `Skill(${short(input.skill ?? input.command)})`,
  };
  if (named[tool]) return named[tool]();
  const mcp = tool.match(/^mcp__(.+?)__(.+)$/);
  return mcp ? `${mcp[1]} · ${mcp[2]}` : tool;
}

/** The fold. `live`: a turn is running (a call without a result is still running, not stopped). */
export function fold(entries: ConsoleEntry[], live: boolean): Block[] {
  const blocks: Block[] = [];
  const tools = new Map<string, ToolBlock>();
  const prompts = new Map<string, Extract<Block, { kind: "permission" }>>();
  let streamed = "", streamedFrom = 0;
  const flush = () => {  // streamed text that no message has replaced yet (a stopped turn) stays visible
    if (streamed) blocks.push({ kind: "live", key: `${streamedFrom}`, text: streamed });
    streamed = "";
  };
  entries.forEach((entry, index) => {
    const key = `${index}`;
    switch (entry.role) {
      case "partial":
        if (!streamed) streamedFrom = index;
        streamed += entry.text;
        return;
      case "thinking":
        if (index === entries.length - 1 && live) blocks.push({ kind: "thinking", key, text: entry.text });
        return;
      case "claude":
        streamed = "";
        blocks.push({ kind: "text", key, text: entry.text, at: entry.at });
        return;
      case "you":
        flush();
        blocks.push({ kind: "prompt", key, text: entry.text, at: entry.at });
        return;
      case "tool": {
        streamed = "";
        const input = entry.input ?? {};
        const block: ToolBlock = { kind: "tool", key, id: entry.id ?? key, tool: entry.tool ?? "tool",
          title: entry.tool ? toolTitle(entry.tool, input) : entry.text, input, at: entry.at, status: "running" };
        if (entry.id) tools.set(entry.id, block);
        blocks.push(block);
        return;
      }
      case "result": {
        const block = entry.id ? tools.get(entry.id) : undefined;
        if (!block) return;  // a result whose call was never shown (an older console): nothing to attach to
        block.output = entry.text;
        block.isError = entry.is_error;
        block.durationMs = entry.duration_ms;
        block.status = block.status === "denied" ? "denied" : entry.is_error ? "failed" : "done";
        return;
      }
      case "permission": {
        const prompt = { kind: "permission" as const, key, id: entry.id ?? key, tool: entry.tool ?? "", text: entry.text,
          input: entry.input ?? {}, rule: entry.rule, at: entry.at };
        const block = entry.id ? tools.get(entry.id) : undefined;
        if (block) {
          block.permission = { id: prompt.id, text: prompt.text, rule: prompt.rule };
          block.status = "awaiting";
        } else {
          blocks.push(prompt);
        }
        if (entry.id) prompts.set(entry.id, prompt);
        return;
      }
      case "answer": {
        const block = entry.id ? tools.get(entry.id) : undefined;
        if (block?.permission) {
          block.permission.answer = entry.text;
          block.status = entry.text.startsWith("Denied") ? "denied" : block.output === undefined ? "running" : block.status;
        }
        const prompt = entry.id ? prompts.get(entry.id) : undefined;
        if (prompt) prompt.answer = entry.text;
        return;
      }
      case "question":
        blocks.push({ kind: "question", key, text: entry.text, options: entry.options ?? [], at: entry.at });
        return;
      case "error":
        flush();
        blocks.push({ kind: "error", key, text: entry.text, at: entry.at, stats: entry.stats });
        return;
      case "system":
        flush();
        blocks.push(entry.stats ? { kind: "summary", key, text: entry.text, at: entry.at, stats: entry.stats }
          : { kind: "note", key, text: entry.text, at: entry.at });
        return;
    }
  });
  flush();
  if (!live) {
    for (const block of tools.values()) {
      if (block.status === "running" || block.status === "awaiting") block.status = "stopped";
    }
    const last = entries.at(-1);  // a turn ends with its summary, an error or a note; anything else never finished
    if (last && !["system", "error", "partial", "thinking"].includes(last.role))
      blocks.push({ kind: "note", key: `${entries.length}`, text: "This Turn Ended Without Finishing (Faraday Stopped or Lost Claude Code).", at: last.at });
  }
  return blocks;
}

/** Prompts waiting for an answer, oldest first (the console shows the first in place of the input). */
export function openPrompts(blocks: Block[], live: boolean): { id: string; tool: string; text: string; rule?: string | null; input: Record<string, unknown> }[] {
  if (!live) return [];  // a prompt outlives nothing: once the turn has ended it cannot be answered
  return blocks.flatMap((block) => {
    if (block.kind === "tool" && block.permission && !block.permission.answer && block.status === "awaiting")
      return [{ id: block.permission.id, tool: block.tool, text: block.permission.text, rule: block.permission.rule, input: block.input }];
    if (block.kind === "permission" && !block.answer) return [{ id: block.id, tool: block.tool, text: block.text, rule: block.rule, input: block.input }];
    return [];
  });
}

/** One line for a finished turn: ✓ 12.4 s · $0.0041 · 3 tools. */
export function summaryLine(stats: TurnStats): string {
  const seconds = stats.duration_ms >= 60_000 ? `${Math.floor(stats.duration_ms / 60_000)} min ${Math.round((stats.duration_ms % 60_000) / 1000)} s`
    : `${(stats.duration_ms / 1000).toFixed(1)} s`;
  const tools = stats.tools ? ` · ${stats.tools} Tool${stats.tools === 1 ? "" : "s"}` : "";
  return `${seconds} · $${stats.cost_usd.toFixed(4)}${tools}`;
}

/** Context in use as a share of the model's window (0 when unknown). */
export const contextShare = (stats?: TurnStats | null) =>
  stats && stats.context_window ? Math.min(100, Math.round((stats.context_tokens / stats.context_window) * 100)) : 0;
