// The elements of a look or a sound, grouped, as plain disclosures (a branch per group, one per element). Each element
// shows its choice and whether it is the template's default, changed, or the user's own value. Opening an element asks
// for its options drawn in the user's own look (onOpen); until they arrive each card says they are being rendered.
import { useEffect, useState } from "react";
import { RadioCards } from "../../../../components/ui/fields";
import { ChevronDown, ChevronRight } from "../../../../components/ui/icons";
import { usePick } from "../../../../components/ui/Said";
import { titleCase } from "../../../../components/ui/text";
import { TITLES } from "../../titles";
import type { LookChoice, LookElement, OptionPictures } from "../../../../types/api";

const GROUP_NAMES: Record<string, string> = {
  mode: "Mode", background: "Background", grid: "Grid", colour: "Color", type: "Type", border: "Border",
  narration: "Narration", subtitles: "Subtitles",
};
export const CUSTOM = "__custom__";
/** The tree's open/closed mark: Untitled UI chevrons, one shown at a time by CSS from the details' [open]. */
const Chevron = () => (
  <>
    <span className="tree__chevron tree__chevron--closed" aria-hidden="true"><ChevronRight /></span>
    <span className="tree__chevron tree__chevron--open" aria-hidden="true"><ChevronDown /></span>
  </>
);

export function LookTree({ elements, choice, defaults, mode, pictures, onOpen, onPick, onCustom, initiallyOpen = [], flat }: {
  elements: LookElement[]; choice: LookChoice; defaults: Record<string, string>; mode: string;
  pictures: (element: string) => OptionPictures | undefined; onOpen: (element: string) => void;
  onPick: (element: string, option: string) => void; onCustom: (element: LookElement) => void; initiallyOpen?: string[];
  /** One group shown under its own heading already (Subtitles): its elements without a group branch. */
  flat?: boolean;
}) {
  const rendering = usePick(TITLES.renderingOption);
  const [open, setOpen] = useState(() => new Set(initiallyOpen));
  useEffect(() => {  // every open element's options, in the look as it is now (asked again when the look changes)
    for (const element of elements) if (element.previewed && open.has(element.id)) onOpen(element.id);
  }, [open, choice, elements, onOpen]);
  const toggle = (key: string, isOpen: boolean) => setOpen((current) => {
    const next = new Set(current);
    if (isOpen) next.add(key);
    else next.delete(key);
    return next;
  });
  const item = (element: LookElement) => {
    const custom = choice.custom[element.id];
    const chosen = element.options.find((option) => option.id === choice.elements[element.id]);
    const mark = custom ? "custom" : choice.elements[element.id] === defaults[element.id] ? "default" : "changed";
    const drawn = element.previewed ? pictures(element.id) : undefined;
    const picture = (option: string, label: string) => {
      if (!element.previewed) return {};
      if (drawn === "failed") return { placeholder: "Preview Unavailable" };
      if (!drawn || drawn === "loading") return { placeholder: rendering, loading: true };
      const ready = drawn[option];
      if (!ready?.url) return { placeholder: ready ? "Text Cannot Be Read in This Look" : "Choose a Value to See It" };
      return { image: { src: ready.url, full: ready.full ?? undefined, alt: `${titleCase(element.label)}: ${label} (${titleCase(mode)} Mode)` } };
    };
    return (
      <li key={element.id}>
        <details open={open.has(element.id)} onToggle={(event) => toggle(element.id, (event.target as HTMLDetailsElement).open)}>
          <summary><Chevron />
            <span className="tree__name">{titleCase(element.label)}</span>
            <span className="tree__value">{custom || titleCase(chosen?.label ?? "")}</span>
            {mark === "default" ? null : <span className="badge badge--solid">{titleCase(mark)}</span>}
          </summary>
          {open.has(element.id) ? (
            <div className="tree__body">
              {element.description ? <p className="note">{element.description}</p> : null}
              <RadioCards
                label={element.label}
                value={custom ? CUSTOM : choice.elements[element.id]}
                layout={element.previewed ? "pictures" : element.options.length <= 3 ? "segmented" : "list"}
                onChange={(value) => (value === CUSTOM ? onCustom(element) : onPick(element.id, value))}
                options={[
                  ...element.options.map((option) => ({
                    id: option.id, label: titleCase(option.label), hint: option.detail || undefined,
                    badge: option.id === defaults[element.id] ? "Default" : undefined,
                    ...picture(option.id, titleCase(option.label)),
                  })),
                  ...(element.custom ? [{
                    id: CUSTOM, label: "Custom", hint: custom || `Your Own ${titleCase(element.custom)}`,
                    ...(custom ? picture(CUSTOM, "Your Value") : element.previewed ? { placeholder: "Choose a Value to See It" } : {}),
                  }] : []),
                ]}
              />
            </div>
          ) : null}
        </details>
      </li>
    );
  };
  const groups = [...new Set(elements.map((element) => element.group))];
  if (flat) return <ul className="tree tree--flat">{elements.map(item)}</ul>;
  return (
    <ul className="tree">
      {groups.map((group) => (
        <li key={group}>
          <details open={open.has(group)} onToggle={(event) => toggle(group, (event.target as HTMLDetailsElement).open)}>
            <summary><Chevron /><span className="tree__name">{GROUP_NAMES[group] ?? titleCase(group)}</span></summary>
            <ul>
              {elements.filter((element) => element.group === group).map(item)}
            </ul>
          </details>
        </li>
      ))}
    </ul>
  );
}
