// Text helpers: the workflow's `code` spans as code (text only, never HTML), and Title Case for every label.
export function WithCode({ text }: { text: string }) {
  return <>{text.split("`").map((part, index) => (index % 2 ? <code key={index}>{part}</code> : part))}</>;
}

// Chicago style: articles, coordinating conjunctions and short prepositions stay lower case unless first or last.
const MINOR = new Set("a an the and but or nor for so yet as at by in of off on per to up via vs".split(" "));

/** "background color" · "obsidian" · "requires_user_approval" → "Background Color" · "Obsidian" · "Requires User
 * Approval". Words already holding a capital after the first letter (1440p, SSML, sNN ids) are kept as written; a
 * hyphen splits words only in an id (no spaces), so "3-body problem" keeps its hyphen. */
export function titleCase(text: string): string {
  const id = !/\s/.test(text.trim());
  const words = text.replace(id ? /[_-]+/g : /_+/g, " ").trim().split(/\s+/);
  return words
    .map((word, index) => {
      if (/[A-Z0-9]/.test(word.slice(1)) || /^[a-z]\d/.test(word)) return word;
      const lower = word.toLowerCase();
      if (index > 0 && index < words.length - 1 && MINOR.has(lower)) return lower;
      return lower.replace(/^(\W*)(\w)/, (_, lead: string, first: string) => lead + first.toUpperCase());
    })
    .join(" ");
}
