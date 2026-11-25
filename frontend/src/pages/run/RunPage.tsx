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
import { Breadcrumbs } from "../../components/navigation/Breadcrumbs";
import { ProgressSteps } from "../../components/navigation/ProgressSteps";
import { Button } from "../../components/ui/Button";
import { RequestChange, Terminal } from "../../components/ui/icons";
import { runTitle } from "../../components/ui/Markdown";
import { WithCode } from "../../components/ui/text";
import { currentStage, isFinished, REQUIRED_STEPS, STAGE_STEPS, stageStatuses, stepState } from "../../config/stages";
import type { Note } from "../../hooks/useAction";
import { useApi } from "../../hooks/useApi";
import { runHash, runPath } from "../../services/runs";
import type { RunDetail } from "../../types/api";
import { ChangeModal } from "./ChangeModal";
import { ClaudePanel } from "./ClaudePanel";
import { Console } from "./Console";
import { type Ask, RunContext } from "./context";
import { Overview } from "./Overview";
import { NextUp } from "./review";
import { LookSound } from "./stages/look/LookSound";
import { Final, Plans, Scenes } from "./stages/Production";
import { Requirements } from "./stages/Requirements";
import { Reshuffle } from "./stages/Reshuffle";
import { Outline, Script } from "./stages/Writing";
import type { StageProps } from "./stages/StageTabs";

const VIEWS: Record<string, (props: StageProps) => ReactNode> = {
  template: LookSound, requirements: Requirements, outline: Outline, script: Script, plan: Plans, scenes: Scenes, final: Final,
  reshuffle: Reshuffle,
};

/** Where the open stage waits for you, if it does: the tab to open (a scene's own tab for a scene). */
function waitingTab(run: RunDetail, stage: string): string | null {
  if (stage === "scenes") return run.awaiting.find((checkpoint) => /^(start:)?s\d{2}$/.test(checkpoint.target))?.target.replace("start:", "") ?? null;
  return run.awaiting.some((checkpoint) => checkpoint.target === stage) ? "checkpoint" : null;
}

export function RunPage({ run: id, stage, tab }: { run: string; stage?: string; tab?: string }) {
  const detail = useApi<RunDetail>(runPath(id));
  const [notice, setNotice] = useState<Note | null>(null);
  const [consoleOpen, setConsoleOpen] = useState(false);
  const [ask, setAsk] = useState<Ask | null>(null);
  const [claudeAsks, setClaudeAsks] = useState(false);  // while Claude asks, its panel leads and the approval bar steps back
  const { reload } = detail;
  const refresh = useCallback((message: string) => {
    setNotice({ text: message });
    reload();
  }, [reload]);
  const run = detail.data;
  const context = useMemo(() => (run ? { run, refresh, ask: setAsk } : null), [run, refresh]);
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
    return (
      <Page title="Run">
        <SystemMessage kind="unavailable" title="Could Not Load This Run" action={<Button variant="secondary" size="sm" onPress={detail.reload}>Try Again</Button>}>
          {detail.error.message}
        </SystemMessage>
      </Page>
    );
  }
  if (!run || !context) return <Page title="Run"><SystemMessage kind="loading" title="Opening the Run" /></Page>;

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
      <Page title={`${step.label} · ${runTitle(run.summary.topic)}`}>
        <div className="run">
          <aside className="run__rail" aria-label="Run">
            <ProgressBar label="Stages Approved" value={approved} max={REQUIRED_STEPS.length} valueLabel={`${approved} of ${REQUIRED_STEPS.length}`} />
            {run.problem ? null : (
              <ProgressSteps label="Stages of This Run" current={open}
                onSelect={(next) => navigate(runHash(id, next))}
                steps={STAGE_STEPS.map((candidate) => ({ ...candidate, state: stepState(run, candidate.id) }))} />
            )}
            <div className="run__actions">
              <Button variant="secondary" size="sm" icon={<Terminal />} onPress={() => setConsoleOpen(true)}>Open Console</Button>
              <Button variant="secondary" size="sm" icon={<RequestChange />} onPress={() => setAsk({ target: open, checkpoint: null })}>Request a Change</Button>
            </div>
          </aside>
          <div className="run__main">
            <Breadcrumbs trail={[list, { label: runTitle(run.summary.topic) }]} />
            <header className="run__head">
              <h1 className="page-header__title">{runTitle(run.summary.topic)}</h1>
              <Overview />
            </header>
            <Notice note={notice} />
            {detail.error ? (
              <SystemMessage kind="offline" title="Not Up to Date" compact
                action={<Button variant="secondary" size="sm" onPress={detail.reload}>Try Again</Button>}>
                {detail.error.message}
              </SystemMessage>
            ) : null}
            {run.problem ? null : <ClaudePanel onAsking={setClaudeAsks} />}
            {run.problem ? (
              <SystemMessage kind="unsupported" title="This Run Was Made by an Older Version"><WithCode text={run.problem} /></SystemMessage>
            ) : (
              <section className="stage" aria-labelledby="stage-title">
                <div className="stage__head">
                  <h2 className="stage__title" id="stage-title" tabIndex={-1} ref={heading}>{step.label}</h2>
                  {step.optional ? <span className="badge">Optional</span> : waitingIn || statuses[open] === "approved" ? null : <StatusPill value={statuses[open] ?? "pending"} />}
                </div>
                {waitingIn && tab !== waitingIn ? (
                  <div className={`approval-bar${claudeAsks ? " approval-bar--quiet" : ""}`} role="status">
                    <span><strong>{step.label}</strong> Is Waiting for Your Decision</span>
                    <Button size="sm" variant={claudeAsks ? "secondary" : "primary"} onPress={() => navigate(runHash(id, open, waitingIn))}>Decide</Button>
                  </div>
                ) : null}
                <NextUp stage={open} />
                <View stage={open} tab={tab} />
              </section>
            )}
          </div>
        </div>
        <Drawer isOpen={consoleOpen} onOpenChange={setConsoleOpen} title="Console">
          <Console />
        </Drawer>
        <ChangeModal ask={ask} onClose={() => setAsk(null)} />
      </Page>
    </RunContext.Provider>
  );
}
