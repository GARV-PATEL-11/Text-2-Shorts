// End-to-end: the Voice Studio (docs/voice-studio/) with REAL Amazon Polly (the demo server loads .env; previews are
// cached). Provider lock, search and filters, picking without playing, the orb and player with real audio and a real
// waveform, out-of-date previews after a settings change, replay, the error state with Try Again (a failed request),
// Select Voice, subtitles rolling out and in with their values kept, saved after reload, three viewport sizes.
//   BASE=http://127.0.0.1:8790/ RUN=<run id> PLAYWRIGHT=<path> node e2e/audio.e2e.mjs OUT
import { createRequire } from "node:module";
import { mkdirSync } from "node:fs";
import assert from "node:assert/strict";

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT);
const BASE = process.env.BASE ?? "http://127.0.0.1:8790/";
const OUT = process.argv[2] ?? "audio-shots";
mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.CHROME ?? "/usr/bin/google-chrome", args: ["--autoplay-policy=no-user-gesture-required"] });
const page = await (await browser.newContext({ viewport: { width: 1440, height: 1000 }, colorScheme: "dark" })).newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
let previews = 0;
page.on("request", (request) => { if (request.url().endsWith("/api/voices/preview")) previews += 1; });
let shot = 0;
const snap = (name, full = false) => page.screenshot({ path: `${OUT}/${String(++shot).padStart(2, "0")}-${name}.png`, fullPage: full });
const step = (name) => console.log(`· ${name}`);

await page.goto(`${BASE}#/signin`);
await page.getByRole("button", { name: /^Continue/ }).click();
await page.waitForURL((url) => !url.hash.startsWith("#/signin"));
const open = async () => {
  await page.goto(`${BASE}#/runs/${process.env.RUN}/template/sound`);
  await page.reload();
  await page.locator(".orb").waitFor({ timeout: 20000 });
};
await open();
const name = async () => (await page.locator(".studio__name").innerText()).split("\n")[0].trim();
const orb = (state) => page.locator(`.orb--${state}`).waitFor({ timeout: 20000 });
const rows = page.locator(".studio__row");
const playMain = async () => page.locator(".aplayer").getByRole("button", { name: new RegExp(`^Play ${await name()}`) }).click();

step("Amazon Polly is chosen; Google Cloud TTS is frosted and cannot be chosen");
const google = page.locator(".studio__provider--soon");
assert.equal(await google.getAttribute("aria-disabled"), "true");
await google.click({ force: true });
assert.equal(await page.locator(".studio__provider.is-on").innerText(), "Amazon Polly");
await snap("studio-desktop", true);

step("search and filters find voices by name, gender and accent");
const all = await rows.count();
assert.ok(all >= 20, `${all} voices`);
await page.getByLabel("Search Voices").fill("ol");
assert.ok((await rows.count()) < all);
await page.getByLabel("Search Voices").fill("zzz");
await page.getByText("No Voice Matches").waitFor();
await page.getByRole("button", { name: "Clear the Search" }).click();
assert.equal(await rows.count(), all);
await page.getByRole("group", { name: "Gender" }).getByRole("button", { name: "Female" }).click();
const women = await rows.count();
assert.ok(women > 0 && women < all);
await page.getByLabel("Accent").selectOption({ label: "British Accent" });
assert.ok((await rows.count()) <= women);
await snap("filtered");
await page.getByRole("group", { name: "Gender" }).getByRole("button", { name: "All" }).click();
await page.getByLabel("Accent").selectOption("");

step("picking a voice from the list shows it without playing");
const before = previews;
await rows.nth(3).locator(".studio__pick").click();
await page.waitForTimeout(400);
assert.equal(previews, before);
assert.equal(await name(), (await rows.nth(3).locator(".studio__row-name").innerText()).trim());
await page.getByText(/^Play to Hear/).waitFor();

step("the orb plays the real voice; the waveform and time follow the audio");
await page.locator(".orb").click();
await orb("playing");
await page.waitForTimeout(800);
assert.ok((await page.locator(".wave__bars span.is-played").count()) > 0);
assert.match(await page.locator(".aplayer__time").innerText(), /00:0\d \/ 00:\d\d$/);
await snap("speaking");

