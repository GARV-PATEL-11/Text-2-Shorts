// The signed-in account and one way to report failures: a signed-out session sends you to sign in; anything else is
// shown where it happened (pages use useApi/useAction), so a failed write never takes over the whole page.
import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { load, send, SignedOut } from "../services/http";
import type { Account, SessionView } from "../types/api";
import { navigate } from "./routes";

interface Session {
  account: Account | null;
  checked: boolean;
  signIn: (account: Account) => void;
  /** Resolves to an error message when the server could not end the session (you stay signed in). */
  signOut: () => Promise<string | null>;
  /** Report an error from anywhere: SignedOut ends the session; other errors are returned for local display. */
  fail: (error: unknown) => void;
}

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [account, setAccount] = useState<Account | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    load<SessionView>("/api/session")
      .then((session) => {
        setAccount(session.signed_in ? session.account ?? null : null);
        if (!session.signed_in) navigate("#/signin");
      })
      .catch(() => navigate("#/signin"))
      .finally(() => setChecked(true));
  }, []);

  const fail = useCallback((error: unknown) => {
    if (error instanceof SignedOut) {
      setAccount(null);
      navigate("#/signin");
    }
  }, []);
  const signOut = useCallback(async () => {
    try {
      await send("/api/session", null, "DELETE");
    } catch (error) {
      return `Signing out failed: ${(error as Error).message}`;
    }
    setAccount(null);
    navigate("#/signin");
    return null;
  }, []);

  const value = useMemo(() => ({ account, checked, signIn: setAccount, signOut, fail }), [account, checked, signOut, fail]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) throw new Error("useSession outside SessionProvider");
  return session;
}
