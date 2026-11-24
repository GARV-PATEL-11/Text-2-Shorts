// Audio: one compact row — play/pause, a waveform you can click to seek (the played part white, the rest grey),
// the time, and volume. The waveform is computed in the browser (Web Audio); while it is computed the bars pulse;
// if it cannot be (format, size), a plain scrubber takes its place and the audio still plays.
import { useEffect, useId, useRef, useState } from "react";
import { WAVEFORM_BARS, WAVEFORM_MAX_BYTES } from "../../config/media";
import { Button } from "../ui/Button";
import { Pause, Play, Volume } from "../ui/icons";

const peaksCache = new Map<string, number[]>();
let decoder: AudioContext | null = null;  // one for the page: browsers limit how many may exist at once

async function computePeaks(src: string, signal: AbortSignal): Promise<number[]> {
  const cached = peaksCache.get(src);
  if (cached) return cached;
  const response = await fetch(src, { signal });
  const bytes = await response.arrayBuffer();
  if (bytes.byteLength > WAVEFORM_MAX_BYTES) throw new Error("too large for a waveform");
  decoder = decoder ?? new AudioContext();
  {
    const samples = (await decoder.decodeAudioData(bytes)).getChannelData(0);
    const size = Math.floor(samples.length / WAVEFORM_BARS) || 1;
    const peaks = Array.from({ length: WAVEFORM_BARS }, (_, bar) => {
      let peak = 0;
      for (let i = bar * size; i < (bar + 1) * size && i < samples.length; i++) peak = Math.max(peak, Math.abs(samples[i]));
      return peak;
    });
    const loudest = Math.max(...peaks, 0.001);
    const normal = peaks.map((peak) => peak / loudest);
    peaksCache.set(src, normal);
    return normal;
  }
}

const clock = (seconds: number) =>
  Number.isFinite(seconds) ? `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}` : "0:00";

export function AudioPreview({ src, label }: { src: string; label: string }) {
  const audio = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState(0);
  const [length, setLength] = useState(0);
  const [volume, setVolume] = useState(1);
  const [peaks, setPeaks] = useState<number[] | "loading" | "unavailable">("loading");
  const clipId = `played-${useId().replace(/:/g, "")}`;

  useEffect(() => {
    const controller = new AbortController();
    setPeaks("loading");
    setPlaying(false);
    setTime(0);
    if (audio.current) audio.current.currentTime = 0;
    computePeaks(src, controller.signal).then(setPeaks).catch((error: Error) => error.name !== "AbortError" && setPeaks("unavailable"));
    return () => controller.abort();
  }, [src]);
  useEffect(() => {  // smooth playhead while playing (timeupdate alone is ~4 times a second)
    if (!playing) return;
    let frame = 0;
    const tick = () => {
      if (audio.current) setTime(audio.current.currentTime);
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [playing]);

  const seek = (seconds: number) => {
    if (audio.current && Number.isFinite(seconds)) audio.current.currentTime = Math.min(Math.max(seconds, 0), length || 0);
  };
  const toggle = () => {
    if (!audio.current) return;
    if (audio.current.paused) void audio.current.play();
    else audio.current.pause();
  };
  const played = length ? time / length : 0;
  return (
    <div className="audio" role="group" aria-label={label}>
      <audio
        ref={audio} src={src} preload="metadata"
        onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onEnded={() => setPlaying(false)}
        onTimeUpdate={(event) => setTime(event.currentTarget.currentTime)}
        onLoadedMetadata={(event) => setLength(Number.isFinite(event.currentTarget.duration) ? event.currentTarget.duration : 0)}
      />
      <Button variant="secondary" size="sm" icon={playing ? <Pause /> : <Play />} onPress={toggle} label={playing ? "Pause" : "Play"} />
      <div className="audio__wave">
        {Array.isArray(peaks) ? (
          <svg viewBox={`0 0 ${WAVEFORM_BARS * 4} 32`} preserveAspectRatio="none" aria-hidden="true"
            onClick={(event) => {
              const box = event.currentTarget.getBoundingClientRect();
              seek(((event.clientX - box.left) / box.width) * length);
            }}>
            <defs><clipPath id={clipId}><rect x="0" y="0" width={played * WAVEFORM_BARS * 4} height="32" /></clipPath></defs>
            {[false, true].map((front) => (
              <g key={String(front)} className={front ? "audio__bars audio__bars--played" : "audio__bars"}
                clipPath={front ? `url(#${clipId})` : undefined}>
                {peaks.map((peak, bar) => {
                  const height = Math.max(2, peak * 30);
                  return <rect key={bar} x={bar * 4 + 0.5} y={(32 - height) / 2} width="2.5" height={height} rx="1" />;
                })}
              </g>
            ))}
          </svg>
        ) : peaks === "loading" ? (
          <span className="audio__skeleton" aria-hidden="true" />
        ) : null}
        <input
          className={`audio__scrub${peaks === "unavailable" ? " audio__scrub--visible" : ""}`} type="range" min={0}
          max={length || 0} step={0.1} value={Math.min(time, length || 0)} aria-label="Position"
          aria-valuetext={`${clock(time)} of ${clock(length)}`} onChange={(event) => seek(Number(event.target.value))}
        />
      </div>
      <span className="audio__time">{clock(time)} / {clock(length)}</span>
      <label className="audio__volume">
        <Volume />
        <input type="range" min={0} max={1} step={0.05} value={volume} aria-label="Volume"
          onChange={(event) => { const next = Number(event.target.value); setVolume(next); if (audio.current) audio.current.volume = next; }} />
      </label>
      {peaks === "unavailable" ? <span className="audio__note">Waveform Unavailable</span> : null}
    </div>
  );
}
