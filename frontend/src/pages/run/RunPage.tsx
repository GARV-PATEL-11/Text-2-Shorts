// One run, in two panes: a rail (progress, the stages, the console and change actions) and the open stage with
// its sub-stage tabs. When the open stage waits for you, a bar says so and leads to its checkpoint. After every write
// the run is re-read in place: nothing remounts, nothing on screen is lost.
import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { navigate } from "../../app/routes";
import { Notice } from "../../components/feedback/Notice";
import { Drawer } from "../../components/feedback/Overlay";
import { ProgressBar } from "../../components/feedback/ProgressBar";
import { StatusPill } from "../../components/feedback/StatusPill";
import { SystemMessage } from "../../components/feedback/SystemMessage";
import { Page } from "../../components/layout/Page";
import { VideoPreview } from "../../components/media/VideoPreview";
import { Breadcrumbs } from "../../components/navigation/Breadcrumbs";
import { ProgressSteps } from "../../components/navigation/ProgressSteps";
import { Button } from "../../components/ui/Button";
import { RequestChange, Terminal } from "../../components/ui/icons";
import { runTitle } from "../../components/ui/Markdown";
import { WithCode } from "../../components/ui/text";
import { ApiError } from "../../services/http";
import { currentStage, isFinished, REQUIRED_STEPS, STAGE_STEPS, stageStatuses, stepState } from "../../config/stages";
import type { Note } from "../../hooks/useAction";
import { useApi } from "../../hooks/useApi";
import { usePolling } from "../../hooks/usePolling";
import { Said, usePick } from "../../components/ui/Said";
import type { Moment } from "../../config/voice";
import { runHash, runPath } from "../../services/runs";
import type { RunDetail } from "../../types/api";
import { ChangeModal, NO_REQUESTS } from "./ChangeModal";
import { ClaudePanel } from "./ClaudePanel";
import { Console } from "./console/Console";
import { type Ask, RunContext } from "./context";
import { Overview } from "./Overview";
import { NextUp } from "./review";
import { LookSound } from "./stages/look/LookSound";
import { Final, Plans, Scenes } from "./stages/Production";
import { Requirements } from "./stages/Requirements";
import { TITLES } from "./titles";
import { Reshuffle } from "./stages/Reshuffle";
import { Outline, Script } from "./stages/Writing";
import type { StageProps } from "./stages/StageTabs";

const VIEWS: Record<string, (props: StageProps) => ReactNode> = {
  template: LookSound, requirements: Requirements, outline: Outline, script: Script, plan: Plans, scenes: Scenes, final: Final,
  reshuffle: Reshuffle,
};

/** Where the open stage waits for you, if it does: the tab to open (a scene's own tab for a scene). */
function waitingTab(run: RunDetail, stage: string): string | null {
  if (stage === "scenes") {
    const scene = run.awaiting.find((checkpoint) => /^(start:)?s\d{2}$/.test(checkpoint.target));
    if (scene) return scene.target.replace("start:", "");
    return run.awaiting.some((checkpoint) => checkpoint.target === "scenes") ? "approval" : null;  // Approve All Scenes
  }
  return run.awaiting.some((checkpoint) => checkpoint.target === stage) ? "checkpoint" : null;
}

/** sessionStorage: the run whose console opens when its page loads (set by Home's Open Console). */
export const OPEN_CONSOLE = "faraday:open-console";

