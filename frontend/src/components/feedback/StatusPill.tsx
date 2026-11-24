// A status in words (never only a colour): filled for done, outlined for in progress, bold for waiting on you.
import type { Status } from "../../types/api";

const WORDS: Record<Status, string> = {
  pending: "Not Started", in_progress: "In Progress", completed: "Done", failed: "Failed",
  requires_refactoring: "Being Fixed", requires_user_approval: "Waiting for You", approved: "Approved",
};

export function StatusPill({ value }: { value: Status }) {
  return <span className="status" data-status={value}>{WORDS[value] ?? value}</span>;
}
