// A lookup chip: a small icon box, a value, what the value is. Used wherever a page states a few facts at a glance.
import type { ReactNode } from "react";

export function Chip({ icon, value, label }: { icon: ReactNode; value: ReactNode; label: string }) {
  return (
    <li className="chip">
      <span className="icon-box icon-box--sm" aria-hidden="true">{icon}</span>
      <span className="chip__value">{value}</span>
      <span className="chip__label">{label}</span>
    </li>
  );
}

export function Chips({ label, children }: { label: string; children: ReactNode }) {
  return <ul className="chips" aria-label={label}>{children}</ul>;
}
