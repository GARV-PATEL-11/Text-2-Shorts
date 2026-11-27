// Ongoing runs (with unfinished Start a Run drafts on top) and previous (finished) runs: searchable, each with its
// name, template, status, where it is, progress and last change; rename, duplicate or move a run to the trash.
import { useState } from "react";
import { Input, SearchField } from "react-aria-components";
import { navigate } from "../app/routes";
import { Modal } from "../components/feedback/Overlay";
import { Notice } from "../components/feedback/Notice";
import { ProgressBar } from "../components/feedback/ProgressBar";
import { SystemMessage } from "../components/feedback/SystemMessage";
import { Page, PageHeader } from "../components/layout/Page";
import { Breadcrumbs } from "../components/navigation/Breadcrumbs";
import { Button, LinkButton } from "../components/ui/Button";
import { Field } from "../components/ui/fields";
import { Delete, Duplicate, Plus, Rename, Search } from "../components/ui/icons";
import { runTitle } from "../components/ui/Markdown";
import { Said, useLine, usePick } from "../components/ui/Said";
import { titleCase } from "../components/ui/text";
import { REQUIRED_STEPS, stageName } from "../config/stages";
import { TITLES } from "../config/titles";
import { useAction } from "../hooks/useAction";
import { useApi } from "../hooks/useApi";
import { useRuns } from "../hooks/useRuns";
import { send } from "../services/http";
import { runHash, runPath } from "../services/runs";
import type { Draft, RunSummary } from "../types/api";

const STATUS: Record<RunSummary["status"], string> = {
  configuring: "Not Started", in_progress: "In Progress", awaiting_approval: "Waiting for You", failed: "Failed", completed: "Done",  // the words of the status pill (config/status.tsx)
};

const runName = (run: RunSummary) => run.name || runTitle(run.topic);
const draftTitle = (draft: Draft) => draft.name || (draft.requirement ? runTitle(draft.requirement) : "Untitled Run");

type Pending = { kind: "rename" | "delete"; run: RunSummary } | { kind: "discard"; draft: Draft } | null;

