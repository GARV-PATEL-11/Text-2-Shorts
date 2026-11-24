// Home: what Faraday does and the way in, beside the runs you are in the middle of; how a run works, below.
import { ProgressBar } from "../components/feedback/ProgressBar";
import { SystemMessage } from "../components/feedback/SystemMessage";
import { Page, Section } from "../components/layout/Page";
import { ProgressSteps } from "../components/navigation/ProgressSteps";
import { LinkButton } from "../components/ui/Button";
import { Plus } from "../components/ui/icons";
import { runTitle } from "../components/ui/Markdown";
import { REQUIRED_STEPS, STAGE_STEPS, stageName } from "../config/stages";
import { useRuns } from "../hooks/useRuns";
import { runHash } from "../services/runs";

export function HomePage() {
  const runs = useRuns();
  return (
    <Page title="Home">
      <div className="hero">
        <div className="hero__pitch">
          <h1 className="page-header__title page-header__title--display">Curiosity, Illustrated.</h1>
          <p className="page-header__lead">
            A question in, a narrated and animated explainer out.
          </p>
          <div className="row">
            <LinkButton href="#/new" size="lg" icon={<Plus />}>Start a Run</LinkButton>
            <LinkButton href="#/previous" size="lg" variant="secondary">Previous Runs</LinkButton>
          </div>
        </div>
        <div className="hero__side">
          <div className="hero__side-head">
            <h2 className="section-header__title">In Progress</h2>
            {runs.data ? <span className="note">{runs.ongoing.length} Ongoing · {runs.finished.length} Finished</span> : null}
          </div>
          {runs.error ? (
            <SystemMessage kind="unavailable" title="Your Runs Could Not Be Read" compact>{runs.error.message}</SystemMessage>
          ) : !runs.data ? (
            <SystemMessage kind="loading" title="Reading Your Runs…" compact />
          ) : !runs.ongoing.length ? (
            <SystemMessage kind="empty" title="Nothing in Progress" compact action={<LinkButton href="#/new" size="sm">Start a Run</LinkButton>}>
              Describe what a video should explain, and Faraday sets the run up.
            </SystemMessage>
          ) : (
            <ul className="run-cards">
              {runs.ongoing.slice(0, 4).map((run) => (
                <li key={run.id}>
                  <a className="run-card" href={runHash(run.id)}>
                    <span className="run-card__topic">{runTitle(run.topic)}</span>
                    <span className="run-card__meta"><span className="badge">{stageName(run.stage)}</span><span>{run.created}</span></span>
                    <ProgressBar label={`${runTitle(run.topic)}: Stages Approved`} value={run.stages_approved} max={REQUIRED_STEPS.length}
                      valueLabel={`${run.stages_approved} of ${REQUIRED_STEPS.length}`} hideLabel />
                  </a>
                </li>
              ))}
              {runs.ongoing.length > 4 ? <li><a className="run-cards__more" href="#/ongoing">All {runs.ongoing.length} Ongoing Runs</a></li> : null}
            </ul>
          )}
        </div>
      </div>
      <Section title="How a Run Works">
        <ProgressSteps label="The stages of a run" current=""
          steps={STAGE_STEPS.map((step) => ({ id: step.id, label: step.label, hint: step.hint, icon: step.icon, optional: step.optional, state: "upcoming" }))} />
      </Section>
    </Page>
  );
}