step("a changed setting makes the preview out of date until played again");
const slider = page.locator(".studio__field input[type=range]");
const otherSpeed = async () => { const now = Number(await slider.inputValue()); await slider.fill(String(now === 0 ? 1 : now - 1)); };
assert.equal(await page.getByLabel("Speaking Style").count(), 0);  // hidden for now
await otherSpeed();
await page.getByText("Settings Changed: Play to Hear Them").waitFor();
const asked = previews;
await playMain();
await orb("playing");
assert.equal(previews, asked + 1);
assert.match(await page.locator(".studio__line").innerText(), new RegExp(`I'm ${await name()}.*powered by Amazon Polly`));

step("replay starts the same preview again without a new request");
await page.waitForTimeout(500);
const again = previews;
await page.getByRole("button", { name: "Replay" }).click();
await orb("playing");
assert.equal(previews, again);

step("‹ › move to the next voice and play it");
const here = await name();
await page.getByRole("button", { name: "Next Voice", exact: true }).click();
await orb("playing");
assert.notEqual(await name(), here);

step("only the engines the voice has are offered (a choice only when there are several)");
const engineSelect = page.getByLabel("Voice Engine");
if (await engineSelect.count()) {
  const engines = await engineSelect.locator("option").allInnerTexts();
  assert.ok(engines.length > 1 && engines.every((engine) => /Generative|Long-Form|Neural|Standard/.test(engine)));
} else {
  assert.match(await page.locator(".studio__meta").innerText(), /(Generative|Long-Form|Neural|Standard) Engine/);
}

step("a preview that cannot be made shows the error and Try Again");
await page.route("**/api/voices/preview", (route) => route.fulfill({ status: 503, contentType: "application/json",
  body: JSON.stringify({ error: "Amazon Polly Did Not Answer. Check the Network and Try Again." }) }));
await otherSpeed();  // a real change: a new request
await playMain();
await orb("error");
await page.getByRole("alert").filter({ hasText: "Amazon Polly Did Not Answer" }).waitFor();
await snap("error");
await page.unroute("**/api/voices/preview");
await page.locator(".aplayer").getByRole("button", { name: /^Try .+ Again$/ }).click();
await orb("playing");

step("Select Voice makes it the narrator: one badge, a tick in the list, the button gone");
const selectButton = page.getByRole("button", { name: /^(Select Voice|Update Narrator)$/ });
if (!(await selectButton.count())) {  // this voice and delivery already are the narrator: take another voice
  await page.getByRole("button", { name: "Next Voice", exact: true }).click();
  await orb("playing");
}
await selectButton.click();
await page.locator(".studio__badge").filter({ hasText: "Your Narrator" }).waitFor();
assert.equal(await page.getByRole("button", { name: /^(Select Voice|Update Narrator)$/ }).count(), 0);
assert.equal(await page.locator(".studio__row.is-current .studio__tick").count(), 1);
const chosen = await name();
await page.getByText("Unsaved Changes").waitFor();  // selected on the page, not yet in the template
await snap("selected-unsaved");

step("subtitle settings roll out only while subtitles are on, and keep their values");
const toggle = page.getByRole("switch", { name: /^(On|Off)$/ });
const body = page.locator(".rollout__body");
if (!(await toggle.isChecked())) await toggle.click({ force: true });
await page.waitForTimeout(300);
await body.locator(".subtitles > summary").click();  // Edit opens the three settings
const kept = await body.innerText();
await toggle.click({ force: true });
await page.waitForTimeout(300);
assert.equal(await body.getAttribute("aria-hidden"), "true");
await toggle.click({ force: true });
await page.waitForTimeout(300);
assert.equal(await body.innerText(), kept);

step("the selected voice is saved and shown again after a reload");
await page.getByRole("button", { name: /Save Template/i }).click();
await page.getByText("Unsaved Changes").waitFor({ state: "detached" });
await open();
assert.equal(await name(), chosen);
await page.locator(".studio__badge").filter({ hasText: "Your Narrator" }).waitFor();

step("tablet and phone");
await page.setViewportSize({ width: 820, height: 1100 });
await snap("tablet", true);
await page.setViewportSize({ width: 390, height: 844 });
await snap("mobile", true);

assert.deepEqual(errors, [], `page errors: ${errors.join(" | ")}`);
await browser.close();
console.log(`ok: ${shot} screenshots, ${previews} preview requests in ${OUT}`);
