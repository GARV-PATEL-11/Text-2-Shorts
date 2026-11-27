// One voice preview at a time: fetches its MP3, plays it through Web Audio (an AnalyserNode the orb reads), decodes its
// waveform for display, and reports idle | loading | playing | paused with the position. Reusable wherever a voice is
// heard (voice selection now; narration previews and audio tests later).
import { useCallback, useEffect, useRef, useState } from "react";

export type PlayerState = "idle" | "loading" | "playing" | "paused" | "error";
const PEAKS = 96;

export interface PreviewPlayer {
  state: PlayerState;
  peaks: number[];  // 0–1 per bar, of the last loaded preview
  position: number;  // seconds
  duration: number;
  problem: string | null;
  loadedKey: string | null;  // which preview is loaded (a changed setting makes it out of date)
  analyser: () => AnalyserNode | null;
  replay: () => void;
  play: (load: (signal: AbortSignal) => Promise<Blob>, key: string) => Promise<void>;
  toggle: () => void;
  seek: (fraction: number) => void;
  stop: () => void;
}

export function usePreviewPlayer(): PreviewPlayer {
  const [state, setState] = useState<PlayerState>("idle");
  const [peaks, setPeaks] = useState<number[]>([]);
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(0);
  const [problem, setProblem] = useState<string | null>(null);
  const [loadedKey, setLoadedKey] = useState<string | null>(null);
  const element = useRef<HTMLAudioElement | null>(null);
  const graph = useRef<{ context: AudioContext; analyser: AnalyserNode } | null>(null);
  const pending = useRef<AbortController | null>(null);
  const url = useRef<string | null>(null);
  const loaded = useRef<string | null>(null);  // which preview the element holds

  const release = () => {
    if (url.current) URL.revokeObjectURL(url.current);
    url.current = null;
    loaded.current = null;
  };
  const stop = useCallback(() => {
    pending.current?.abort();
    element.current?.pause();
    if (element.current) element.current.currentTime = 0;
    setState("idle");
    setPosition(0);
  }, []);
  useEffect(() => () => { pending.current?.abort(); element.current?.pause(); release(); void graph.current?.context.close(); }, []);
  useEffect(() => {  // a smoother playhead than timeupdate's 4 Hz, only while playing
    if (state !== "playing") return;
    const timer = window.setInterval(() => { if (element.current) setPosition(element.current.currentTime); }, 100);
    return () => window.clearInterval(timer);
  }, [state]);

  const audio = () => {
    if (element.current) return element.current;
    const created = new Audio();
    created.onended = () => { setState("idle"); setPosition(0); };
    created.ontimeupdate = () => setPosition(created.currentTime);
    created.onloadedmetadata = () => setDuration(Number.isFinite(created.duration) ? created.duration : 0);
    element.current = created;
    if ("AudioContext" in window) {
      const context = new AudioContext();
      const analyser = context.createAnalyser();
      analyser.fftSize = 512;
      analyser.smoothingTimeConstant = 0.75;
      context.createMediaElementSource(created).connect(analyser);  // once per element: the graph is reused
      analyser.connect(context.destination);
      graph.current = { context, analyser };
    }
    return created;
  };

  /** Load (unless it is the one already loaded) and play; stops whatever was playing first. */
  const play = useCallback(async (load: (signal: AbortSignal) => Promise<Blob>, key: string) => {
    pending.current?.abort();
    const player = audio();
    player.pause();
    setProblem(null);
    if (loaded.current === key) {  // the same preview: play it again from the start, no new request
      player.currentTime = 0;
      try {
        await graph.current?.context.resume();
        await player.play();
        setState("playing");
      } catch (error) {
        setState("error");
        setProblem((error as Error).message);
      }
      return;
    }
    const aborter = new AbortController();
    pending.current = aborter;
    setState("loading");
    setPosition(0);
    setPeaks([]);
    try {
      const blob = await load(aborter.signal);
      if (aborter.signal.aborted) return;
      release();
      url.current = URL.createObjectURL(blob);
      loaded.current = key;
      setLoadedKey(key);
      player.src = url.current;
      void waveform(blob).then((bars) => { if (!aborter.signal.aborted) setPeaks(bars); }).catch(() => setPeaks([]));  // no bars, still playable
      await graph.current?.context.resume();
      await player.play();
      if (!aborter.signal.aborted) setState("playing");
    } catch (error) {
      if (aborter.signal.aborted) return;
      setState("error");
      setProblem((error as Error).message);
    }
  }, []);

  const toggle = useCallback(() => {
    const player = element.current;
    if (!player || !loaded.current) return;
    if (player.paused) {
      void graph.current?.context.resume().then(() => player.play()).then(() => setState("playing"))
        .catch((error: Error) => { setState("error"); setProblem(error.message); });
    } else { player.pause(); setState("paused"); }
  }, []);
  const replay = useCallback(() => {
    const player = element.current;
    if (!player || !loaded.current) return;
    player.currentTime = 0;
    void graph.current?.context.resume().then(() => player.play()).then(() => setState("playing"))
      .catch((error: Error) => { setState("error"); setProblem(error.message); });
  }, []);
  const seek = useCallback((fraction: number) => {
    const player = element.current;
    if (player && duration) { player.currentTime = Math.max(0, Math.min(duration, fraction * duration)); setPosition(player.currentTime); }
  }, [duration]);

  const analyser = useCallback(() => graph.current?.analyser ?? null, []);  // stable: the orb's loop keeps running
  return { state, peaks, position, duration, problem, loadedKey, analyser, replay, play, toggle, seek, stop };
}

/** The preview's waveform: PEAKS bars of its loudest sample, 0–1. */
async function waveform(blob: Blob): Promise<number[]> {
  if (!("OfflineAudioContext" in window)) return [];
  const decoder = new OfflineAudioContext(1, 1, 44100);
  const buffer = await decoder.decodeAudioData(await blob.arrayBuffer());
  const samples = buffer.getChannelData(0);
  const step = Math.max(1, Math.floor(samples.length / PEAKS));
  const bars = Array.from({ length: PEAKS }, (_, bar) => {
    let peak = 0;
    for (let index = bar * step; index < Math.min(samples.length, (bar + 1) * step); index += 8) peak = Math.max(peak, Math.abs(samples[index]));
    return peak;
  });
  const loudest = Math.max(...bars, 0.01);
  return bars.map((bar) => bar / loudest);
}
