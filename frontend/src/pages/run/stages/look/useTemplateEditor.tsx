// Choosing a template, shared by Start a Run (its first step) and a run's Template stage: the starter gallery (a Dark |
// Light switch over that mode's six starters, 2 × 3), an optional Build Your Own pane with every visual element (each
// option previewed and openable full screen at 2560×1440), audio and subtitles, and the whole look as one frame.
// Returns the tabs and the overlays (the pane, the custom-value editor); the caller owns the choice.
import { type Dispatch, type ReactNode, type SetStateAction, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Drawer } from "../../../../components/feedback/Overlay";
import { SystemMessage } from "../../../../components/feedback/SystemMessage";
import { Section } from "../../../../components/layout/Page";
import { ImagePreview } from "../../../../components/media/ImagePreview";
import { Button } from "../../../../components/ui/Button";
import { RadioCards, Toggle } from "../../../../components/ui/fields";
import { Check, Moon, Palette, Picture, Sun } from "../../../../components/ui/icons";
import type { TabSpec } from "../../../../components/ui/Tabs";
import { ToggleButton, ToggleButtonGroup } from "react-aria-components";
import { titleCase } from "../../../../components/ui/text";
import { Said } from "../../../../components/ui/Said";
import { useAction } from "../../../../hooks/useAction";
import { send } from "../../../../services/http";
import { starterPreview } from "../../../../services/runs";
import type { LookCatalogue, LookChoice, LookElement, LookOptionPicture, OptionPictures } from "../../../../types/api";
import { CustomEditor } from "./CustomEditor";
import { LookTree } from "./LookTree";

/** The starter's own choice: every element as the starter sets it, nothing custom. */
export const starterChoice = (catalogue: LookCatalogue, name: string): LookChoice | null => {
  const template = catalogue.templates.find((candidate) => candidate.name === name);
  return template ? { template: name, elements: { ...template.elements }, custom: {} } : null;
};


/** What an element's options depend on: the whole look except that element's own pick (its custom value counts). */
const optionsKey = (choice: LookChoice, element: string) =>
  `${element}|${JSON.stringify({ ...choice, elements: { ...choice.elements, [element]: null } })}`;

