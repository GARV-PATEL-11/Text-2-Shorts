// The run's console, a Claude Code terminal in the page: one Claude Code turn per message, streamed as it happens;
// tool calls with their results, permission prompts answered here, modes, model, slash commands, history. The only
// component here that talks to the server; the others render and handle keys.
import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { SystemMessage } from "../../../components/feedback/SystemMessage";
import { Button } from "../../../components/ui/Button";
import { Said, usePick } from "../../../components/ui/Said";
import { useApi } from "../../../hooks/useApi";
import { usePolling } from "../../../hooks/usePolling";
import { ApiError, errorText, load, send, streamTurn } from "../../../services/http";
import { runPath } from "../../../services/runs";
import type { ConsoleEntry, ConsoleMode, ConsoleSettings, ConsoleView } from "../../../types/api";
import { useRun } from "../context";
import { TITLES } from "../titles";
import { commandList, LOCAL, parseCommand } from "./commands";
import { editDiff } from "./diff";
import { fold, openPrompts } from "./fold";
import { promptHistory } from "./history";
import { MODES, modeName, PermissionPrompt, ShortcutHelp, StatusLine } from "./parts";
import { Composer } from "./Composer";
import { Diff, type LocalBlock, Transcript } from "./Transcript";

const draftKey = (run: string) => `faraday:console-draft:${run}`;
const readDraft = (run: string) => { try { return sessionStorage.getItem(draftKey(run)) ?? ""; } catch { return ""; } };
const keepDraft = (run: string, text: string) => { try { sessionStorage.setItem(draftKey(run), text); } catch { /* private mode */ } };
const BARE = new Set(LOCAL.filter((command) => !command.args).map((command) => command.name));  // run here only when typed alone
const SHOWN_BLOCKS = 300;  // a long transcript renders its last blocks; earlier ones on request

