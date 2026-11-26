// The journey as a breadcrumb: every stage of a run in one line (done ticked, the current one white, upcoming quiet),
// and under it the current stage's steps as a smaller breadcrumb of their own. Text and chevrons only: two short lines.
import { Button } from "react-aria-components";
import { Check, ChevronRight } from "../ui/icons";
import type { StepState } from "./ProgressSteps";

export interface JourneyStage { id: string; label: string; state: StepState; optional?: boolean }
export interface JourneyStep { id: string; label: string; state: StepState; open?: boolean }  // open: reachable though upcoming

export function Journey({ label, stages, steps, current, onStep }: {
  label: string; stages: JourneyStage[]; steps: JourneyStep[]; current: string; onStep?: (id: string) => void;
}) {
  return (
    <nav className="journey" aria-label={label}>
      <ol className="journey__stages">
        {stages.map((stage, index) => (
          <li key={stage.id} className={`journey__stage journey__stage--${stage.state}${stage.optional ? " journey__stage--optional" : ""}`}
            aria-current={stage.state === "current" ? "step" : undefined}>
            {index ? <span className="journey__sep" aria-hidden="true"><ChevronRight /></span> : null}
            {stage.state === "done" ? <span className="journey__tick" aria-hidden="true"><Check /></span> : null}
            {stage.label}{stage.optional ? <span className="sr-only"> (Optional)</span> : null}
          </li>
        ))}
      </ol>
      {steps.length ? <ol className="journey__steps" aria-label="Steps of this stage">
        {steps.map((step, index) => (
          <li key={step.id} className="journey__crumb">
            {index ? <span className="journey__sep" aria-hidden="true"><ChevronRight /></span> : null}
            <Button className={`journey__step journey__step--${step.state}`} aria-current={step.id === current ? "step" : undefined}
              onPress={() => onStep?.(step.id)} isDisabled={!onStep || (step.state === "upcoming" && !step.open)}>
              {step.state === "done" ? <span className="journey__tick" aria-hidden="true"><Check /></span> : null}
              {step.label}
            </Button>
          </li>
        ))}
      </ol> : null}
    </nav>
  );
}
