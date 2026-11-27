// The console's keyboard map, as Claude Code's (interactive-mode docs), minus what a browser keeps for itself.
// Pure; unit-tested. The component turns each action into behaviour.

export type KeyAction =
  | "submit" | "newline" | "menu-up" | "menu-down" | "menu-accept" | "menu-close" | "history-older" | "history-newer"
  | "stop" | "clear-input" | "escape" | "cycle-mode" | "toggle-help" | "toggle-detail" | "search-history" | "none";

export interface KeyPress { key: string; shift?: boolean; ctrl?: boolean; alt?: boolean; meta?: boolean }
export interface KeyContext {
  menuOpen: boolean; busy: boolean; empty: boolean; onFirstLine: boolean; onLastLine: boolean; selecting: boolean;
  searching?: boolean; helpOpen?: boolean;
}

export function keyAction(press: KeyPress, at: KeyContext): KeyAction {
  const plain = !press.shift && !press.ctrl && !press.alt && !press.meta;
  const ctrl = (press.ctrl || press.meta) && !press.alt;
  if (at.searching) {  // Ctrl+R: Enter takes a match, Esc leaves the search; nothing is sent from here
    if (press.key === "Escape") return "menu-close";
    if (press.key === "Enter") return at.menuOpen ? "menu-accept" : "none";
  }
  switch (press.key) {
    case "Enter":
      if (press.shift || press.alt) return "newline";  // Shift+Enter, Option/Alt+Enter
      if (at.menuOpen && plain) return "menu-accept";
      return plain || press.ctrl || press.meta ? "submit" : "none";  // Ctrl/Cmd+Enter sends too
    case "ArrowUp":
      if (!plain) return "none";
      return at.menuOpen ? "menu-up" : at.onFirstLine ? "history-older" : "none";
    case "ArrowDown":
      if (!plain) return "none";
      return at.menuOpen ? "menu-down" : at.onLastLine ? "history-newer" : "none";
    case "Tab":
      if (press.shift) return "cycle-mode";
      return at.menuOpen && plain ? "menu-accept" : "none";
    case "Escape":
      return at.menuOpen ? "menu-close" : at.busy ? "stop" : at.helpOpen && at.empty ? "toggle-help" : "escape";
    case "?":
      return at.empty && !press.ctrl && !press.meta ? "toggle-help" : "none";
  }
  if (ctrl && !press.shift) {
    switch (press.key.toLowerCase()) {
      case "c": return at.selecting ? "none" : at.busy ? "stop" : at.empty ? "none" : "clear-input";
      case "j": return "newline";
      case "o": return "toggle-detail";
      case "r": return "search-history";
    }
  }
  return "none";
}