export function RunListPage({ which }: { which: "ongoing" | "previous" }) {
  const runs = useRuns();
  const drafts = useApi<Draft[]>(which === "ongoing" ? "/api/drafts" : null);
  const [query, setQuery] = useState("");
  const [pending, setPending] = useState<Pending>(null);
  const [name, setName] = useState("");
  const action = useAction();
  const loadingRuns = usePick(TITLES.loadingRuns);
  const copying = usePick(TITLES.copying);
  const noMatches = usePick(TITLES.noMatches);
  const draftLine = useLine("draft");
  const title = which === "ongoing" ? "Ongoing Runs" : "Previous Runs";
  const wanted = which === "ongoing" ? runs.ongoing : runs.finished;
  const matches = (text: string) => text.toLowerCase().includes(query.trim().toLowerCase());
  const shown = wanted.filter((run) => matches(`${run.name} ${run.topic} ${run.template}`));
  const shownDrafts = (drafts.data ?? []).filter((draft) => matches(`${draft.name} ${draft.requirement}`));

  const done = (text: string) => { setPending(null); runs.reload(); drafts.reload(); return text; };
  const rename = (run: RunSummary) => action.run("Renaming…", async () => {
    await send(runPath(run.id, ""), { name: name.trim() }, "PATCH");
    return done(`Renamed to ${name.trim()}`);
  });
  const duplicate = (run: RunSummary) => action.run(copying, async () => {
    const copy = await send<RunSummary>(runPath(run.id, "/duplicate"), null);
    navigate(runHash(copy.id));
    return done(`${copy.name} Created`);
  });
  const remove = (run: RunSummary) => action.run("Moving to the Trash…", async () => {
    await send(runPath(run.id, ""), null, "DELETE");
    return done(`${run.name} Moved to the Trash`);
  });
  const discard = (draft: Draft) => action.run("Discarding the Draft…", async () => {
    await send(`/api/drafts/${draft.id}`, null, "DELETE");
    return done("Draft Discarded");
  });

  const draftRows = shownDrafts.map((draft) => (
    <tr key={draft.id}>
      <td>
        <a className="table__link" href={`#/new?draft=${draft.id}`}>{draftTitle(draft)}</a>
        <span className="table__sub" title={draftLine.source ? `${draftLine.text} — ${draftLine.source}` : undefined}>Draft</span>
      </td>
      <td className="table__muted">{draft.look ? titleCase(draft.look.template) : "—"}</td>
      <td><span className="badge">Not Started</span></td>
      <td>Start a Run</td>
      <td className="table__progress"><span className="table__muted">—</span></td>
      <td className="table__muted table__nowrap">{draft.updated.replace("T", " ").slice(0, 16)}</td>
      <td className="table__actions">
        <Button variant="tertiary" size="sm" icon={<Delete />} label={`Discard Draft: ${draftTitle(draft)}`} onPress={() => setPending({ kind: "discard", draft })} />
      </td>
    </tr>
  ));
  const runRows = shown.map((run) => (
    <tr key={run.id}>
      <td>
        <a className="table__link" href={runHash(run.id)}>{run.name || runTitle(run.topic)}</a>
        <span className="table__sub">Started {run.created}</span>
      </td>
      <td className="table__muted">{run.template ? titleCase(run.template) : "—"}</td>
      <td><span className={`badge${run.status === "awaiting_approval" ? " badge--solid" : ""}`}>{STATUS[run.status]}</span></td>
      <td>{run.readable ? stageName(run.stage) : run.has_final ? "Older Version: Final Video Only" : "Cannot Be Read"}</td>
      <td className="table__progress">
        {run.readable ? (
          <div className="table__bar">
            <ProgressBar label={`${run.name}: Stages Approved`} value={run.stages_approved} max={REQUIRED_STEPS.length}
              valueLabel={`${run.stages_approved} of ${REQUIRED_STEPS.length}`} hideLabel />
            <span className="table__muted">{run.stages_approved} of {REQUIRED_STEPS.length}</span>
          </div>
        ) : <span className="table__muted">Not Tracked</span>}
      </td>
      <td className="table__muted table__nowrap">{run.updated}</td>
      <td className="table__actions">
        <Button variant="tertiary" size="sm" icon={<Rename />} label={`Rename ${runName(run)}`} onPress={() => { setName(run.name); setPending({ kind: "rename", run }); }} />
        <Button variant="tertiary" size="sm" icon={<Duplicate />} label={`Duplicate ${runName(run)}`} onPress={() => duplicate(run)} isDisabled={action.busy} />
        <Button variant="tertiary" size="sm" icon={<Delete />} label={`Move ${runName(run)} to the Trash`} onPress={() => setPending({ kind: "delete", run })} />
      </td>
    </tr>
  ));

  let body;
  if (runs.error) body = <SystemMessage kind="unavailable" title="Could Not Load Runs" action={<Button variant="secondary" size="sm" onPress={runs.reload}>Try Again</Button>}>{runs.error.message}</SystemMessage>;
  else if (!runs.data) body = <SystemMessage kind="loading" title={loadingRuns} />;
  else if (!shown.length && !shownDrafts.length) {
    body = query ? (
      <SystemMessage kind="empty" title={noMatches} said="noMatches" action={<Button variant="secondary" size="sm" onPress={() => setQuery("")}>Clear Search</Button>}>
        Nothing in {title.toLowerCase()} mentions “{query}”
      </SystemMessage>
    ) : (
      <SystemMessage kind="empty" title={which === "ongoing" ? "Nothing in Progress" : "No Finished Run Yet"}
        action={<LinkButton href="#/new" size="sm" icon={<Plus />}>Start a Run</LinkButton>}>
        {which === "ongoing" ? <Said moment="noRuns" /> : "A Run Lands Here Once Its Final Video Is Approved"}
      </SystemMessage>
    );
  } else {
    body = (
      <div className="table-wrap" tabIndex={0} role="region" aria-label={`${title} Table`}>
        <table className="table">
          <thead>
            <tr>
              <th scope="col">Run</th><th scope="col">Template</th><th scope="col">Status</th><th scope="col">Where It Is</th>
              <th scope="col">Progress</th><th scope="col">Last Saved</th><th scope="col"><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>{draftRows}{runRows}</tbody>
        </table>
      </div>
    );
  }

  const close = () => setPending(null);
  const dialog = pending?.kind === "rename" ? (
    <Modal isOpen onOpenChange={close} title="Rename the Run" description="Only the Name Changes: Its Files and Progress Stay"
      footer={<><Button variant="secondary" onPress={close}>Cancel</Button><Button onPress={() => rename(pending.run)} isDisabled={action.busy || !name.trim()}>Rename</Button></>}>
      <Field label="Name" value={name} onChange={setName} maxLength={120} isRequired />
    </Modal>
  ) : pending?.kind === "delete" ? (
    <Modal isOpen onOpenChange={close} title={`Move ${pending.run.name} to the Trash?`}
      description="It Leaves Your Runs. Its Folder Moves to .trash in the Runs Folder; You Can Move It Back by Hand."
      footer={<><Button variant="secondary" onPress={close}>Keep It</Button><Button icon={<Delete />} onPress={() => remove(pending.run)} isDisabled={action.busy}>Move to the Trash</Button></>} />
  ) : pending?.kind === "discard" ? (
    <Modal isOpen onOpenChange={close} title="Discard This Draft?" description="The Choices Made So Far in Start a Run Are Deleted"
      footer={<><Button variant="secondary" onPress={close}>Keep It</Button><Button icon={<Delete />} onPress={() => discard(pending.draft)} isDisabled={action.busy}>Discard</Button></>} />
  ) : null;

  return (
    <Page title={title}>
      <Breadcrumbs trail={[{ label: title }]} />
      <PageHeader
        title={title}
        lead={which === "ongoing" ? "Newest First; Drafts From Start a Run on Top" : "Newest First, With Their Final Videos"}
        actions={
          <SearchField className="search" value={query} onChange={setQuery} aria-label={`Search ${title}`}>
            <Search />
            <Input className="search__input" placeholder="Search Runs" />
          </SearchField>
        }
      />
      <Notice note={action.note} />
      {action.note?.text === copying ? <p className="note"><Said moment="checking" /></p> : null}
      {drafts.error ? <SystemMessage kind="unavailable" title="Could Not Load Your Drafts" compact said="loadFailed" action={<Button variant="secondary" size="sm" onPress={drafts.reload}>Try Again</Button>}>{drafts.error.message}</SystemMessage> : null}
      {body}
      {dialog}
    </Page>
  );
}
