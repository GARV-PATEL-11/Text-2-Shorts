// A run at a glance, under its title: lookup chips (approach, length, started, stages, scenes, clips, what waits for
// you, open change requests) and, once there are scenes, each scene's clips by status as one stacked bar. Greys only:
// a status is told by its fill (solid, grey, hatched, outline) and always named in the legend and the tooltip.
import type { ReactNode } from "react";
import { Clapperboard, Clock, Message, Outline, Requirements, Storyboard } from "../../components/ui/icons";
import { titleCase } from "../../components/ui/text";
import { REQUIRED_STEPS, stageStatuses } from "../../config/stages";
import type { SceneView, Status } from "../../types/api";
import { useRun } from "./context";

const BUCKETS: { id: string; label: string; statuses: Status[] }[] = [
  { id: "done", label: "Built", statuses: ["approved", "completed"] },
  { id: "working", label: "In Progress", statuses: ["in_progress", "requires_refactoring"] },
  { id: "you", label: "Needs You", statuses: ["requires_user_approval", "failed"] },
  { id: "pending", label: "Not Started", statuses: ["pending"] },
];
const bucketOf = (status: Status) => BUCKETS.find((bucket) => bucket.statuses.includes(status))?.id ?? "pending";

function Chip({ icon, value, label }: { icon: ReactNode; value: ReactNode; label: string }) {
  return (
    <li className="chip">
      <span className="chip__icon" aria-hidden="true">{icon}</span>
      <span className="chip__value">{value}</span>
      <span className="chip__label">{label}</span>
    </li>
  );
}

function ClipChart({ scenes }: { scenes: SceneView[] }) {
  return (
    <figure className="clip-chart">
      <figcaption className="clip-chart__head">
        <span className="clip-chart__title">Clips per Scene</span>
        <ul className="clip-chart__legend">
          {BUCKETS.map((bucket) => <li key={bucket.id}><span className={`swatch swatch--${bucket.id}`} aria-hidden="true" />{bucket.label}</li>)}
        </ul>
      </figcaption>
      <ul className="clip-chart__rows">
        {scenes.map((scene) => {
          const counts = BUCKETS.map((bucket) => ({ ...bucket, count: scene.clips.filter((clip) => bucketOf(clip.status) === bucket.id).length }));
          const built = counts[0].count;
          const summary = counts.filter((bucket) => bucket.count).map((bucket) => `${bucket.label}: ${bucket.count}`).join(", ");
          return (
            <li key={scene.scene_id} className="clip-chart__row" aria-label={`${scene.scene_id}, ${scene.title}: ${summary || "no clips yet"}`}>
              <span className="clip-chart__scene id" title={scene.title}>{scene.scene_id}</span>
              <span className="clip-chart__bar">
                {scene.clips.length ? counts.filter((bucket) => bucket.count).map((bucket) => (
                  <span key={bucket.id} className={`clip-chart__segment swatch--${bucket.id}`} style={{ flexGrow: bucket.count }}
                    title={`${scene.scene_id} · ${titleCase(scene.title)} — ${bucket.label}: ${bucket.count} of ${scene.clips.length} clips`} />
                )) : <span className="clip-chart__segment swatch--pending" style={{ flexGrow: 1 }} title={`${scene.scene_id}: no clips planned yet`} />}
              </span>
              <span className="clip-chart__count">{built}/{scene.clips.length}</span>
            </li>
          );
        })}
      </ul>
    </figure>
  );
}

export function Overview() {
  const { run } = useRun();
  const statuses = stageStatuses(run);
  const approved = REQUIRED_STEPS.filter((step) => statuses[step.id] === "approved").length;
  const clips = run.scenes.flatMap((scene) => scene.clips);
  const built = clips.filter((clip) => bucketOf(clip.status) === "done").length;
  const open = run.requests.filter((request) => request.status === "open").length;
  return (
    <div className="overview">
      <ul className="chips" aria-label="This run at a glance">
        <Chip icon={<Requirements />} value={`${approved}/${REQUIRED_STEPS.length}`} label="Stages" />
        {run.approach ? <Chip icon={<Outline />} value={titleCase(run.approach)} label="Approach" /> : null}
        {run.minutes ? <Chip icon={<Clock />} value={`${run.minutes} Min`} label="Length" /> : null}
        <Chip icon={<Storyboard />} value={run.scenes.length} label="Scenes" />
        <Chip icon={<Clapperboard />} value={`${built}/${clips.length}`} label="Clips Built" />
        <Chip icon={<Message />} value={run.awaiting.length} label="Waiting for You" />
        {open ? <Chip icon={<Message />} value={open} label="Open Requests" /> : null}
        <Chip icon={<Clock />} value={run.summary.created} label="Started" />
      </ul>
      {run.scenes.length ? <ClipChart scenes={run.scenes} /> : null}
    </div>
  );
}
