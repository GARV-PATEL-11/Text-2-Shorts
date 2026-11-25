// Reshuffle, the optional last stage: the look reshuffled by a seed, the same seed always giving the same look. Only
// colors, fonts, background, grid and border change, never sizes, so every clip keeps its layout. Applying it
// recolors the built clips without Claude and keeps the current final video in versions/; the scene previews and the
// final video are then rendered again.
import { useState } from "react";
import { navigate } from "../../../app/routes";
import { Notice } from "../../../components/feedback/Notice";
import { Modal } from "../../../components/feedback/Overlay";
import { SystemMessage } from "../../../components/feedback/SystemMessage";
import { Section } from "../../../components/layout/Page";
import { ImagePreview } from "../../../components/media/ImagePreview";
import { Button } from "../../../components/ui/Button";
import { Checkbox, Field } from "../../../components/ui/fields";
import { Dice, Preview, Shuffle } from "../../../components/ui/icons";
import { titleCase } from "../../../components/ui/text";
import { stageStatuses } from "../../../config/stages";
import { useAction } from "../../../hooks/useAction";
import { send } from "../../../services/http";
import { runHash, runPath } from "../../../services/runs";
import type { ReshuffleGroup, ReshuffleView } from "../../../types/api";
import { useRun } from "../context";
import type { StageProps } from "./StageTabs";

const GROUPS: { id: ReshuffleGroup; label: string; hint: string }[] = [
  { id: "colours", label: "Colors & Palettes", hint: "Primary, Secondary and Accent Palettes" },
  { id: "fonts", label: "Fonts", hint: "Text and Math Fonts" },
  { id: "background", label: "Background", hint: "Type and Color" },
  { id: "grid", label: "Grid", hint: "Type, Color and Opacity" },
  { id: "border", label: "Border", hint: "Style and Color" },
];
const newSeed = () => String(Math.floor(Math.random() * 1_000_000));

export function Reshuffle(_: StageProps) {
  const { run, refresh } = useRun();
  const id = run.summary.id;
  const [groups, setGroups] = useState<ReshuffleGroup[]>(["colours"]);
  const [seed, setSeed] = useState(newSeed);
  const [view, setView] = useState<ReshuffleView | null>(null);
  const [still, setStill] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const action = useAction();

  if (stageStatuses(run).template !== "approved") {
    return (
      <SystemMessage kind="pending" title="Choose a Template First"
        action={<Button size="sm" onPress={() => navigate(runHash(id, "template"))}>Open Template</Button>}>
        A Reshuffle Starts From the Run's Approved Template
      </SystemMessage>
    );
  }
  const valid = groups.length > 0 && /^\d{1,9}$/.test(seed);
  const wanted = { seed: Number(seed), groups };
  const forget = () => {  // a preview belongs to the seed and groups it was made from
    setView(null);
    setStill(null);
  };
  const toggle = (group: ReshuffleGroup, on: boolean) => {
    setGroups((current) => (on ? [...current, group] : current.filter((candidate) => candidate !== group)));
    forget();
  };
  const preview = () => action.run("Reshuffling, Then Rendering One Frame…", async () => {
    const answer = await send<ReshuffleView>(runPath(id, "/reshuffle"), { ...wanted, apply: false });
    setView(answer);
    if (!answer.changes.length) return "Nothing Changes With This Seed: Try Another";
    setStill((await send<{ url: string }>(runPath(id, "/look/still"), answer.look)).url);
    return `${answer.changes.length} Elements Change`;
  });
  const apply = () => action.run("Recoloring Every Built Clip…", async () => {
    await send<ReshuffleView>(runPath(id, "/reshuffle"), { ...wanted, apply: true });
    setConfirming(false);
    forget();
    refresh(`Reshuffle Applied (Seed ${seed}): Send Any Message in the Console and Claude Renders the Previews and Final Video Again`);
  });

  return (
    <Section title="Reshuffle the Look"
      description="Colors, Fonts and Backgrounds Change; Layouts Never Do">
      <div className="split">
        <div className="card stack">
          <fieldset className="fieldset">
            <legend className="field__label">What to Reshuffle</legend>
            {GROUPS.map((group) => (
              <Checkbox key={group.id} label={group.label} hint={group.hint} isSelected={groups.includes(group.id)} onChange={(on) => toggle(group.id, on)} />
            ))}
          </fieldset>
          <div className="seed">
            <Field label="Seed" type="number" value={seed} min={0} step={1} hint="The Same Seed Always Gives the Same Look"
              onChange={(value) => { setSeed(value); forget(); }} />
            <Button variant="secondary" icon={<Dice />} onPress={() => { setSeed(newSeed()); forget(); }}>New Seed</Button>
          </div>
          <div className="form-foot">
            <Button variant="secondary" icon={<Preview />} onPress={preview} isDisabled={!valid || action.busy}>Preview</Button>
            <Button icon={<Shuffle />} onPress={() => setConfirming(true)} isDisabled={!view?.changes.length || action.busy}>Apply Reshuffle</Button>
          </div>
          <Notice note={action.note} />
        </div>
        <div className="stack">
          {still ? <ImagePreview src={still} fullSrc={still} alt={`Reshuffled Look (Seed ${seed})`} caption="One Frame at 2560 × 1440, as Every Clip Would Get It" />
            : <SystemMessage kind="empty" title="No Preview Yet" compact />}
          {view?.changes.length ? (
            <div className="table-wrap" tabIndex={0} role="region" aria-label="What changes (scrolls sideways on small screens)">
              <table className="table table--compact">
                <thead><tr><th scope="col">Element</th><th scope="col">Now</th><th scope="col">After</th></tr></thead>
                <tbody>
                  {view.changes.map((change) => (
                    <tr key={change.element}><td>{titleCase(change.element)}</td><td className="table__muted">{titleCase(change.before)}</td><td>{titleCase(change.after)}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      </div>
      <Modal isOpen={confirming} onOpenChange={setConfirming} icon={<Shuffle />} title="Apply This Reshuffle?"
        description="Recolors Every Built Clip, Then Renders the Previews and Final Video Again. The Current Final Video Is Kept; Every Scene Needs Approval Again."
        footer={<>
          <Button variant="secondary" onPress={() => setConfirming(false)}>Cancel</Button>
          <Button icon={<Shuffle />} onPress={apply} isDisabled={action.busy}>Apply Reshuffle</Button>
        </>} />
    </Section>
  );
}
