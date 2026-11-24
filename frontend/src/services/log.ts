// The frontend's logging: every entry goes to the browser console; info and above are batched to the server
// (POST /api/logs → artifacts/logs/frontend.log), every 3 seconds and when the page is hidden. Uncaught errors and
// unhandled rejections are caught here. Never throws: a failed upload is dropped.
type Level = "debug" | "info" | "warn" | "error";
interface Entry { level: Level; message: string; at: string; page: string; details: string }

const MAX_QUEUE = 200;
let queue: Entry[] = [];
let timer: number | undefined;

function flush(useBeacon = false) {
  window.clearTimeout(timer);
  timer = undefined;
  while (queue.length) {
    const body = JSON.stringify({ entries: queue.splice(0, 50) });
    if (useBeacon && navigator.sendBeacon?.("/api/logs", new Blob([body], { type: "application/json" }))) continue;
    void fetch("/api/logs", { method: "POST", headers: { "Content-Type": "application/json" }, body, keepalive: true }).catch(() => undefined);
  }
}

const describe = (details: unknown) => {
  if (details === undefined) return "";
  if (details instanceof Error) return `${details.name}: ${details.message}${details.stack ? `\n${details.stack}` : ""}`.slice(0, 4000);
  try {
    return (typeof details === "string" ? details : JSON.stringify(details)).slice(0, 4000);
  } catch {
    return String(details).slice(0, 4000);
  }
};

function write(level: Level, message: string, details?: unknown) {
  const entry = { level, message: message.slice(0, 2000), at: new Date().toISOString(), page: window.location.hash || "#/", details: describe(details) };
  (level === "error" ? console.error : level === "warn" ? console.warn : level === "debug" ? console.debug : console.info)(
    `[faraday] ${entry.message}`, ...(details === undefined ? [] : [details]),
  );
  if (level === "debug") return;
  queue.push(entry);
  if (queue.length > MAX_QUEUE) queue = queue.slice(-MAX_QUEUE);
  if (level === "error") flush();
  else timer ??= window.setTimeout(() => flush(), 3000);
}

export const log = {
  debug: (message: string, details?: unknown) => write("debug", message, details),
  info: (message: string, details?: unknown) => write("info", message, details),
  warn: (message: string, details?: unknown) => write("warn", message, details),
  error: (message: string, details?: unknown) => write("error", message, details),
};

/** Once, at start: uncaught errors, unhandled rejections, page changes, and a last upload when the page is hidden. */
export function startLogging() {
  window.addEventListener("error", (event) => log.error(`Uncaught: ${event.message}`, event.error ?? `${event.filename}:${event.lineno}`));
  window.addEventListener("unhandledrejection", (event) => log.error("Unhandled promise rejection", event.reason));
  window.addEventListener("hashchange", () => log.info(`Opened ${window.location.hash || "#/"}`));
  document.addEventListener("visibilitychange", () => document.visibilityState === "hidden" && flush(true));
  log.info(`Faraday opened at ${window.location.hash || "#/"} (${navigator.userAgent})`);
}
