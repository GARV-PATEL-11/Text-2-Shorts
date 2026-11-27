// The prompt, as in Claude Code: Enter sends (queued while Claude works), Shift/Alt+Enter, Ctrl+J or "\" then Enter
// add a line, Up/Down walk history at the first/last line, "/" commands, "@" files, Ctrl+R history search, Esc stops
// Claude (twice clears the draft), Shift+Tab switches mode, "?" shows shortcuts. Behaviour lives in keys.ts.
import { type KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import type { Command } from "./commands";
import { matchCommands } from "./commands";
import { AT_DRAFT, type HistoryPosition, search, step } from "./history";
import { keyAction } from "./keys";

interface Item { value: string; label: string; description?: string; disabled?: boolean; submit?: boolean }
const MODELS = [
  { name: "haiku", description: "Fastest and Cheapest" }, { name: "sonnet", description: "Balanced" }, { name: "opus", description: "Most Capable" },
];
const MAX = 8000;
const MENU_ROWS = 10;

export function Composer({ value, onChange, busy, history, commands, files, onSubmit, onStop, onCycleMode, onToggleHelp, helpOpen, onToggleDetail, placeholder, fallback, inputRef }: {
  value: string; onChange: (text: string) => void; busy: boolean; history: string[]; commands: Command[];
  files: (query: string) => Promise<string[]>; onSubmit: (text: string) => void; onStop: () => void; onCycleMode: () => void;
  onToggleHelp: () => void; helpOpen: boolean; onToggleDetail: () => void; placeholder: string; fallback: string; inputRef: React.RefObject<HTMLTextAreaElement | null>;
}) {
  const [at, setAt] = useState<HistoryPosition>(AT_DRAFT);
  const [selected, setSelected] = useState(0);
  const [closed, setClosed] = useState<string | null>(null);  // the text the menu was dismissed for
  const [searching, setSearching] = useState<{ before: string } | null>(null);
  const [found, setFound] = useState<string[]>([]);
  const lastEscape = useRef(0);
  const caret = inputRef.current?.selectionStart ?? value.length;
  const atToken = value.slice(0, caret).match(/(?:^|\s)@([^\s@]*)$/);
  const query = atToken?.[1];

  useEffect(() => {  // asked 150 ms after the last keystroke, not on every one
    if (query === undefined) return setFound([]);
    let current = true;
    const timer = setTimeout(() => {
      void files(query).then((names) => { if (current) setFound(names); }).catch(() => { if (current) setFound([]); });
    }, 150);
    return () => { current = false; clearTimeout(timer); };
  }, [query, files]);

  const items: Item[] = useMemo(() => {
    if (searching) return search(history, value).map((text) => ({ value: text, label: text.split("\n")[0] }));
    if (/^\/model\s+\S*$/.test(value)) {
      const typed = value.split(/\s+/)[1] ?? "";
      return MODELS.filter((model) => model.name.startsWith(typed))
        .map((model) => ({ value: `/model ${model.name}`, label: model.name, description: model.description, submit: true }));
    }
    if (/^\/\S*$/.test(value)) {
      return matchCommands(commands, value.slice(1)).map((command) => ({
        value: `/${command.name}${command.args ? " " : ""}`, label: `/${command.name}${command.args ? ` ${command.args}` : ""}`,
        description: command.description, disabled: command.kind === "unavailable", submit: !command.args,
      }));
    }
    if (query !== undefined) return found.map((name) => ({ value: name, label: `@${name}` }));
    return [];
  }, [searching, history, value, commands, query, found]);
  const menuOpen = items.length > 0 && closed !== value;
  const index = Math.min(selected, Math.max(0, Math.min(items.length, MENU_ROWS) - 1));
  useEffect(() => setSelected(0), [value]);

  const accept = (item: Item, submit: boolean) => {
    if (item.disabled) {  // Enter on an unavailable command runs it: the console says why it is unavailable
      if (submit) send(item.value.trim());
      return;
    }
    if (searching) {
      setSearching(null);
      onChange(item.value);
      return;
    }
    if (query !== undefined && atToken) {  // replace the @token with the path
      const start = caret - query.length - 1;
      onChange(`${value.slice(0, start)}@${item.value} ${value.slice(caret)}`);
      return;
    }
    if (submit && item.submit) {
      send(item.value.trim());
      return;
    }
    onChange(item.value);
  };
  const send = (text: string) => {
    if (!text.trim()) return;
    setAt(AT_DRAFT);
    setSearching(null);
    onSubmit(text);
  };

  const onKey = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.nativeEvent.isComposing || event.keyCode === 229) return;  // an input method is composing: its keys are its own
    const box = event.currentTarget;
    const position = box.selectionStart;
    const action = keyAction(
      { key: event.key, shift: event.shiftKey, ctrl: event.ctrlKey, alt: event.altKey, meta: event.metaKey },
      { menuOpen, busy, empty: value === "", onFirstLine: !value.slice(0, position).includes("\n"),
        onLastLine: !value.slice(box.selectionEnd).includes("\n"), selecting: box.selectionStart !== box.selectionEnd,
        searching: Boolean(searching), helpOpen },
    );
    if (action === "none") return;
    const handled = () => { event.preventDefault(); event.stopPropagation(); };
    switch (action) {
      case "submit":
        handled();
        if (value.slice(0, position).endsWith("\\")) {  // "\" then Enter: a new line, as in Claude Code
          onChange(`${value.slice(0, position - 1)}\n${value.slice(position)}`);
          requestAnimationFrame(() => box.setSelectionRange(position, position));
          return;
        }
        send(value || fallback);  // Enter on an empty first prompt starts production, as the placeholder says
        return;
      case "newline": {
        handled();
        const next = `${value.slice(0, position)}\n${value.slice(box.selectionEnd)}`;
        onChange(next);
        requestAnimationFrame(() => box.setSelectionRange(position + 1, position + 1));
        return;
      }
      case "menu-up": handled(); setSelected((index - 1 + Math.min(items.length, MENU_ROWS)) % Math.min(items.length, MENU_ROWS)); return;
      case "menu-down": handled(); setSelected((index + 1) % Math.min(items.length, MENU_ROWS)); return;
      case "menu-accept": handled(); accept(items[index], event.key === "Enter"); return;
      case "menu-close":
        handled();
        if (searching) { onChange(searching.before); setSearching(null); return; }
        setClosed(value);
        return;
      case "history-older":
      case "history-newer": {
        const moved = step(history, at, action === "history-older" ? -1 : 1, value);
        if (!moved) return;
        handled();
        setAt(moved.at);
        onChange(moved.text);
        return;
      }
      case "stop": handled(); onStop(); return;
      case "clear-input": handled(); onChange(""); setAt(AT_DRAFT); return;
      case "escape": {  // twice within a moment clears the draft; on an empty prompt the drawer closes as usual
        if (!value) return;
        handled();
        const now = Date.now();
        if (now - lastEscape.current < 800) { onChange(""); setAt(AT_DRAFT); }
        lastEscape.current = now;
        return;
      }
      case "cycle-mode": handled(); onCycleMode(); return;
      case "toggle-help": handled(); onToggleHelp(); return;
      case "toggle-detail": handled(); onToggleDetail(); return;
      case "search-history": handled(); if (!searching) { setSearching({ before: value }); onChange(""); } return;
    }
  };

  const rows = Math.min(10, Math.max(1, value.split("\n").length));
  return (
    <div className="con__composer">
      {menuOpen ? (
        <ul className="con__menu" role="listbox" id="console-menu" aria-label={searching ? "Earlier Prompts" : "Suggestions"}>
          {items.slice(0, MENU_ROWS).map((item, position) => (
            <li key={item.label} id={`console-option-${position}`} role="option" aria-selected={position === index} aria-disabled={item.disabled || undefined}
              className={position === index ? "is-selected" : undefined} onMouseDown={(event) => { event.preventDefault(); accept(item, true); }}>
              <span className="con__menu-label">{item.label}</span>
              {item.description ? <span className="con__menu-hint">{item.description}</span> : null}
            </li>
          ))}
          {items.length > MENU_ROWS ? <li className="con__menu-more" aria-hidden="true">↓ {items.length - MENU_ROWS} More: Keep Typing</li> : null}
        </ul>
      ) : null}
      <div className={`con__input${busy ? " is-busy" : ""}`}>
        <span className="con__glyph" aria-hidden="true">{searching ? "⌕" : "›"}</span>
        <textarea ref={inputRef} rows={rows} maxLength={MAX} value={value} spellCheck={false}
          aria-label={searching ? "Search Earlier Prompts" : "Message to Claude"} aria-describedby="console-hints"
          aria-controls={menuOpen ? "console-menu" : undefined} aria-activedescendant={menuOpen ? `console-option-${index}` : undefined}
          aria-autocomplete="list" role="combobox" aria-expanded={menuOpen}
          placeholder={searching ? "Search Earlier Prompts…" : placeholder} onChange={(event) => { onChange(event.target.value); setAt(AT_DRAFT); }} onKeyDown={onKey} />
      </div>
      {value.length > MAX - 1000 ? <p className="con__hint" role="status">{value.length.toLocaleString()} / {MAX.toLocaleString()} characters</p> : null}
    </div>
  );
}
