// Progress steps: horizontal (a wizard's steps, the stages on Home) or vertical (a run's stages in its side rail).
// A step is done (filled check), current, waiting for you (bold, says so) or upcoming; its label never moves.
import type { ReactNode } from "react";
import { Button } from "react-aria-components";
import { Check } from "../ui/icons";

export type StepState = "done" | "current" | "waiting" | "upcoming";
export interface Step { id: string; label: string; hint: string; state: StepState; icon: ReactNode; optional?: boolean }

export function ProgressSteps({ steps, current, onSelect, orientation = "horizontal", label = "Steps, in order" }: {
  steps: Step[]; current: string; onSelect?: (id: string) => void; orientation?: "horizontal" | "vertical"; label?: string;
}) {
  return (
    <ol className={`steps steps--${orientation}`} aria-label={label}>
      {steps.map((step) => (
        <li key={step.id} className={`steps__item steps__item--${step.state}${step.optional ? " steps__item--optional" : ""}${step.id === current ? " is-open" : ""}`}>
          <Button className="steps__button" onPress={() => onSelect?.(step.id)} isDisabled={!onSelect}
            aria-current={step.id === current ? "step" : undefined}>
            <span className="steps__icon" aria-hidden="true">{step.state === "done" ? <Check /> : step.icon}</span>
            <span className="steps__text">
              <span className="steps__label">{step.label}</span>
              <span className="steps__hint">{step.state === "waiting" ? "Waiting for You" : step.hint}</span>
            </span>
          </Button>
        </li>
      ))}
    </ol>
  );
}
