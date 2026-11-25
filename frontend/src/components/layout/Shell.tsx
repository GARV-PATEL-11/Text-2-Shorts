// The frame of every page: a skip link, the one-tier header (brand · sections · account), the main area, the footer
// (Home has its own closing line instead).
import { type MouseEvent, type ReactNode, useState } from "react";
import { NAV, type Route } from "../../app/routes";
import { useSession } from "../../app/session";
import { Button } from "../ui/Button";
import { Logo } from "./Logo";

export function Shell({ route, children }: { route: Route; children: ReactNode }) {
  const { account, signOut } = useSession();
  const [problem, setProblem] = useState<string | null>(null);
  // a run belongs to Ongoing or Previous: its breadcrumbs say which, so no section is lit on a run page
  const active = route.page === "run" ? null : route.page;
  const skip = (event: MouseEvent) => {  // focus the content without touching the route (the hash is the route)
    event.preventDefault();
    document.getElementById("app")?.focus();
  };
  return (
    <>
      <a className="skip" href="#app" onClick={skip}>Skip to Content</a>
      <header className="header">
        <div className="header__inner">
          <a className="brand" href="#/" aria-label="Faraday: home"><Logo /></a>
          {account && route.page !== "signin" ? (
            <>
              <nav className="header__nav" aria-label="Main">
                {NAV.map((item) => (
                  <a key={item.href} href={item.href} className="header__link" aria-current={active === item.page ? "page" : undefined}>
                    {item.label}
                  </a>
                ))}
              </nav>
              <div className="header__account">
                <span className="header__email">{account.email}</span>
                {problem ? <span className="header__problem" role="alert">{problem}</span> : null}
                <Button variant="secondary" size="sm" onPress={async () => setProblem(await signOut())}>Sign Out</Button>
              </div>
            </>
          ) : null}
        </div>
      </header>
      <main id="app" tabIndex={-1}>{children}</main>
      {route.page === "home" ? null : (  // Home closes with its own line
        <footer className="footer">
          <div className="footer__inner">
            <span className="footer__brand"><Logo height={16} /></span>
            <span>Curiosity, Illustrated.</span>
          </div>
        </footer>
      )}
    </>
  );
}
