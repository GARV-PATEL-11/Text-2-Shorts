// Form controls: text fields, a select, a checkbox, a toggle and select-one cards. All share the control heights and
// borders of the tokens; states come from React Aria's data attributes.
import type { ReactNode } from "react";
import {
  Button as AriaButton, Checkbox as AriaCheckbox, FieldError, Input, Label, ListBox, ListBoxItem, Popover, Radio, RadioGroup,
  Select, SelectValue, Switch, Text, TextArea, TextField, ToggleButton, ToggleButtonGroup,
} from "react-aria-components";
import { ExpandImage, MediaImage } from "../media/ImagePreview";
import { useState } from "react";
import { Check, ChevronDown } from "./icons";
import { Markdown } from "./Markdown";

export function Field({ label, hint, value, onChange, placeholder, multiline, rows = 3, type = "text", isRequired, maxLength, min, max, step }: {
  label: string; hint?: string; value: string; onChange: (value: string) => void; placeholder?: string; multiline?: boolean;
  rows?: number; type?: string; isRequired?: boolean; maxLength?: number; min?: number; max?: number; step?: number;
}) {
  return (
    <TextField className="field" value={value} onChange={onChange} isRequired={isRequired} maxLength={maxLength}>
      <Label className="field__label">{label}{isRequired ? <span className="field__required" aria-hidden="true"> *</span> : null}</Label>
      {multiline
        ? <TextArea className="control control--area" rows={rows} placeholder={placeholder} />
        : <Input className="control" type={type} placeholder={placeholder} min={min} max={max} step={step} />}
      {hint ? <Text slot="description" className="field__hint">{hint}</Text> : null}
      <FieldError className="field__error" />
    </TextField>
  );
}

/** A multi-line field that takes Markdown: Write, or Preview it rendered as it will be shown. */
export function MarkdownField({ label, hint, value, onChange, placeholder, rows = 4, isRequired, maxLength }: {
  label: string; hint?: string; value: string; onChange: (value: string) => void; placeholder?: string; rows?: number;
  isRequired?: boolean; maxLength?: number;
}) {
  const [preview, setPreview] = useState(false);
  return (
    <div className="md-field">
      <ToggleButtonGroup className="segmented md-field__modes" aria-label={`${label}: Write or Preview (Markdown Supported)`} selectionMode="single"
        disallowEmptySelection selectedKeys={[preview ? "preview" : "write"]} onSelectionChange={(keys) => setPreview(keys.has("preview"))}>
        <span className="md-field__tag" aria-hidden="true">Markdown</span>
        <ToggleButton id="write" className="segmented__option">Write</ToggleButton>
        <ToggleButton id="preview" className="segmented__option">Preview</ToggleButton>
      </ToggleButtonGroup>
      {preview ? (
        <div className="field">
          <span className="field__label">{label}</span>
          <div className="md-field__preview">{value.trim() ? <Markdown text={value} /> : <p className="note">Nothing to Preview Yet</p>}</div>
        </div>
      ) : (
        <Field label={label} value={value} onChange={onChange} multiline rows={rows} placeholder={placeholder} isRequired={isRequired}
          maxLength={maxLength} hint={hint} />
      )}
    </div>
  );
}

export interface Choice { id: string; label: string; detail?: string }

export function SelectField({ label, value, onChange, options, hint, hideLabel }: {
  label: string; value: string; onChange: (value: string) => void; options: Choice[]; hint?: string; hideLabel?: boolean;
}) {
  return (
    <Select className="field" selectedKey={value} onSelectionChange={(key) => onChange(String(key))}>
      <Label className={hideLabel ? "sr-only" : "field__label"}>{label}</Label>
      <AriaButton className="control select">
        <SelectValue className="select__value" />
        <ChevronDown />
      </AriaButton>
      {hint ? <Text slot="description" className="field__hint">{hint}</Text> : null}
      <Popover className="popover">
        <ListBox className="listbox">
          {options.map((option) => (
            <ListBoxItem key={option.id} id={option.id} textValue={option.label} className="listbox__item">
              <span className="listbox__label">{option.label}</span>
              {option.detail ? <span className="listbox__detail">{option.detail}</span> : null}
              <span className="listbox__check" aria-hidden="true"><Check /></span>
            </ListBoxItem>
          ))}
        </ListBox>
      </Popover>
    </Select>
  );
}

export function Checkbox({ label, hint, isSelected, onChange }: {
  label: string; hint?: string; isSelected: boolean; onChange: (selected: boolean) => void;
}) {
  return (
    <AriaCheckbox className="choice" isSelected={isSelected} onChange={onChange}>
      <span className="choice__box" aria-hidden="true"><Check /></span>
      <span className="choice__text"><span className="choice__label">{label}</span>{hint ? <span className="choice__hint">{hint}</span> : null}</span>
    </AriaCheckbox>
  );
}

export function Toggle({ label, hint, isSelected, onChange }: {
  label: string; hint?: string; isSelected: boolean; onChange: (selected: boolean) => void;
}) {
  return (
    <Switch className="choice toggle" isSelected={isSelected} onChange={onChange}>
      <span className="toggle__track" aria-hidden="true"><span className="toggle__thumb" /></span>
      <span className="choice__text"><span className="choice__label">{label}</span>{hint ? <span className="choice__hint">{hint}</span> : null}</span>
    </Switch>
  );
}

export interface CardOption {
  id: string; label: string; hint?: string; badge?: string; image?: { src: string; full?: string; alt: string }; placeholder?: string; loading?: boolean;
  /** Said to screen readers after the label (e.g. a twin's mode). */
  srLabel?: string;
}

/** Select one, as cards. A card's picture is part of the choice; its Full Screen button sits beside the radio, not inside
 * its label, so the two controls never nest. */
export function RadioCards({ label, value, onChange, options, layout = "list" }: {
  label: string; value: string; onChange: (value: string) => void; options: CardOption[]; layout?: "list" | "pictures" | "segmented" | "templates";
}) {
  const hintId = (option: CardOption) => `hint-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${option.id}`;
  return (
    <RadioGroup className={`cards cards--${layout}`} value={value} onChange={onChange} aria-label={label}>
      {options.map((option) => (
        <div key={option.id} className="cards__item">
          <Radio value={option.id} className="card-choice" aria-describedby={option.hint ? hintId(option) : undefined}>
            <span className="card-choice__head">
              {layout === "list" || layout === "segmented" ? <span className="card-choice__dot" aria-hidden="true" /> : null}
              <span className="card-choice__label">{option.label}{option.srLabel ? <span className="sr-only">{`, ${option.srLabel}`}</span> : null}</span>
              {option.badge ? <span className="badge">{option.badge}</span> : null}
            </span>
            {option.image ? <MediaImage src={option.image.src} alt="" ratio="16/9" fit="cover" /> : null}
            {!option.image && option.placeholder ? <span className={`media media--empty${option.loading ? " media--rendering" : ""}`}>{option.placeholder}</span> : null}
            {option.hint ? <span className="card-choice__hint" id={hintId(option)}>{option.hint}</span> : null}
          </Radio>
          {option.image ? <ExpandImage src={option.image.src} fullSrc={option.image.full} alt={option.image.alt} /> : null}
        </div>
      ))}
    </RadioGroup>
  );
}

export function FormRow({ children }: { children: ReactNode }) {
  return <div className="form-row">{children}</div>;
}
