// Requirements: the brief, the topic list and the content the outline is built from.
import { approachName } from "../../../config/approaches";
import { Markdown } from "../../../components/ui/Markdown";
import { usePick } from "../../../components/ui/Said";
import { useRunFile } from "../../../hooks/useRunFile";
import { CheckpointPanel } from "../CheckpointPanel";
import { useRun } from "../context";
import { NotYet } from "../review";
import { TITLES } from "../titles";
import { type StageProps, StageTabs, waiting } from "./StageTabs";

export function Requirements(props: StageProps) {
  const { run } = useRun();
  const unset = usePick(TITLES.objectivesUnset);
  const topics = useRunFile<string>(run.summary.id, "topics.md", "text");
  const content = useRunFile<string>(run.summary.id, "content.md", "text");
  return (
    <StageTabs {...props} label="Requirements" tabs={[
      { id: "brief", label: "Brief", content: (
        <dl className="facts facts--wide">
          <div><dt>Topic</dt><dd><Markdown text={run.summary.topic} compact /></dd></div>
          <div><dt>Objectives</dt><dd>{run.objectives.length ? <ul>{run.objectives.map((goal) => <li key={goal}>{goal}</li>)}</ul> : unset}</dd></div>
          <div><dt>Approach</dt><dd>{approachName(run.approach)}</dd></div>
          <div><dt>Length</dt><dd>{run.minutes} Min</dd></div>
        </dl>
      ) },
      { id: "topics", label: "Topics", content: topics.data ? <div className="document"><Markdown text={topics.data} /></div> : <NotYet what="Topic List" /> },
      { id: "content", label: "Content", content: content.data ? <div className="document"><Markdown text={content.data} /></div> : <NotYet what="Content" /> },
      { id: "checkpoint", label: "Checkpoint", count: waiting(run.awaiting, "requirements"), content: <CheckpointPanel target="requirements" /> },
    ]} />
  );
}
