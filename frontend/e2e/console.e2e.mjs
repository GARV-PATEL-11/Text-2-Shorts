// End-to-end: the console in a real browser against a demo server whose `claude` is tests/fixtures/console/fake_claude.py
// (real permission endpoint, real event shapes, no live turn). Fails on the first broken expectation; saves a
// screenshot of every state in OUT. Usage:
//   BASE=http://127.0.0.1:8790/ RUN=<run id> PLAYWRIGHT=<path to playwright> node e2e/console.e2e.mjs OUT
import { createRequire } from "node:module";
import { mkdirSync } from "node:fs";
import assert from "node:assert/strict";

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT);
const BASE = process.env.BASE ?? "http://127.0.0.1:8790/";
const OUT = process.argv[2] ?? "console-shots";
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ executablePath: process.env.CHROME ?? "/usr/bin/google-chrome" });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: "dark" });
const page = await context.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
let shot = 0;
const snap = async (name) => page.screenshot({ path: `${OUT}/${String(++shot).padStart(2, "0")}-${name}.png` });
const step = (name) => console.log(`· ${name}`);

await page.goto(`${BASE}#/signin`);
await page.getByRole("button", { name: /^Continue/ }).click();
await page.waitForURL((url) => !url.hash.startsWith("#/signin"));

const openConsole = async () => {
  await page.goto(`${BASE}#/runs/${process.env.RUN}/script`);
  await page.reload();  // a hash change alone keeps the page (and an open drawer)
  await page.locator(".run__console").getByRole("button", { name: /Console/ }).click();  // in the run's side panel (wide screens)
  await page.locator(".con__input textarea").waitFor();
};
await openConsole();
const box = page.locator(".con__input textarea");
const type = async (text) => { await box.click(); await box.fill(""); await box.pressSequentially(text, { delay: 10 }); };
const send = async (text) => { await type(text); await box.press("Enter"); };
const status = page.locator(".con__status");

step("empty console, status line");
await page.locator(".con__empty").waitFor();
assert.match(await status.innerText(), /Accept Edits On/);
await snap("empty");

step("/ opens the command menu; Esc closes it");
await type("/");
await page.locator(".con__menu").waitFor();
assert.match(await page.locator(".con__menu").innerText(), /\/help[\s\S]*\/clear[\s\S]*\/model/);
await snap("slash-menu");
await box.press("Escape");
assert.equal(await page.locator(".con__menu").count(), 0);

step("? shows the shortcuts");
await type("");
await box.press("?");
await page.locator(".con__help").waitFor();
assert.equal(await box.inputValue(), "");
await snap("shortcuts");
await box.press("?");

step("/status runs here");
await send("/status");
await page.getByText("Working Folder").waitFor();
await snap("status");

step("a turn streams, asks permission, and runs once allowed");
await send("shorten scene 2");
await page.locator(".con__working").waitFor();
await page.locator(".con__said--live, .con__working:has-text(\"Thinking\")").first().waitFor();
await snap("working");
await page.locator(".con__ask").waitFor({ timeout: 15000 });
assert.match(await page.locator(".con__ask").innerText(), /python3 tools\/check_script\.py[\s\S]*Do You Want to Proceed\?[\s\S]*Bash\(python3 tools\/check_script\.py \*\)/);
await page.locator(".con__ask-options").press("1");  // within the guard: ignored, nothing is answered
await page.waitForTimeout(100);
assert.equal(await page.locator(".con__ask").count(), 1);
await page.waitForTimeout(700);
await snap("permission");
await page.locator(".con__ask-options").press("1");
await page.locator(".con__summary").last().waitFor({ timeout: 15000 });
const log = page.locator(".con__log");
const transcript = await log.innerText();
for (const title of ["Read(demo/script.json)", "Update(demo/script.json)", "Bash(python3 tools/check_script.py script.json)"])
  assert.ok(transcript.includes(title), `missing ${title}`);
assert.match(transcript, /Allowed Once/);
assert.match(transcript, /All checks passed/);
assert.match(transcript, /Added 2 Lines, Removed 2 Lines/);
await snap("done");

