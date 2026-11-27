// Hash routes: #/signin · #/ · #/new · #/ongoing · #/previous · #/runs/<run>[/<stage>[/<tab>]].
import { useEffect, useState } from "react";

export type Route =
  | { page: "signin" } | { page: "home" } | { page: "new" } | { page: "ongoing" } | { page: "previous" }
  | { page: "run"; run: string; stage?: string; tab?: string };

export const NAV: { page: Route["page"]; href: string; label: string }[] = [
  { page: "home", href: "#/", label: "Home" },
  { page: "new", href: "#/new", label: "Start a Run" },
  { page: "ongoing", href: "#/ongoing", label: "Ongoing Runs" },
  { page: "previous", href: "#/previous", label: "Previous Runs" },
];

export function parseHash(hash: string): Route {
  const run = hash.match(/^#\/runs\/([^/]+)(?:\/([^/]+))?(?:\/([^/]+))?$/);
  if (run) return { page: "run", run: decodeURIComponent(run[1]), stage: run[2], tab: run[3] };
  const page = { "#/signin": "signin", "#/new": "new", "#/ongoing": "ongoing", "#/previous": "previous" }[hash.split("?")[0]];
  return { page: (page ?? "home") as "home" };
}

export const navigate = (hash: string) => {
  if (window.location.hash !== hash) window.location.hash = hash;
};

/** The current route; on a change of page (not of tab), the page scrolls to the top and focus moves to <main>. */
export function useHashRoute(): Route {
  const [route, setRoute] = useState(() => parseHash(window.location.hash || "#/"));
  useEffect(() => {
    const onChange = () => {
      const next = parseHash(window.location.hash || "#/");
      setRoute((current) => {
        const samePage = current.page === "run" && next.page === "run" && current.run === next.run;
        if (!samePage) {
          window.scrollTo(0, 0);
          requestAnimationFrame(() => document.getElementById("app")?.focus({ preventScroll: true }));
        }
        return next;
      });
    };
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}
