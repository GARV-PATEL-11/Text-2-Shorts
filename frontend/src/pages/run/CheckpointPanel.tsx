// A checkpoint: approve it (accepting open problems explicitly), or ask for changes; and its history.
import { useState } from "react";
import { Notice } from "../../components/feedback/Notice";
import { SystemMessage } from "../../components/feedback/SystemMessage";
import { Button } from "../../components/ui/Button";
import { Checkbox, MarkdownField } from "../../components/ui/fields";
import { Check } from "../../components/ui/icons";
import { Markdown } from "../../components/ui/Markdown";
import { titleCase, WithCode } from "../../components/ui/text";
import { navigate } from "../../app/routes";
import { REQUIRED_STEPS, STAGE_STEPS, stageStatuses } from "../../config/stages";
import { useAction } from "../../hooks/useAction";
import { send } from "../../services/http";
import { runHash, runPath } from "../../services/runs";
import type { Decision } from "../../types/api";
import { useRun } from "./context";

export function CheckpointPanel({ target }: { target: string }) {
  const { run, refresh, ask } = useRun();
  const checkpoint = run.awaiting.find((candidate) => candidate.target === target);
  const [notes, setNotes] = useState("");
  const [accepted, setAccepted] = useState(false);
  const action = useAction();
  const decisions = run.decisions.filter((decision) => decision.checkpoint === target);
  const approved = stageStatuses(run)[target] === "approved";

  const history = decisions.length ? (
    <div className="stack">
      <h3 className="subhead">Decisions</h3>
      <ul className="list">
        {decisions.map((decision, index) => (
          <li key={index}>
            <span>{`${titleCase(decision.decision)}${decision.forced ? " (Accepted With Open Problems)" : ""}`}</span>
            <span className="list__meta">{decision.decided_at.replace("T", " ")}</span>
            {decision.notes ? <Markdown text={decision.notes} compact /> : null}
          </li>
        ))}
      </ul>
    </div>
  ) : null;
  if (!checkpoint) {
    return (
      <div className="stack">
        {approved
          ? <SystemMessage kind="success" title="You Approved This Checkpoint">Changing what it covers asks you again.</SystemMessage>
          : <SystemMessage kind="pending" title="Nothing to Decide Here Yet">Claude asks you here when this stage is ready.</SystemMessage>}
        {history}
      </div>
    );
  }
  const blocked = checkpoint.problems.length > 0;
  const approve = () =>
    action.run("Approving…", async () => {
      const decision = await send<Decision>(runPath(run.summary.id, "/approve"), { checkpoint: target, notes: notes.trim(), force: blocked });
      const index = REQUIRED_STEPS.findIndex((step) => step.id === target);  // -1 for a scene's checkpoint: stay on it
      const next = index >= 0 ? REQUIRED_STEPS[index + 1] : undefined;
      const after = target === "final" ? STAGE_STEPS.find((step) => step.optional) : next;  // stages follow one after the other
      refresh(`${checkpoint.label} approved${decision.forced ? " with its open problems" : ""}.${after ? ` Next: ${after.label}.` : ""}`);
      if (after) navigate(runHash(run.summary.id, after.id));
    });
  return (
    <div className="stack">
      <div className="card stack">
        <h3 className="card__title">{checkpoint.label}</h3>
        {blocked ? (
          <>
            <p className="subhead">Open Problems</p>
            <ul className="problems">{checkpoint.problems.map((problem) => <li key={problem}><WithCode text={problem} /></li>)}</ul>
            <Checkbox label="I Accept These Open Problems" hint="Approving records that you accepted them." isSelected={accepted} onChange={setAccepted} />
          </>
        ) : <p className="note">Nothing blocks this checkpoint. Look through the other tabs, then decide.</p>}
        <MarkdownField label="Notes (Optional)" value={notes} onChange={setNotes} rows={2} maxLength={4000} />
        <div className="row">
          <Button onPress={approve} isDisabled={action.busy || (blocked && !accepted)} icon={<Check />} describedBy={blocked && !accepted ? `why-${target}` : undefined}>Approve</Button>
          <Button variant="secondary" onPress={() => ask({ target, checkpoint: target })}>Ask for Changes</Button>
        </div>
        {blocked && !accepted ? <p className="note" id={`why-${target}`}>Tick “I Accept These Open Problems” to approve with them, or ask for changes.</p> : null}
        <Notice note={action.note} />
      </div>
      {history}
    </div>
  );
}
