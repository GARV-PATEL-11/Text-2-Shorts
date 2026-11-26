// Home: who Faraday is and the quick actions, beside the live run and Claude's usage limits; then the closing line. Every number on the page is live; nothing here is a placeholder.
import { useCallback, useRef, useState } from "react";
import { ProgressBar } from "../components/feedback/ProgressBar";
import { Pill } from "../components/feedback/StatusPill";
import { SystemMessage } from "../components/feedback/SystemMessage";
import { Logo } from "../components/layout/Logo";
import { Page } from "../components/layout/Page";
import { Journey } from "../components/navigation/Journey";
import { Button, LinkButton } from "../components/ui/Button";
import { Chip, Chips } from "../components/ui/Chip";
import { ArrowRight, Calendar, Done, Error, Plus, Refresh, Stopwatch, Terminal, Waiting, Warning, Working } from "../components/ui/icons";
import { plainText, runTitle } from "../components/ui/Markdown";
import { Said } from "../components/ui/Said";
import { titleCase } from "../components/ui/text";
import { REQUIRED_STEPS, STAGE_STEPS, isFinished, stageName, stepState } from "../config/stages";
import { useApi } from "../hooks/useApi";
import { usePolling } from "../hooks/usePolling";
import { useRuns } from "../hooks/useRuns";
import { send } from "../services/http";
import { runHash, runPath } from "../services/runs";
import type { ConsoleView, RunDetail, RunSummary, UsageView, UsageWindow } from "../types/api";

/** Time since a run's folder was made ("2026-11-19 11:01"), in days, hours and minutes. */
function since(created: string): string {
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(created.replace(" ", "T")).getTime()) / 60000));
  const [days, hours] = [Math.floor(minutes / 1440), Math.floor((minutes % 1440) / 60)];
  return days ? `${days} d ${hours} h` : hours ? `${hours} h ${minutes % 60} min` : `${minutes} min`;
}

const WINDOW_NAMES: Record<string, string> = { five_hour: "Current Session", seven_day: "All Models", seven_day_opus: "Opus", seven_day_sonnet: "Sonnet" };
const STALE_MS = 10 * 60_000;  // older numbers are checked again (one short Haiku turn) while Home is open

function resets(epoch: number): string {
  const at = new Date(epoch * 1000);
  const time = at.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  return at.getTime() - Date.now() < 86_400_000 ? `Resets at ${time}` : `Resets ${at.toLocaleDateString("en-US", { weekday: "short" })} ${time}`;
}

function Limit({ window: limit }: { window: UsageWindow }) {
  const name = WINDOW_NAMES[limit.id] ?? titleCase(limit.id.replace(/_/g, " "));
  return (
    <div className="limit">
      <div className="limit__about">
        <span className="limit__name">{name}</span>
        <span className="limit__reset">{limit.status === "allowed" ? resets(limit.resets_at) : <><Warning /> Limit Reached · {resets(limit.resets_at)}</>}</span>
      </div>
      <ProgressBar label={`${name}: Used`} value={Math.min(limit.used_percent, 100)} max={100} hideLabel />
      <span className="limit__used">{Math.round(limit.used_percent)}% Used</span>
    </div>
  );
}

/** The Claude plan's usage limits, as Claude Code last reported them; every console turn updates them. */
function UsageLimits() {
  const usage = useApi<UsageView>("/api/usage");
  const [checking, setChecking] = useState(false);
  const busy = useRef(false);  // one check at a time, whoever asks
  const check = useCallback(() => {
    if (busy.current) return;
    busy.current = true;
    setChecking(true);
    send<UsageView>("/api/usage", {}).catch(() => undefined).finally(() => { busy.current = false; setChecking(false); usage.reload(); });
  }, [usage.reload]);
  const checkedAt = usage.data?.checked_at ? new Date(usage.data.checked_at).getTime() : 0;
  usePolling(() => (usage.data && Date.now() - checkedAt > STALE_MS ? check() : usage.reload()), 30_000);
  const windows = usage.data?.windows ?? [];
  const session = windows.filter((limit) => limit.id === "five_hour");
  const weekly = windows.filter((limit) => limit.id !== "five_hour");

  return (
    <section className="limits card" aria-labelledby="limits-title">
      <div className="limits__head">
        <h2 id="limits-title" className="section-header__title">Usage Limits</h2>
        {usage.data?.plan ? <span className="badge">{titleCase(usage.data.plan)}</span> : null}
        <span className="limits__checked note">{checkedAt ? `Updated ${new Date(checkedAt).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}` : null}</span>
        <Button size="sm" variant="secondary" icon={<Refresh className={checking ? "icon-spin" : undefined} />} onPress={check} isDisabled={checking}>
          {checking ? "Checking" : "Refresh"}
        </Button>
      </div>
      {usage.error ? <SystemMessage kind="unavailable" title="Could Not Load Usage" compact>{usage.error.message}</SystemMessage>
        : !usage.data ? <SystemMessage kind="loading" title="Loading Usage" compact />
        : !windows.length ? <SystemMessage kind={checking ? "processing" : "empty"} title={checking ? "Asking Claude Code" : "Not Checked Yet"} compact />
        : (
          <>
            {session.map((limit) => <Limit key={limit.id} window={limit} />)}
            {weekly.length ? <h3 className="limits__group">Weekly Limits</h3> : null}
            {weekly.map((limit) => <Limit key={limit.id} window={limit} />)}
          </>
        )}
    </section>
  );
}