export function Console() {
  const { run, refresh } = useRun();
  const id = run.summary.id;
  const path = runPath(id, "/console");
  const view = useApi<ConsoleView>(path);
  const [entries, setEntries] = useState<ConsoleEntry[]>([]);
  const [streamed, setStreamed] = useState("");  // text Claude is writing (never stored; its message replaces it)
  const [thinking, setThinking] = useState(false);
  const [settings, setSettings] = useState<ConsoleSettings | null>(null);
  const [following, setFollowing] = useState(false);  // this page streams a turn
  const [queued, setQueued] = useState<string[]>([]);
  const [local, setLocal] = useState<(LocalBlock & { after: number })[]>([]);
  const [detail, setDetail] = useState(false);
  const [help, setHelp] = useState(false);
  const [shownFrom, setShownFrom] = useState<number | null>(null);
  const [text, setText] = useState(() => readDraft(id));
  const [started, setStarted] = useState<number | null>(null);
  const [turnMode, setTurnMode] = useState<ConsoleMode | null>(null);  // the mode the running turn started with
  const [now, setNow] = useState(Date.now());
  const controller = useRef<AbortController | null>(null);
  const unmounted = useRef(false);
  const lastFollow = useRef(0);
  const beforePlan = useRef<ConsoleMode>("acceptEdits");
  const incoming = useRef<ConsoleEntry[]>([]);
  const frame = useRef(0);
  const input = useRef<HTMLTextAreaElement>(null);
  const log = useRef<HTMLDivElement>(null);
  const pinned = useRef(true);  // follow the bottom unless the user scrolled up
  const connecting = usePick(TITLES.connecting);
  const noMessages = usePick(TITLES.noMessages);

  useEffect(() => () => { unmounted.current = true; controller.current?.abort(); cancelAnimationFrame(frame.current); }, []);
  useEffect(() => keepDraft(id, text), [id, text]);
  useEffect(() => {
    if (!view.data) return;
    setSettings(view.data.settings);
    if (!following) setEntries(view.data.entries);
  }, [view.data]);  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (settings) requestAnimationFrame(() => input.current?.focus()); }, [Boolean(settings)]);  // eslint-disable-line react-hooks/exhaustive-deps
  usePolling(() => { if (!following) view.reload(); }, 2000);  // another tab's turn, a turn this page is not following
  usePolling(() => { if (following) setNow(Date.now()); }, 1000);

  const note = useCallback((title: string, body: ReactNode) => {
    setLocal((current) => [...current, { kind: "local", key: `local-${Date.now()}-${current.length}`, title, body, after: entries.length }]);
  }, [entries.length]);

  /** Streamed entries, applied once per frame: text and thinking stay apart from the stored entries. */
  const take = useCallback((entry: ConsoleEntry) => {
    incoming.current.push(entry);
    if (frame.current) return;
    frame.current = requestAnimationFrame(() => {
      frame.current = 0;
      const batch = incoming.current.splice(0);
      let text = "";
      let reset = false;
      let think: boolean | null = null;
      const kept: ConsoleEntry[] = [];
      for (const item of batch) {
        if (item.role === "partial") { text += item.text; think = false; continue; }
        if (item.role === "thinking") { think = true; continue; }
        if (item.role === "claude" || item.role === "tool" || item.role === "you") { reset = true; text = ""; }
        if (item.role !== "result" && item.role !== "answer" && item.role !== "permission") think = false;
        kept.push(item);
      }
      if (kept.length) setEntries((current) => [...current, ...kept]);
      setStreamed((current) => (reset ? text : current + text));
      if (think !== null) setThinking(think);
    });
  }, []);

  const stream = useCallback(async (message: string | null): Promise<"done" | "refused" | "lost"> => {
    const aborter = new AbortController();
    controller.current = aborter;
    lastFollow.current = Date.now();
    setFollowing(true);
    setStarted(Date.now());
    setTurnMode(settings?.mode ?? null);
    setStreamed("");
    setThinking(false);
    if (message === null) {  // follow the running turn from its start: drop what we hold of it
      setEntries((current) => current.slice(0, Math.max(0, current.map((entry) => entry.role).lastIndexOf("you"))));
    }
    let received = 0;
    try {
      await streamTurn(path, message, (entry) => { received += 1; take(entry); }, aborter.signal);
      return "done";
    } catch (error) {
      if (aborter.signal.aborted) return "lost";
      if ((error instanceof ApiError && error.status) || received === 0) {  // refused, or never reached Faraday: nothing ran
        if (message !== null) note("The Message Was Not Sent", <p className="con__out">{errorText(error)}</p>);
        return "refused";
      }
      return "lost";  // the connection broke mid-turn: the turn goes on at the server, and this page follows it again
    } finally {
      cancelAnimationFrame(frame.current);  // what is still batched is in the reload below; never apply it twice
      frame.current = 0;
      incoming.current = [];
      if (!unmounted.current) {
        setFollowing(false);
        setStarted(null);
        setStreamed("");
        setThinking(false);
        view.reload();
      }
    }
  }, [path, note, view, take, settings?.mode]);

  useEffect(() => {  // a turn this page is not following (another tab, Start Production, a lost connection): follow it
    if (view.data?.busy && !following && Date.now() - lastFollow.current > 1500) void stream(null);
  }, [view.data, following, stream]);

  useEffect(() => {  // what was typed while Claude worked goes next, as in Claude Code
    if (!following && queued.length && !view.data?.busy) {
      const [next, ...rest] = queued;
      setQueued(rest);
      void stream(next).then((outcome) => { if (outcome === "refused") setText((current) => current || next); });
    }
  }, [following, queued, view.data?.busy, stream]);

  useEffect(() => {
    const box = log.current;
    if (box && pinned.current) box.scrollTop = box.scrollHeight;
  }, [entries, local, streamed]);

  const live = following || Boolean(view.data?.busy);
  const blocks = useMemo(() => fold(entries, live), [entries, live]);
  const prompts = openPrompts(blocks, live);
  const history = useMemo(() => promptHistory(entries), [entries]);
  const commands = useMemo(() => commandList(view.data?.session), [view.data?.session]);
  const files = useCallback((query: string) => load<string[]>(`${path}/files?q=${encodeURIComponent(query)}`), [path]);
  const lastStats = useMemo(() => [...entries].reverse().find((entry) => entry.stats)?.stats ?? null, [entries]);

  if (view.error && !view.data) return <SystemMessage kind="unavailable" title="Could Not Load the Console"
    action={<Button variant="secondary" size="sm" onPress={view.reload}>Try Again</Button>}>{view.error.message}</SystemMessage>;
  if (!view.data || !settings) return <SystemMessage kind="loading" title={connecting} />;
  const data = view.data;
  const model = settings.model ?? data.session?.model ?? data.default_model;

  const changeSettings = async (change: { model?: string; mode?: ConsoleMode }): Promise<boolean> => {
    try {
      setSettings(await send<ConsoleSettings>(`${path}/settings`, change, "PUT"));
      return true;
    } catch (error) {
      note("The Setting Was Not Changed", <p className="con__out">{errorText(error)}</p>);
      return false;
    }
  };
  const stop = async () => {
    if (queued.length) {  // as in Claude Code: what was queued comes back to the prompt instead of running next
      setText((current) => [current, ...queued].filter(Boolean).join("\n"));
      setQueued([]);
    }
    try { await send(`${path}/stop`, null); } catch (error) { note("Nothing to Stop", <p className="con__out">{errorText(error)}</p>); }
  };
  const setMode = (mode: ConsoleMode) => {
    if (mode === "plan" && settings.mode !== "plan") beforePlan.current = settings.mode;
    void changeSettings({ mode });
  };

  const runCommand = async (name: string, args: string, typed: string): Promise<boolean> => {  // true: handled here
    const echo = `› ${typed}`;
    const list = (items: string[], empty: string) => items.length
      ? <ul className="con__list">{items.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="con__quiet">{empty}</p>;
    if (BARE.has(name) && args) return false;  // "/plan add a hook for X" is a request for Claude, not the command
    switch (name) {
      case "help":
        note(echo, <><ul className="con__list">{commands.filter((command) => command.kind !== "unavailable").map((command) => (
          <li key={command.name}><code>/{command.name}{command.args ? ` ${command.args}` : ""}</code> {command.description}</li>))}</ul><ShortcutHelp /></>);
        return true;
      case "clear":
        if (live) { note(echo, <p className="con__quiet">Stop Claude First (Esc); a New Conversation Starts Once This Turn Ends.</p>); return true; }
        try { await send(`${path}/clear`, null); setLocal([]); view.reload(); } catch (error) { note(echo, <p className="con__out">{errorText(error)}</p>); }
        return true;
      case "model":
        if (!args) { setText("/model "); return true; }
        if (!["haiku", "sonnet", "opus"].includes(args)) { note(echo, <p className="con__quiet">Choose Haiku, Sonnet or Opus.</p>); setText(typed); return true; }
        if (await changeSettings({ model: args })) note(echo, <p className="con__quiet">Model Set to {args}{live ? ", From the Next Message On" : ""}.</p>);
        return true;
      case "plan":
        setMode(settings.mode === "plan" ? beforePlan.current : "plan");
        return true;
      case "permissions":
        note(echo, <>
          <p className="con__quiet">Mode: {modeName(settings.mode)}. Anything Else Claude Wants to Do Asks You Here First.</p>
          <div className="con__local-title">Always Allowed (This Run's Settings)</div>{list(data.rules.allow ?? [], "Nothing")}
          <div className="con__local-title">Never Allowed</div>{list(data.rules.deny ?? [], "Nothing")}
          <div className="con__local-title">Allowed for This Session (Until /clear)</div>{list(settings.allowed, "Nothing Yet")}
        </>);
        return true;
      case "status":
        note(echo, <dl className="con__facts-list">
          {[["Model", model], ["Mode", modeName(settings.mode)], ["Session", data.session?.session_id || "Not Started"],
            ["Working Folder", data.session?.cwd || id], ["At", new Date().toLocaleTimeString()]].map(([label, value]) => (
            <div key={label}><dt>{label}</dt><dd>{value}</dd></div>))}
        </dl>);
        return true;
      case "diff": {
        const edits = blocks.flatMap((block) => block.kind === "tool" && block.status === "done" ? [{ block, lines: editDiff(block.tool, block.input) }] : [])
          .filter((edit) => edit.lines);
        note(echo, edits.length ? <>{edits.map(({ block, lines }) => (
          <div key={block.key}><div className="con__local-title">{block.title}</div><Diff lines={lines!} expanded /></div>))}</> : <p className="con__quiet">No File Was Changed Yet.</p>);
        return true;
      }
      case "skills": note(echo, list(data.session?.skills ?? [], "Known After the First Message")); return true;
      case "agents": note(echo, list(data.session?.agents ?? [], "Known After the First Message")); return true;
      case "stop": await stop(); return true;
    }
    const known = commands.find((command) => command.name === name);
    if (known?.kind === "unavailable") { note(echo, <p className="con__quiet">/{name} Is Not Available Here: {known.reason}</p>); return true; }
    if (!known) { note(echo, <p className="con__quiet">Unknown Command /{name}. Type / to See the Commands and Skills.</p>); setText(typed); return true; }
    return false;  // Claude Code's own (/compact, /context, /cost, skills): sent as the message
  };

  const submit = async (message: string) => {
    const trimmed = message.trim();
    if (!trimmed) return;
    setText("");
    setHelp(false);
    const command = parseCommand(trimmed);
    if (command && await runCommand(command.name, command.args, trimmed)) return;
    if (live) { setQueued((current) => [...current, trimmed]); return; }
    const outcome = await stream(trimmed);
    if (outcome === "refused") setText((current) => current || trimmed);  // nothing ran: the message is kept
    else if (outcome === "done") refresh("Claude Finished", "claudeFinished");
  };
  const answer = async (prompt: string, decision: "once" | "session" | "deny", noteText = "") => {
    try {
      await send(`${path}/permissions/${encodeURIComponent(prompt)}`, { decision, note: noteText });
      if (decision === "session") view.reload();
    } catch (error) {
      note("The Answer Was Not Taken", <p className="con__out">{errorText(error)}</p>);
    } finally {
      requestAnimationFrame(() => input.current?.focus());
    }
  };
  const cycleMode = () => setMode(MODES[(MODES.indexOf(settings.mode) + 1) % MODES.length]);
  const elapsed = started ? Math.max(0, Math.round((now - started) / 1000)) : 0;
  const first = shownFrom ?? Math.max(0, blocks.length - SHOWN_BLOCKS);
  const hidden = first;

  return (
    <div className={detail ? "con con--detail" : "con"}>
      <div className="con__scroll" ref={log} tabIndex={0} aria-label="Transcript" onScroll={(event) => {
        const box = event.currentTarget;
        pinned.current = box.scrollHeight - box.scrollTop - box.clientHeight < 40;
      }}>
        {hidden ? <button type="button" className="con__more con__earlier" onClick={() => setShownFrom(0)}>… {hidden} Earlier Lines (Show All)</button> : null}
        <Transcript blocks={blocks.slice(first)} local={local} detail={detail} streamed={streamed} onOption={(option) => void submit(option)}
          empty={<>{noMessages}<br /><span className="con__quiet">Type a Message, / for Commands, ? for Shortcuts.</span><br /><Said moment="consoleIdle" /></>} />
        {live ? <p className="con__working" role="status"><span aria-hidden="true">✻ </span>{thinking ? "Thinking…" : prompts.length ? "Waiting for Your Answer…" : "Working…"} <span className="con__quiet">({elapsed} s · Esc to Interrupt)</span></p> : null}
        {queued.map((message, index) => <p key={index} className="con__queued"><span aria-hidden="true">› </span>{message} <span className="con__quiet">(Queued · Esc Returns It to the Prompt)</span></p>)}
      </div>
      {help ? <ShortcutHelp /> : null}
      {prompts.length ? (
        <PermissionPrompt prompt={prompts[0]} waiting={prompts.length} onAnswer={(decision, noteText) => answer(prompts[0].id, decision, noteText)} />
      ) : (
        <Composer value={text} onChange={setText} busy={live} history={history} commands={commands} files={files} inputRef={input}
          onSubmit={(message) => void submit(message)} onStop={() => void stop()} onCycleMode={cycleMode}
          onToggleHelp={() => setHelp((open) => !open)} helpOpen={help} onToggleDetail={() => setDetail((open) => !open)}
          placeholder={entries.length ? "Message Claude" : data.kickoff} fallback={entries.length ? "" : data.kickoff} />
      )}
      <StatusLine mode={settings.mode} pendingMode={live && turnMode && turnMode !== settings.mode ? turnMode : null}
        model={model} stats={lastStats} spend={data.spend_usd} busy={live} empty={!text} cwd={data.session?.cwd ?? ""}
        detail={detail} onCycleMode={cycleMode} onHelp={() => setHelp((open) => !open)} />
    </div>
  );
}
