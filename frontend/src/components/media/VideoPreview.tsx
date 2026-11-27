// Video: the box holds its ratio in every state (empty, loading, buffering, playing, failed); a large play button
// until the first play and after the end; the browser's own controls (timeline, volume, speed, fullscreen) once
// playing; the duration from the file's metadata; full screen on this page from the corner button at any time.
import { useEffect, useRef, useState } from "react";
import { type Ratio, RATIOS } from "../../config/media";
import { Button } from "../ui/Button";
import { Expand, Film, Play, Shrink } from "../ui/icons";
import { Said } from "../ui/Said";
import { useFullScreen } from "./ImagePreview";

const clock = (seconds: number) =>
  Number.isFinite(seconds) ? `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}` : "";

export function VideoPreview({ src, label, ratio = "16/9", empty = "No Video Yet", emptyHint }: {
  src?: string | null; label: string; ratio?: Ratio; empty?: string; emptyHint?: string;
}) {
  const video = useRef<HTMLVideoElement>(null);
  const box = useRef<HTMLDivElement>(null);
  const screen = useFullScreen();
  const [state, setState] = useState<"loading" | "ready" | "playing" | "buffering" | "ended" | "failed">("loading");
  const [duration, setDuration] = useState(NaN);
  const [started, setStarted] = useState(false);
  useEffect(() => {  // a stalled network fires nothing: offer the play button after a while anyway
    if (state !== "loading") return;
    const timer = window.setTimeout(() => setState((current) => (current === "loading" ? "ready" : current)), 8000);
    return () => window.clearTimeout(timer);
  }, [state]);

  if (!src) {
    return (
      <div className="player player--empty">
        <Film />
        <strong className="player__empty-title">{empty}</strong>
        {emptyHint ? <span>{emptyHint}</span> : <span><Said moment="notYet" /></span>}
      </div>
    );
  }
  const play = () => {
    setStarted(true);
    void video.current?.play();
  };
  return (
    <div className={`player player--${state}`} style={{ aspectRatio: RATIOS[ratio] }} ref={box}>
      <video
        ref={video} src={src} preload="metadata" playsInline controls={started && state !== "ended"} aria-label={label}
        onLoadedMetadata={(event) => { setDuration(event.currentTarget.duration); setState("ready"); }}
        onPlaying={() => setState("playing")} onWaiting={() => setState("buffering")} onPause={() => setState((s) => (s === "ended" ? s : "ready"))}
        onEnded={() => setState("ended")} onError={() => setState("failed")}
      />
      {state === "loading" || state === "buffering" ? <span className="spinner player__spinner" role="status" aria-label="Loading the Video" /> : null}
      {(!started || state === "ended") && state !== "failed" && state !== "loading" ? (
        <button className="player__play" type="button" onClick={play} aria-label={`${state === "ended" ? "Play again" : "Play"}: ${label}`}>
          <Play />
        </button>
      ) : null}
      {Number.isFinite(duration) && !started ? <span className="player__duration">{clock(duration)}</span> : null}
      {screen.supported && state !== "failed" ? (
        <button className="media__expand media__expand--top" type="button" onClick={() => screen.toggle(box.current)}
          aria-label={`${screen.on ? "Exit Full Screen" : "Full Screen"}: ${label}`} title={screen.on ? "Exit Full Screen" : "Full Screen"}>
          {screen.on ? <Shrink /> : <Expand />}
        </button>
      ) : null}
      {state === "failed" ? (
        <div className="player__failed" role="alert">
          <span>Could Not Play This Video <Said moment="loadFailed" /></span>
          <Button variant="secondary" size="sm" onPress={() => { setState("loading"); video.current?.load(); }}>Try Again</Button>
        </div>
      ) : null}
    </div>
  );
}
