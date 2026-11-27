// Asking for a change to any stage, scene or clip, in a modal.
import { useEffect, useMemo, useRef, useState } from "react";
import { Modal } from "../../components/feedback/Overlay";
import { Notice } from "../../components/feedback/Notice";
import { Button } from "../../components/ui/Button";
import { MarkdownField, SelectField } from "../../components/ui/fields";
import { RequestChange } from "../../components/ui/icons";
import { useAction } from "../../hooks/useAction";
import { load, send, streamTurn } from "../../services/http";
import { runPath } from "../../services/runs";
import type { ConsoleView, TrackedRequest } from "../../types/api";
import { type Ask, useRun } from "./context";
import { clipName, sceneName } from "./Overview";

const KINDS = [
  { id: "wording", label: "Wording: What Is Said" }, { id: "visual", label: "Visuals: What Is Shown" },
  { id: "audio-timing", label: "Audio Timing" }, { id: "accuracy", label: "Accuracy: a Claim Is Wrong" },
  { id: "structure", label: "Structure: Order or Scenes" }, { id: "style", label: "Style: Look or Tone" },
  { id: "other", label: "Something Else" },
];

/** Stages a change request cannot name: the look is edited on the Template stage, the requirements and a
 * reshuffle through the console. */
export const NO_REQUESTS = ["template", "requirements", "reshuffle"];

export function ChangeModal({ ask, onClose }: { ask: Ask | null; onClose: () => void }) {
  const { run, refresh } = useRun();
  const targets = useMemo(() => [
    { id: "outline", label: "The Outline" }, { id: "script", label: "The Script" }, { id: "plan", label: "All Scene Plans" }, { id: "scenes", label: "All Scenes" },
    ...run.scenes.flatMap((scene) => [
      { id: scene.scene_id, label: `${sceneName(scene.scene_id)}: ${scene.title}` },
      ...scene.clips.map((clip) => ({ id: clip.clip_id, label: `${clipName(clip.clip_id)}: ${clip.objective}` })),
    ]),
    { id: "final", label: "The Final Video" },
  ], [run.scenes]);
  const [target, setTarget] = useState("outline");
  const [kind, setKind] = useState("wording");
  const [text, setText] = useState("");
  const action = useAction();
  const tooShort = text.trim().length < 3;
  const { setNote } = action;

  const latestTargets = useRef(targets);
  latestTargets.current = targets;
  useEffect(() => {  // only when the modal opens: a refresh while the user types never resets the form (M19)
    if (!ask) return;
    setTarget(latestTargets.current.some((candidate) => candidate.id === ask.target) ? ask.target : "outline");
    setText("");
    setNote(null);
  }, [ask, setNote]);

  const submit = () =>
    action.run("Sending…", async () => {
      const request = await send<TrackedRequest>(runPath(run.summary.id, "/requests"), {
        target, kind, text: text.trim(), checkpoint: ask?.checkpoint && !ask.checkpoint.startsWith("start:") ? ask.checkpoint : null,
      });
      onClose();
      // a recorded request starts nothing by itself: tell an idle session, or the running turn picks it up (M20)
      const path = runPath(run.summary.id, "/console");
      const busy = await load<ConsoleView>(path).then((view) => view.busy, () => null);
      if (busy === null) {  // the page, not the closed modal, must say what happened
        refresh(`Change Request ${request.id} Recorded: Tell Claude in the Console to Apply It`);
        return;
      }
      if (busy) {
        refresh(`Change Request ${request.id} Recorded: Claude Applies It After the Step It Is On`, "changeRecorded");
        return;
      }
      const message = `I asked for a change: ${request.id} (${request.target}, ${request.kind}). Apply it, then carry on.`;
      void streamTurn(path, message, () => undefined).catch(() => undefined);  // the server owns the turn; the page polls it
      refresh(`Change Request ${request.id} Recorded: Claude Is Being Asked to Apply It`, "changeRecorded");
    });
  return (
    <Modal isOpen={ask !== null} onOpenChange={(open) => (open ? null : onClose())} icon={<RequestChange />}
      title="Request a Change" description="Any Stage, Scene or Clip: Claude Applies It and Marks It Done"
      footer={<>
        <Button variant="secondary" onPress={onClose}>Cancel</Button>
        <Button onPress={submit} isDisabled={action.busy || tooShort} describedBy={tooShort ? "change-why" : undefined}>Send Request</Button>
      </>}>
      <SelectField label="What Should Change" value={target} onChange={setTarget} options={targets} />
      <SelectField label="Kind of Change" value={kind} onChange={setKind} options={KINDS} />
      <MarkdownField label="Describe the Change" value={text} onChange={setText} rows={4} maxLength={4000} isRequired />
      {tooShort ? <p className="note" id="change-why">Describe the Change in at Least 3 Characters</p> : null}
      <Notice note={action.note} />
    </Modal>
  );
}
