// What Claude says and asks, on every stage page: the last message of the last turn (Markdown), its questions with
// one-click answers, and a reply box, so nothing waits unseen in the console. Before the first turn it offers to start
// production; while a turn runs elsewhere it says so.
import { useEffect, useState } from "react";
import { Notice } from "../../components/feedback/Notice";
import { SystemMessage } from "../../components/feedback/SystemMessage";
import { Button } from "../../components/ui/Button";
import { MarkdownField } from "../../components/ui/fields";
import { ArrowRight, Claude, Terminal } from "../../components/ui/icons";
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

export function ClaudePanel({ onOpenConsole, onAsking }: { onOpenConsole: () => void; onAsking?: (asking: boolean) => void }) {
  const { run, refresh } = useRun();
  const id = run.summary.id;
  const view = useApi<ConsoleView>(runPath(id, "/console"));
  const [reply, setReply] = useState("");
  const [live, setLive] = useState<ConsoleEntry[] | null>(null);  // this page's own turn, as it streams
  const turn = useAction();
  const { reload } = view;
  useEffect(() => reload(), [run, reload]);  // the run changed (a write, the console drawer): read the console again
  const said = live ?? lastTurn(view.data?.entries ?? []);
  const lastText = [...said].reverse().find((entry) => entry.role === "claude")?.text ?? "";
  const asks = !turn.busy && (said.some((entry) => entry.role === "question") || /\?\s*$/.test(lastText));
  useEffect(() => onAsking?.(asks), [asks, onAsking]);  // the run page quiets its approval bar while Claude asks

  if (view.error) return <SystemMessage kind="unavailable" title="Claude's Messages Did Not Load" compact>{view.error.message}</SystemMessage>;
  if (!view.data) return null;
  const send = (message: string) => {
    setReply("");
    setLive([]);
    void turn.run("Claude is working. Renders and voice can take minutes.", async () => {
      await streamTurn(runPath(id, "/console"), message, (entry) => setLive((current) => [...(current ?? []), entry]));
      setLive(null);
      refresh("Claude finished.");
    });
  };
  if (view.data.busy && !turn.busy) {
    return (
      <SystemMessage kind="processing" title="Claude Is Working" compact action={<Button size="sm" variant="secondary" icon={<Terminal />} onPress={onOpenConsole}>Open Console</Button>}>
        Started from the console. Its reply appears here when it ends.
      </SystemMessage>
    );
  }
  if (!view.data.entries.length && !live) {
    return (
      <SystemMessage kind="pending" title="Ready to Begin"
        action={<Button icon={<ArrowRight />} onPress={() => send(view.data!.kickoff)} isDisabled={turn.busy}>Start Production</Button>}>
        Claude works through each stage and asks you here when it needs you.
      </SystemMessage>
    );
  }
  return (
    <section className={`claude${asks ? " claude--asks" : ""}`} aria-label="Claude" aria-live="polite">
      <div className="claude__head">
        <span className="icon-box icon-box--lg" aria-hidden="true"><Claude /></span>
        <h2 className="claude__title">{turn.busy ? "Claude Is Working" : asks ? "Claude Asks" : "Claude Says"}</h2>
        <Button size="sm" variant="tertiary" icon={<Terminal />} onPress={onOpenConsole}>Open Console</Button>
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
        )) : <p className="note">{turn.busy ? "Waiting for Claude's first words." : "Claude finished without a reply."}</p>}
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
