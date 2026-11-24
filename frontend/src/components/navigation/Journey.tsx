// The journey: every stage of a run in one compact row (done, current, waiting, upcoming; the optional one dashed), and
// under it the current stage's sub-steps, numbered, one after the other. One strip instead of a heading and a paragraph.
import type { ReactNode } from "react";
import { Check } from "../ui/icons";
import type { StepState } from "./ProgressSteps";

export interface JourneyStage { id: string; label: string; icon: ReactNode; state: StepState; optional?: boolean }
export interface JourneyStep { id: string; label: string; state: StepState; open?: boolean }  // open: reachable though upcoming

export function Journey({ label, stages, steps, current, onStep }: {
  label: string; stages: JourneyStage[]; steps: JourneyStep[]; current: string; onStep?: (id: string) => void;
}) {
  return (
    <nav className="journey" aria-label={label}>
      <ol className="journey__stages">
        {stages.map((stage) => (
          <li key={stage.id} className={`journey__stage journey__stage--${stage.state}${stage.optional ? " journey__stage--optional" : ""}`}
            aria-current={stage.state === "current" ? "step" : undefined} title={stage.optional ? `${stage.label} (Optional)` : stage.label}>
            <span className="journey__icon" aria-hidden="true">{stage.state === "done" ? <Check /> : stage.icon}</span>
            <span className="journey__label">{stage.label}</span>
          </li>
        ))}
      </ol>
      <ol className="journey__steps" aria-label="Steps of this stage">
        {steps.map((step, index) => (
          <li key={step.id}>
            <button type="button" className={`journey__step journey__step--${step.state}`} aria-current={step.id === current ? "step" : undefined}
              onClick={() => onStep?.(step.id)} disabled={!onStep || (step.state === "upcoming" && !step.open)}>
              <span className="journey__number" aria-hidden="true">{step.state === "done" ? <Check /> : index + 1}</span>
              {step.label}
            </button>
          </li>
        ))}
      </ol>
    </nav>
  );
}
