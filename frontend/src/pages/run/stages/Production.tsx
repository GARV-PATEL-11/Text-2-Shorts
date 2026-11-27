// The pictures: scene plans (with critiques and accuracy), the scenes as they are built, and the final video.
import { ProgressBar } from "../../../components/feedback/ProgressBar";
import { StatusPill } from "../../../components/feedback/StatusPill";
import { SystemMessage } from "../../../components/feedback/SystemMessage";
import { VideoPreview } from "../../../components/media/VideoPreview";
import { titleCase } from "../../../components/ui/text";
import { Said, usePick } from "../../../components/ui/Said";
import { Markdown, runTitle } from "../../../components/ui/Markdown";
import { sceneName } from "../Overview";
import { fill, TITLES } from "../titles";
import { useRunFile } from "../../../hooks/useRunFile";
import { CheckpointPanel } from "../CheckpointPanel";
import { useRun } from "../context";
import { CritiqueRounds, type Finding, Findings, NotYet, type Round } from "../review";
import { type StageProps, StageTabs, waiting } from "./StageTabs";

interface ClipPlan { clip_id: string; objective: string; visual_intent: string; beats: string[]; est_seconds: number }
interface ScenePlan { scene_id: string; title: string; composition: string; transition_in: string; clips: ClipPlan[] }

/** The Visual Director's Scene Execution Plan (plan.json's execution_plan): its tagged sections as headings. */
function ExecutionPlan({ sceneId }: { sceneId: string }) {
  const { run } = useRun();
  const plan = useRunFile<{ execution_plan?: string }>(run.summary.id, `scenes/${sceneId}/plan.json`);
  const loadingTitle = usePick(TITLES.loadingExecution);
  if (plan.loading && !plan.data) return <SystemMessage kind="loading" title={fill(loadingTitle, { scene: sceneName(sceneId) })} compact said="loading" />;
  if (plan.error && !plan.data) return <SystemMessage kind="unavailable" title={`Could Not Load the Execution Plan for ${sceneName(sceneId)}`} compact>{plan.error.message}</SystemMessage>;
  if (!plan.data?.execution_plan) return <SystemMessage kind="missing" title={`No Execution Plan for ${sceneName(sceneId)} Yet`} compact />;
  const text = plan.data.execution_plan
    .replace(/^<\/[A-Z_]+>\s*$/gm, "")
    .replace(/^<([A-Z_]+)>\s*$/gm, (_, tag: string) => `### ${titleCase(tag.toLowerCase().replace(/_/g, " "))}`);
  return (
    <article className="card stack">
      <div className="row row--tight"><span className="badge">{sceneName(sceneId)}</span><h3 className="card__title">Execution Plan</h3></div>
      <Markdown text={text} />
    </article>
  );
}

/** The scene's accepted Manim code (scene_code.py: one _clip_N method per clip) and the builder's notes on it. */
function SceneCode({ sceneId }: { sceneId: string }) {
  const { run } = useRun();
  const code = useRunFile<string>(run.summary.id, `scenes/${sceneId}/scene_code.py`, "text");
  const changes = useRunFile<string>(run.summary.id, `scenes/${sceneId}/work/CHANGES.md`, "text");
  if (!code.data) return null;
  return (
    <article className="card stack">
      <h3 className="card__title">Scene Code</h3>
      <p className="note"><Said moment="sceneCode" /></p>
      {changes.data ? <Markdown text={changes.data} /> : null}
      <pre className="document" tabIndex={0} aria-label={`Manim Code of ${sceneName(sceneId)}`}><code>{code.data}</code></pre>
    </article>
  );
}