export function useTemplateEditor({ catalogue, choice, setChoice, soundExtras, next }: {
  catalogue: LookCatalogue; choice: LookChoice; setChoice: Dispatch<SetStateAction<LookChoice | null>>; soundExtras?: ReactNode;
  /** Start a Run's Continue, shown at the right of the Build Your Own line. */
  next?: ReactNode;
}): { tabs: TabSpec[]; overlay: ReactNode; note: string | null; stillAction: ReturnType<typeof useAction> } {
  const [editing, setEditing] = useState<LookElement | null>(null);
  const [drawn, setDrawn] = useState<Record<string, OptionPictures>>({});  // optionsKey → the options in that look
  const asked = useRef(new Set<string>());
  const [note, setNote] = useState<string | null>(null);
  const [still, setStill] = useState<string | null>(null);
  const stillAction = useAction();
  const defaults = useMemo(() => catalogue.templates.find((template) => template.name === choice.template)?.elements ?? {}, [catalogue, choice.template]);
  const mode = choice.elements.theme_mode === "light" ? "light" : "dark";
  const starters = catalogue.templates;  // each shown in the mode the switch is on
  const card = `${choice.template}:${mode}`;
  const [building, setBuilding] = useState(false);  // the Build Your Own pane

  const onOpen = useCallback((element: string) => {  // an element's options drawn in this look, asked once per look
    const key = optionsKey(choice, element);
    if (asked.current.has(key)) return;
    asked.current.add(key);
    setDrawn((current) => ({ ...current, [key]: "loading" }));
    send<{ pictures: LookOptionPicture[] }>("/api/look/options", { look: choice, element })
      .then((answer) => setDrawn((current) => ({ ...current, [key]: Object.fromEntries(answer.pictures.map((picture) => [picture.option, picture])) })))
      .catch(() => {
        asked.current.delete(key);
        setDrawn((current) => ({ ...current, [key]: "failed" }));
        setNote(`Could Not Render the ${titleCase(element)} Options in Your Look`);
      });
  }, [choice]);
  useEffect(() => setStill(null), [choice]);  // the whole look belongs to the choice it was rendered from

  const pick = (element: string, option: string) => setChoice((current) => {
    if (!current) return current;
    const custom = { ...current.custom };
    delete custom[element];
    return { ...current, elements: { ...current.elements, [element]: option }, custom };
  });
  const renderStill = () => stillAction.run("Rendering the Whole Look…", async () => {
    const answer = await send<{ url: string; note?: string | null }>("/api/look/still", choice);
    setStill(answer.url);
    return answer.note ?? "Whole Look Ready";
  });
  const tree = (kind: "visual" | "sound", open: string[]) => (
    <LookTree elements={catalogue.elements.filter((element) => element.kind === kind && element.id !== "subtitles")} choice={choice}
      defaults={defaults} mode={mode} pictures={(element) => drawn[optionsKey(choice, element)]} onOpen={onOpen}
      onPick={pick} onCustom={setEditing} initiallyOpen={open} />
  );

  const choose = (id: string) => {
    const [name, chosenMode] = id.split(":");
    const base = starterChoice(catalogue, name);
    if (base) setChoice({ ...base, elements: { ...base.elements, theme_mode: chosenMode } });
  };

  const tabs: TabSpec[] = [
    { id: "starters", label: "Starter Templates", content: (
      <div className="stack">
        {/* the switch is the chosen template's mode: switching keeps the template (and anything built on it) */}
        <Section title="Starter Templates" description={<Said moment="chooseLook" />} actions={
          <ToggleButtonGroup className="segmented" aria-label="Dark or Light Templates" selectionMode="single" disallowEmptySelection
            selectedKeys={[mode]} onSelectionChange={(keys) => {
              const next = [...keys][0];
              if (next) setChoice((current) => (current ? { ...current, elements: { ...current.elements, theme_mode: String(next) } } : current));
            }}>
            <ToggleButton id="dark" className="segmented__option"><Moon aria-hidden="true" />Dark</ToggleButton>
            <ToggleButton id="light" className="segmented__option"><Sun aria-hidden="true" />Light</ToggleButton>
          </ToggleButtonGroup>
        }>
          <RadioCards label={`${titleCase(mode)} Starter Templates`} value={card} layout="templates" onChange={choose}
            options={starters.map((template) => ({
              id: `${template.name}:${mode}`, label: titleCase(template.name), srLabel: titleCase(mode),
              image: { src: starterPreview(template.name, mode), full: starterPreview(template.name, mode), alt: `${titleCase(template.name)}, ${titleCase(mode)}` },
            }))} />
          <div className="build-own">
            <span>Want to Make It Your Own?</span>
            <Button variant="secondary" icon={<Palette />} onPress={() => setBuilding(true)}>Build Your Own</Button>
            {next ? <span className="build-own__next">{next}</span> : null}
          </div>
        </Section>

      </div>
    ) },
    { id: "sound", label: "Audio & Subtitles", content: (
      <Section title="Audio & Subtitles" actions={soundExtras}>
        <Toggle label="Subtitles" hint="Previewed Now; Burned Into the Video in a Later Version"
          isSelected={choice.elements.subtitles === "on"} onChange={(on) => pick("subtitles", on ? "on" : "off")} />
        {tree("sound", ["narration"])}
      </Section>
    ) },
    { id: "whole", label: "Whole Look", content: (
      <Section title="Whole Look" description="One Frame at 2560 × 1440, as Every Clip Will Look"
        actions={<Button icon={<Picture />} onPress={renderStill} isDisabled={stillAction.busy}>Render the Whole Look</Button>}>
        {still ? <ImagePreview src={still} fullSrc={still} alt="Whole Look" caption="Backdrop, Grid, Border, Colors, Font and Sizes at Delivery Size" />
          : <SystemMessage kind="empty" title="Nothing Rendered Yet" compact />}
      </Section>
    ) },
  ];
  const customEditor = (
    <CustomEditor element={editing} value={editing ? choice.custom[editing.id] ?? "" : ""} onClose={() => setEditing(null)}
      onApply={(value) => {
        if (editing) setChoice((currentChoice) => (currentChoice ? { ...currentChoice, custom: { ...currentChoice.custom, [editing.id]: value } } : currentChoice));
        setEditing(null);
      }} />
  );
  // Build Your Own: every visual element in a wide pane over the page; its custom-value editor opens inside the pane,
  // so the pane's focus scope holds both
  const overlay = (
    <>
      {building ? null : customEditor}
      <Drawer wide isOpen={building} onOpenChange={setBuilding} title="Build Your Own"
        description={`Starting From ${titleCase(choice.template)}, ${titleCase(mode)}`}
        footer={<Button icon={<Check />} onPress={() => setBuilding(false)}>Done</Button>}>
        {tree("visual", ["mode"])}
        {building ? customEditor : null}
      </Drawer>
    </>
  );
  return { tabs, overlay, note, stillAction };
}
