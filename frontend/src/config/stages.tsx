// The stages a run goes through, as the website shows them: their order, words, icons, and where a run is. The look
// comes first (Template); Reshuffle, after the final video, is optional and never holds a run back.
import type { ReactNode } from "react";
import type { RunDetail, RunSummary, Status } from "../types/api";
import type { StepState } from "../components/navigation/ProgressSteps";
import { Clapperboard, FinalVideo, Outline, Palette, Requirements, Script, Shuffle, Storyboard } from "../components/ui/icons";

export interface StageStep {
  id: string; label: string; icon: ReactNode; checkpoint: string; batch: string[]; optional?: boolean;
}

export const STAGE_STEPS: StageStep[] = [
  { id: "template", label: "Template", icon: <Palette />, checkpoint: "template", batch: ["1 template"] },
  { id: "requirements", label: "Requirements", icon: <Requirements />, checkpoint: "requirements", batch: ["1 requirements"] },
  { id: "outline", label: "Outline", icon: <Outline />, checkpoint: "outline", batch: ["2 outline"] },
  { id: "script", label: "Script", icon: <Script />, checkpoint: "script", batch: ["3 script"] },
  { id: "plan", label: "Scene Plans", icon: <Storyboard />, checkpoint: "plan", batch: ["4 plans"] },
  { id: "scenes", label: "Scenes", icon: <Clapperboard />, checkpoint: "scenes", batch: ["5 production"] },
  { id: "final", label: "Final Video", icon: <FinalVideo />, checkpoint: "final", batch: ["final", "done"] },
  { id: "reshuffle", label: "Reshuffle", icon: <Shuffle />, checkpoint: "", batch: [], optional: true },
];
/** The stages every run must pass (the progress counts these). */
export const REQUIRED_STEPS = STAGE_STEPS.filter((step) => !step.optional);

export const isFinished = (run: RunSummary) => run.stage === "done" || (!run.readable && run.has_final);

/** Scenes as one stage, from the real scene statuses: nothing is called done unless every scene is approved. */
export function scenesStatus(run: RunDetail): Status {
  const states = run.scenes.map((scene) => scene.status);
  if (!states.length) return "pending";
  if (states.every((state) => state === "approved")) return "approved";
  for (const state of ["failed", "requires_user_approval", "requires_refactoring"] as Status[]) if (states.includes(state)) return state;
  return states.every((state) => state === "pending") && run.stages.plan !== "approved" ? "pending" : "in_progress";
}

export function stageStatuses(run: RunDetail): Record<string, Status> {
  return { ...run.stages, scenes: scenesStatus(run) };
}

/** The stage the run is at: the first one not approved. */
export function currentStage(run: RunDetail): string {
  const statuses = stageStatuses(run);
  return REQUIRED_STEPS.find((step) => statuses[step.id] !== "approved")?.id ?? "final";
}

export function stepState(run: RunDetail, id: string): StepState {
  const status = stageStatuses(run)[id] ?? "pending";
  if (status === "approved") return "done";
  if (STAGE_STEPS.find((step) => step.id === id)?.optional) return "upcoming";
  if (status === "requires_user_approval" || run.awaiting.some((checkpoint) => checkpoint.target === id)) return "waiting";
  return id === currentStage(run) ? "current" : "upcoming";
}

/** The stage a batch of next actions belongs to (change requests: the stage the run is at). */
export function batchStage(run: RunDetail): string | null {
  const stage = run.next?.stage;
  if (!stage) return null;
  return STAGE_STEPS.find((step) => step.batch.includes(stage))?.id ?? currentStage(run);
}

const BATCH_NAMES: Record<string, string> = {
  "1 template": "Template", "1 requirements": "Requirements", "2 outline": "Outline", "3 script": "Script",
  "4 plans": "Scene Plans", "5 production": "Scenes", final: "Final Video",
  "change requests": "Applying Your Changes", done: "Done",
};
/** The workflow's stage of a batch ("3 script"), in plain words. */
export const stageName = (stage: string) => BATCH_NAMES[stage] ?? stage;
