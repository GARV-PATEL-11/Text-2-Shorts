// The preview's real waveform (decoded from its MP3), played part bright, rest dim; click or arrow keys to seek.
import type { KeyboardEvent, MouseEvent } from "react";

const time = (seconds: number) => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;

export function Waveform({ peaks, position, duration, onSeek }: {
  peaks: number[]; position: number; duration: number; onSeek: (fraction: number) => void;
}) {
  const played = duration ? position / duration : 0;
  const seek = (event: MouseEvent<HTMLDivElement>) => {
    const box = event.currentTarget.getBoundingClientRect();
    onSeek((event.clientX - box.left) / box.width);
  };
  const keys = (event: KeyboardEvent<HTMLDivElement>) => {
    const step = { ArrowLeft: -0.1, ArrowRight: 0.1 }[event.key];
    if (step !== undefined && duration) { event.preventDefault(); onSeek(Math.max(0, Math.min(1, played + step))); }
  };
  return (
    <div className="wave">
      <div className="wave__bars" role="slider" tabIndex={duration ? 0 : -1} aria-label="Preview Position"
        aria-valuemin={0} aria-valuemax={Math.round(duration)} aria-valuenow={Math.round(position)} aria-valuetext={`${time(position)} of ${time(duration)}`}
        onClick={seek} onKeyDown={keys}>
        {(peaks.length ? peaks : new Array<number>(96).fill(0.08)).map((peak, index, all) => (
          <span key={index} className={index / all.length < played ? "is-played" : undefined} style={{ height: `${Math.max(6, peak * 100)}%` }} />
        ))}
      </div>
    </div>
  );
}
