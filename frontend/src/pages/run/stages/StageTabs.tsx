// A stage's sub-stages as tabs; the open tab lives in the address (#/runs/<run>/<stage>/<tab>), so a reload or a
// shared link opens the same place.
import type { ReactNode } from "react";
import { navigate } from "../../../app/routes";
import { type TabSpec, Tabs } from "../../../components/ui/Tabs";
import { runHash } from "../../../services/runs";
import { useRun } from "../context";

export interface StageProps { stage: string; tab?: string }

export function StageTabs({ stage, tab, label, tabs, toolbar }: StageProps & { label: string; tabs: TabSpec[]; toolbar?: ReactNode }) {
  const { run } = useRun();
  const selected = tabs.some((candidate) => candidate.id === tab) ? (tab as string) : tabs[0].id;
  return <Tabs label={label} selected={selected} onChange={(next) => navigate(runHash(run.summary.id, stage, next))} tabs={tabs} toolbar={toolbar} />;
}

export const waiting = (awaiting: { target: string }[], target: string) => (awaiting.some((checkpoint) => checkpoint.target === target) ? 1 : 0);
