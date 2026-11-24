// A status as a word with its icon (never a color alone), from the one status vocabulary (config/status.tsx).
import { STATES } from "../../config/status";
import type { Status } from "../../types/api";

export function StatusPill({ value }: { value: Status }) {
  const state = STATES[value];
  return <span className="status" data-status={value}><span className="status__icon" aria-hidden="true">{state?.icon}</span>{state?.label ?? value}</span>;
}
