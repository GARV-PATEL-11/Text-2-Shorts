// A run at a glance, under its title: lookup chips (approach, length, scenes, what waits for you, open change requests,
// started) and, once there are scenes, each scene's clips by state. The rail already shows the stages, so they are not
// repeated here. Greys only: a state is told by its fill (solid, grey, hatched, crossed, outline), and always named in
// the legend and the tooltip (config/status.tsx).
import type { ReactNode } from "react";
import { Calendar, Outline, RequestChange, Stopwatch, Storyboard, Waiting } from "../../components/ui/icons";
import { titleCase } from "../../components/ui/text";
import { BUCKETS, bucketOf } from "../../config/status";
import type { SceneView } from "../../types/api";
import { useRun } from "./context";

function Chip({ icon, value, label }: { icon: ReactNode; value: ReactNode; label: string }) {
  return (
    <li className="chip">
      <span className="icon-box icon-box--sm" aria-hidden="true">{icon}</span>
      <span className="chip__value">{value}</span>
      <span className="chip__label">{label}</span>
    </li>
  );
}

/** Scene 3, from "s03". */
export const sceneName = (sceneId: string) => `Scene ${Number(sceneId.replace(/\D/g, "")) || sceneId}`;

function ClipChart({ scenes }: { scenes: SceneView[] }) {
  const longest = Math.max(1, ...scenes.map((scene) => scene.clips.length));
  const present = BUCKETS.filter((bucket) => scenes.some((scene) => scene.clips.some((clip) => bucketOf(clip.status) === bucket.id)));
  return (
    <figure className="clip-chart">
      <figcaption className="clip-chart__head">
        <span className="clip-chart__title">Clips per Scene</span>
        <ul className="clip-chart__legend">
          {present.map((bucket) => <li key={bucket.id}><span className={`swatch swatch--${bucket.id}`} aria-hidden="true" />{bucket.label}</li>)}
        </ul>
      </figcaption>
      <ul className="clip-chart__rows">
        {scenes.map((scene) => {
          const counts = BUCKETS.map((bucket) => ({ ...bucket, count: scene.clips.filter((clip) => bucketOf(clip.status) === bucket.id).length }));
          const done = counts.find((bucket) => bucket.id === "done")?.count ?? 0;
          const summary = counts.filter((bucket) => bucket.count).map((bucket) => `${bucket.label}: ${bucket.count}`).join(", ");
          return (
            <li key={scene.scene_id} className="clip-chart__row" aria-label={`${sceneName(scene.scene_id)}, ${titleCase(scene.title)}: ${summary || "no clips planned"}`}>
              <span className="clip-chart__scene" title={titleCase(scene.title)}>{sceneName(scene.scene_id)}</span>
              {/* the bar's length is the scene's share of the longest scene: a 2-clip scene is shorter than a 4-clip one */}
              <span className="clip-chart__track">
                <span className="clip-chart__bar" style={{ width: `${(Math.max(scene.clips.length, 1) / longest) * 100}%` }}>
                  {scene.clips.length ? counts.filter((bucket) => bucket.count).map((bucket) => (
                    <span key={bucket.id} className={`clip-chart__segment swatch--${bucket.id}`} style={{ flexGrow: bucket.count }}
                      title={`${sceneName(scene.scene_id)} · ${titleCase(scene.title)} — ${bucket.label}: ${bucket.count} of ${scene.clips.length}`} />
                  )) : <span className="clip-chart__segment swatch--not-started" style={{ flexGrow: 1 }} title={`${sceneName(scene.scene_id)}: no clips planned`} />}
                </span>
              </span>
              <span className="clip-chart__count">{done}/{scene.clips.length}</span>
            </li>
          );
        })}
      </ul>
    </figure>
  );
}

export function Overview() {
  const { run } = useRun();
  const open = run.requests.filter((request) => request.status === "open").length;
  return (
    <div className="overview">
      <ul className="chips" aria-label="At a Glance">
        {run.approach ? <Chip icon={<Outline />} value={titleCase(run.approach)} label="Approach" /> : null}
        {run.minutes ? <Chip icon={<Stopwatch />} value={`${run.minutes} Min`} label="Length" /> : null}
        <Chip icon={<Storyboard />} value={run.scenes.length} label="Scenes" />
        {run.awaiting.length ? <Chip icon={<Waiting />} value={run.awaiting.length} label="Waiting for You" /> : null}
        {open ? <Chip icon={<RequestChange />} value={open} label="Open Requests" /> : null}
        <Chip icon={<Calendar />} value={run.summary.created} label="Started" />
      </ul>
      {run.scenes.length ? <ClipChart scenes={run.scenes} /> : null}
    </div>
  );
}