/** The run you are in the middle of, as it happens: stages, progress, time, what Claude last did, what is wrong. */
function LiveRun({ run, others }: { run: RunSummary; others: RunSummary[] }) {
  const detail = useApi<RunDetail>(runPath(run.id));
  const log = useApi<ConsoleView>(runPath(run.id, "/console"));
  usePolling(() => { detail.reload(); log.reload(); });
  const percent = Math.round((run.stages_approved / REQUIRED_STEPS.length) * 100);
  const data = detail.data;
  const state = log.data?.busy ? { icon: <Working />, label: "Claude Is Working" }
    : data?.awaiting.length ? { icon: <Waiting />, label: "Waiting for You" }
    : isFinished(run) ? { icon: <Done />, label: "Done" }
    : { icon: <Terminal />, label: "Ready to Continue" };
  const problems = data ? [
    ...(data.problem ? [{ error: true, text: data.problem }] : []),
    ...data.awaiting.flatMap((checkpoint) => checkpoint.problems.map((text) => ({ error: false, text: `${checkpoint.label}: ${text}` }))),
    ...data.scenes.filter((scene) => scene.status === "failed").map((scene) => ({ error: true, text: `${titleCase(scene.title)} Failed` })),
    ...data.final_checks.map((finding) => ({ error: finding.severity === "ERROR", text: finding.message })),
  ] : [];
  const updates = (log.data?.entries ?? []).filter((entry) => entry.text.trim()).slice(-4).reverse();

  return (
    <div className="live card">
      <div className="live__head">
        <a className="live__topic" href={runHash(run.id)}>{run.name || runTitle(run.topic)}</a>
        <Pill icon={state.icon}>{state.label}</Pill>
      </div>
      {data ? (
        <Journey label="Stages of this run" current="" steps={[]}
          stages={STAGE_STEPS.map((step) => ({ id: step.id, label: step.label, optional: step.optional, state: stepState(data, step.id) }))} />
      ) : <SystemMessage kind="loading" title="Loading This Run" compact />}
      <ProgressBar label="Stages Approved" value={run.stages_approved} max={REQUIRED_STEPS.length} valueLabel={`${percent}%`} />
      <Chips label="This Run Now">
        <Chip icon={<Working />} value={stageName(run.stage)} label="Now" />
        <Chip icon={<Stopwatch />} value={since(run.created)} label="Since Start" />
      </Chips>
      <div className="live__block">
        <h3 className="live__title">Problems</h3>
        {!data ? null : problems.length ? (
          <ul className="live__list">
            {problems.slice(0, 4).map((problem) => (
              <li key={problem.text} className="live__problem">{problem.error ? <Error /> : <Warning />}<span>{problem.text}</span></li>
            ))}
          </ul>
        ) : <p className="note live__problem"><Done /> None</p>}
      </div>
      {updates.length ? (
        <div className="live__block">
          <h3 className="live__title">Updates</h3>
          <ol className="live__list">
            {updates.map((entry) => (
              <li key={`${entry.at}${entry.text}`} className="live__update">
                <time dateTime={entry.at}>{entry.at.slice(11, 16)}</time>
                <span className="badge">{titleCase(entry.role === "you" ? "You" : entry.role)}</span>
                <span className="live__text">{plainText(entry.text)}</span>
              </li>
            ))}
          </ol>
        </div>
      ) : null}
      <div className="row">
        <LinkButton href={runHash(run.id)} size="sm" icon={<ArrowRight />}>Open Run</LinkButton>
        {others.length ? <a className="live__more" href="#/ongoing">{others.length} More in Progress</a> : null}
      </div>
    </div>
  );
}

export function HomePage() {
  const runs = useRuns();
  usePolling(runs.reload, 15_000);
  const [live, ...others] = runs.ongoing;

  return (
    <Page title="Home">
      <div className="hero">
        <div className="hero__pitch">
          <Logo height={40} />
          <h1 className="page-header__title page-header__title--display">Curiosity, Illustrated.</h1>
          <p className="page-header__lead">A Question In, a Narrated Explainer Video Out: Claude Writes It, Manim Draws It, You Approve Every Stage</p>
          <p><Said moment="homeLead" lead /></p>
          <nav className="quick" aria-label="Quick Actions">
            <LinkButton href="#/new" icon={<Plus />}>Start a Run</LinkButton>
            {live ? <LinkButton href={runHash(live.id)} variant="secondary" icon={<ArrowRight />}>Continue</LinkButton> : null}
            <LinkButton href="#/previous" variant="secondary" icon={<Calendar />}>Previous Runs</LinkButton>
          </nav>
        </div>
        <section className="hero__side" aria-labelledby="live-title">
          <div className="hero__side-head">
            <h2 id="live-title" className="section-header__title">Live Run</h2>
            {runs.data ? <span className="note">{runs.ongoing.length} Ongoing · {runs.finished.length} Finished</span> : null}
          </div>
          {runs.error ? <SystemMessage kind="unavailable" title="Could Not Load Runs" compact>{runs.error.message}</SystemMessage>
            : !runs.data ? <SystemMessage kind="loading" title="Loading Your Runs" compact />
            : live ? <LiveRun run={live} others={others} />
            : (
              <SystemMessage kind="empty" title="Nothing in Progress" compact>
                <Said moment="nothingInProgress" />
              </SystemMessage>
            )}
          <UsageLimits />
        </section>
      </div>

      <footer className="closing">
        <Logo height={32} />
        <p className="closing__motto">Curiosity, Illustrated.</p>
        <Said moment="closing" block />
      </footer>
    </Page>
  );
}
