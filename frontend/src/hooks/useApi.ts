// Data from the API: cancelled when the path changes (a slow answer for run A never overwrites run B), kept while it
// reloads (no flash, no remount), and a signed-out session reported to the session.
import { useCallback, useEffect, useState } from "react";
import { useSession } from "../app/session";
import { load, loadText, SignedOut } from "../services/http";

export interface Loaded<T> {
  data: T | null;
  error: Error | null;
  loading: boolean;
  reload: () => void;
}

export function useApi<T>(path: string | null, kind: "json" | "text" = "json"): Loaded<T> {
  const { fail } = useSession();
  const [state, setState] = useState<{ data: T | null; error: Error | null; loading: boolean; for: string | null }>(
    { data: null, error: null, loading: Boolean(path), for: path },
  );
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (!path) return;
    const controller = new AbortController();
    setState((current) => ({ ...current, loading: true, error: null, data: current.for === path ? current.data : null, for: path }));
    (kind === "json" ? load<T>(path, controller.signal) : (loadText(path, controller.signal) as Promise<T>))
      .then((data) => setState({ data, error: null, loading: false, for: path }))
      .catch((error: Error) => {
        if (error.name === "AbortError") return;
        fail(error);
        if (!(error instanceof SignedOut)) setState((current) => ({ ...current, error, loading: false, for: path }));
      });
    return () => controller.abort();
  }, [path, kind, version, fail]);

  const reload = useCallback(() => setVersion((value) => value + 1), []);
  const current = state.for === path;
  return { data: current ? state.data : null, error: current ? state.error : null, loading: state.loading, reload };
}
