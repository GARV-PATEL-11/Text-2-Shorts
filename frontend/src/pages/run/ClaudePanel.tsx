// What Claude says and asks, on every stage page: the last message of the last turn (Markdown), its questions with
// one-click answers, and a reply box, so nothing waits unseen in the console. Before the first turn it offers to start
// production (one line, so the stage stays in view); while a turn runs elsewhere it says so.
import { useEffect, useRef, useState } from "react";
import { Notice } from "../../components/feedback/Notice";
import { SystemMessage } from "../../components/feedback/SystemMessage";
import { Button } from "../../components/ui/Button";
import { MarkdownField } from "../../components/ui/fields";
import { ArrowRight, Claude } from "../../components/ui/icons";
import { Markdown } from "../../components/ui/Markdown";
import { Said, usePick } from "../../components/ui/Said";
import { useAction } from "../../hooks/useAction";
import { useApi } from "../../hooks/useApi";
import { streamTurn } from "../../services/http";
import { runPath } from "../../services/runs";
import type { ConsoleEntry, ConsoleView } from "../../types/api";
import { useRun } from "./context";
import { TITLES } from "./titles";

/** Claude's words since the user last spoke (or all of them before that). */
export function lastTurn(entries: ConsoleEntry[], live = true): ConsoleEntry[] {
  const lastYou = entries.map((entry) => entry.role).lastIndexOf("you");
  const turn = entries.slice(lastYou + 1);
  const answered = new Set(turn.filter((entry) => entry.role === "answer").map((entry) => entry.id));
  return turn.filter((entry) => entry.role === "claude" || entry.role === "question" || entry.role === "error"
    || (live && entry.role === "permission" && !answered.has(entry.id)))  // a prompt still open: answered in the console
    .map((entry) => entry.role === "permission"
      ? { ...entry, text: `Claude Is Waiting for Your Permission: ${entry.text}. Open the Console to Answer.` } : entry);
}

export function ClaudePanel({ onAsking }: { onAsking?: (asking: boolean) => void }) {
  const { run, refresh } = useRun();
  const id = run.summary.id;
  const view = useApi<ConsoleView>(runPath(id, "/console"));
  const [reply, setReply] = useState("");
  const [live, setLive] = useState<ConsoleEntry[] | null>(null);  // this page's own turn, as it streams
  const turn = useAction();
  const working = usePick(TITLES.working);
  const loadingTitle = usePick(TITLES.loadingMessages);
  const waitingTitle = usePick(TITLES.waitingForClaude);
  const noReply = usePick(TITLES.noReply);
  const following = useRef<AbortController | null>(null);
  useEffect(() => () => following.current?.abort(), []);  // leaving the page stops following; the turn goes on
  const { reload } = view;
  useEffect(() => reload(), [run, reload]);  // the run changed (a write, the console drawer): read the console again
  const said = lastTurn(live ?? view.data?.entries ?? [], live !== null || Boolean(view.data?.busy));
  const lastText = [...said].reverse().find((entry) => entry.role === "claude")?.text ?? "";
  const asks = !turn.busy && (said.some((entry) => entry.role === "question") || /\?\s*$/.test(lastText));
  useEffect(() => onAsking?.(asks), [asks, onAsking]);  // the run page quiets its approval bar while Claude asks

  if (view.error) return <SystemMessage kind="unavailable" title="Could Not Load Claude's Messages" compact
    action={<Button variant="secondary" size="sm" onPress={reload}>Try Again</Button>}>{view.error.message}</SystemMessage>;
  if (!view.data) return <SystemMessage kind="loading" title={loadingTitle} compact said="loading" />;
  const send = (message: string, typed = false) => {
    setReply("");
    setLive([]);
    const controller = new AbortController();
    following.current = controller;
    void turn.run(working, async () => {
      await streamTurn(runPath(id, "/console"), message, (entry) => setLive((current) => [...(current ?? []), entry]), controller.signal);
      setLive(null);
      refresh("Claude Finished", "claudeFinished");
    }).then((sent) => {
      if (sent || controller.signal.aborted) return;
      setLive(null);  // back to what the console holds, and the Start button or the question stays answerable
      if (typed) setReply((current) => current || message);
      reload();
    });
  };
  if (view.data.busy && !turn.busy) {
    return (
      <SystemMessage kind="processing" title="Claude Is Working" compact said="processing">Its Reply Appears Here When It Ends</SystemMessage>
    );
  }
  if (!view.data.entries.length && !live) {
    return (
      <section className="claude claude--idle" aria-label="Claude">
        <span className="icon-box icon-box--md" aria-hidden="true"><Claude /></span>
        <div className="claude__titles">
          <h2 className="claude__title">Ready to Begin</h2>
          <Said moment="readyToBegin" />
        </div>
        <Button icon={<ArrowRight />} onPress={() => send(view.data!.kickoff)} isDisabled={turn.busy}>Start Production</Button>
      </section>
    );
  }
  return (
    <section className={`claude${asks ? " claude--asks" : ""}`} aria-label="Claude" aria-live="polite">
      <div className="claude__head">
        <span className="icon-box icon-box--md" aria-hidden="true"><Claude /></span>
        <div className="claude__titles">
          <h2 className="claude__title">{turn.busy ? "Claude Is Working" : asks ? "Claude Asks" : "Claude Says"}</h2>
          {turn.busy ? <p className="note"><Said moment="processing" /></p> : asks ? <p className="note"><Said moment="asks" /></p> : null}
        </div>
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
        )) : <p className="note">{turn.busy ? waitingTitle : noReply}</p>}
      </div>
      <form className="claude__reply" onSubmit={(event) => { event.preventDefault(); if (reply.trim()) send(reply.trim(), true); }}>
        <MarkdownField label={asks ? "Your Answer" : "Reply to Claude"} value={reply} onChange={setReply} rows={3} maxLength={8000}
          placeholder={asks ? "Your Answer" : "Message Claude"} />
        <div className="row"><Button type="submit" isDisabled={turn.busy || !reply.trim()}>Send</Button></div>
      </form>
      <Notice note={turn.note} />
    </section>
  );
}