export function RunPage({ run: id, stage, tab }: { run: string; stage?: string; tab?: string }) {
  const detail = useApi<RunDetail>(runPath(id));
  const [notice, setNotice] = useState<Note | null>(null);
  const [noticeSaid, setNoticeSaid] = useState<Moment | null>(null);  // a quote beside the notice, once it is true
  const [consoleOpen, setConsoleOpen] = useState(() => {  // Home's "Open Console" lands here with it open
    try { return sessionStorage.getItem(OPEN_CONSOLE) === id && (sessionStorage.removeItem(OPEN_CONSOLE), true); } catch { return false; }
  });
  useEffect(() => {  // Ctrl+` opens or closes the console from anywhere on the run page, as in a code editor
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.ctrlKey && event.key === "`") { event.preventDefault(); setConsoleOpen((open) => !open); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  const [ask, setAsk] = useState<Ask | null>(null);
  const [claudeAsks, setClaudeAsks] = useState(false);  // while Claude asks, its panel leads and the approval bar steps back
  const { reload } = detail;
  // Claude works between the user's clicks: statuses, scenes and new checkpoints appear without a reload (H4)
  usePolling(() => { if (detail.data && !detail.data.problem && detail.data.summary.status !== "completed") reload(); });
  const refresh = useCallback((message: string, said?: Moment) => {
    setNotice({ text: message });
    setNoticeSaid(said ?? null);
    reload();
  }, [reload]);
  const run = detail.data;
  const context = useMemo(() => (run ? { run, refresh, ask: setAsk } : null), [run, refresh]);
  const openingTitle = usePick(TITLES.openingRun);
  const decisionTitle = usePick(TITLES.decision);
  const noFinalVideo = usePick(TITLES.noFinalVideo);
  const staleTitle = usePick(TITLES.stale);
  const heading = useRef<HTMLHeadingElement>(null);
  const firstStage = useRef(true);
  useEffect(() => {  // a new stage was chosen in the rail: move focus to its heading (the page itself did not change)
    if (firstStage.current) {
      firstStage.current = false;
      return;
    }
    heading.current?.focus({ preventScroll: true });
  }, [stage]);

  if (detail.error && !run) {
    const missing = detail.error instanceof ApiError && detail.error.status === 404;
    return (
      <Page title="Run">
        <SystemMessage kind="unavailable" title={missing ? "This Run Does Not Exist" : "Could Not Load This Run"} said={missing ? "notFound" : undefined} action={<>
          <Button variant="secondary" size="sm" onPress={detail.reload}>Try Again</Button>
          <Button variant="secondary" size="sm" onPress={() => navigate("#/ongoing")}>Ongoing Runs</Button>
        </>}>
          {detail.error.message}
        </SystemMessage>
      </Page>
    );
  }
  if (!run || !context) return <Page title="Run"><SystemMessage kind="loading" title={openingTitle} said="openingRun" /></Page>;

  const finished = isFinished(run.summary);
  const list = finished ? { label: "Previous Runs", href: "#/previous" } : { label: "Ongoing Runs", href: "#/ongoing" };
  const open = stage && VIEWS[stage] ? stage : currentStage(run);
  const step = STAGE_STEPS.find((candidate) => candidate.id === open) ?? STAGE_STEPS[0];
  const statuses = stageStatuses(run);
  const approved = REQUIRED_STEPS.filter((candidate) => statuses[candidate.id] === "approved").length;
  const waitingIn = waitingTab(run, open);
  const View = VIEWS[open];
  return (
    <RunContext.Provider value={context}>
      <Page title={`${step.label} · ${run.summary.name || runTitle(run.summary.topic)}`}>
        <div className={run.problem ? "run run--solo" : "run"}>
          {run.problem ? null : (  /* an older version's run: nothing to approve, ask or change, only its final video */
            <aside className="run__rail" aria-label="Run Progress and Stages">
              <ProgressBar label="Stages Approved" value={approved} max={REQUIRED_STEPS.length} valueLabel={`${approved} of ${REQUIRED_STEPS.length}`} />
              <ProgressSteps label="Stages of This Run" current={open}
                onSelect={(next) => navigate(runHash(id, next))}
                steps={STAGE_STEPS.map((candidate) => ({ ...candidate, state: stepState(run, candidate.id) }))} />
              <div className="run__actions">
                <span className="run__console"><Button variant="secondary" size="sm" icon={<Terminal />} onPress={() => setConsoleOpen(true)}>Console <kbd className="console-dock__key">Ctrl `</kbd></Button></span>
                {NO_REQUESTS.includes(open) ? null : <Button variant="secondary" size="sm" icon={<RequestChange />} onPress={() => setAsk({ target: open, checkpoint: null })}>Request a Change</Button>}
              </div>
            </aside>
          )}
          <div className="run__main">
            <Breadcrumbs trail={[list, { label: run.summary.name || runTitle(run.summary.topic) }]} />
            <header className="run__head">
              <h1 className="page-header__title">{run.summary.name || runTitle(run.summary.topic)}</h1>
              <Overview />
            </header>
            <Notice note={notice} />
            {noticeSaid && notice ? <p className="note" key={notice.text}><Said moment={noticeSaid} /></p> : null}
            {detail.error ? (
              <SystemMessage kind="offline" title={staleTitle} compact said="stalePage"
                action={<Button variant="secondary" size="sm" onPress={detail.reload}>Try Again</Button>}>
                {detail.error.message}
              </SystemMessage>
            ) : null}
            {run.problem ? null : <ClaudePanel onAsking={setClaudeAsks} />}
            {run.problem ? (
              <>
                <SystemMessage kind="unsupported" title={run.problem.startsWith("This run cannot be read") ? "This Run Cannot Be Read Right Now" : "This Run Was Made by an Older Version"}><WithCode text={run.problem} /></SystemMessage>
                <VideoPreview src={run.final_video} label={`Final Video: ${run.summary.name || runTitle(run.summary.topic)}`} empty={noFinalVideo} />
              </>
            ) : (
              <section className="stage" aria-labelledby="stage-title">
                <div className="stage__head">
                  <h2 className="stage__title" id="stage-title" tabIndex={-1} ref={heading}>{step.label}</h2>
                  {step.optional ? <span className="badge">Optional</span> : waitingIn || statuses[open] === "approved" ? null : <StatusPill value={statuses[open] ?? "pending"} />}
                </div>
                {waitingIn && tab !== waitingIn ? (
                  <div className={`approval-bar${claudeAsks ? " approval-bar--quiet" : ""}`} role="status">
                    <span>{decisionTitle.split("{step}").flatMap((part, index) => (index ? [<strong key={index}>{step.label}</strong>, part] : [part]))}</span>
                    <Button size="sm" variant={claudeAsks ? "secondary" : "primary"} onPress={() => navigate(runHash(id, open, waitingIn))}>Decide</Button>
                  </div>
                ) : null}
                <NextUp stage={open} />
                <View stage={open} tab={tab} />
              </section>
            )}
          </div>
        </div>
        {!consoleOpen ? (
          <div className="console-dock" title="Console (Ctrl+`)">
            <Button variant="secondary" icon={<Terminal />} onPress={() => setConsoleOpen(true)} label="Console"><span className="console-dock__text">Console</span> <kbd className="console-dock__key">Ctrl `</kbd></Button>
          </div>
        ) : null}
        <Drawer isOpen={consoleOpen} onOpenChange={setConsoleOpen} title="Console" terminal>
          <Console />
        </Drawer>
        <ChangeModal ask={ask} onClose={() => setAsk(null)} />
      </Page>
    </RunContext.Provider>
  );
}
