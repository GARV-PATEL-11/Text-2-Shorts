// Template, the first stage: chosen when the run was started, changeable here until it is approved. The editor is the
// one Start a Run uses (useTemplateEditor); this page adds what needs the run: hearing the voice with the run's
// provider, saving, and the checkpoint.
import { type Dispatch, type SetStateAction, useEffect, useState } from "react";
import { Notice } from "../../../../components/feedback/Notice";
import { SystemMessage } from "../../../../components/feedback/SystemMessage";
import { Button } from "../../../../components/ui/Button";
import { Check } from "../../../../components/ui/icons";
import { titleCase } from "../../../../components/ui/text";
import { useAction } from "../../../../hooks/useAction";
import { usePick } from "../../../../components/ui/Said";
import { useApi } from "../../../../hooks/useApi";
import { send } from "../../../../services/http";
import { runPath } from "../../../../services/runs";
import type { LookCatalogue, LookChoice, LookView } from "../../../../types/api";
import { CheckpointPanel } from "../../CheckpointPanel";
import { useRun } from "../../context";
import { type StageProps, StageTabs, waiting } from "../StageTabs";
import { TITLES } from "../../titles";
import { useTemplateEditor } from "./useTemplateEditor";

export function LookSound(props: StageProps) {
  const { run } = useRun();
  const catalogue = useApi<LookCatalogue>("/api/look");
  const saved = useApi<LookView>(runPath(run.summary.id, "/look"));
  const [choice, setChoice] = useState<LookChoice | null>(null);
  const loadingTitle = usePick(TITLES.loadingOptions);
  useEffect(() => {
    if (saved.data && !choice) setChoice({ template: saved.data.template, elements: saved.data.elements, custom: saved.data.custom });
  }, [saved.data, choice]);

  if (catalogue.error || saved.error) {
    return <SystemMessage kind="unavailable" title="Could Not Load the Template"
      action={<Button variant="secondary" size="sm" onPress={() => { catalogue.reload(); saved.reload(); }}>Try Again</Button>}>{(catalogue.error ?? saved.error)?.message}</SystemMessage>;
  }
  if (!catalogue.data || !choice || !saved.data) return <SystemMessage kind="loading" title={loadingTitle} />;
  return <TemplateStage {...props} catalogue={catalogue.data} choice={choice} setChoice={setChoice} saved={saved.data.saved} provider={saved.data.provider} savedLook={saved.data} onSaved={saved.reload} />;
}

function TemplateStage({ catalogue, choice, setChoice, saved, provider, savedLook, onSaved, ...props }: StageProps & {
  catalogue: LookCatalogue; choice: LookChoice; setChoice: Dispatch<SetStateAction<LookChoice | null>>; saved: boolean; provider?: string;
  savedLook: LookView; onSaved: () => void;
}) {
  // what the page shows that template.json does not have yet (a voice selected in the studio, a new starter…)
  const same = (a: Record<string, string>, b: Record<string, string>) =>
    Object.keys({ ...a, ...b }).every((key) => (a[key] ?? "") === (b[key] ?? ""));
  const unsaved = choice.template !== savedLook.template || !same(choice.elements, savedLook.elements) || !same(choice.custom, savedLook.custom);
  const { run, refresh } = useRun();
  const id = run.summary.id;
  const action = useAction();
  const editor = useTemplateEditor({ catalogue, choice, setChoice, provider });  // its narrator picker plays each voice itself
  const save = () => action.run("Saving…", async () => {
    await send(runPath(id, "/look"), choice);
    onSaved();  // what is saved now: the Unsaved Changes mark goes
    refresh("Template Saved: Approve It in the Checkpoint Tab, Then the Requirements Come Next");
    return "Saved";
  });
  const tabs = editor.tabs;
  return (
    <div className="stack">
      <StageTabs {...props} label="Template"
        toolbar={<>
          <span className="badge">Starter: {titleCase(choice.template)}</span>
          {unsaved ? <span className="badge badge--solid" role="status">Unsaved Changes</span> : null}
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
