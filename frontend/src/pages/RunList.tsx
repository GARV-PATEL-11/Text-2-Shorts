// Ongoing runs and previous (finished) runs: searchable, each with where it is and its progress.
import { useState } from "react";
import { Input, SearchField } from "react-aria-components";
import { ProgressBar } from "../components/feedback/ProgressBar";
import { SystemMessage } from "../components/feedback/SystemMessage";
import { Page, PageHeader } from "../components/layout/Page";
import { Breadcrumbs } from "../components/navigation/Breadcrumbs";
import { Button, LinkButton } from "../components/ui/Button";
import { Plus, Search } from "../components/ui/icons";
import { runTitle } from "../components/ui/Markdown";
import { REQUIRED_STEPS, stageName } from "../config/stages";
import { useRuns } from "../hooks/useRuns";
import { runHash } from "../services/runs";

export function RunListPage({ which }: { which: "ongoing" | "previous" }) {
  const runs = useRuns();
  const [query, setQuery] = useState("");
  const title = which === "ongoing" ? "Ongoing Runs" : "Previous Runs";
  const wanted = which === "ongoing" ? runs.ongoing : runs.finished;
  const shown = wanted.filter((run) => run.topic.toLowerCase().includes(query.trim().toLowerCase()));

  let body;
  if (runs.error) body = <SystemMessage kind="unavailable" title="Your Runs Did Not Load" action={<Button variant="secondary" size="sm" onPress={runs.reload}>Try Again</Button>}>{runs.error.message}</SystemMessage>;
  else if (!runs.data) body = <SystemMessage kind="loading" title="Loading Your Runs" />;
  else if (!shown.length) {
    body = query ? (
      <SystemMessage kind="empty" title="No Matches" action={<Button variant="secondary" size="sm" onPress={() => setQuery("")}>Clear Search</Button>}>
        Nothing in {title.toLowerCase()} mentions “{query}”.
      </SystemMessage>
    ) : (
      <SystemMessage kind="empty" title={which === "ongoing" ? "Nothing in Progress" : "No Finished Run Yet"}
        action={<LinkButton href="#/new" size="sm" icon={<Plus />}>Start a Run</LinkButton>}>
        {which === "ongoing" ? "No runs yet. Ask your first question." : "A run lands here once its final video is approved."}
      </SystemMessage>
    );
  } else {
    body = (
      <div className="table-wrap" tabIndex={0} role="region" aria-label="Table (scrolls sideways on small screens)">
        <table className="table">
          <thead><tr><th scope="col">Topic</th><th scope="col">Started</th><th scope="col">Where It Is</th><th scope="col">Progress</th></tr></thead>
          <tbody>
            {shown.map((run) => (
              <tr key={run.id}>
                <td><a className="table__link" href={runHash(run.id)}>{runTitle(run.topic)}</a></td>
                <td className="table__muted">{run.created}</td>
                <td>{run.readable ? stageName(run.stage) : "Older Version: Final Video Only"}{run.has_final ? <span className="badge">Final Video</span> : null}</td>
                <td className="table__progress">
                  <ProgressBar label={`${runTitle(run.topic)}: Stages Approved`} value={run.stages_approved} max={REQUIRED_STEPS.length}
                    valueLabel={`${run.stages_approved} of ${REQUIRED_STEPS.length}`} hideLabel />
                  <span className="table__muted">{run.stages_approved} of {REQUIRED_STEPS.length}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  return (
    <Page title={title}>
      <Breadcrumbs trail={[{ label: title }]} />
      <PageHeader
        title={title}
        lead={which === "ongoing" ? "Runs still being made, newest first. Open one to see its stages." : "Finished runs and their final videos."}
        actions={
          <SearchField className="search" value={query} onChange={setQuery} aria-label={`Search ${title.toLowerCase()}`}>
            <Search />
            <Input className="search__input" placeholder="Search by Topic" />
          </SearchField>
        }
      />
      {body}
    </Page>
  );
}
