// The feedback contract: one component for every state that is not content — loading, processing, pending, empty,
// missing, unavailable, offline, unsupported, restricted, success and error. Styled like a game's system message: a
// small spaced label, a short heading, one line of context, an action where there is one. Kinds differ by label,
// icon and border (solid · dashed · dotted · double; white only for success and error), never by color.
import type { ReactNode } from "react";
import { Done, Empty, Error, Film, Lock, Offline, Pending, Unavailable, Unsupported, Working } from "../ui/icons";
import { ProgressBar } from "./ProgressBar";

export type MessageKind =
  | "loading" | "processing" | "pending" | "empty" | "missing" | "unavailable" | "offline" | "unsupported"
  | "restricted" | "success" | "error";

// Each kind: its word, its icon and how urgent it is. "Nothing Here": there is no such data. "Not Made Yet": it will be
// made later in the run. "Unavailable": the server answered with an error. "Connection Lost": no answer at all.
const KINDS: Record<MessageKind, { label: string; icon: ReactNode; urgent: boolean }> = {
  loading: { label: "Loading", icon: <span className="spinner" />, urgent: false },
  processing: { label: "Processing", icon: <Working />, urgent: false },
  pending: { label: "Pending", icon: <Pending />, urgent: false },
  empty: { label: "Nothing Here", icon: <Empty />, urgent: false },
  missing: { label: "Not Made Yet", icon: <Film />, urgent: false },
  unavailable: { label: "Unavailable", icon: <Unavailable />, urgent: true },
  offline: { label: "Connection Lost", icon: <Offline />, urgent: true },
  unsupported: { label: "Not Supported", icon: <Unsupported />, urgent: false },
  restricted: { label: "Access Restricted", icon: <Lock />, urgent: true },
  success: { label: "Done", icon: <Done />, urgent: false },
  error: { label: "Error", icon: <Error />, urgent: true },
};

export function SystemMessage({ kind, title, children, action, progress, compact }: {
  kind: MessageKind; title: string; children?: ReactNode; action?: ReactNode;
  /** 0–1 for measurable work, "indeterminate" when it cannot be measured. */
  progress?: number | "indeterminate"; compact?: boolean;
}) {
  const spec = KINDS[kind];
  return (
    <div className={`sysmsg sysmsg--${kind}${compact ? " sysmsg--compact" : ""}`} role={spec.urgent ? "alert" : "status"}>
      <span className="sysmsg__icon" aria-hidden="true">{spec.icon}</span>
      <div className="sysmsg__body">
        <span className="sysmsg__label">{spec.label}</span>
        <p className="sysmsg__title">{title}</p>
        {children ? <p className="sysmsg__text">{children}</p> : null}
        {action ? <div className="sysmsg__action">{action}</div> : null}
        {progress !== undefined ? (
          <ProgressBar label={title} value={progress === "indeterminate" ? null : Math.round(progress * 100)} max={100} hideLabel />
        ) : null}
      </div>
    </div>
  );
}
