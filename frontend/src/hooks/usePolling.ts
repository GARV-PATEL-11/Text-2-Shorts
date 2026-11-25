// Runs `tick` every `every` ms while the page is visible (a hidden tab costs nothing); the latest `tick` is always used.
import { useEffect, useRef } from "react";

export function usePolling(tick: () => void, every = 5000) {
  const latest = useRef(tick);
  useEffect(() => { latest.current = tick; });
  useEffect(() => {
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") latest.current();
    }, every);
    return () => window.clearInterval(timer);
  }, [every]);
}
