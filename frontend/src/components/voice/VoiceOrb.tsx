// The living voice orb: a monochrome blob drawn on a canvas. Idle: it breathes. Loading: arcs turn around it while the
// preview is generated. Playing: its edge moves with the voice's real frequencies (an AnalyserNode), never otherwise.
// Paused: it settles and floats. Error: it dims inside a broken ring. Hover: it glows brighter. Reduced motion: a still
// sphere. Off screen it draws nothing. It is the voice's play and pause button.
import { useEffect, useRef } from "react";
import type { PlayerState } from "./usePreviewPlayer";

const POINTS = 72;
const BANDS = 6;  // ripples around the edge, each driven by one band of the voice's spectrum

export function VoiceOrb({ state, analyser, onPress, label, size = 220 }: {
  state: PlayerState; analyser: () => AnalyserNode | null; onPress: () => void; label: string; size?: number;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef(state);
  stateRef.current = state;

  useEffect(() => {
    const element = canvas.current;
    const context = element?.getContext("2d");
    if (!element || !context) return;
    const ratio = window.devicePixelRatio || 1;
    element.width = size * ratio;
    element.height = size * ratio;
    context.scale(ratio, ratio);
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const bins = new Uint8Array(256);
    const energy = new Array<number>(BANDS).fill(0);  // smoothed, 0–1
    const phases = Array.from({ length: BANDS }, (_, band) => band * 1.7);
    let frame = 0;
    const centre = size / 2;
    const radius = size * 0.3;  // room for the glow, the rings and the voice's swell inside the canvas

    let visible = true;
    const watcher = new IntersectionObserver(([seen]) => {
      visible = seen.isIntersecting;
      if (visible && !still) { cancelAnimationFrame(frame); frame = requestAnimationFrame(draw); }
    });
    watcher.observe(element);

    let last = 0;
    const draw = (time: number) => {
      const now = time / 1000;
      const current = stateRef.current;
      if (current === "idle" || current === "paused" || current === "error") {  // slow states: 30 frames a second is plenty
        if (time - last < 33) { frame = requestAnimationFrame(draw); return; }
      }
      last = time;
      context.clearRect(0, 0, size, size);
      const node = current === "playing" ? analyser() : null;
      if (node) {
        node.getByteFrequencyData(bins);
        const span = Math.floor(node.frequencyBinCount / 2 / BANDS);  // speech lives in the lower half
        for (let band = 0; band < BANDS; band += 1) {
          let sum = 0;
          for (let bin = band * span; bin < (band + 1) * span; bin += 1) sum += bins[bin];
          energy[band] += ((sum / span / 255) - energy[band]) * 0.35;
        }
      } else {
        for (let band = 0; band < BANDS; band += 1) energy[band] *= 0.9;
      }
      const loudness = energy.reduce((total, value) => total + value, 0) / BANDS;
      const breathing = still ? 0 : current === "idle" || current === "error" ? Math.sin(now * 1.3) * (current === "error" ? 0.008 : 0.025) : 0;
      const floating = still ? 0 : current === "paused" ? Math.sin(now * 0.9) * 4 : 0;
      const y = centre + floating;

      if (current === "loading") {  // arcs turning around the orb: the preview is being generated
        for (let ring = 0; ring < 2; ring += 1) {
          const start = (still ? 0 : now * (ring ? -1.1 : 1.6)) + ring * Math.PI;
          context.beginPath();
          context.arc(centre, y, radius * (1.25 + ring * 0.18), start, start + Math.PI * 0.7);
          context.strokeStyle = `rgba(255, 255, 255, ${ring ? 0.25 : 0.5})`;
          context.lineWidth = 1.5;
          context.lineCap = "round";
          context.stroke();
        }
      }
      if (current === "error") {  // a broken ring: this voice could not be heard
        context.beginPath();
        context.arc(centre, y, radius * 1.28, Math.PI * 0.15, Math.PI * 1.85);
        context.strokeStyle = "rgba(255, 255, 255, 0.35)";
        context.lineWidth = 1.5;
        context.setLineDash([4, 6]);
        context.stroke();
        context.setLineDash([]);
      }

      context.beginPath();
      for (let point = 0; point <= POINTS; point += 1) {
        const angle = (point / POINTS) * Math.PI * 2;
        let swell = 1 + breathing;
        for (let band = 0; band < BANDS; band += 1) {
          if (!still) phases[band] += 0.0006 * (band + 1);
          swell += energy[band] * 0.07 * Math.sin(angle * (band + 2) + phases[band] + now * (0.8 + band * 0.3));
        }
        const r = radius * Math.min(1.3, Math.max(0.82, swell + loudness * 0.12));  // organic, never torn or clipped
        const x = centre + Math.cos(angle) * r;
        const pointY = y + Math.sin(angle) * r;
        if (point === 0) context.moveTo(x, pointY); else context.lineTo(x, pointY);
      }
      context.closePath();
      const light = context.createRadialGradient(centre - radius * 0.35, y - radius * 0.4, radius * 0.05, centre, y, radius * 1.25);
      light.addColorStop(0, "#ffffff");
      light.addColorStop(0.35, "#d6d7dc");
      light.addColorStop(0.75, "#6a6b74");
      light.addColorStop(1, "#17181c");
      context.globalAlpha = current === "error" ? 0.45 : 1;
      context.shadowColor = `rgba(255, 255, 255, ${0.18 + loudness * 0.5})`;
      context.shadowBlur = 24 + loudness * 50;
      context.fillStyle = light;
      context.fill();
      context.shadowBlur = 0;
      context.globalAlpha = 1;
      if (!still && visible) frame = requestAnimationFrame(draw);
    };
    frame = requestAnimationFrame(draw);
    const redraw = new MutationObserver(() => { if (still) requestAnimationFrame(draw); });  // a still orb shows state changes
    redraw.observe(element.parentElement ?? element, { attributes: true, attributeFilter: ["class"] });
    return () => { cancelAnimationFrame(frame); watcher.disconnect(); redraw.disconnect(); };
  }, [analyser, size]);

  return (
    <button type="button" className={`orb orb--${state}`} onClick={onPress} aria-label={label} style={{ width: size, height: size }}>
      <canvas ref={canvas} style={{ width: size, height: size }} aria-hidden="true" />
    </button>
  );
}
