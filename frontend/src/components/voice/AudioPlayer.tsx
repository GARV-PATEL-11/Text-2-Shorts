// The preview player: play/pause, the real waveform (decoded from the audio) with its progress, time, replay and the
// speed it was made at. It says what is true: nothing yet, being generated, could not be made (with Try Again), or out of
// date (a setting changed since). Its height never changes between states. Reusable for any voice preview.
import { Button } from "../ui/Button";
import type { PreviewPlayer } from "./usePreviewPlayer";
import { Waveform } from "./Waveform";

const clock = (seconds: number) => `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;

export function AudioPlayer({ player, onPlay, stale, speed, name }: {
  player: PreviewPlayer; onPlay: () => void; stale: boolean; speed: string; name: string;
}) {
  const { state } = player;
  const ready = Boolean(player.loadedKey) && !stale && state !== "error";  // the audio shown is the audio of these settings
  const playing = ready && state === "playing";
  const main = () => (ready ? player.toggle() : onPlay());
  const message = state === "error" ? player.problem ?? "The Preview Could Not Be Made."
    : state === "loading" ? "Generating the Preview…"
    : stale ? "Settings Changed: Play to Hear Them"
    : !ready ? `Play to Hear ${name}` : null;
  return (
    <div className={`aplayer aplayer--${ready ? state : state === "error" || state === "loading" ? state : "empty"}`} aria-busy={state === "loading"}>
      <Button variant="primary" label={playing ? `Pause ${name}` : state === "loading" ? "Generating the Preview" : state === "error" ? `Try ${name} Again` : `Play ${name}`}
        onPress={() => { if (state !== "loading") main(); }}
        icon={<span aria-hidden="true" className={`aplayer__glyph${state === "loading" ? " is-waiting" : ""}`}>{playing ? "❚❚" : state === "loading" ? "…" : state === "error" ? "↻" : "▶"}</span>} />
      <div className="aplayer__track">
        {ready ? <Waveform peaks={player.peaks} position={player.position} duration={player.duration} onSeek={player.seek} />
          : <p className={`aplayer__message${state === "error" ? " is-error" : ""}`} role={state === "error" ? "alert" : "status"}>{message}</p>}
      </div>
      {ready ? <>
        <span className="aplayer__time"><span className="sr-only">Position </span>{clock(player.position)} / {clock(player.duration)}</span>
        <Button variant="tertiary" size="sm" onPress={player.replay}>Replay</Button>
        <span className="aplayer__speed" title="The Speed This Preview Is Spoken At">{speed}</span>
      </> : null}
    </div>
  );
}
