// Faraday: the session, the frame, and a route table (pages need a session, except sign-in).
import { HomePage } from "../pages/Home";
import { NewRunPage } from "../pages/NewRun";
import { RunPage } from "../pages/run/RunPage";
import { RunListPage } from "../pages/RunList";
import { SignInPage } from "../pages/SignIn";
import { Shell } from "../components/layout/Shell";
import { SystemMessage } from "../components/feedback/SystemMessage";
import { useHashRoute } from "./routes";
import { SessionProvider, useSession } from "./session";

function Routes() {
  const route = useHashRoute();
  const { account, checked } = useSession();
  let page;
  if (route.page === "signin") page = <SignInPage />;
  else if (!checked || !account) page = <div className="page"><SystemMessage kind="loading" title="Opening Your Workspace…">Checking which Claude account this computer uses.</SystemMessage></div>;
  else if (route.page === "run") page = <RunPage key={route.run} run={route.run} stage={route.stage} tab={route.tab} />;
  else if (route.page === "new") page = <NewRunPage />;
  else if (route.page === "ongoing" || route.page === "previous") page = <RunListPage key={route.page} which={route.page} />;
  else page = <HomePage />;
  return <Shell route={route}>{page}</Shell>;
}

export function App() {
  return (
    <SessionProvider>
      <Routes />
    </SessionProvider>
  );
}
