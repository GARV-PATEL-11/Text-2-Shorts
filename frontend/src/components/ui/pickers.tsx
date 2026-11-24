// The colour picker (saturation/brightness area, hue slider, hex field, the template's colours to start from) and the
// gradient picker (top and bottom colour, as the video's gradient background draws them). The page around them stays
// black and white; the colours are the user's content.
import { useState } from "react";
import {
  ColorArea, ColorField, ColorPicker as AriaColorPicker, ColorSlider, ColorSwatch, ColorSwatchPicker,
  ColorSwatchPickerItem, ColorThumb, Input, Label, parseColor, SliderTrack,
} from "react-aria-components";
import { Button } from "./Button";
import { Swap } from "./icons";

const toHex = (value: string) => {
  try {
    return parseColor(value).toString("hex");
  } catch {
    return null;
  }
};

export function ColorPicker({ label, value, onChange, swatches = [] }: {
  label: string; value: string; onChange: (hex: string) => void; swatches?: string[];
}) {
  const color = parseColor(toHex(value) ?? "#ffffff").toFormat("hsb");
  return (
    <AriaColorPicker value={color} onChange={(next) => onChange(next.toString("hex"))}>
      <div className="color-picker" role="group" aria-label={label}>
        <ColorArea className="color-picker__area" colorSpace="hsb" xChannel="saturation" yChannel="brightness">
          <ColorThumb className="color-thumb" />
        </ColorArea>
        <ColorSlider className="color-picker__slider" colorSpace="hsb" channel="hue">
          <SliderTrack className="color-picker__track">
            <ColorThumb className="color-thumb color-thumb--slider" />
          </SliderTrack>
        </ColorSlider>
        <ColorField className="color-picker__field">
          <Label className="field__label">Hex</Label>
          <span className="color-picker__input">
            <ColorSwatch className="color-swatch" />
            <Input className="field__control" />
          </span>
        </ColorField>
        {swatches.length ? (
          <div className="color-picker__saved">
            <span className="field__label">From This Template</span>
            <ColorSwatchPicker className="swatches" aria-label="Template colours">
              {swatches.map((swatch) => (
                <ColorSwatchPickerItem key={swatch} color={swatch} className="swatches__item">
                  <ColorSwatch className="color-swatch color-swatch--round" />
                </ColorSwatchPickerItem>
              ))}
            </ColorSwatchPicker>
          </div>
        ) : null}
      </div>
    </AriaColorPicker>
  );
}

/** A two-stop vertical gradient ("top,bottom"): the video's gradient background runs from the base to the shade. */
export function GradientPicker({ value, onChange, swatches = [] }: {
  value: string; onChange: (value: string) => void; swatches?: string[];
}) {
  const [top, bottom] = value.includes(",") ? value.split(",") : [value || "#2a2b31", value || "#0b0b0d"];
  const [stop, setStop] = useState<"top" | "bottom">("top");
  const set = (which: "top" | "bottom", hex: string) => onChange(which === "top" ? `${hex},${bottom}` : `${top},${hex}`);
  return (
    <div className="gradient-picker">
      <div className="gradient-picker__preview" style={{ background: `linear-gradient(to bottom, ${top}, ${bottom})` }}>
        <button type="button" className={`gradient-picker__stop gradient-picker__stop--top${stop === "top" ? " is-active" : ""}`}
          style={{ background: top }} onClick={() => setStop("top")} aria-label="Edit the top colour" />
        <button type="button" className={`gradient-picker__stop gradient-picker__stop--bottom${stop === "bottom" ? " is-active" : ""}`}
          style={{ background: bottom }} onClick={() => setStop("bottom")} aria-label="Edit the bottom colour" />
      </div>
      <div className="gradient-picker__stops">
        <span className="field__label">Linear, Top to Bottom</span>
        <Button variant="tertiary" size="sm" icon={<Swap />} onPress={() => onChange(`${bottom},${top}`)} label="Swap the Colours" />
      </div>
      <ColorPicker
        label={stop === "top" ? "Top Colour" : "Bottom Colour"} value={stop === "top" ? top : bottom}
        onChange={(hex) => set(stop, hex)} swatches={swatches}
      />
    </div>
  );
}
