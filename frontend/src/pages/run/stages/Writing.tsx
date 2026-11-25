// The words of the video: the outline, then the script (with its accuracy review and critique rounds).
import { titleCase } from "../../../components/ui/text";
import { useRunFile } from "../../../hooks/useRunFile";
import { CheckpointPanel } from "../CheckpointPanel";
import { useRun } from "../context";
import { Changes, CritiqueRounds, type Finding, Findings, NotYet, type Round } from "../review";
import { type StageProps, StageTabs, waiting } from "./StageTabs";

interface Segment { scene_id: number; segment_type: string; title: string; duration_seconds: number; talking_points: string[]; visual_plan: string }

export function Outline(props: StageProps) {
  const { run } = useRun();
  const outline = useRunFile<{ outline: Segment[] }>(run.summary.id, "outline.json");
  return (
    <StageTabs {...props} label="Outline" tabs={[
      { id: "outline", label: "Outline", content: outline.data ? (
        <ol className="cards cards--list">
          {outline.data.outline.map((segment) => (
            <li className="card stack" key={segment.scene_id}>
              <div className="row row--tight"><span className="id">{segment.scene_id}</span><h3 className="card__title">{segment.title}</h3><span className="badge">{titleCase(segment.segment_type)}</span><span className="table__muted">{segment.duration_seconds} s</span></div>
              <ul className="points">{segment.talking_points.map((point) => <li key={point}>{point}</li>)}</ul>
              <p className="note">Picture: {segment.visual_plan}</p>
            </li>
          ))}
        </ol>
      ) : <NotYet what="Outline" /> },
      { id: "changes", label: "Changes", content: <Changes targets={(target) => target === "outline"} defaultTarget="outline" /> },
      { id: "checkpoint", label: "Checkpoint", count: waiting(run.awaiting, "outline"), content: <CheckpointPanel target="outline" /> },
    ]} />
  );
}

interface ScriptScene { scene_id: string; role: string; title: string; objective: string; duration_seconds: number; bridge_in: string; narration: string }

export function Script(props: StageProps) {
  const { run } = useRun();
  const script = useRunFile<{ scenes: ScriptScene[] }>(run.summary.id, "script.json");
  const review = useRunFile<{ findings: Finding[] }>(run.summary.id, "script_review.json");
  const critique = useRunFile<{ rounds: Round[] }>(run.summary.id, "script_critique.json");
  return (
    <StageTabs {...props} label="Script" tabs={[
      { id: "script", label: "Script", content: script.data ? (
        <div className="stack">
          {script.data.scenes.map((scene) => (
            <article className="card scene-text" key={scene.scene_id}>
              <div className="scene-text__meta">
                <span className="id">{scene.scene_id}</span>
                <span className="badge">{titleCase(scene.role)}</span>
                <span className="table__muted">{scene.duration_seconds} s · {scene.narration.split(/\s+/).length} words</span>
              </div>
              <div className="scene-text__body">
                <h3 className="card__title">{titleCase(scene.title)}</h3>
                <p className="note">{scene.objective}</p>
                {scene.bridge_in ? <p className="narration narration--bridge">{scene.bridge_in}</p> : null}
                <p className="narration">{scene.narration}</p>
              </div>
            </article>
          ))}
        </div>
      ) : <NotYet what="Script" /> },
      { id: "accuracy", label: "Accuracy", count: review.data?.findings.filter((finding) => finding.severity === "ERROR").length,
        content: review.data ? <Findings findings={review.data.findings} /> : <NotYet what="Accuracy Review" /> },
      { id: "critique", label: "Critique", content: critique.data ? <CritiqueRounds rounds={critique.data.rounds} />
        : <NotYet what="Script Critique">Critiqued When You Request a Change at Its Checkpoint</NotYet> },
      { id: "changes", label: "Changes", content: <Changes targets={(target) => target === "script"} defaultTarget="script" /> },
      { id: "checkpoint", label: "Checkpoint", count: waiting(run.awaiting, "script"), content: <CheckpointPanel target="script" /> },
    ]} />
  );
}
