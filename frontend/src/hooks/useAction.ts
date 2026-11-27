// A write the user started: busy while it runs, then one message — what happened, or what went wrong and why.
import { useCallback, useState } from "react";
import { useSession } from "../app/session";
import { errorText, SignedOut } from "../services/http";
import { log } from "../services/log";

export interface Note {
  text: string;
  error?: boolean;
}

export function useAction() {
  const { fail } = useSession();
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<Note | null>(null);

  const run = useCallback(
    async (working: string, work: () => Promise<string | void>) => {
      setBusy(true);
      setNote({ text: working });
      log.info(working);
      try {
        const done = await work();
        setNote(done ? { text: done } : null);
        return true;
      } catch (error) {
        if ((error as Error).name === "AbortError") return false;  // the page stopped following on purpose
        fail(error);
        if (!(error instanceof SignedOut)) log.error(`Failed: ${working}`, error);
        if (!(error instanceof SignedOut)) setNote({ text: errorText(error), error: true });
        return false;
      } finally {
        setBusy(false);
      }
    },
    [fail],
  );
  return { run, busy, note, setNote };
}
