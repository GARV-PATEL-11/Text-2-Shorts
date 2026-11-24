// All runs, split into ongoing and finished (one definition of "finished" for every page).
import { isFinished } from "../config/stages";
import type { RunSummary } from "../types/api";
import { useApi } from "./useApi";

export function useRuns() {
  const runs = useApi<RunSummary[]>("/api/runs");
  const all = runs.data ?? [];
  return {
    ...runs,
    ongoing: all.filter((run) => !isFinished(run)),
    finished: all.filter(isFinished),
  };
}
