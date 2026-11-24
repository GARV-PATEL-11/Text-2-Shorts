// Markdown, everywhere text is written or shown: what you type (the question, change requests, notes, the console)
// and what Claude writes (its replies and questions, topics.md, content.md). GitHub-flavoured (tables, task lists,
// strikethrough); raw HTML is never rendered, so nothing typed can run in the page. Links open in a new tab.
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { titleCase } from "./text";

export function Markdown({ text, compact }: { text: string; compact?: boolean }) {
  return (
    <div className={`md${compact ? " md--compact" : ""}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}
        components={{ a: ({ node: _, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" /> }}>
        {text}
      </ReactMarkdown>
    </div>
  );
}

/** Markdown as one plain line: its first line without the marks (for titles, breadcrumbs, tab titles). */
export function plainText(markdown: string): string {
  const first = markdown.trim().split("\n").find((line) => line.trim()) ?? "";
  return first
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/^\s*(#{1,6}|>|[-*+]|\d+\.)\s+/, "")
    .replace(/[*_~`]+/g, "")
    .trim();
}

/** A run's title: its question, as one plain line in Title Case. */
export const runTitle = (topic: string) => titleCase(plainText(topic));
