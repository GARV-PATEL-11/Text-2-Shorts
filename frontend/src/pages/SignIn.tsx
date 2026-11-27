// Sign in with the Claude account Claude Code is signed in to on this computer.
import { useEffect, useState } from "react";
import { navigate } from "../app/routes";
import { afterSignIn, useSession } from "../app/session";
import { Notice } from "../components/feedback/Notice";
import { Logo } from "../components/layout/Logo";
import { Page } from "../components/layout/Page";
import { Said } from "../components/ui/Said";
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
          navigate(afterSignIn());
        } else setCodeSignedIn(Boolean(session.claude_code_signed_in));
      })
      .catch(() => setCodeSignedIn(false));
  }, [signIn]);

  const proceed = () =>
    run("Checking Your Sign-In…", async () => {
      const signed = await send<SessionView>("/api/session", null).catch((error) => {
        setCodeSignedIn(false);
        throw error;
      });
      if (signed.account) signIn(signed.account);
      navigate(afterSignIn());
    });

  return (
    <Page title="Sign In" width="form">
      <div className="signin">
        <p className="signin__brand"><Logo height={32} /><span>Curiosity, Illustrated.</span></p>
        <h1 className="page-header__title">Sign In</h1>
        <p className="page-header__lead">Uses the Claude Account Already on This Computer</p>
        <Said moment="welcome" block />
        <div className="card stack">
          <Button onPress={proceed} isDisabled={busy}>Continue with Claude</Button>
          <p className="note">No Password Needed: You Stay Signed In for 12 Hours</p>
          <Notice note={note} />
        </div>
        {!codeSignedIn ? (
          <div className="card stack">
            <h2 className="section-header__title">Claude Code Is Not Signed In</h2>
            <ol className="steps-list">
              <li>Open a Terminal on This Computer</li>
              <li>Run <code>claude auth login</code>. It Opens claude.ai So You Can Sign In</li>
              <li>Come Back Here and Continue</li>
            </ol>
          </div>
        ) : null}
      </div>
    </Page>
  );
}
