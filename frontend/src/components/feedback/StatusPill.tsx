// A status as a word with its icon (never a color alone): StatusPill from the one status vocabulary
// (config/status.tsx); Pill for any other state a page names (e.g. "Claude Is Working" on Home).
import type { ReactNode } from "react";
import { STATES } from "../../config/status";
import type { Status } from "../../types/api";

export function Pill({ icon, children, status }: { icon: ReactNode; children: ReactNode; status?: Status }) {
  return <span className="status" data-status={status}><span className="status__icon" aria-hidden="true">{icon}</span>{children}</span>;
}

export function StatusPill({ value }: { value: Status }) {
  const state = STATES[value];
  return <Pill icon={state?.icon} status={value}>{state?.label ?? value}</Pill>;
}
