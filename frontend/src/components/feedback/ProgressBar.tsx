// A progress bar: determinate (value of max) or indeterminate (value null) — never a made-up percentage.
import { Label, ProgressBar as AriaProgressBar } from "react-aria-components";

export function ProgressBar({ label, value, max, valueLabel, hideLabel }: {
  label: string; value: number | null; max: number; valueLabel?: string; hideLabel?: boolean;
}) {
  const indeterminate = value === null;
  return (
    <AriaProgressBar className={`progress${indeterminate ? " progress--indeterminate" : ""}`} value={value ?? undefined}
      maxValue={max || 1} isIndeterminate={indeterminate} valueLabel={valueLabel} aria-label={hideLabel ? label : undefined}>
      {({ percentage, valueText }) => (
        <>
          {!hideLabel ? (
            <span className="progress__head"><Label className="progress__label">{label}</Label><span className="progress__value">{valueText}</span></span>
          ) : null}
          <span className="progress__track">
            <span className="progress__fill" style={indeterminate ? undefined : { width: `${percentage}%` }} />
          </span>
        </>
      )}
    </AriaProgressBar>
  );
}
