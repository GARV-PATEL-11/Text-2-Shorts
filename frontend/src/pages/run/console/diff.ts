// Line diff for the edits Claude makes (Edit, MultiEdit, Write input), shown like a unified diff. Pure; unit-tested.

export interface DiffLine { op: " " | "-" | "+"; text: string }
const LIMIT = 400;  // lines per side: beyond it, the old text is shown removed and the new one added (no LCS table)

export function lineDiff(before: string, after: string): DiffLine[] {
  const a = before === "" ? [] : before.split("\n");
  const b = after === "" ? [] : after.split("\n");
  if (a.length > LIMIT || b.length > LIMIT)
    return [...a.map((text) => ({ op: "-" as const, text })), ...b.map((text) => ({ op: "+" as const, text }))];
  const lcs = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0));
  for (let i = a.length - 1; i >= 0; i--)
    for (let j = b.length - 1; j >= 0; j--)
      lcs[i][j] = a[i] === b[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
  const lines: DiffLine[] = [];
  let i = 0, j = 0;
  while (i < a.length || j < b.length) {
    if (i < a.length && j < b.length && a[i] === b[j]) { lines.push({ op: " ", text: a[i] }); i++; j++; }
    else if (i < a.length && (j === b.length || lcs[i + 1][j] >= lcs[i][j + 1])) lines.push({ op: "-", text: a[i++] });  // removals first
    else lines.push({ op: "+", text: b[j++] });
  }
  return lines;
}

/** The diff a tool call makes, from its real input; null for tools that edit nothing. */
export function editDiff(tool: string, input: Record<string, unknown>): DiffLine[] | null {
  const text = (value: unknown) => (typeof value === "string" ? value : "");
  if (tool === "Edit") return lineDiff(text(input.old_string), text(input.new_string));
  if (tool === "MultiEdit" && Array.isArray(input.edits))
    return (input.edits as Record<string, unknown>[]).flatMap((edit) => lineDiff(text(edit.old_string), text(edit.new_string)));
  if (tool === "Write") return lineDiff("", text(input.content));
  return null;
}

/** "Added 3 lines, removed 1 line". */
export function diffSummary(lines: DiffLine[]): string {
  const count = (op: string) => lines.filter((line) => line.op === op).length;
  const say = (n: number, verb: string) => `${verb} ${n} Line${n === 1 ? "" : "s"}`;
  const added = count("+"), removed = count("-");
  return [added ? say(added, "Added") : "", removed ? say(removed, "Removed") : ""].filter(Boolean).join(", ") || "No Change";
}
