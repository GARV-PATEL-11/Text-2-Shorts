// Asking for a change to any stage, scene or clip, in a modal.
import { useEffect, useMemo, useState } from "react";
import { Modal } from "../../components/feedback/Overlay";
import { Notice } from "../../components/feedback/Notice";
import { Button } from "../../components/ui/Button";
import { MarkdownField, SelectField } from "../../components/ui/fields";
import { RequestChange } from "../../components/ui/icons";
import { useAction } from "../../hooks/useAction";
import { send } from "../../services/http";
import { runPath } from "../../services/runs";
import type { TrackedRequest } from "../../types/api";
import { type Ask, useRun } from "./context";

const KINDS = [
  { id: "wording", label: "Wording: What Is Said" }, { id: "visual", label: "Visuals: What Is Shown" },
  { id: "audio-timing", label: "Audio Timing" }, { id: "accuracy", label: "Accuracy: a Claim Is Wrong" },
  { id: "structure", label: "Structure: Order or Scenes" }, { id: "style", label: "Style: Look or Tone" },
  { id: "other", label: "Something Else" },
];

export function ChangeModal({ ask, onClose }: { ask: Ask | null; onClose: () => void }) {
  const { run, refresh } = useRun();
  const targets = useMemo(() => [
    { id: "outline", label: "The Outline" }, { id: "script", label: "The Script" }, { id: "plan", label: "All Scene Plans" },
    ...run.scenes.flatMap((scene) => [
      { id: scene.scene_id, label: `Scene ${scene.scene_id}: ${scene.title}` },
      ...scene.clips.map((clip) => ({ id: clip.clip_id, label: `Clip ${clip.clip_id}: ${clip.objective}` })),
    ]),
    { id: "final", label: "The Final Video" },
  ], [run.scenes]);
  const [target, setTarget] = useState("outline");
  const [kind, setKind] = useState("wording");
  const [text, setText] = useState("");
  const action = useAction();
  const { setNote } = action;

  useEffect(() => {
    if (!ask) return;
    setTarget(targets.some((candidate) => candidate.id === ask.target) ? ask.target : "outline");
    setText("");
    setNote(null);
  }, [ask, targets, setNote]);

  const submit = () =>
    action.run("Sending your request…", async () => {
      const request = await send<TrackedRequest>(runPath(run.summary.id, "/requests"), {
        target, kind, text: text.trim(), checkpoint: ask?.checkpoint && !ask.checkpoint.startsWith("start:") ? ask.checkpoint : null,
      });
      onClose();
      refresh(`Change request ${request.id} recorded. The run's session applies it at its next step.`);
    });
  return (
    <Modal isOpen={ask !== null} onOpenChange={(open) => (open ? null : onClose())} icon={<RequestChange />}
      title="Request a Change" description="Any stage, scene or clip. Claude applies it and marks it done."
      footer={<>
        <Button variant="secondary" onPress={onClose}>Cancel</Button>
        <Button onPress={submit} isDisabled={action.busy || text.trim().length < 3}>Send Request</Button>
      </>}>
      <SelectField label="What Should Change" value={target} onChange={setTarget} options={targets} />
      <SelectField label="Kind of Change" value={kind} onChange={setKind} options={KINDS} />
      <MarkdownField label="Describe the Change" value={text} onChange={setText} rows={4} maxLength={4000} isRequired hint="At least a few words." />
      <Notice note={action.note} />
    </Modal>
  );
}
