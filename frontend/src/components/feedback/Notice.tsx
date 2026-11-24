// The outcome of an action, announced once: both live regions are always on the page (a region inserted with its
// text already in it is often not read out); errors go to the assertive one.
import type { Note } from "../../hooks/useAction";

export function Notice({ note }: { note: Note | null }) {
  return (
    <>
      <p className="notice" role="status" aria-live="polite">{note && !note.error ? note.text : ""}</p>
      <p className="notice notice--error" role="alert" aria-live="assertive">{note?.error ? note.text : ""}</p>
    </>
  );
}
