// The console's status line, permission prompt and shortcut help (Claude Code's footer, approval dialog and "?").
import { type KeyboardEvent, useEffect, useRef, useState } from "react";
import type { ConsoleMode, TurnStats } from "../../../types/api";
import { contextShare } from "./fold";
import { Diff } from "./Transcript";
import { editDiff } from "./diff";

const MODE: Record<ConsoleMode, string> = { default: "⏸ Manual Mode On", acceptEdits: "⏵⏵ Accept Edits On", plan: "⏸ Plan Mode On" };
export const MODES: ConsoleMode[] = ["default", "acceptEdits", "plan"];
export const modeName = (mode: ConsoleMode) => MODE[mode].replace(/^\S+ /, "").replace(/ On$/, "");

export function StatusLine({ mode, pendingMode, model, stats, spend, busy, empty, cwd, detail, onCycleMode, onHelp }: {
  mode: ConsoleMode; pendingMode: ConsoleMode | null; model: string; stats?: TurnStats | null; spend: number; busy: boolean;
  empty: boolean; cwd: string; detail: boolean; onCycleMode: () => void; onHelp: () => void;
}) {
  const share = contextShare(stats);
  return (
    <div className="con__status" id="console-hints">
      <button type="button" className="con__mode" onClick={onCycleMode} aria-live="polite"
        title="Switch Mode: Manual → Accept Edits → Plan (Shift+Tab)">
        {MODE[mode]}{pendingMode ? <span className="con__quiet"> (From the Next Message; This One Runs in {modeName(pendingMode)})</span> : null}
        <span className="con__quiet con__keyhint"> (Shift+Tab to Cycle)</span>
      </button>
      {detail ? <span className="con__mode">Detail View <span className="con__quiet">(Ctrl+O to Hide)</span></span> : null}
      <span className="con__quiet con__keyhint">{busy ? "Esc to Interrupt" : empty ? "" : "Enter to Send · Shift+Enter for a New Line"}</span>
      <button type="button" className="con__help-button" onClick={onHelp} title="Commands and Shortcuts (?)">? for Shortcuts</button>
      <span className="con__facts">
        <span title="The Model of the Next Message">{model}</span>
        {stats ? <span title={`${stats.context_tokens.toLocaleString()} of ${stats.context_window.toLocaleString()} tokens in the last request`}>Ctx {share}%</span> : null}
        {stats ? <span title="What the Last Turn Cost">Last ${stats.cost_usd.toFixed(4)}</span> : null}
        <span title="What This Run's Console Turns Cost in All">Run ${spend.toFixed(2)}</span>
        {cwd ? <span className="con__cwd" title={cwd}>In {cwd.split("/").pop()}</span> : null}
      </span>
    </div>
  );
}

const GUARD_MS = 600;  // keys that arrive this soon after a prompt appears were not meant for it

export interface Prompt { id: string; tool: string; text: string; rule?: string | null; input: Record<string, unknown> }

