// The run's console: talk to its Claude Code session, one turn per message; replies stream in.
import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";
import { usePolling } from "../../hooks/usePolling";
import { Notice } from "../../components/feedback/Notice";
import { SystemMessage } from "../../components/feedback/SystemMessage";
import { Button } from "../../components/ui/Button";
import { ArrowRight, Failed } from "../../components/ui/icons";
import { Markdown } from "../../components/ui/Markdown";
import { useAction } from "../../hooks/useAction";
import { useApi } from "../../hooks/useApi";
import { streamTurn } from "../../services/http";
import { runPath } from "../../services/runs";
import type { ConsoleEntry, ConsoleView } from "../../types/api";
import { useRun } from "./context";

export function Console() {
  const { run, refresh } = useRun();
  const id = run.summary.id;
  const view = useApi<ConsoleView>(runPath(id, "/console"));
  const [lines, setLines] = useState<ConsoleEntry[]>([]);
  const [text, setText] = useState("");
  const turn = useAction();
  const log = useRef<HTMLOListElement>(null);
  const form = useRef<HTMLFormElement>(null);
  const following = useRef<AbortController | null>(null);
  useEffect(() => () => following.current?.abort(), []);  // closing the drawer stops following; the turn goes on
  usePolling(() => { if (view.data?.busy && !turn.busy) view.reload(); }, 3000);  // a turn this page is not following

  useEffect(() => {
    if (view.data) setLines(view.data.entries);
  }, [view.data]);
  useEffect(() => {
    if (log.current) log.current.scrollTop = log.current.scrollHeight;
  }, [lines]);

  if (view.error) return <SystemMessage kind="unavailable" title="Could Not Load the Console">{view.error.message}</SystemMessage>;
  if (!view.data) return <SystemMessage kind="loading" title="Connecting" />;
  const kickoff = view.data.kickoff;
  const started = lines.length > 0;
  const busy = turn.busy || view.data.busy;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const message = text.trim() || (started ? "" : kickoff);
    if (!message) return;
    setText("");
    const controller = new AbortController();
    following.current = controller;
    void turn.run("Claude Is Working: Renders and Voice Can Take Minutes", async () => {
      await streamTurn(runPath(id, "/console"), message, (entry) => setLines((current) => [...current, entry]), controller.signal);
      refresh("Claude Finished");
    }).then((sent) => {
      if (sent || controller.signal.aborted) return;
      setText((current) => current || message);  // a turn that could not start or broke off keeps what was typed
      view.reload();
    });
  };
  const onKey = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.current?.requestSubmit();
    }
  };
  return (
    <div className="term">
      <div className="term__bar"><span>claude code</span><span>{id}</span></div>
      <ol className="term__log" aria-live="polite" aria-label="Conversation with Claude" ref={log}>
        {started
          ? lines.map((entry, index) => (
            <li key={index} className={entry.role}>
              {entry.role === "tool" ? <span className="term__glyph" aria-hidden="true"><ArrowRight /></span> : null}
              {entry.role === "error" ? <span className="term__glyph" aria-hidden="true"><Failed /></span> : null}
              {["claude", "question", "you"].includes(entry.role) ? <Markdown text={entry.text} compact /> : entry.text}
              {entry.options?.length ? <span className="term__options">Choices: {entry.options.join(" · ")}</span> : null}
            </li>
          ))
          : <li className="term__empty">No Messages Yet</li>}
      </ol>
      <form className="term__input" ref={form} onSubmit={submit}>
        <span className="term__prompt" aria-hidden="true">›</span>
        <textarea rows={2} maxLength={8000} value={text} aria-readonly={busy} readOnly={busy} aria-label="Message to Claude"
          aria-describedby="console-keys" placeholder={started ? "Message Claude" : kickoff}
          onChange={(event) => setText(event.target.value)} onKeyDown={onKey} />
        <Button size="sm" type="submit" isDisabled={busy}>{started ? "Send" : "Start"}</Button>
      </form>
      <p className="term__keys" id="console-keys">Enter Sends · Shift+Enter for a New Line</p>
      <div className="term__status">
        {view.data.busy && !turn.busy ? <p className="note">Claude Is Still Replying: Its Messages Appear Here as It Works</p> : null}
        <Notice note={turn.note} />
      </div>
    </div>
  );
}
