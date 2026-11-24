// What several stages show: what Claude does next, your change requests, critique rounds, accuracy findings.
import { useState } from "react";
import { SystemMessage } from "../../components/feedback/SystemMessage";
import { Section } from "../../components/layout/Page";
import { Button } from "../../components/ui/Button";
import { ChevronDown, Message } from "../../components/ui/icons";
import { Markdown } from "../../components/ui/Markdown";
import { titleCase, WithCode } from "../../components/ui/text";
import { batchStage } from "../../config/stages";
import { useRun } from "./context";

/** What happens next, in a closed disclosure: it is the workflow's own instruction to Claude, there for the curious. */
export function NextUp({ stage }: { stage: string }) {
  const { run } = useRun();
  const [open, setOpen] = useState(false);
  if (batchStage(run) !== stage || !run.next?.actions.length) return null;
  return (
    <div className="disclosure">
      <button type="button" className="disclosure__toggle" aria-expanded={open} onClick={() => setOpen(!open)}>
        <ChevronDown /> What Claude Does Next ({run.next.actions.length}), When You Message It in the Console
      </button>
      {open ? (
        <ul className="disclosure__body next-list">
          {run.next.actions.map((action, index) => (
            <li key={index}>
              {action.agent ? <span className="badge">{titleCase(action.agent)}</span> : null}
              {action.target ? <span className="id">{action.target}: </span> : null}
              <WithCode text={action.what} />
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export function Changes({ targets, defaultTarget }: { targets: (target: string) => boolean; defaultTarget: string }) {
  const { run, ask } = useRun();
  const requests = run.requests.filter((request) => targets(request.target));
  return (
    <Section title="Change Requests" description="What you asked to change here, and where each stands."
      actions={<Button size="sm" icon={<Message />} onPress={() => ask({ target: defaultTarget, checkpoint: null })}>Ask for a Change</Button>}>
      {requests.length ? (
        <ul className="list">
          {requests.map((request) => (
            <li key={request.id}>
              <Markdown text={request.text} compact />
              <span className="list__meta">{`${request.id} · ${request.kind} on ${request.target} · ${request.status}${request.note ? ` (${request.note})` : ""}`}</span>
            </li>
          ))}
        </ul>
      ) : <SystemMessage kind="empty" title="No Change Requests" compact>Ask for one whenever something should be different.</SystemMessage>}
    </Section>
  );
}

export interface Issue { target: string; criterion: string; tier: string; aspect: string; evidence: string; problem: string; impact: string; fix: string }
export interface Round { verdict: string; score?: number | null; summary?: string; strengths?: string[]; issues: Issue[] }

export function CritiqueRounds({ rounds, title }: { rounds: Round[]; title?: string }) {
  return (
    <div className="stack">
      {title ? <h3 className="subhead">{title}</h3> : null}
      {rounds.map((round, index) => (
        <article className="card stack" key={index}>
          <div className="row row--tight">
            <h4 className="card__title">Round {index + 1}</h4>
            <span className={`badge${round.verdict === "pass" ? " badge--solid" : ""}`}>{titleCase(round.verdict)}</span>
            {round.score != null ? <span className="score">{round.score}/100</span> : null}
          </div>
          {round.summary ? <p>{round.summary}</p> : null}
          {round.strengths?.length ? <p className="note">Keeps: {round.strengths.join(" · ")}</p> : null}
          {round.issues.length ? (
            <div className="table-wrap" tabIndex={0} role="region" aria-label="Table (scrolls sideways on small screens)">
              <table className="table table--compact">
                <thead><tr><th scope="col">Rule</th><th scope="col">Where</th><th scope="col">Problem</th><th scope="col">Fix</th></tr></thead>
                <tbody>
                  {round.issues.map((issue, issueIndex) => (
                    <tr key={issueIndex}>
                      <td><span className="id">{issue.criterion}</span> <span className="table__muted">{issue.tier}</span></td>
                      <td className="id">{issue.target}</td>
                      <td>{issue.problem}<span className="table__muted"> {issue.evidence}</span></td>
                      <td>{issue.fix}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </article>
      ))}
    </div>
  );
}

export interface Finding { target: string; severity: string; kind: string; quote: string; why: string; fix: string }

export function Findings({ findings }: { findings: Finding[] }) {
  if (!findings.length) return <SystemMessage kind="success" title="No Accuracy Problems">The accuracy reviewer found nothing to fix.</SystemMessage>;
  return (
    <div className="table-wrap" tabIndex={0} role="region" aria-label="Table (scrolls sideways on small screens)">
      <table className="table table--compact">
        <thead><tr><th scope="col">Severity</th><th scope="col">Where</th><th scope="col">Quote</th><th scope="col">Why</th><th scope="col">Fix</th></tr></thead>
        <tbody>
          {findings.map((finding, index) => (
            <tr key={index}>
              <td><span className={`badge${finding.severity === "ERROR" ? " badge--solid" : ""}`}>{titleCase(`${finding.severity} ${finding.kind}`)}</span></td>
              <td className="id">{finding.target}</td><td>“{finding.quote}”</td><td>{finding.why}</td><td>{finding.fix}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** A file this stage has not produced yet. */
export function NotYet({ what, children }: { what: string; children?: string }) {
  return <SystemMessage kind="missing" title={`No ${what} Yet`}>{children ?? "Claude writes it when the run reaches this stage."}</SystemMessage>;
}
