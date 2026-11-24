// The run's console: talk to its Claude Code session, one turn per message; replies stream in.
import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";
import { Notice } from "../../components/feedback/Notice";
import { SystemMessage } from "../../components/feedback/SystemMessage";
import { Button } from "../../components/ui/Button";
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

  useEffect(() => {
    if (view.data) setLines(view.data.entries);
  }, [view.data]);
  useEffect(() => {
    if (log.current) log.current.scrollTop = log.current.scrollHeight;
  }, [lines]);

  if (view.error) return <SystemMessage kind="unavailable" title="The Console Could Not Be Opened">{view.error.message}</SystemMessage>;
  if (!view.data) return <SystemMessage kind="loading" title="Connecting to the Run's Session…" />;
  const kickoff = view.data.kickoff;
  const started = lines.length > 0;
  const busy = turn.busy || view.data.busy;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const message = text.trim() || (started ? "" : kickoff);
    if (!message) return;
    setText("");
    void turn.run("Claude is working. Replies appear as they come; long steps (renders, voice) can take minutes.", async () => {
      await streamTurn(runPath(id, "/console"), message, (entry) => setLines((current) => [...current, entry]));
      refresh("Claude finished its turn.");
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
              {["claude", "question", "you"].includes(entry.role) ? <Markdown text={entry.text} compact /> : entry.text}
              {entry.options?.length ? <span className="term__options">Choices: {entry.options.join(" · ")}</span> : null}
            </li>
          ))
          : <li className="term__empty">Nothing said yet. Press Start to begin production, or tell Claude what you want.</li>}
      </ol>
      <form className="term__input" ref={form} onSubmit={submit}>
        <span className="term__prompt" aria-hidden="true">›</span>
        <textarea rows={2} maxLength={8000} value={text} aria-readonly={busy} readOnly={busy} aria-label="Message to Claude"
          aria-describedby="console-keys" placeholder={started ? "Reply to Claude, or ask for anything in this run" : kickoff}
          onChange={(event) => setText(event.target.value)} onKeyDown={onKey} />
        <Button size="sm" type="submit" isDisabled={busy}>{started ? "Send" : "Start"}</Button>
      </form>
      <p className="term__keys" id="console-keys">Enter sends · Shift+Enter starts a new line</p>
      <div className="term__status">
        {view.data.busy && !turn.busy ? <p className="note">Claude is still working on an earlier message; close and reopen to see its replies.</p> : null}
        <Notice note={turn.note} />
      </div>
    </div>
  );
}
