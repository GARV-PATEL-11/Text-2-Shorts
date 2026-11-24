import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/App";
import { log, startLogging } from "./services/log";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/layout.css";
import "./styles/components.css";
import "./styles/motion.css";

startLogging();
createRoot(document.getElementById("root") as HTMLElement, {
  onUncaughtError: (error, info) => log.error("The page crashed while drawing", { error: String(error), stack: info.componentStack }),
  onCaughtError: (error, info) => log.error("A part of the page failed to draw", { error: String(error), stack: info.componentStack }),
  onRecoverableError: (error) => log.warn("React recovered from an error", String(error)),
}).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
