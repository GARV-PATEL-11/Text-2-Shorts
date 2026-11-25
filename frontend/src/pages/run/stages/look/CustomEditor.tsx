// The user's own value for an element: a color (picker), a color or gradient (background), or text (font, voice,
// speaking rate), in a modal.
import { useEffect, useState } from "react";
import { Modal } from "../../../../components/feedback/Overlay";
import { Button } from "../../../../components/ui/Button";
import { Field } from "../../../../components/ui/fields";
import { Check, Palette } from "../../../../components/ui/icons";
import { titleCase } from "../../../../components/ui/text";
import { ColorPicker, GradientPicker } from "../../../../components/ui/pickers";
import { Tabs } from "../../../../components/ui/Tabs";
import type { LookElement } from "../../../../types/api";

export function CustomEditor({ element, value, onApply, onClose }: {
  element: LookElement | null; value: string; onApply: (value: string) => void; onClose: () => void;
}) {
  const [draft, setDraft] = useState(value);
  const [kind, setKind] = useState(value.includes(",") ? "gradient" : "solid");
  useEffect(() => {
    setDraft(value);
    setKind(value.includes(",") ? "gradient" : "solid");
  }, [value, element]);
  if (!element) return null;
  const color = element.custom?.startsWith("color");
  const solid = <ColorPicker label={titleCase(element.label)} value={draft.split(",")[0] || "#ffffff"} onChange={setDraft} />;
  let editor = solid;
  if (element.custom === "color or gradient") {
    editor = (
      <Tabs label="Color or Gradient" selected={kind}
        onChange={(next) => {
          setKind(next);
          const [top, bottom] = draft.split(",");
          setDraft(next === "gradient" ? `${top || "#2a2b31"},${bottom || "#0b0b0d"}` : top);
        }}
        tabs={[
          { id: "solid", label: "Solid", content: solid },
          { id: "gradient", label: "Gradient", content: <GradientPicker value={draft} onChange={setDraft} /> },
        ]} />
    );
  } else if (!color) {
    editor = <Field label={titleCase(element.label)} value={draft} onChange={setDraft} hint={element.custom ?? ""}
      type={element.id === "speaking_speed" ? "number" : "text"} min={0.8} max={1.2} step={0.05} />;
  }
  return (
    <Modal isOpen onOpenChange={(open) => (open ? null : onClose())} icon={<Palette />}
      title={`Your Own ${titleCase(element.label)}`} description={element.description}
      footer={<>
        <Button variant="secondary" onPress={onClose}>Cancel</Button>
        <Button icon={<Check />} onPress={() => onApply(draft.trim())} isDisabled={!draft.trim()}>Apply</Button>
      </>}>
      {editor}
    </Modal>
  );
}
