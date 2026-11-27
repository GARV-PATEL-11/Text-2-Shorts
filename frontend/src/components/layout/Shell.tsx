// The frame of every page: a skip link, the one-tier header (brand · sections · you, opening your profile), the main
// area, the footer
// (Home has its own closing line instead).
import { type MouseEvent, type ReactNode, useState } from "react";
import { NAV, type Route } from "../../app/routes";
import { useSession } from "../../app/session";
import { useApi } from "../../hooks/useApi";
import type { Profile } from "../../types/api";
import { Logo } from "./Logo";
import { ProfileDialog } from "./Profile";

export function Shell({ route, children }: { route: Route; children: ReactNode }) {
  const { account } = useSession();
  const [open, setOpen] = useState(false);
  const profile = useApi<Profile>(account ? "/api/profile" : null);
  const shown = profile.data?.name || account?.email.split("@")[0] || "";
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
          <a className="brand" href="#/" aria-label="Faraday, Home"><Logo /></a>
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
                <button type="button" className="header__user" onClick={() => setOpen(true)} aria-haspopup="dialog" title={account.email}>
                  <span className="header__avatar" aria-hidden="true">{shown.slice(0, 1).toUpperCase()}</span>
                  <span>{shown}</span>
                </button>
              </div>
              <ProfileDialog profile={profile.data} isOpen={open} onOpenChange={setOpen} onSaved={profile.reload} />
            </>
          ) : null}
        </div>
      </header>
      <main id="app" tabIndex={-1}>{children}</main>
      {route.page === "home" || route.page === "signin" ? null : (  // Home closes with its own line; Sign In shows the line above
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
