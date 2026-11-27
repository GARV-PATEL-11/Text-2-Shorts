// The Voice Studio (docs/voice-studio/): find a voice (search, gender, accent, a list with a preview button per voice),
// hear it (the orb is its play button and moves with the real audio; ‹ › move to the next voice and play it), set its
// speed and engine (speaking style is hidden for now), and make it the narrator. Picking from the list or changing a setting never plays by itself: it stops what
// was playing and the player says the preview needs playing again. Everything shown comes from Polly's own voice data.
import { memo, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "../../../../components/ui/Button";
import { Check } from "../../../../components/ui/icons";
import { AudioPlayer } from "../../../../components/voice/AudioPlayer";
import { usePreviewPlayer } from "../../../../components/voice/usePreviewPlayer";
import { VoiceOrb } from "../../../../components/voice/VoiceOrb";
import { useApi } from "../../../../hooks/useApi";
import type { LookCatalogue, LookChoice, PollyVoice, VoiceList } from "../../../../types/api";
import { accentLabel, ENGINE_LABEL, ENGINE_ORDER, engineFor, filterVoices, previewLine, rateLabel, spokenBy, withVoice } from "./voice";

interface Browse { voice: string; engine: string; speed: string }  // speaking style is hidden for now
const keyOf = (browse: Browse) => `${browse.voice}|${browse.engine}|${browse.speed}`;
const rateOf = (detail = "") => Number(detail.match(/(\d+)%/)?.[1] ?? 100) / 100;

async function previewBlob(body: Browse, signal: AbortSignal): Promise<Blob> {
  const response = await fetch("/api/voices/preview", {
    method: "POST", credentials: "same-origin", signal,
    headers: { "Content-Type": "application/json", Accept: "audio/mpeg" }, body: JSON.stringify(body),
  });
  if (!response.ok) {
    const answer = await response.json().catch(() => ({}));
    throw new Error(answer.error ?? `The Preview Could Not Be Made (Error ${response.status}).`);
  }
  return response.blob();
}

/** Amazon Polly; Google Cloud TTS behind frosted glass until it is ready (reachable, explained, not choosable). */
export function ProviderTabs() {
  return (
    <div className="studio__providers" role="group" aria-label="Voice Provider">
      <button type="button" className="studio__provider is-on" aria-pressed="true">Amazon Polly</button>
      <button type="button" className="studio__provider studio__provider--soon" aria-disabled="true"
        aria-label="Google Cloud TTS, Coming Soon" title="Google Cloud TTS Is Still Being Built" onClick={(event) => event.preventDefault()}>
        Google Cloud TTS <span className="studio__soon" aria-hidden="true">Coming Soon</span>
      </button>
    </div>
  );
}

type RowState = "idle" | "loading" | "playing" | "error";
const VoiceRow = memo(function VoiceRow({ voice, current, narrator, state, problem, onPick, onPlay }: {
  voice: PollyVoice; current: boolean; narrator: boolean; state: RowState; problem?: string | null; onPick: (id: string) => void; onPlay: (id: string) => void;
}) {
  const glyph = { idle: "▶", loading: "…", playing: "❚❚", error: "!" }[state];
  const label = { idle: `Preview ${voice.name}`, loading: `Generating ${voice.name}`, playing: `Pause ${voice.name}`, error: `Try ${voice.name} Again` }[state];
  return (
    <li className={`studio__row${current ? " is-current" : ""}`}>
      <button type="button" className="studio__pick" aria-current={current || undefined} onClick={() => onPick(voice.id)}>
        <span className="studio__dot" aria-hidden="true" />
        <span className="studio__row-name">{voice.name}</span>
        <span className="studio__row-meta">{voice.gender} · {accentLabel(voice.language)}</span>
        {narrator ? <span className="studio__tick" title="Your Narrator"><Check aria-hidden="true" /><span className="sr-only">Your Narrator</span></span> : null}
      </button>
      <Button variant="tertiary" size="sm" label={label} onPress={() => onPlay(voice.id)}
        icon={<span aria-hidden="true" className={`aplayer__glyph${state === "loading" ? " is-waiting" : ""}`}>{glyph}</span>} />
      {state === "error" && problem ? <p className="studio__row-problem" role="alert">{problem}</p> : null}
    </li>
  );
});

export function VoiceStudio({ catalogue, choice, setChoice, provider = "polly" }: {
  catalogue: LookCatalogue; choice: LookChoice; setChoice: (next: (current: LookChoice) => LookChoice) => void;
  /** The run's narration provider (its brief): a run set up for Google is told it speaks with Polly for now. */
  provider?: string;
}) {
  const list = useApi<VoiceList>("/api/voices");
  const player = usePreviewPlayer();
  const speeds = catalogue.elements.find((element) => element.id === "speaking_speed")?.options ?? [];
  const [query, setQuery] = useState("");
  const [gender, setGender] = useState("");
  const [accent, setAccent] = useState("");
  const [browse, setBrowse] = useState<Browse | null>(null);
  const [announce, setAnnounce] = useState("");
  const heading = useRef<HTMLHeadingElement>(null);
  const data = list.data;
  const spoken = data ? spokenBy(choice, data.curated) : null;
  const narrator = data?.voices.find((voice) => voice.id === spoken?.voice);
  const missing = data && spoken && !narrator ? spoken.voice : null;

  useEffect(() => {  // browsing starts at the look's narrator
    if (!data || browse) return;
    const start = narrator ?? data.voices[0];
    if (start) setBrowse({ voice: start.id, engine: engineFor(start, spoken?.engine ?? "neural"),
      speed: choice.elements.speaking_speed ?? speeds[0]?.id ?? "" });
  }, [data, browse, narrator, spoken, choice.elements.speaking_speed, speeds]);

  const genders = useMemo(() => [...new Set((data?.voices ?? []).map((voice) => voice.gender).filter(Boolean))].sort(), [data]);
  const accents = useMemo(() => [...new Set((data?.voices ?? []).map((voice) => voice.language))].sort(), [data]);
  const found = useMemo(() => filterVoices(data?.voices ?? [], query, gender, accent), [data, query, gender, accent]);

  if (list.error) return <div className="studio__note" role="alert">{list.error.message} <Button variant="secondary" size="sm" onPress={list.reload}>Try Again</Button></div>;
  if (!speeds.length) return <p className="studio__note" role="alert">The Voice Settings Could Not Be Read. Reload the Page.</p>;
  if (!data || !browse) return <p className="note" role="status">Loading the Voices…</p>;
  const voice = data.voices.find((candidate) => candidate.id === browse.voice) ?? data.voices[0];
  const engine = engineFor(voice, browse.engine);
  const speed = speeds.find((option) => option.id === browse.speed) ?? speeds[0];
  const rate = rateOf(speed.detail);
  const speedIndex = Math.max(0, speeds.findIndex((option) => option.id === speed.id));
  const settled: Browse = { voice: voice.id, engine, speed: speed.id };
  const stale = player.loadedKey !== null && player.loadedKey !== keyOf(settled);
  const isNarrator = narrator?.id === voice.id;
  const sameAsNarrator = isNarrator && spoken?.engine === engine && choice.elements.speaking_speed === speed.id;
  const engineChanged = narrator && spoken && engineFor(narrator, spoken.engine) !== spoken.engine ? spoken.engine : null;
  const engines = ENGINE_ORDER.filter((name) => voice.engines.includes(name));

  const settle = (next: Partial<Browse>): Browse => {
    const target = data.voices.find((candidate) => candidate.id === (next.voice ?? browse.voice)) ?? voice;
    return { ...settled, ...next, voice: target.id, engine: engineFor(target, next.engine ?? engine) };
  };
  const set = (next: Partial<Browse>) => {  // browse to new settings: what was playing stops; nothing new plays
    const chosen = settle(next);
    if (keyOf(chosen) !== keyOf(settled)) player.stop();
    if (chosen.voice !== voice.id) setAnnounce(`${data.voices.find((candidate) => candidate.id === chosen.voice)?.name ?? ""} Selected for Preview`);
    setBrowse(chosen);
  };
  const hear = (next: Partial<Browse> = {}) => {  // browse and play (always a press, so the browser lets it play)
    const chosen = settle(next);
    setBrowse(chosen);
    if (chosen.voice !== voice.id) setAnnounce(`Playing ${data.voices.find((candidate) => candidate.id === chosen.voice)?.name ?? ""}`);
    void player.play((signal) => previewBlob(chosen, signal), keyOf(chosen));
  };
  const toggleOrPlay = () => {
    if (!stale && player.loadedKey && (player.state === "playing" || player.state === "paused")) player.toggle();
    else if (player.state !== "loading") hear();
  };
  const pool = found.length ? found : data.voices;
  const index = Math.max(0, pool.findIndex((candidate) => candidate.id === voice.id));
  const move = (direction: -1 | 1) => hear({ voice: pool[(index + direction + pool.length) % pool.length].id });
  const select = () => {
    setChoice((look) => {
      const voiced = withVoice(look, voice.id, engine, data.curated);
      return { ...voiced, elements: { ...voiced.elements, speaking_speed: speed.id } };  // the tone stays the look's own
    });
    setAnnounce(`${voice.name} Is Your Narrator`);
    requestAnimationFrame(() => heading.current?.focus());  // the button leaves; focus stays with the voice
  };
  const rowState = (id: string): RowState => (id !== voice.id || stale ? "idle"
    : player.state === "loading" ? "loading" : player.state === "playing" ? "playing" : player.state === "error" ? "error" : "idle");
  const line = previewLine(data.template, { agent: voice.name, tone: "", speed: speed.label, provider: data.provider, engine });
  const orbState = stale && (player.state === "playing" || player.state === "paused") ? "idle" : player.state;

  return (
    <div className="studio">
      <p className="sr-only" aria-live="polite">{announce}</p>
      {provider === "google" ? <p className="studio__note">This Run Was Set Up for Google Cloud TTS, Which Is Coming Soon: It Speaks With Amazon Polly for Now.</p> : null}
      {missing ? <p className="studio__note" role="status">{missing}, This Run's Saved Voice, Is Not an English Amazon Polly Voice Here. Select Another to Replace It.</p> : null}
      {engineChanged ? <p className="studio__note" role="status">{narrator?.name} Has No {ENGINE_LABEL[engineChanged] ?? engineChanged} Engine Here. Update the Narrator to Use {ENGINE_LABEL[engineFor(narrator!, engineChanged)]}.</p> : null}

      <div className="studio__layout">
        <section className="studio__main" aria-label="Voice">
          <div className="studio__hero">
            <div className="studio__orb" onKeyDown={(event) => {
              const step = { ArrowLeft: -1, ArrowRight: 1 }[event.key] as -1 | 1 | undefined;
              if (step) { event.preventDefault(); move(step); }
            }}>
              <Button variant="secondary" label="Previous Voice" icon={<span aria-hidden="true" className="studio__chevron">‹</span>} onPress={() => move(-1)} />
              <VoiceOrb state={orbState} analyser={player.analyser} onPress={toggleOrPlay} size={248}
                label={`${orbState === "playing" ? "Pause" : "Play"} ${voice.name}`} />
              <Button variant="secondary" label="Next Voice" icon={<span aria-hidden="true" className="studio__chevron">›</span>} onPress={() => move(1)} />
            </div>
            <div className="studio__identity">
              <h3 className="studio__name" ref={heading} tabIndex={-1}>{voice.name}
                {isNarrator ? <span className="studio__badge"><Check aria-hidden="true" />Your Narrator</span> : null}
              </h3>
              <p className="studio__meta">{[voice.gender, accentLabel(voice.language), `${ENGINE_LABEL[engine]} Engine`].filter(Boolean).join(" · ")}</p>
              {sameAsNarrator ? null : <Button onPress={select} icon={<Check />}>{isNarrator ? "Update Narrator" : "Select Voice"}</Button>}
            </div>
          </div>
          <AudioPlayer player={player} onPlay={() => hear()} stale={stale} speed={rateLabel(rate)} name={voice.name} />
          <blockquote className="studio__line">{line}</blockquote>
          <div className="studio__delivery">
            <label className="studio__field">
              <span>Speed <strong>{speed.label} · {rateLabel(rate)}</strong></span>
              <input type="range" min={0} max={speeds.length - 1} step={1} value={speedIndex} aria-valuetext={`${speed.label}, ${rateLabel(rate)}`}
                onChange={(event) => set({ speed: speeds[Number(event.target.value)].id })} />
              <span className="studio__scale"><span>{rateLabel(rateOf(speeds[0].detail))}</span><span>{rateLabel(rateOf(speeds.at(-1)?.detail))}</span></span>
            </label>
            {engines.length > 1 ? (
              <label className="studio__field">
                <span>Voice Engine</span>
                <select className="studio__select" value={engine} onChange={(event) => set({ engine: event.target.value })}>
                  {engines.map((name) => <option key={name} value={name}>{ENGINE_LABEL[name]}</option>)}
                </select>
              </label>
            ) : null}
          </div>
        </section>

        <section className="studio__discover" aria-label="Find a Voice">
          <input className="studio__search" type="search" placeholder="Search Voices…" aria-label="Search Voices" value={query}
            onChange={(event) => setQuery(event.target.value)} />
          <div className="studio__filters">
            <div className="studio__segment" role="group" aria-label="Gender">
              {["", ...genders].map((option) => (
                <button key={option || "all"} type="button" aria-pressed={gender === option} className={gender === option ? "is-on" : undefined}
                  onClick={() => setGender(option)}>{option || "All"}</button>
              ))}
            </div>
            <select className="studio__select" aria-label="Accent" value={accent} onChange={(event) => setAccent(event.target.value)}>
              <option value="">All Accents</option>
              {accents.map((name) => <option key={name} value={name}>{accentLabel(name)}</option>)}
            </select>
          </div>
          <p className="studio__count" role="status">{found.length} {found.length === 1 ? "Voice" : "Voices"}</p>
          <ul className="studio__list" aria-label="Voices">
            {found.map((candidate) => (
              <VoiceRow key={candidate.id} voice={candidate} current={candidate.id === voice.id} narrator={candidate.id === narrator?.id}
                state={rowState(candidate.id)} problem={player.problem} onPick={(id) => set({ voice: id })}
                onPlay={(id) => (rowState(id) === "playing" ? player.toggle() : hear({ voice: id }))} />
            ))}
            {found.length ? null : <li className="studio__empty">No Voice Matches. <button type="button" className="studio__link" onClick={() => { setQuery(""); setGender(""); setAccent(""); }}>Clear the Search</button></li>}
          </ul>
        </section>
      </div>
    </div>
  );
}