function PlanCard({ sceneId }: { sceneId: string }) {
  const { run } = useRun();
  const plan = useRunFile<ScenePlan>(run.summary.id, `scenes/${sceneId}/plan.json`);
  const loadingTitle = usePick(TITLES.loadingPlan);
  if (!plan.data) return plan.loading ? <SystemMessage kind="loading" title={fill(loadingTitle, { scene: sceneName(sceneId) })} compact said="loading" /> : null;
  return (
    <article className="card stack">
      <div className="row row--tight"><span className="badge">{sceneName(plan.data.scene_id)}</span><h3 className="card__title">{titleCase(plan.data.title)}</h3></div>
      <p className="note">{plan.data.composition}</p>
      {plan.data.transition_in ? <p className="note">Opens With: {plan.data.transition_in}</p> : null}
      <div className="table-wrap" tabIndex={0} role="region" aria-label="Scene Plan Table (Scrolls Sideways on Small Screens)">
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
  if (!critique.data) return <SystemMessage kind="pending" title={`No ${titleCase(kind)} Critique for ${sceneName(sceneId)} Yet`} compact said="critiquing" />;
  return <CritiqueRounds title={`${sceneName(sceneId)} · ${titleCase(kind)} Critique`} rounds={critique.data.rounds} />;
}

export function Plans(props: StageProps) {
  const { run } = useRun();
  const review = useRunFile<{ findings: Finding[] }>(run.summary.id, "plan_review.json");
  if (!run.scenes.length) return <NotYet what="Scene Plans" said="planningScenes">Written After You Approve the Script</NotYet>;
  return (
    <StageTabs {...props} label="Scene Plans" tabs={[
      { id: "plans", label: "Plans", content: <div className="stack">{run.scenes.map((scene) => <PlanCard key={scene.scene_id} sceneId={scene.scene_id} />)}</div> },
      { id: "execution", label: "Execution Plans", content: <div className="stack">{run.scenes.map((scene) => <ExecutionPlan key={scene.scene_id} sceneId={scene.scene_id} />)}</div> },
      { id: "critiques", label: "Critiques", content: <div className="stack">{run.scenes.map((scene) => <SceneCritique key={scene.scene_id} sceneId={scene.scene_id} kind="plan" />)}</div> },
      { id: "accuracy", label: "Accuracy", content: review.data ? <Findings findings={review.data.findings} /> : <NotYet what="Accuracy Review" said="critiquing" /> },
      { id: "checkpoint", label: "Checkpoint", count: waiting(run.awaiting, "plan"), content: <CheckpointPanel target="plan" /> },
    ]} />
  );
}

export function Scenes(props: StageProps) {
  const { run } = useRun();
  const noPreview = usePick(TITLES.noPreview);
  if (!run.scenes.length) return <NotYet what="Scenes" said="buildingClips">Built After the Scene Plans Are Approved</NotYet>;
  const count = (wanted: string[]) => run.scenes.filter((scene) => wanted.includes(scene.status)).length;
  const approval = {  // CP3: every scene built and previewed first, then one approval for all of them
    id: "approval", label: "Approve All Scenes", count: waiting(run.awaiting, "scenes"),
    content: (
      <div className="stack">
        <dl className="facts">
          <div><dt>Scenes</dt><dd>{run.scenes.length}</dd></div>
          <div><dt>Ready</dt><dd>{count(["requires_user_approval", "approved"])}</dd></div>
          <div><dt>Still Building</dt><dd>{count(["pending", "in_progress", "requires_refactoring"])}</dd></div>
          <div><dt>Failed</dt><dd>{count(["failed"])}</dd></div>
        </dl>
        <CheckpointPanel target="scenes" />
      </div>
    ),
  };
  return (
    <StageTabs {...props} label="Scenes" tabs={[...run.scenes.map((scene) => {
      const built = scene.clips.filter((clip) => ["completed", "approved"].includes(clip.status)).length;
      const decision = run.awaiting.find((checkpoint) => checkpoint.target === `start:${scene.scene_id}`);
      return {
        id: scene.scene_id, label: sceneName(scene.scene_id), count: decision ? 1 : 0,
        content: (
          <div className="scene-view">
            <VideoPreview src={scene.preview} label={`Preview of ${scene.title}`} empty={noPreview} emptyHint="Appears Once the Scene's Code Is Built" />
            <div className="stack">
              <div className="row row--tight"><h3 className="card__title">{titleCase(scene.title)}</h3><StatusPill value={scene.status} /></div>
              <ProgressBar label="Clips Built" value={built} max={scene.clips.length} valueLabel={`${built} of ${scene.clips.length}`} />
              {scene.clips.length && built < scene.clips.length && scene.status !== "failed" ? <p className="note"><Said moment="buildingClips" /></p> : null}
              <div className="table-wrap" tabIndex={0} role="region" aria-label="Clips Table (Scrolls Sideways on Small Screens)">
                <table className="table table--compact">
                  <thead><tr><th scope="col">Clip</th><th scope="col">What It Shows</th><th scope="col">Status</th></tr></thead>
                  <tbody>{scene.clips.map((clip) => <tr key={clip.clip_id}><td className="id">{clip.clip_id}</td><td>{clip.objective}</td><td><StatusPill value={clip.status} /></td></tr>)}</tbody>
                </table>
              </div>
              {scene.sync_problems.length ? <>
                <h4 className="subhead">Sync Problems</h4>
                <p className="note"><Said moment="syncing" /></p>
                <ul className="points">{scene.sync_problems.map((problem) => <li key={problem}>{problem}</li>)}</ul>
              </> : null}
            </div>
            <div className="scene-view__wide stack">
              <SceneCritique sceneId={scene.scene_id} kind="video" />
              <SceneCode sceneId={scene.scene_id} />
              {decision ? <CheckpointPanel target={decision.target} /> : null}
            </div>
          </div>
        ),
      };
    }), approval]} />
  );
}

export function Final(props: StageProps) {
  const { run } = useRun();
  const noFinal = usePick(TITLES.noFinalRendered);
  return (
    <StageTabs {...props} label="Final Video" tabs={[
      { id: "video", label: "Video", content: (
        <div className="stack">
          {run.final_video ? <p className="note"><Said moment="complete" /></p> : null}
          <VideoPreview src={run.final_video} label={`Final Video: ${runTitle(run.summary.topic)}`} empty={noFinal} emptyHint="Rendered at 2560 × 1440 Once Every Scene Is Approved" />
          {run.final_video ? null : <p className="note"><Said moment="rendering" /></p>}
        </div>
      ) },
      { id: "checks", label: "Media Checks", count: run.final_checks.length, content: !run.final_video ? <NotYet what="Media Checks" verb="Run" said={false} /> : run.final_checks.length ? (
        <div className="table-wrap" tabIndex={0} role="region" aria-label="Media Checks Table (Scrolls Sideways on Small Screens)">
          <table className="table table--compact">
            <thead><tr><th scope="col">Severity</th><th scope="col">Check</th></tr></thead>
            <tbody>{run.final_checks.map((check, index) => (
              <tr key={index}><td><span className={`badge${check.severity === "ERROR" ? " badge--solid" : ""}`}>{check.severity === "ERROR" ? "Error" : "Warning"}</span></td><td>{`${titleCase(check.code)}: ${check.message}`}</td></tr>
            ))}</tbody>
          </table>
        </div>
      ) : <SystemMessage kind={run.final_checked ? "success" : "pending"} title={run.final_checked ? "Every Check Passed" : "No Media Checks Recorded"} said={run.final_checked ? "checksPassed" : false} /> },
      { id: "checkpoint", label: "Checkpoint", count: waiting(run.awaiting, "final"), content: <CheckpointPanel target="final" /> },
    ]} />
  );
}