step("Ctrl+O shows every output and the times");
await box.click();
await box.press("Control+o");
await page.locator(".con__time").first().waitFor();
await snap("detail");
await box.press("Control+o");

step("Shift+Tab cycles the mode");
await box.press("Shift+Tab");
await page.getByText("⏸ Plan Mode On").waitFor();
await snap("plan-mode");
await box.press("Shift+Tab");
await page.getByText("⏸ Manual Mode On").waitFor();
await box.press("Shift+Tab");
await page.getByText("⏵⏵ Accept Edits On").waitFor();

step("Up brings back the last prompt");
await type("");
await box.press("ArrowUp");
assert.equal(await box.inputValue(), "shorten scene 2");
await box.fill("");

step("Ctrl+R searches earlier prompts; with no match Enter sends nothing and Esc leaves the search");
await type("draft text");
await box.press("Control+r");
await box.pressSequentially("zzz-no-match");
await box.press("Enter");
assert.equal(await page.locator(".con__working").count(), 0);
await box.press("Escape");
assert.equal(await box.inputValue(), "draft text");
await box.press("Control+r");
await box.pressSequentially("shorten");
await page.locator(".con__menu").getByText("shorten scene 2").waitFor();
await snap("history-search");
await box.press("Enter");
assert.equal(await box.inputValue(), "shorten scene 2");
await box.fill("");

step("/diff lists this conversation's edits");
await send("/diff");
await page.locator(".con__echo", { hasText: "/diff" }).waitFor();
assert.match(await page.locator(".con__local").last().innerText(), /Update\(demo\/script.json\)/);
await snap("diff");

step("/model picks a model");
await type("/model ");
await page.locator(".con__menu").getByText("sonnet").waitFor();
await snap("model-menu");
await box.press("ArrowDown");
await box.press("Enter");
await status.getByText("sonnet").waitFor();

step("@ suggests the run's files");
await type("look at @scr");
await page.locator(".con__menu").getByText("@script.json").waitFor();
await snap("files");
await box.press("Tab");
assert.equal(await box.inputValue(), "look at @script.json ");
await box.fill("");

step("an unavailable command says why");
await send("/resume");
await page.getByText("/resume Is Not Available Here").waitFor();

step("deny with a note");
await send("try again please");
await page.locator(".con__ask").waitFor({ timeout: 15000 });
await page.waitForTimeout(700);
await page.locator(".con__ask-options").press("3");
await page.locator("#console-deny-note").fill("skip the check for now");
await page.locator("#console-deny-note").press("Enter");
await page.locator(".con__summary").nth(1).waitFor({ timeout: 15000 });
assert.match(await log.innerText(), /Denied\. skip the check for now/);
await snap("denied");

step("Esc stops a running turn");
await send("go slow");
await page.locator(".con__working").waitFor();
await box.press("Escape");
await log.getByText("Stopped by You").waitFor({ timeout: 15000 });
assert.equal(await log.getByText("Stopped by You").count(), 1);
await snap("stopped");

step("/context goes to Claude Code");
await send("/context");
await page.locator(".con__log").getByText("Context Usage").waitFor({ timeout: 15000 });
await snap("context");

step("the transcript comes back after a reload");
await openConsole();
await page.locator(".con__log").getByText("Context Usage").waitFor();
assert.ok((await page.locator(".con__prompt").count()) >= 4);
await snap("restored");

step("Ctrl+` closes and opens the console from anywhere on the run page");
await page.keyboard.press("Escape");
await page.locator(".con").waitFor({ state: "detached", timeout: 5000 }).catch(() => undefined);
if (await page.locator(".con").count()) await page.getByRole("button", { name: "Close" }).click();
await page.locator(".run__console").waitFor();
await page.keyboard.press("Control+`");
await page.locator(".con__input textarea").waitFor();

step("small screen");
await page.setViewportSize({ width: 390, height: 844 });
await snap("mobile");

assert.deepEqual(errors, [], `page errors: ${errors.join(" | ")}`);
await browser.close();
console.log(`ok: ${shot} screenshots in ${OUT}`);
