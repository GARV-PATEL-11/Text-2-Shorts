// A run's stages in its side rail. A step is done (filled check), current, waiting for you (says so) or upcoming; an
// optional one says so. Nothing else is written under a label.
import type { ReactNode } from "react";
import { Button } from "react-aria-components";
import { Check } from "../ui/icons";

export type StepState = "done" | "current" | "waiting" | "upcoming";
export interface Step { id: string; label: string; state: StepState; icon: ReactNode; optional?: boolean }

export function ProgressSteps({ steps, current, onSelect, label }: {
  steps: Step[]; current: string; onSelect?: (id: string) => void; label: string;
}) {
  return (
    <ol className="steps steps--vertical" aria-label={label}>
      {steps.map((step) => (
        <li key={step.id} className={`steps__item steps__item--${step.state}${step.optional ? " steps__item--optional" : ""}${step.id === current ? " is-open" : ""}`}>
          <Button className="steps__button" onPress={() => onSelect?.(step.id)} isDisabled={!onSelect}
            aria-current={step.id === current ? "step" : undefined}>
            <span className="steps__icon" aria-hidden="true">{step.state === "done" ? <Check /> : step.icon}</span>
            <span className="steps__text">
              <span className="steps__label">{step.label}</span>
              {step.state === "waiting" ? <span className="steps__hint">Waiting for You</span> : step.optional ? <span className="steps__hint">Optional</span> : null}
            </span>
          </Button>
        </li>
      ))}
    </ol>
  );
}
