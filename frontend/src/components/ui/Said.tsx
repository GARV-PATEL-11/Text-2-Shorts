// A line from the voice catalogue (config/voice.ts): the words as their source wrote them, then a quiet credit. A moment
// with several lines shows one, chosen once per visit (like a game's splash text), so the page never flickers.
import { useState } from "react";
import { type Line, type Moment, VOICE } from "../../config/voice";

export function useLine(moment: Moment): Line {
  const lines = VOICE[moment];
  const [index] = useState(() => Math.floor(Math.random() * lines.length));
  return lines[index] ?? lines[0];
}

/** The line, quoted when it is a quotation, with its credit. `block` sets it apart as an epigraph; `lead` sets it as
 * a page's lead line (Home). */
export function Said({ moment, block, lead }: { moment: Moment; block?: boolean; lead?: boolean }) {
  const line = useLine(moment);
  if (!line.source) return <>{line.text}</>;
  const credit = <cite className="said__source">{line.source}</cite>;
  return block ? (
    <figure className="epigraph">
      <blockquote cite={line.url}>{line.text}</blockquote>
      <figcaption>{credit}</figcaption>
    </figure>
  ) : (
    <span className={lead ? "said said--lead" : "said"}><q cite={line.url}>{line.text}</q> {credit}</span>
  );
}
