// The API of `text-2-shorts serve`: its Pydantic contracts (backend/schemas/api.py), as TypeScript types.
export type Status =
  | "pending" | "in_progress" | "completed" | "failed" | "requires_refactoring" | "requires_user_approval" | "approved";

export interface Account { email: string; organization: string; plan: string; method: string }
export interface Profile { name: string; account: Account; runs: number; spend_usd: number }
export interface SessionView { signed_in: boolean; account?: Account | null; claude_code_signed_in?: boolean }
export type RunStatus = "configuring" | "in_progress" | "awaiting_approval" | "failed" | "completed";
export interface RunSummary {
  id: string; name: string; topic: string; created: string; updated: string; template: string; status: RunStatus;
  stage: string; readable: boolean; has_final: boolean; stages_approved: number;
}
/** Start a Run as far as the user got, saved on this machine as they go (PUT /api/drafts/<id>). */
export interface Draft {
  id: string; updated: string; name: string; step: number; look: LookChoice | null; requirement: string; objectives: string;
  approach: string; minutes: string; audience: string; tts: string; notes: string;
}
export interface Action {
  do: "write" | "subagent" | "command" | "ask_user"; what: string; agent?: string | null; target?: string | null;
  file?: string | null; read: string[]; before?: string | null; after?: string | null; command?: string | null;
  checkpoint?: string | null; user_text?: string | null;  // ask_user: what a person reads (`what` is for Claude)
}
export interface ActionBatch { stage: string; parallel: boolean; actions: Action[] }
export interface Checkpoint { target: string; label: string; problems: string[]; people?: string[]; fingerprint?: string | null }  // people: problems in plain words, same order
export interface ClipView { clip_id: string; objective: string; status: Status }
export interface SceneView {
  scene_id: string; title: string; status: Status; clips: ClipView[]; preview?: string | null; sync_problems: string[];
}
export interface MediaFinding { severity: "ERROR" | "WARN"; code: string; message: string }
export interface TrackedRequest { id: string; target: string; kind: string; text: string; status: string; note?: string | null }
export interface Decision { checkpoint: string; decision: string; forced: boolean; decided_at: string; notes: string; by?: string }
export interface RunDetail {
  summary: RunSummary; objectives: string[]; approach?: string | null; minutes?: number | null;
  stages: Record<string, Status>; next?: ActionBatch | null; awaiting: Checkpoint[]; scenes: SceneView[];
  final_video?: string | null; final_checks: MediaFinding[]; final_checked: boolean; requests: TrackedRequest[];
  decisions: Decision[]; problem?: string | null;
}
export type ConsoleRole = "you" | "claude" | "question" | "tool" | "result" | "permission" | "answer" | "partial" | "thinking" | "system" | "error";
export interface TurnStats { model: string; cost_usd: number; duration_ms: number; context_tokens: number; context_window: number; output_tokens: number; tools: number }
export interface ConsoleEntry {
  at: string; role: ConsoleRole; text: string; options?: string[];
  id?: string | null; tool?: string | null; input?: Record<string, unknown> | null; is_error?: boolean;
  duration_ms?: number | null; stats?: TurnStats | null; rule?: string | null;
}
export type ConsoleMode = "default" | "acceptEdits" | "plan";
export interface ConsoleSettings { model?: string | null; mode: ConsoleMode; allowed: string[] }
export interface ConsoleSession { session_id: string; model: string; cwd: string; permission_mode: string; slash_commands: string[]; skills: string[]; agents: string[]; tools: string[] }
export interface ConsoleView {
  busy: boolean; entries: ConsoleEntry[]; kickoff: string; settings: ConsoleSettings; session?: ConsoleSession | null;
  pending: ConsoleEntry[]; rules: Record<string, string[]>; default_model: string; spend_usd: number;
}
export interface LookOption { id: string; label: string; detail: string }
export interface LookElement {
  id: string; label: string; group: string; kind: "visual" | "sound"; description: string; options: LookOption[];
  custom?: string | null; previewed: boolean;
}
export interface LookTemplate { name: string; description: string; elements: Record<string, string> }
export interface LookCatalogue { templates: LookTemplate[]; elements: LookElement[] }
export interface LookView { template: string; elements: Record<string, string>; custom: Record<string, string>; saved: boolean; provider?: string }
export interface LookChoice { template: string; elements: Record<string, string>; custom: Record<string, string> }
export interface LookOptionPicture { option: string; url: string | null; full: string | null }
/** An element's options drawn in the user's look: rendering, ready (by option id), or failed. */
export type OptionPictures = "loading" | "failed" | Record<string, LookOptionPicture>;
export type ReshuffleGroup = "colours" | "fonts" | "background" | "grid" | "border";
export interface ReshuffleView { look: LookChoice; changes: { element: string; before: string; after: string }[]; applied: boolean }
export interface UsageWindow { id: string; used_percent: number; resets_at: number; status: string }
export interface UsageView { plan: string; checked_at?: string | null; windows: UsageWindow[] }
export interface PollyVoice { id: string; name: string; gender: string; language_code: string; language: string; engines: string[] }
export interface VoiceList { provider: string; template: string; voices: PollyVoice[]; curated: Record<string, string> }
