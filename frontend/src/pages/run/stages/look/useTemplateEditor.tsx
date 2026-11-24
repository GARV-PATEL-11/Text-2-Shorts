// Choosing a template, shared by Start a Run (its first step) and a run's Template stage: the starter gallery, Build
// Your Own (every visual element, each option previewed and openable full screen at 2560×1440), the sound elements,
// and the whole look rendered as one frame. Returns the tabs and the custom-value editor; the caller owns the choice.
import { type Dispatch, type ReactNode, type SetStateAction, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { SystemMessage } from "../../../../components/feedback/SystemMessage";
import { Section } from "../../../../components/layout/Page";
import { ImagePreview } from "../../../../components/media/ImagePreview";
import { Button } from "../../../../components/ui/Button";
import { RadioCards, Toggle } from "../../../../components/ui/fields";
import { Picture } from "../../../../components/ui/icons";
import type { TabSpec } from "../../../../components/ui/Tabs";
import { titleCase } from "../../../../components/ui/text";
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

export function useTemplateEditor({ catalogue, choice, setChoice, soundExtras }: {
  catalogue: LookCatalogue; choice: LookChoice; setChoice: Dispatch<SetStateAction<LookChoice | null>>; soundExtras?: ReactNode;
}): { tabs: TabSpec[]; overlay: ReactNode; note: string | null; stillAction: ReturnType<typeof useAction> } {
  const [editing, setEditing] = useState<LookElement | null>(null);
  const [drawn, setDrawn] = useState<Record<string, OptionPictures>>({});  // optionsKey → the options in that look
  const asked = useRef(new Set<string>());
  const [note, setNote] = useState<string | null>(null);
  const [still, setStill] = useState<string | null>(null);
  const stillAction = useAction();
  const defaults = useMemo(() => catalogue.templates.find((template) => template.name === choice.template)?.elements ?? {}, [catalogue, choice.template]);
  const mode = choice.elements.theme_mode === "light" ? "light" : "dark";

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
        setNote(`The ${titleCase(element)} options could not be rendered in your look.`);
      });
  }, [choice]);
  useEffect(() => setStill(null), [choice]);  // the whole look belongs to the choice it was rendered from

  const pick = (element: string, option: string) => setChoice((current) => {
    if (!current) return current;
    const custom = { ...current.custom };
    delete custom[element];
    return { ...current, elements: { ...current.elements, [element]: option }, custom };
  });
  const renderStill = () => stillAction.run("Rendering the whole look with Manim…", async () => {
    const answer = await send<{ url: string; note?: string | null }>("/api/look/still", choice);
    setStill(answer.url);
    return answer.note ?? "The whole look is ready.";
  });
  const tree = (kind: "visual" | "sound", open: string[]) => (
    <LookTree elements={catalogue.elements.filter((element) => element.kind === kind && element.id !== "subtitles")} choice={choice}
      defaults={defaults} mode={mode} pictures={(element) => drawn[optionsKey(choice, element)]} onOpen={onOpen}
      onPick={pick} onCustom={setEditing} initiallyOpen={open} />
  );

  const tabs: TabSpec[] = [
    { id: "starters", label: "Starter Templates", content: (
      <Section title="Starter Templates">
        <RadioCards label="Starter templates" value={choice.template} layout="pictures"
          onChange={(name) => setChoice(starterChoice(catalogue, name))}
          options={catalogue.templates.map((template) => ({
            id: template.name, label: titleCase(template.name), hint: template.description,
            image: { src: starterPreview(template.name), full: starterPreview(template.name), alt: `${titleCase(template.name)} Template` },
          }))} />
      </Section>
    ) },
    { id: "look", label: "Build Your Own", content: (
      <Section title="Build Your Own" description={`Every option is drawn in your look: ${titleCase(choice.template)}, ${mode} mode.`}>
        {tree("visual", ["mode"])}
      </Section>
    ) },
    { id: "sound", label: "Sound", content: (
      <Section title="Sound" actions={soundExtras}>
        <Toggle label="Subtitles" hint="Kept with the template and previewed now; burned into the video in a later version."
          isSelected={choice.elements.subtitles === "on"} onChange={(on) => pick("subtitles", on ? "on" : "off")} />
        {tree("sound", ["narration"])}
      </Section>
    ) },
    { id: "whole", label: "Whole Look", content: (
      <Section title="Whole Look" description="One frame at 2560 × 1440, as every clip will look."
        actions={<Button icon={<Picture />} onPress={renderStill} isDisabled={stillAction.busy}>Render the Whole Look</Button>}>
        {still ? <ImagePreview src={still} fullSrc={still} alt="Whole Look" caption="Backdrop, grid, border, colors, font and sizes, at the delivery size." />
          : <SystemMessage kind="empty" title="Nothing Rendered Yet" compact>Render the whole look to see your combination.</SystemMessage>}
      </Section>
    ) },
  ];
  const overlay = (
    <CustomEditor element={editing} value={editing ? choice.custom[editing.id] ?? "" : ""} onClose={() => setEditing(null)}
      onApply={(value) => {
        if (editing) setChoice((currentChoice) => (currentChoice ? { ...currentChoice, custom: { ...currentChoice.custom, [editing.id]: value } } : currentChoice));
        setEditing(null);
      }} />
  );
  return { tabs, overlay, note, stillAction };
}
