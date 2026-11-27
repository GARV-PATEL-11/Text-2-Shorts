// A run at a glance, under its title: lookup chips (approach, length, scenes, open change requests, started) and, once
// there are scenes, each scene's clips by state. The stages and what waits for you are the rail's and the approval
// bar's to show, so they are not repeated here. Greys only: a state is told by its fill (solid, grey, hatched, crossed, outline), and always named in
// the legend and the tooltip (config/status.tsx).
import { approachName } from "../../config/approaches";
import { Chip, Chips } from "../../components/ui/Chip";
import { Calendar, Outline, RequestChange, Stopwatch, Storyboard } from "../../components/ui/icons";
import { titleCase } from "../../components/ui/text";
import { BUCKETS, bucketOf } from "../../config/status";
import type { SceneView } from "../../types/api";
import { useRun } from "./context";

/** Scene 3, from "s03". */
export const sceneName = (sceneId: string) => `Scene ${Number(sceneId.replace(/\D/g, "")) || sceneId}`;
/** Clip 3.1, from "c0301". */
export const clipName = (clipId: string) => {
  const match = /^c(\d\d)(\d\d)$/.exec(clipId);
  return match ? `Clip ${Number(match[1])}.${Number(match[2])}` : `Clip ${clipId}`;
};
/** What a change request names, in words: "the Outline", "Scene 3", "Clip 3.1". */
export const targetName = (target: string) =>
  ({ outline: "the Outline", script: "the Script", plan: "All Scene Plans", scenes: "All Scenes", final: "the Final Video" } as Record<string, string>)[target]
  ?? (/^s\d+$/.test(target) ? sceneName(target) : /^c\d{4}$/.test(target) ? clipName(target) : target);
/** 2026-11-27T10:15:00 → 27 Nov 2026, 10:15 (as written when it is not a date). */
export const when = (stamp: string) => {
  const date = new Date(stamp);
  return Number.isNaN(date.getTime()) ? stamp
    : date.toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
};

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
            <li key={scene.scene_id} className="clip-chart__row" aria-label={`${sceneName(scene.scene_id)}, ${titleCase(scene.title)}: ${summary || "No Clips Planned"}`}>
              <span className="clip-chart__scene" title={titleCase(scene.title)}>{sceneName(scene.scene_id)}</span>
              {/* the bar's length is the scene's share of the longest scene: a 2-clip scene is shorter than a 4-clip one */}
              <span className="clip-chart__track">
                <span className="clip-chart__bar" style={{ width: `${(Math.max(scene.clips.length, 1) / longest) * 100}%` }}>
                  {scene.clips.length ? counts.filter((bucket) => bucket.count).map((bucket) => (
                    <span key={bucket.id} className={`clip-chart__segment swatch--${bucket.id}`} style={{ flexGrow: bucket.count }}
                      title={`${sceneName(scene.scene_id)} · ${titleCase(scene.title)} — ${bucket.label}: ${bucket.count} of ${scene.clips.length}`} />
                  )) : <span className="clip-chart__segment swatch--not-started" style={{ flexGrow: 1 }} title={`${sceneName(scene.scene_id)}: No Clips Planned`} />}
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
      <Chips label="At a Glance">
        {run.approach ? <Chip icon={<Outline />} value={approachName(run.approach)} label="Approach" /> : null}
        {run.minutes ? <Chip icon={<Stopwatch />} value={`${run.minutes} Min`} label="Length" /> : null}
        <Chip icon={<Storyboard />} value={run.scenes.length} label="Scenes" />
        {open ? <Chip icon={<RequestChange />} value={open} label="Open Change Requests" /> : null}
        <Chip icon={<Calendar />} value={when(run.summary.created)} label="Started" />
      </Chips>
      {run.scenes.length ? <ClipChart scenes={run.scenes} /> : null}
    </div>
  );
}
