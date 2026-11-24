// The pictures: scene plans (with critiques and accuracy), the scenes as they are built, and the final video.
import { ProgressBar } from "../../../components/feedback/ProgressBar";
import { StatusPill } from "../../../components/feedback/StatusPill";
import { SystemMessage } from "../../../components/feedback/SystemMessage";
import { VideoPreview } from "../../../components/media/VideoPreview";
import { titleCase } from "../../../components/ui/text";
import { runTitle } from "../../../components/ui/Markdown";
import { useRunFile } from "../../../hooks/useRunFile";
import { CheckpointPanel } from "../CheckpointPanel";
import { useRun } from "../context";
import { CritiqueRounds, type Finding, Findings, NotYet, type Round } from "../review";
import { type StageProps, StageTabs, waiting } from "./StageTabs";

interface ClipPlan { clip_id: string; objective: string; visual_intent: string; beats: string[]; est_seconds: number }
interface ScenePlan { scene_id: string; title: string; composition: string; transition_in: string; clips: ClipPlan[] }

function PlanCard({ sceneId }: { sceneId: string }) {
  const { run } = useRun();
  const plan = useRunFile<ScenePlan>(run.summary.id, `scenes/${sceneId}/plan.json`);
  if (!plan.data) return plan.loading ? <SystemMessage kind="loading" title={`Reading the Plan of ${sceneId}…`} compact /> : null;
  return (
    <article className="card stack">
      <div className="row row--tight"><span className="id">{plan.data.scene_id}</span><h3 className="card__title">{titleCase(plan.data.title)}</h3></div>
      <p className="note">{plan.data.composition}</p>
      {plan.data.transition_in ? <p className="note">Opens With: {plan.data.transition_in}</p> : null}
      <div className="table-wrap" tabIndex={0} role="region" aria-label="Table (scrolls sideways on small screens)">
        <table className="table table--compact">
          <thead><tr><th scope="col">Clip</th><th scope="col">What It Shows</th><th scope="col">Beats</th><th scope="col">Seconds</th></tr></thead>
          <tbody>
            {plan.data.clips.map((clip) => (
              <tr key={clip.clip_id}>
                <td className="id">{clip.clip_id}</td>
                <td>{clip.objective}<span className="table__muted"> {clip.visual_intent}</span></td>
                <td><ol className="points">{clip.beats.map((beat) => <li key={beat}>{beat}</li>)}</ol></td>
                <td>{clip.est_seconds}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}

function SceneCritique({ sceneId, kind }: { sceneId: string; kind: "plan" | "video" }) {
  const { run } = useRun();
  const critique = useRunFile<{ rounds: Round[] }>(run.summary.id, `scenes/${sceneId}/${kind}_critique.json`);
  if (!critique.data) return <SystemMessage kind="pending" title={`No ${titleCase(kind)} Critique for ${sceneId} Yet`} compact>Critics review it once it exists.</SystemMessage>;
  return <CritiqueRounds title={`${sceneId} · ${titleCase(kind)} Critique`} rounds={critique.data.rounds} />;
}

export function Plans(props: StageProps) {
  const { run } = useRun();
  const review = useRunFile<{ findings: Finding[] }>(run.summary.id, "plan_review.json");
  if (!run.scenes.length) return <NotYet what="Scene Plans">The scene-planner writes them after you approve the script.</NotYet>;
  return (
    <StageTabs {...props} label="Scene Plans" tabs={[
      { id: "plans", label: "Plans", content: <div className="stack">{run.scenes.map((scene) => <PlanCard key={scene.scene_id} sceneId={scene.scene_id} />)}</div> },
      { id: "critiques", label: "Critiques", content: <div className="stack">{run.scenes.map((scene) => <SceneCritique key={scene.scene_id} sceneId={scene.scene_id} kind="plan" />)}</div> },
      { id: "accuracy", label: "Accuracy", content: review.data ? <Findings findings={review.data.findings} /> : <NotYet what="Accuracy Review" /> },
      { id: "checkpoint", label: "Checkpoint", count: waiting(run.awaiting, "plan"), content: <CheckpointPanel target="plan" /> },
    ]} />
  );
}

export function Scenes(props: StageProps) {
  const { run } = useRun();
  if (!run.scenes.length) return <NotYet what="Scenes">Scenes are built one at a time after the scene plans are approved.</NotYet>;
  return (
    <StageTabs {...props} label="Scenes" tabs={run.scenes.map((scene) => {
      const built = scene.clips.filter((clip) => ["completed", "approved"].includes(clip.status)).length;
      const decision = run.awaiting.find((checkpoint) => checkpoint.target === scene.scene_id || checkpoint.target === `start:${scene.scene_id}`);
      return {
        id: scene.scene_id, label: scene.scene_id, count: decision ? 1 : 0,
        content: (
          <div className="scene-view">
            <VideoPreview src={scene.preview} label={`Preview of ${scene.title}`} empty="No Preview Yet: Rendered Once Every Clip Is Built" />
            <div className="stack">
              <div className="row row--tight"><h3 className="card__title">{titleCase(scene.title)}</h3><StatusPill value={scene.status} /></div>
              <ProgressBar label="Clips Built" value={built} max={scene.clips.length} valueLabel={`${built} of ${scene.clips.length}`} />
              <div className="table-wrap" tabIndex={0} role="region" aria-label="Table (scrolls sideways on small screens)">
                <table className="table table--compact">
                  <thead><tr><th scope="col">Clip</th><th scope="col">What It Shows</th><th scope="col">Status</th></tr></thead>
                  <tbody>{scene.clips.map((clip) => <tr key={clip.clip_id}><td className="id">{clip.clip_id}</td><td>{clip.objective}</td><td><StatusPill value={clip.status} /></td></tr>)}</tbody>
                </table>
              </div>
              {scene.sync_problems.length ? <ul className="problems">{scene.sync_problems.map((problem) => <li key={problem}>{problem}</li>)}</ul> : null}
            </div>
            <div className="scene-view__wide stack">
              <SceneCritique sceneId={scene.scene_id} kind="video" />
              {decision ? <CheckpointPanel target={decision.target} /> : null}
            </div>
          </div>
        ),
      };
    })} />
  );
}

export function Final(props: StageProps) {
  const { run } = useRun();
  return (
    <StageTabs {...props} label="Final Video" tabs={[
      { id: "video", label: "Video", content: <VideoPreview src={run.final_video} label={`Final Video: ${runTitle(run.summary.topic)}`} empty="No Final Video Yet: Rendered at 2560 × 1440 Once Every Scene Is Approved" /> },
      { id: "checks", label: "Media Checks", count: run.final_checks.length, content: !run.final_video ? <NotYet what="Media Checks" /> : run.final_checks.length ? (
        <div className="table-wrap" tabIndex={0} role="region" aria-label="Table (scrolls sideways on small screens)">
          <table className="table table--compact">
            <thead><tr><th scope="col">Severity</th><th scope="col">Check</th></tr></thead>
            <tbody>{run.final_checks.map((check, index) => (
              <tr key={index}><td><span className={`badge${check.severity === "ERROR" ? " badge--solid" : ""}`}>{check.severity === "ERROR" ? "Error" : "Warning"}</span></td><td>{`${check.code.replaceAll("_", " ").toLowerCase()}: ${check.message}`}</td></tr>
            ))}</tbody>
          </table>
        </div>
      ) : <SystemMessage kind={run.final_checked ? "success" : "pending"} title={run.final_checked ? "Every Check Passed" : "No Media Checks Recorded"} /> },
      { id: "checkpoint", label: "Checkpoint", count: waiting(run.awaiting, "final"), content: <CheckpointPanel target="final" /> },
    ]} />
  );
}
