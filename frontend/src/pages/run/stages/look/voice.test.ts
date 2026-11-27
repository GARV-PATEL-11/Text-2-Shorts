import { test } from "node:test";
import assert from "node:assert/strict";
import { accentLabel, engineFor, filterVoices, previewLine, rateLabel, speedText, spokenBy, stepSpeed, withVoice } from "./voice.ts";

const curated = { "Joanna:neural": "us_female_warm", "Matthew:neural": "us_male_steady" };
const look = { template: "obsidian", elements: { voice: "us_male_steady" }, custom: {} as Record<string, string> };

test("the look's voice: its option, or its custom voice", () => {
  assert.deepEqual(spokenBy(look, curated), { voice: "Matthew", engine: "neural" });
  assert.deepEqual(spokenBy({ ...look, custom: { voice: "Danielle:generative" } }, curated), { voice: "Danielle", engine: "generative" });
});

test("choosing a voice uses the template's own option when there is one, else a custom voice", () => {
  const joanna = withVoice({ ...look, custom: { voice: "Danielle:generative" } }, "Joanna", "neural", curated);
  assert.equal(joanna.elements.voice, "us_female_warm");
  assert.equal(joanna.custom.voice, undefined);
  const danielle = withVoice(look, "Danielle", "generative", curated);
  assert.equal(danielle.custom.voice, "Danielle:generative");
  assert.equal(danielle.elements.voice, "us_male_steady");  // the option underneath stays (Google's equivalent)
});

test("an engine the voice lacks falls back to its best one", () => {
  const kajal = { id: "Kajal", name: "Kajal", gender: "Female", language_code: "en-IN", language: "Indian English", engines: ["generative", "neural"] };
  assert.equal(engineFor(kajal, "long-form"), "generative");
  assert.equal(engineFor(kajal, "neural"), "neural");
});

test("the preview line fills every variable and keeps unknown ones", () => {
  const line = previewLine("Hello! I'm {agent}. {tone} tone, {speed} speed, {provider}'s {engine} engine. {other}",
    { agent: "Danielle", tone: "friendly teacher", speed: "brisk", provider: "Amazon Polly", engine: "long-form" });
  assert.equal(line, "Hello! I'm Danielle. Friendly Teacher tone, Brisk speed, Amazon Polly's Long-Form engine. {other}");
});

test("speed steps stop at the ends", () => {
  const speeds = ["slow", "relaxed", "natural", "brisk", "fast"];
  assert.equal(stepSpeed(speeds, "natural", 1), "brisk");
  assert.equal(stepSpeed(speeds, "fast", 1), "fast");
  assert.equal(stepSpeed(speeds, "slow", -1), "slow");
  assert.equal(rateLabel(1.08), "1.08×");
  assert.equal(rateLabel(0.9), "0.9×");
});

test("accent and speed read as the studio shows them", () => {
  assert.equal(accentLabel("Singaporean English"), "Singaporean Accent");
  assert.equal(accentLabel("US English"), "US Accent");
  assert.equal(speedText("Natural", 1), "Natural · 1.0×");
});

test("voices are found by name, gender and accent together", () => {
  const voices = [
    { name: "Olivia", gender: "Female", language: "Australian English" },
    { name: "Oliver", gender: "Male", language: "British English" },
    { name: "Aria", gender: "Female", language: "New Zealand English" },
  ];
  assert.deepEqual(filterVoices(voices, "oli", "", "").map((voice) => voice.name), ["Olivia", "Oliver"]);
  assert.deepEqual(filterVoices(voices, "", "Female", "").map((voice) => voice.name), ["Olivia", "Aria"]);
  assert.deepEqual(filterVoices(voices, "oli", "Male", "British English").map((voice) => voice.name), ["Oliver"]);
  assert.deepEqual(filterVoices(voices, "zzz", "", ""), []);
});
