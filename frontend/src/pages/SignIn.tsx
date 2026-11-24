// Sign in with the Claude account Claude Code is signed in to on this computer.
import { useEffect, useState } from "react";
import { navigate } from "../app/routes";
import { useSession } from "../app/session";
import { Notice } from "../components/feedback/Notice";
import { Logo } from "../components/layout/Logo";
import { Page } from "../components/layout/Page";
import { Button } from "../components/ui/Button";
import { useAction } from "../hooks/useAction";
import { load, send } from "../services/http";
import type { SessionView } from "../types/api";

export function SignInPage() {
  const { signIn } = useSession();
  const [codeSignedIn, setCodeSignedIn] = useState(true);
  const { run, busy, note } = useAction();

  useEffect(() => {
    load<SessionView>("/api/session")
      .then((session) => {
        if (session.signed_in && session.account) {
          signIn(session.account);
          navigate("#/");
        } else setCodeSignedIn(Boolean(session.claude_code_signed_in));
      })
      .catch(() => setCodeSignedIn(false));
  }, [signIn]);

  const proceed = () =>
    run("Asking Claude Code which account this computer uses…", async () => {
      const signed = await send<SessionView>("/api/session", null).catch((error) => {
        setCodeSignedIn(false);
        throw error;
      });
      if (signed.account) signIn(signed.account);
      navigate("#/");
    });

  return (
    <Page title="Sign In" width="form">
      <div className="signin">
        <p className="signin__brand"><Logo height={32} /><span>Curiosity, Illustrated.</span></p>
        <h1 className="page-header__title">Sign In</h1>
        <p className="page-header__lead">Use the Claude account your Claude Code is signed in to on this computer.</p>
        <div className="card stack">
          <Button size="lg" onPress={proceed} isDisabled={busy}>Continue with Claude</Button>
          <p className="note">No password is entered here: Faraday asks Claude Code which Claude account this computer uses. You stay signed in for 12 hours, or until you sign out.</p>
          <Notice note={note} />
        </div>
        {!codeSignedIn ? (
          <div className="card stack">
            <h2 className="section-header__title">Claude Code Is Not Signed In Here</h2>
            <ol className="steps-list">
              <li>Open a terminal on this computer.</li>
              <li>Run <code>claude auth login</code>. It opens claude.ai so you can sign in.</li>
              <li>Come back here and continue.</li>
            </ol>
          </div>
        ) : null}
      </div>
    </Page>
  );
}
