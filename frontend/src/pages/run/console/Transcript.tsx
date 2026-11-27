// The console's transcript, laid out like Claude Code's: "›" for your prompts, ⏺ for what Claude says and does, ⎿
// under a call for its result, collapsed to a few lines until expanded (one block, or all with Ctrl+O).
import { type ReactNode, memo, useState } from "react";
import { Markdown } from "../../../components/ui/Markdown";
import type { Block, ToolBlock } from "./fold";
import { summaryLine } from "./fold";
import { type DiffLine, diffSummary, editDiff } from "./diff";

export interface LocalBlock { kind: "local"; key: string; title: string; body: ReactNode }  // a command's output, kept on this page only
const SHOWN_LINES = 3;
const clock = (at: string) => at.slice(11, 19);  // 2026-11-27T10:15:04 → 10:15:04 (Ctrl+O shows when)
const SHOWN_DIFF = 12;
const GLYPH: Record<ToolBlock["status"], string> = { running: "✻", awaiting: "⏸", done: "⏺", failed: "✗", denied: "⊘", stopped: "○" };
const STATUS: Record<ToolBlock["status"], string> = {
  running: "Running", awaiting: "Waiting for Your Answer", done: "Done", failed: "Failed", denied: "Denied", stopped: "Stopped",
};

function Lines({ text, expanded, onExpand }: { text: string; expanded: boolean; onExpand: () => void }) {
  const lines = text.replace(/\s+$/, "").split("\n");
  const shown = expanded ? lines : lines.slice(0, SHOWN_LINES);
  return (
    <>
      <pre className="con__out">{shown.join("\n") || " "}</pre>
      {lines.length > shown.length ? (
        <button type="button" className="con__more" onClick={onExpand}>… +{lines.length - shown.length} lines (Ctrl+O to Expand)</button>
      ) : null}
    </>
  );
}

export function Diff({ lines, expanded, onExpand }: { lines: DiffLine[]; expanded: boolean; onExpand?: () => void }) {
  const shown = expanded ? lines : lines.slice(0, SHOWN_DIFF);
  return (
    <>
      <pre className="con__diff" aria-label="Changes">{shown.map((line, index) => (
        <span key={index} className={`con__diff-${line.op === "+" ? "add" : line.op === "-" ? "del" : "same"}`}>
          {line.op === " " ? "  " : `${line.op} `}{line.text}{"\n"}
        </span>
      ))}</pre>
      {lines.length > shown.length && onExpand ? (
        <button type="button" className="con__more" onClick={onExpand}>… +{lines.length - shown.length} lines (Ctrl+O to Expand)</button>
      ) : null}
    </>
  );
}

const Tool = memo(function Tool({ block, detail }: { block: ToolBlock; detail: boolean }) {
  const [open, setOpen] = useState(false);
  const expanded = detail || open;
  const diff = block.status !== "denied" ? editDiff(block.tool, block.input) : null;
  const seconds = block.durationMs != null && block.durationMs >= 1000 ? ` · ${(block.durationMs / 1000).toFixed(1)} s` : "";
  return (
    <li className={`con__tool con__tool--${block.status}`}>
      <span className="con__glyph" aria-hidden="true">{GLYPH[block.status]}</span>
      <div className="con__line">
        <span className="con__title">{block.title}</span>
        <span className="sr-only">: {STATUS[block.status]}</span>
        {block.status !== "done" && block.status !== "running" ? <span className="con__tag" aria-hidden="true">· {STATUS[block.status]}</span> : null}
        {detail ? <span className="con__time">{clock(block.at)}{seconds}</span> : null}
      </div>
      {block.permission?.answer ? <div className="con__sub"><span aria-hidden="true">⎿</span><span>{block.permission.answer}</span></div> : null}
      {diff && block.status === "done" ? (
        <div className="con__sub">
          <span aria-hidden="true">⎿</span>
          <div>{diffSummary(diff)}<Diff lines={diff} expanded={expanded} onExpand={() => setOpen(true)} /></div>
        </div>
      ) : block.status === "denied" ? null : block.output !== undefined && (block.tool !== "Read" || expanded || block.isError) ? (
        <div className="con__sub">
          <span aria-hidden="true">⎿</span>
          <div><Lines text={block.output} expanded={expanded} onExpand={() => setOpen(true)} /></div>
        </div>
      ) : block.output !== undefined ? (
        <div className="con__sub"><span aria-hidden="true">⎿</span>
          <div>Read {block.output.split("\n").length} lines <button type="button" className="con__more con__more--inline" onClick={() => setOpen(true)}>(Ctrl+O to Expand)</button></div></div>
      ) : null}
    </li>
  );
});

