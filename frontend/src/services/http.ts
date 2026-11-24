// One request core for the API of `text-2-shorts serve`: JSON in and out, a signed-out session as its own error, the
// server's ApiError ({error, problems}) as ApiError. Everything that talks to the backend goes through here.
import type { ConsoleEntry } from "../types/api";
import { log } from "./log";

export class SignedOut extends Error {}

export class ApiError extends Error {
  constructor(message: string, readonly problems: string[] = [], readonly status = 0) {
    super(message);
  }
  /** The message and its problems, for one line of feedback. */
  get full(): string {
    return [this.message, ...this.problems].join(" — ");
  }
}

export const errorText = (error: unknown) => (error instanceof ApiError ? error.full : (error as Error).message);

async function request(path: string, init: RequestInit = {}, signal?: AbortSignal): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(path, { ...init, signal });
  } catch (error) {
    if ((error as Error).name === "AbortError") throw error;
    log.error(`${init.method ?? "GET"} ${path}: the server did not answer`, error);
    throw new ApiError("Faraday's server did not answer. Check that `text-2-shorts serve` is running.", [], 0);
  }
  if (response.status === 401 && path !== "/api/session") throw new SignedOut("sign in first");
  if (!response.ok) {
    const answer = await response.json().catch(() => ({}));
    const level = response.status >= 500 ? log.error : response.status === 404 && path.startsWith("/media/") ? log.debug : log.warn;  // a file not made yet is normal
    level(`${init.method ?? "GET"} ${path} → ${response.status}: ${answer.error ?? ""}`, answer.problems?.length ? answer.problems : undefined);
    throw new ApiError(answer.error || `${path} answered ${response.status}`, answer.problems || [], response.status);
  }
  return response;
}

export async function load<T>(path: string, signal?: AbortSignal): Promise<T> {
  return (await request(path, { headers: { Accept: "application/json" } }, signal)).json() as Promise<T>;
}

export async function loadText(path: string, signal?: AbortSignal): Promise<string> {
  return (await request(path, {}, signal)).text();
}

export async function send<T>(path: string, body: unknown, method = "POST"): Promise<T> {
  const response = await request(path, {
    method,
    headers: body === null ? { Accept: "application/json" } : { "Content-Type": "application/json", Accept: "application/json" },
    body: body === null ? undefined : JSON.stringify(body),
  });
  return response.json().catch(() => ({})) as Promise<T>;
}

/** One console turn: the user's message, then Claude's lines as they stream in (NDJSON, one entry per line). */
export async function streamTurn(path: string, message: string, onEntry: (entry: ConsoleEntry) => void): Promise<void> {
  const response = await request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/x-ndjson" },
    body: JSON.stringify({ message }),
  });
  if (!response.body) throw new ApiError("The console sent no reply.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffered = "";
  const emit = (line: string) => {
    if (!line.trim()) return;
    try {
      onEntry(JSON.parse(line) as ConsoleEntry);
    } catch {
      onEntry({ at: "", role: "error", text: "A reply from Claude could not be read; the rest of the turn continues." });
    }
  };
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffered += decoder.decode(value, { stream: true });
    const lines = buffered.split("\n");
    buffered = lines.pop() ?? "";
    lines.forEach(emit);
  }
  emit(buffered + decoder.decode());  // a last line without its newline still counts
}