/** In place of the prompt while Claude waits: 1 Yes · 2 Yes for this session · 3 No, with what to do instead. */
export function PermissionPrompt({ prompt, onAnswer, waiting }: {
  prompt: Prompt; waiting: number; onAnswer: (decision: "once" | "session" | "deny", note?: string) => Promise<void>;
}) {
  const options = [
    { decision: "once" as const, label: "Yes" },
    ...(prompt.rule ? [{ decision: "session" as const, label: `Yes, and Don't Ask Again This Session for ${prompt.rule}` }] : []),
    { decision: "deny" as const, label: "No, and Tell Claude What to Do Differently" },
  ];
  const [chosen, setChosen] = useState(0);
  const [noting, setNoting] = useState(false);
  const [note, setNote] = useState("");
  const [sending, setSending] = useState(false);
  const list = useRef<HTMLDivElement>(null);
  const noteField = useRef<HTMLInputElement>(null);
  const shownAt = useRef(0);
  useEffect(() => {  // focus moves here (it replaced the prompt), but keys pressed in its first moments do nothing
    setChosen(0); setNoting(false); setNote(""); shownAt.current = Date.now(); list.current?.focus({ preventScroll: true });
  }, [prompt.id]);
  useEffect(() => { if (noting) noteField.current?.focus(); }, [noting]);

  const answer = (decision: "once" | "session" | "deny", text = "") => {
    if (sending) return;
    setSending(true);
    void onAnswer(decision, text).finally(() => setSending(false));
  };
  const pick = (position: number) => {
    const option = options[position];
    if (option.decision === "deny") setNoting(true); else answer(option.decision);
  };
  const onKey = (event: KeyboardEvent<HTMLDivElement>) => {
    if (noting) return;
    if (Date.now() - shownAt.current < GUARD_MS || event.repeat) { event.preventDefault(); event.stopPropagation(); return; }  // typing that was meant for the prompt
    const number = Number(event.key);
    if (number >= 1 && number <= options.length) { event.preventDefault(); pick(number - 1); return; }
    const moves: Record<string, () => void> = {
      ArrowUp: () => setChosen((chosen - 1 + options.length) % options.length),
      ArrowDown: () => setChosen((chosen + 1) % options.length),
      Enter: () => pick(chosen),
      Escape: () => answer("deny"),
      Tab: () => setNoting(true),
    };
    if (moves[event.key] && !event.shiftKey) { event.preventDefault(); event.stopPropagation(); moves[event.key](); }
  };
  const diff = editDiff(prompt.tool, prompt.input);
  const command = prompt.tool === "Bash" ? String(prompt.input.command ?? "") : "";
  return (
    <div className="con__ask" role="group" aria-label="Permission Needed">
      <div className="con__ask-head">{prompt.tool === "Bash" ? "Bash Command" : prompt.tool}{waiting > 1 ? <span className="con__quiet"> · {waiting - 1} More Waiting</span> : null}</div>
      {command ? <pre className="con__out con__ask-command">{command}</pre> : null}
      {diff ? <Diff lines={diff} expanded={false} /> : null}
      <p className="con__ask-what">{command ? String(prompt.input.description ?? "") : prompt.text.replace(/`/g, "")}</p>
      <p className="con__ask-q">Do You Want to Proceed?</p>
      <div className="con__ask-options" role="listbox" aria-label="Your Answer" tabIndex={0} ref={list} onKeyDown={onKey}
        aria-activedescendant={`console-answer-${chosen}`}>
        {options.map((option, position) => (
          <div key={option.decision} id={`console-answer-${position}`} role="option" aria-selected={position === chosen}
            className={position === chosen ? "is-selected" : undefined} onClick={() => pick(position)} onMouseEnter={() => setChosen(position)}>
            <span className="con__pointer" aria-hidden="true">{position === chosen ? "❯" : ""}</span>{position + 1}. {option.label}{option.decision === "deny" ? " (Esc)" : ""}
          </div>
        ))}
      </div>
      {noting ? (
        <form className="con__ask-note" onSubmit={(event) => { event.preventDefault(); answer("deny", note.trim()); }}>
          <label htmlFor="console-deny-note">What Should Claude Do Instead? (Optional)</label>
          <input id="console-deny-note" ref={noteField} value={note} maxLength={2000} onChange={(event) => setNote(event.target.value)}
            onKeyDown={(event) => { if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); setNoting(false); list.current?.focus(); } }} />
          <span className="con__quiet">Enter to Deny · Esc to Go Back</span>
        </form>
      ) : null}
    </div>
  );
}

const SHORTCUTS: [string, [string, string][]][] = [
  ["Send", [["Enter", "Send; While Claude Works, Queue It"], ["Shift+Enter, Alt+Enter, Ctrl+J, \\ Enter", "A New Line"]]],
  ["Stop", [["Esc", "Stop Claude; Esc Again Returns Queued Messages"], ["Ctrl+C", "Stop Claude, or Clear the Prompt"], ["Esc Esc", "Clear the Prompt"]]],
  ["History", [["↑ ↓", "Earlier Prompts (at the First or Last Line)"], ["Ctrl+R", "Search Earlier Prompts"]]],
  ["Modes and View", [["Shift+Tab", "Manual → Accept Edits → Plan"], ["Ctrl+O", "Every Tool's Full Output, and Times"]]],
  ["Menus", [["/", "Commands and Skills"], ["@", "A File of This Run"], ["Tab, Enter", "Take a Suggestion"], ["?", "These Shortcuts"]]],
  ["Permission Prompts", [["1 2 3, ↑ ↓ Enter", "Answer"], ["Tab", "Deny with a Note"], ["Esc", "Deny"]]],
];

export function ShortcutHelp() {
  return (
    <div className="con__help" aria-label="Keyboard Shortcuts" role="region">
      {SHORTCUTS.map(([group, keys]) => (
        <dl key={group}><div className="con__help-group">{group}</div>
          {keys.map(([key, what]) => <div key={key}><dt>{key}</dt><dd>{what}</dd></div>)}
        </dl>
      ))}
    </div>
  );
}
