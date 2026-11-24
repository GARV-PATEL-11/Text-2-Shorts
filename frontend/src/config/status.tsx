// One status vocabulary for the whole interface: the word, the icon and the chart fill of every state a stage, scene or
// clip can be in. StatusPill, the clips chart and the run overview read it; nothing else names a state.
import type { ReactNode } from "react";
import { Done, Failed, NotStarted, Waiting, Working } from "../components/ui/icons";
import type { Status } from "../types/api";

export type Bucket = "done" | "working" | "waiting" | "failed" | "not-started";
export interface StateWord { label: string; icon: ReactNode; bucket: Bucket }

export const STATES: Record<Status, StateWord> = {
  approved: { label: "Approved", icon: <Done />, bucket: "done" },
  completed: { label: "Done", icon: <Done />, bucket: "done" },
  in_progress: { label: "In Progress", icon: <Working />, bucket: "working" },
  requires_refactoring: { label: "Being Revised", icon: <Working />, bucket: "working" },
  requires_user_approval: { label: "Waiting for You", icon: <Waiting />, bucket: "waiting" },
  failed: { label: "Failed", icon: <Failed />, bucket: "failed" },
  pending: { label: "Not Started", icon: <NotStarted />, bucket: "not-started" },
};

/** The chart's legend, in order: one word per bucket. */
export const BUCKETS: { id: Bucket; label: string }[] = [
  { id: "done", label: "Done" },
  { id: "working", label: "In Progress" },
  { id: "waiting", label: "Waiting for You" },
  { id: "failed", label: "Failed" },
  { id: "not-started", label: "Not Started" },
];
export const bucketOf = (status: Status): Bucket => STATES[status]?.bucket ?? "not-started";
