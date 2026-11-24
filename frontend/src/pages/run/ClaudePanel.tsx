// What Claude says and asks, on every stage page: the last message of the last turn (Markdown), its questions with
// one-click answers, and a reply box, so nothing waits unseen in the console. Before the first turn it offers to start
// production; while a turn runs elsewhere it says so.
import { useEffect, useState } from "react";
import { Notice } from "../../components/feedback/Notice";
import { SystemMessage } from "../../components/feedback/SystemMessage";
import { Button } from "../../components/ui/Button";
import { MarkdownField } from "../../components/ui/fields";
import { Message, Terminal } from "../../components/ui/icons";
import { Markdown } from "../../components/ui/Markdown";
import { useAction } from "../../hooks/useAction";
import { useApi } from "../../hooks/useApi";
import { streamTurn } from "../../services/http";
import { runPath } from "../../services/runs";
import type { ConsoleEntry, ConsoleView } from "../../types/api";
import { useRun } from "./context";

/** Claude's words since the user last spoke (or all of them before that). */
export function lastTurn(entries: ConsoleEntry[]): ConsoleEntry[] {
  const lastYou = entries.map((entry) => entry.role).lastIndexOf("you");
  return entries.slice(lastYou + 1).filter((entry) => entry.role === "claude" || entry.role === "question" || entry.role === "error");
}

export function ClaudePanel({ onOpenConsole }: { onOpenConsole: () => void }) {
  const { run, refresh } = useRun();
  const id = run.summary.id;
  const view = useApi<ConsoleView>(runPath(id, "/console"));
  const [reply, setReply] = useState("");
  const [live, setLive] = useState<ConsoleEntry[] | null>(null);  // this page's own turn, as it streams
  const turn = useAction();
  const { reload } = view;
  useEffect(() => reload(), [run, reload]);  // the run changed (a write, the console drawer): read the console again

  if (view.error) return <SystemMessage kind="unavailable" title="Claude's Messages Could Not Be Read" compact>{view.error.message}</SystemMessage>;
  if (!view.data) return null;
  const send = (message: string) => {
    setReply("");
    setLive([]);
    void turn.run("Claude is working. Replies appear here as they come; long steps (renders, voice) can take minutes.", async () => {
      await streamTurn(runPath(id, "/console"), message, (entry) => setLive((current) => [...(current ?? []), entry]));
      setLive(null);
      refresh("Claude finished its turn.");
    });
  };
  if (view.data.busy && !turn.busy) {
    return (
      <SystemMessage kind="processing" title="Claude Is Working" compact action={<Button size="sm" variant="secondary" icon={<Terminal />} onPress={onOpenConsole}>Open Console</Button>}>
        A turn started in the console is still running. Its messages show here when it ends.
      </SystemMessage>
    );
  }
  if (!view.data.entries.length && !live) {
    return (
      <section className="claude" aria-label="Claude">
        <div className="claude__head"><span className="claude__badge"><Message /></span><h2 className="claude__title">Claude Has Not Started Yet</h2></div>
        <p className="note">Start production and Claude works through the stages, asking you here whenever it needs you.</p>
        <div className="row"><Button icon={<Terminal />} onPress={() => send(view.data!.kickoff)} isDisabled={turn.busy}>Start Production</Button></div>
      </section>
    );
  }
  const said = live ?? lastTurn(view.data.entries);
  const questions = said.filter((entry) => entry.role === "question");
  const lastText = [...said].reverse().find((entry) => entry.role === "claude")?.text ?? "";
  const asks = questions.length > 0 || /\?\s*$/.test(lastText);
  return (
    <section className={`claude${asks ? " claude--asks" : ""}`} aria-label="Claude" aria-live="polite">
      <div className="claude__head">
        <span className="claude__badge"><Message /></span>
        <h2 className="claude__title">{turn.busy ? "Claude Is Working…" : asks ? "Claude Asks" : "Claude Says"}</h2>
        <Button size="sm" variant="tertiary" icon={<Terminal />} onPress={onOpenConsole}>Full Console</Button>
      </div>
      <div className="claude__body">
        {said.length ? said.map((entry, index) => (
          <div key={index} className={`claude__entry claude__entry--${entry.role}`}>
            <Markdown text={entry.text} />
            {entry.options?.length ? (
              <div className="row row--tight">
                {entry.options.map((option) => <Button key={option} size="sm" variant="secondary" onPress={() => send(option)} isDisabled={turn.busy}>{option}</Button>)}
              </div>
            ) : null}
          </div>
        )) : <p className="note">{turn.busy ? "Waiting for Claude's first words…" : "Claude ended its turn without a message."}</p>}
      </div>
      <form className="claude__reply" onSubmit={(event) => { event.preventDefault(); if (reply.trim()) send(reply.trim()); }}>
        <MarkdownField label={asks ? "Your Answer" : "Reply to Claude"} value={reply} onChange={setReply} rows={3} maxLength={8000}
          placeholder={asks ? "Answer Claude's question" : "Ask for anything in this run"} />
        <div className="row"><Button type="submit" isDisabled={turn.busy || !reply.trim()}>Send</Button></div>
      </form>
      <Notice note={turn.note} />
    </section>
  );
}