function Entry({ block, detail, onOption }: { block: Block | LocalBlock; detail: boolean; onOption: (text: string) => void }) {
  switch (block.kind) {
    case "prompt":
      return <li className="con__prompt"><span className="con__glyph" aria-hidden="true">›</span><span className="sr-only">You: </span><span className="con__text">{block.text}</span></li>;
    case "text":
      return <li className="con__said"><span className="con__glyph" aria-hidden="true">⏺</span><span className="sr-only">Claude: </span><div className="con__md"><Markdown text={block.text} compact /></div></li>;
    case "live":
      return <li className="con__said con__said--live" aria-hidden="true"><span className="con__glyph">⏺</span><div className="con__md"><Markdown text={block.text} compact /></div></li>;
    case "thinking":
      return <li className="con__thinking" aria-hidden="true"><span className="con__glyph">✻</span>{block.text}</li>;
    case "tool":
      return <Tool block={block} detail={detail} />;
    case "question":
      return (
        <li className="con__said">
          <span className="con__glyph" aria-hidden="true">?</span><span className="sr-only">Claude asks: </span>
          <div className="con__md"><Markdown text={block.text} compact />
            {block.options.length ? <div className="con__options">{block.options.map((option, index) => (
              <button key={option} type="button" className="con__option" onClick={() => onOption(option)}>{index + 1}. {option}</button>
            ))}</div> : null}
          </div>
        </li>
      );
    case "permission":
      return <li className="con__note"><span className="con__glyph" aria-hidden="true">⏸</span>{block.text}{block.answer ? ` · ${block.answer}` : ""}</li>;
    case "error":
      return <li className="con__error"><span className="con__glyph" aria-hidden="true">✗</span><span className="sr-only">Error: </span>{block.text}{block.stats ? <span className="con__time"> · {summaryLine(block.stats)}</span> : null}</li>;
    case "summary":
      return <li className="con__summary"><span className="con__glyph" aria-hidden="true">✓</span>{block.text.replace(/\.$/, "")} · {summaryLine(block.stats)}</li>;
    case "note":
      return <li className="con__divider"><span>{block.text}</span></li>;
    case "local":  // a command run here: its line as typed, then its output
      return <li className="con__local"><div className="con__echo">{block.title}</div><div className="con__local-body">{block.body}</div></li>;
  }
}

/** Blocks and command output merged by position (a block's key is the index of its first entry). */
export function Transcript({ blocks, local, detail, streamed, onOption, empty }: {
  blocks: Block[]; local: (LocalBlock & { after: number })[]; detail: boolean; streamed: string; onOption: (text: string) => void; empty: ReactNode;
}) {
  const all: { order: number; block: Block | LocalBlock }[] = [
    ...blocks.map((block) => ({ order: Number(block.key), block })),
    ...local.map((block) => ({ order: block.after - 0.5, block })),
  ].sort((a, b) => a.order - b.order);
  return (
    <ol className="con__log" aria-label="Conversation with Claude" aria-live="polite" aria-relevant="additions">
      {all.length || streamed ? all.map(({ block }) => <Entry key={block.key} block={block} detail={detail} onOption={onOption} />)
        : <li className="con__empty">{empty}</li>}
      {streamed ? <Entry block={{ kind: "live", key: "streaming", text: streamed }} detail={detail} onOption={onOption} /> : null}
    </ol>
  );
}
