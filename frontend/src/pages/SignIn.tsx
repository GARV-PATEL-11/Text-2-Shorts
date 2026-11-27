// Sign in with the Claude account Claude Code is signed in to on this computer.
import { useEffect, useState } from "react";
import { navigate } from "../app/routes";
import { afterSignIn, useSession } from "../app/session";
import { Notice } from "../components/feedback/Notice";
import { Logo } from "../components/layout/Logo";
import { Page } from "../components/layout/Page";
import { Said, usePick } from "../components/ui/Said";
import { WithCode } from "../components/ui/text";
import { TITLES } from "../config/titles";
import { Button } from "../components/ui/Button";
import { useAction } from "../hooks/useAction";
import { ApiError, load, send } from "../services/http";
import type { SessionView } from "../types/api";

export function SignInPage() {
  const { signIn } = useSession();
  const [codeSignedIn, setCodeSignedIn] = useState(true);
  const [down, setDown] = useState<string | null>(null);  // the server did not answer: not the same as "Claude Code is not signed in"
  const { run, busy, note } = useAction();
  const checking = usePick(TITLES.signingIn);

  useEffect(() => {
    load<SessionView>("/api/session")
      .then((session) => {
        if (session.signed_in && session.account) {
          signIn(session.account);
          navigate(afterSignIn());
        } else setCodeSignedIn(Boolean(session.claude_code_signed_in));
      })
      .catch((error: Error) => (error instanceof ApiError && error.status === 0 ? setDown(error.message) : setCodeSignedIn(false)));
  }, [signIn]);

  const proceed = () =>
    run(checking, async () => {
      setDown(null);
      const signed = await send<SessionView>("/api/session", null, "POST").catch((error) => {
        if (error instanceof ApiError && error.status === 0) setDown(error.message);
        else setCodeSignedIn(false);
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
          <Button onPress={proceed} isDisabled={busy}>Continue</Button>
          <p className="note">No Password Needed: You Stay Signed In for 24 Hours</p>
          {down ? <p className="note" role="alert"><WithCode text={down} /> <Said moment="serverSilent" /></p> : <Notice note={note} />}
        </div>
        {!codeSignedIn && !down ? (
          <div className="card stack">
            <h2 className="section-header__title">Claude Code Is Not Signed In</h2>
            <ol className="steps-list">
              <li>Open a Terminal on This Computer</li>
              <li>Run <code>claude auth login</code>. It Opens claude.ai So You Can Sign In</li>
              <li>Come Back Here and Continue</li>
            </ol>
            <p className="note"><Said moment="signInSteps" /></p>
          </div>
        ) : null}
      </div>
    </Page>
  );
}
