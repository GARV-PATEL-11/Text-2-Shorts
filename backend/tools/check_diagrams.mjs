// check_diagrams.mjs — parse every docs/diagrams/*.mmd with the real Mermaid parser.
// Setup: npm i mermaid@11 jsdom@24 ; run: node backend/tools/check_diagrams.mjs diagrams   (all 14 pass, 2026-11-19)
import { JSDOM } from "jsdom";
import fs from "fs";
const dom = new JSDOM("<!doctype html><html><body></body></html>", { pretendToBeVisual: true });
globalThis.window = dom.window; globalThis.document = dom.window.document;
Object.defineProperty(globalThis, "navigator", { value: dom.window.navigator, configurable: true });
globalThis.Element = dom.window.Element; globalThis.HTMLElement = dom.window.HTMLElement;
const { default: mermaid } = await import("mermaid");
mermaid.initialize({ startOnLoad: false });
const dir = process.argv[2]; let bad = 0;
for (const f of fs.readdirSync(dir).filter(f => f.endsWith(".mmd")).sort()) {
  try { await mermaid.parse(fs.readFileSync(`${dir}/${f}`, "utf8")); console.log("ok  ", f); }
  catch (e) { bad++; console.log("FAIL", f, String(e.message || e).split("\n").slice(0, 4).join(" | ")); }
}
process.exit(bad ? 1 : 0);
