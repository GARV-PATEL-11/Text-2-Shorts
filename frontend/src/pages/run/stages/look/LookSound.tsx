// Template, the first stage: chosen when the run was started, changeable here until it is approved. The editor is the
// one Start a Run uses (useTemplateEditor); this page adds what needs the run: hearing the voice with the run's
// provider, saving, and the checkpoint.
import { type Dispatch, type SetStateAction, useEffect, useState } from "react";
import { Notice } from "../../../../components/feedback/Notice";
import { SystemMessage } from "../../../../components/feedback/SystemMessage";
import { AudioPreview } from "../../../../components/media/AudioPreview";
import { Button } from "../../../../components/ui/Button";
import { Check, Volume } from "../../../../components/ui/icons";
import { titleCase } from "../../../../components/ui/text";
import { useAction } from "../../../../hooks/useAction";
import { useApi } from "../../../../hooks/useApi";
import { send } from "../../../../services/http";
import { runPath } from "../../../../services/runs";
import type { LookCatalogue, LookChoice, LookView } from "../../../../types/api";
import { CheckpointPanel } from "../../CheckpointPanel";
import { useRun } from "../../context";
import { type StageProps, StageTabs, waiting } from "../StageTabs";
import { useTemplateEditor } from "./useTemplateEditor";

export function LookSound(props: StageProps) {
  const { run } = useRun();
  const catalogue = useApi<LookCatalogue>("/api/look");
  const saved = useApi<LookView>(runPath(run.summary.id, "/look"));
  const [choice, setChoice] = useState<LookChoice | null>(null);
  useEffect(() => {
    if (saved.data && !choice) setChoice({ template: saved.data.template, elements: saved.data.elements, custom: saved.data.custom });
  }, [saved.data, choice]);

  if (catalogue.error || saved.error) {
    return <SystemMessage kind="unavailable" title="Could Not Load the Template">{(catalogue.error ?? saved.error)?.message}</SystemMessage>;
  }
  if (!catalogue.data || !choice || !saved.data) return <SystemMessage kind="loading" title="Loading Options" />;
  return <TemplateStage {...props} catalogue={catalogue.data} choice={choice} setChoice={setChoice} saved={saved.data.saved} />;
}

function TemplateStage({ catalogue, choice, setChoice, saved, ...props }: StageProps & {
  catalogue: LookCatalogue; choice: LookChoice; setChoice: Dispatch<SetStateAction<LookChoice | null>>; saved: boolean;
}) {
  const { run, refresh } = useRun();
  const id = run.summary.id;
  const action = useAction();
  const [audio, setAudio] = useState<string | null>(null);
  useEffect(() => setAudio(null), [choice]);  // the voice sample belongs to the choice it was made from
  const hear = () => action.run("Synthesizing a Few Seconds…", async () => {
    setAudio((await send<{ url: string }>(runPath(id, "/look/voice"), choice)).url);
    return "Voice Sample Ready";
  });
  const editor = useTemplateEditor({
    catalogue, choice, setChoice,
    soundExtras: <Button variant="secondary" icon={<Volume />} onPress={hear} isDisabled={action.busy}>Hear the Voice</Button>,
  });
  const save = () => action.run("Saving…", async () => {
    await send(runPath(id, "/look"), choice);
    refresh("Template Saved: Approve It in the Checkpoint Tab, Then the Requirements Come Next");
    return "Saved";
  });
  const tabs = editor.tabs.map((tab) => (tab.id === "sound" && audio
    ? { ...tab, content: <div className="stack"><AudioPreview src={audio} label="Voice Sample" />{tab.content}</div> } : tab));
  return (
    <div className="stack">
      <StageTabs {...props} label="Template"
        toolbar={<>
          <span className="badge">Starter: {titleCase(choice.template)}</span>
          <Button onPress={save} isDisabled={action.busy} icon={<Check />}>Save Template</Button>
        </>}
        tabs={[...tabs, { id: "checkpoint", label: "Checkpoint", count: waiting(run.awaiting, "template"), content: <CheckpointPanel target="template" /> }]}
      />
      {!saved ? <p className="note">Showing Defaults: The Video Uses These Until You Save</p> : null}
      <Notice note={action.note ?? editor.stillAction.note} />
      {editor.note ? <p className="note" role="status">{editor.note}</p> : null}
      {editor.overlay}
    </div>
  );
}
