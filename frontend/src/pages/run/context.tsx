// What every part of a run page shares: the run, a way to re-read it after a write, and asking for a change.
import { createContext, useContext } from "react";
import type { Moment } from "../../config/voice";
import type { RunDetail } from "../../types/api";

export interface Ask {
  target: string;
  checkpoint: string | null;
}

export interface RunPageContext {
  run: RunDetail;
  /** Re-read the run (keeping everything on screen) and announce what happened. */
  refresh: (notice: string, said?: Moment) => void;
  ask: (ask: Ask) => void;
}

export const RunContext = createContext<RunPageContext | null>(null);

export function useRun(): RunPageContext {
  const context = useContext(RunContext);
  if (!context) throw new Error("useRun outside a run page");
  return context;
}
