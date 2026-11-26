// Start a run, one step after another, under the journey strip (every stage of a run; the current one's steps below
// it): the template's steps (starter templates with Build Your Own, audio and subtitles, whole look), then the requirements' (the question, who it
// is for and how long, review). Starting saves and approves the template, so the run opens at the requirements.
// Everything is saved as a draft on this machine from the first change (#/new?draft=<id>), so a refresh, a closed
// browser or a sign-out loses nothing; Ongoing Runs lists the draft until the run starts.
import { type Dispatch, type ReactNode, type SetStateAction, useEffect, useRef, useState } from "react";
import { navigate } from "../app/routes";
import { Notice } from "../components/feedback/Notice";
import { Modal } from "../components/feedback/Overlay";
import { SystemMessage } from "../components/feedback/SystemMessage";
import { Page } from "../components/layout/Page";
import { Journey } from "../components/navigation/Journey";
import { Button } from "../components/ui/Button";
import { Field, FormRow, MarkdownField, RadioCards } from "../components/ui/fields";
import { ArrowLeft, ArrowRight } from "../components/ui/icons";
import { Markdown } from "../components/ui/Markdown";
import { titleCase } from "../components/ui/text";
import { Said } from "../components/ui/Said";
import { useAction } from "../hooks/useAction";
import { STAGE_STEPS } from "../config/stages";
import { useApi } from "../hooks/useApi";
import { load, send } from "../services/http";
import { APPROACHES } from "../config/approaches";
import { runHash } from "../services/runs";
import type { Draft, LookCatalogue, LookChoice, RunSummary } from "../types/api";
import { starterChoice, useTemplateEditor } from "./run/stages/look/useTemplateEditor";

const PROVIDERS = [
  { id: "polly", label: "AWS Polly", hint: "Uses Your ~/.aws Credentials" },
  { id: "google", label: "Google Cloud", hint: "Uses Your gcloud Application-Default Login" },
];
/** The steps of Start a Run, in order: the template stage's, then the requirements stage's. */
const STEPS = [
  { id: "starters", stage: "template", label: "Starter Templates" },
  { id: "sound", stage: "template", label: "Audio & Subtitles" },
  { id: "whole", stage: "template", label: "Whole Look" },
  { id: "question", stage: "requirements", label: "The Question" },
  { id: "audience", stage: "requirements", label: "Audience & Length" },
  { id: "review", stage: "requirements", label: "Review" },
];

function TemplateStep({ catalogue, choice, setChoice, step, next }: {
  catalogue: LookCatalogue; choice: LookChoice; setChoice: Dispatch<SetStateAction<LookChoice | null>>; step: string; next: ReactNode;
}) {
  const editor = useTemplateEditor({ catalogue, choice, setChoice, next });
  return (
    <div className="stack">
      {editor.tabs.find((tab) => tab.id === step)?.content}
      <Notice note={editor.stillAction.note} />
      {editor.note ? <p className="note" role="status">{editor.note}</p> : null}
      {editor.overlay}
    </div>
  );
}

export function NewRunPage() {
  const catalogue = useApi<LookCatalogue>("/api/look");
  const [choice, setChoice] = useState<LookChoice | null>(null);
  const [step, setStep] = useState(0);  // index into STEPS
  const [topic, setTopic] = useState("");
  const [objectives, setObjectives] = useState("");
  const [approach, setApproach] = useState("visual_intuition");
  const [notes, setNotes] = useState("");
  const [minutes, setMinutes] = useState("4");
  const [audience, setAudience] = useState("curious beginners");
  const [tts, setTts] = useState("polly");
  const [name, setName] = useState("");
  const [typed, setTyped] = useState("");  // the name pop-up's field, applied with Enter
  const [naming, setNaming] = useState(!window.location.hash.includes("draft="));  // a new run asks for its name first
  const { run, busy, note } = useAction();

  // the draft: restored when the address names one, then saved (debounced) on every change after the first
  const [draftId] = useState(() => new URLSearchParams(window.location.hash.split("?")[1] ?? "").get("draft") ?? crypto.randomUUID());
  const [restored, setRestored] = useState(!window.location.hash.includes("draft="));
  const [saving, setSaving] = useState<"idle" | "saving" | "saved" | "failed">("idle");
  const [savedAt, setSavedAt] = useState("");
  const baseline = useRef<string | null>(null);
  useEffect(() => {
    if (restored) return;
    load<Draft[]>("/api/drafts").then((drafts) => {
      const draft = drafts.find((candidate) => candidate.id === draftId);
      if (draft) {
        setName(draft.name); setStep(draft.step); setChoice(draft.look); setTopic(draft.requirement);
        setObjectives(draft.objectives); setApproach(draft.approach); setMinutes(draft.minutes); setAudience(draft.audience);
        setTts(draft.tts); setNotes(draft.notes); setSaving("saved"); setSavedAt(draft.updated.slice(11, 16));
      }
    }).finally(() => setRestored(true));
  }, [draftId, restored]);
  useEffect(() => {
    if (restored && catalogue.data && !choice) setChoice(starterChoice(catalogue.data, "obsidian") ?? starterChoice(catalogue.data, catalogue.data.templates[0].name));
  }, [catalogue.data, choice, restored]);
  const draft = { name, step, look: choice, requirement: topic, objectives, approach, minutes, audience, tts, notes };
  const snapshot = JSON.stringify(draft);
  useEffect(() => {
    if (!restored || !choice) return;
    if (baseline.current === null) { baseline.current = snapshot; return; }  // opening the page is not a change
    if (baseline.current === snapshot) return;
    baseline.current = "";  // from the first change on, every change is saved
    const timer = window.setTimeout(() => {
      setSaving("saving");
      send<Draft>(`/api/drafts/${draftId}`, JSON.parse(snapshot), "PUT")
        .then((saved) => {
          setSaving("saved"); setSavedAt(saved.updated.slice(11, 16));
          if (!window.location.hash.includes("draft=")) window.history.replaceState(null, "", `#/new?draft=${draftId}`);
        })
        .catch(() => setSaving("failed"));
    }, 600);
    return () => window.clearTimeout(timer);
  }, [snapshot, restored, choice, draftId]);
  const saveState = { idle: "", saving: "Saving…", saved: `All Changes Saved${savedAt ? ` · ${savedAt}` : ""}`, failed: "Not Saved: Trying Again on Your Next Change" }[saving];

  const goals = objectives.split("\n").map((line) => line.trim()).filter(Boolean);
  const ready: Record<string, boolean> = {
    starters: choice !== null, sound: true, whole: true, question: topic.trim().length >= 3,
    audience: Number(minutes) >= 3 && Number(minutes) <= 20 && audience.trim().length > 0, review: true,
  };
  const at = STEPS[step];
  const canReach = (index: number) => index <= step || STEPS.slice(0, index).every((candidate) => ready[candidate.id]);
  const changed = choice && catalogue.data
    ? Object.entries(choice.elements).filter(([element, value]) => starterChoice(catalogue.data!, choice.template)?.elements[element] !== value).length + Object.keys(choice.custom).length
    : 0;
  const start = () =>
    run("Checking Manim, LaTeX, ffmpeg and Voice Credentials, Then Creating the Run…", async () => {
      const created = await send<RunSummary>("/api/runs", {
        requirement: topic.trim(), objectives: goals, approach, minutes: Number(minutes), audience: audience.trim(), tts, look: choice, notes: notes.trim(),
        name: name.trim(),
      });
      await send(`/api/drafts/${draftId}`, null, "DELETE").catch(() => undefined);  // the run holds it all now
      navigate(runHash(created.id));  // the template is approved: the run opens at its next stage
    });

  const summary = (
    <aside className="card summary" aria-label="Your run so far">
      <h2 className="section-header__title">Your Run</h2>
      <dl className="facts">
        <div><dt>Template</dt><dd>{choice ? `${titleCase(choice.template)}${changed ? ` · ${changed} Changed` : ""}` : "—"}</dd></div>
        <div><dt>Explain</dt><dd>{topic.trim() ? <Markdown text={topic} compact /> : "—"}</dd></div>
        <div><dt>Objectives</dt><dd>{goals.length ? <ul>{goals.map((goal) => <li key={goal}>{goal}</li>)}</ul> : "Claude Suggests Some"}</dd></div>
        <div><dt>Approach</dt><dd>{APPROACHES.find((candidate) => candidate.id === approach)?.label}</dd></div>
        <div><dt>Length</dt><dd>{minutes} Min</dd></div>
        <div><dt>Audience</dt><dd>{titleCase(audience)}</dd></div>
        <div><dt>Voice Provider</dt><dd>{PROVIDERS.find((candidate) => candidate.id === tts)?.label}</dd></div>
      </dl>
    </aside>
  );
  const next = step < STEPS.length - 1
    ? <Button onPress={() => setStep(step + 1)} isDisabled={!ready[at.id]} icon={<ArrowRight />}>{`Continue: ${STEPS[step + 1].label}`}</Button>
    : <Button icon={<ArrowRight />} onPress={start} isDisabled={busy}>Start the Run</Button>;
  const foot = (
    <div className="form-foot">
      {step > 0 ? <Button variant="secondary" icon={<ArrowLeft />} onPress={() => setStep(step - 1)} isDisabled={busy}>Back</Button> : <span />}
      {next}
    </div>
  );

  let body;
  if (at.stage === "template") {
    body = catalogue.error ? <SystemMessage kind="unavailable" title="Could Not Load Templates">{catalogue.error.message}</SystemMessage>
      : !catalogue.data || !choice ? <SystemMessage kind="loading" title="Loading Templates" />
      : <div className="stack"><TemplateStep catalogue={catalogue.data} choice={choice} setChoice={setChoice} step={at.id} next={next} />{step ? foot : null}</div>;
  } else {
    body = (
      <div className="split">
        <div className="card stack">
          {at.id === "question" ? (
            <>
              <p className="note"><Said moment="question" /></p>
              <MarkdownField label="What Should the Video Explain?" value={topic} onChange={setTopic} rows={5} isRequired maxLength={2000}
                placeholder="Why is the sky blue, and why are sunsets red?" hint="A Question Works Best" />
              <Field label="Objectives" value={objectives} onChange={setObjectives} multiline rows={4}
                placeholder={"explain Rayleigh scattering\nsay why sunsets are red"} hint="One per Line: What the Viewer Can Do Afterwards (Optional)" />
            </>
          ) : null}
          {at.id === "audience" ? (
            <>
              <p className="note"><Said moment="audience" /></p>
              <div className="field">
                <span className="field__label">How Should It Be Told?</span>
                <RadioCards label="Approach" value={approach} options={APPROACHES} onChange={(id) => {
                  setApproach(id);
                  setMinutes(String(APPROACHES.find((candidate) => candidate.id === id)?.minutes ?? 4));
                }} />
              </div>
              {approach === "custom" ? (
                <Field label="How Should It Be Taught?" value={notes} onChange={setNotes} multiline rows={4} maxLength={2000}
                  placeholder={"conversational, with everyday examples\nstart from a question, end with a challenge"}
                  hint="Teaching Style, Depth, Examples, Pacing, Visuals or Your Own Scene Order" />
              ) : null}
              <FormRow>
                <Field label="Length (Minutes)" type="number" value={minutes} onChange={setMinutes} min={3} max={20} step={0.5} isRequired hint="3–20 of Teaching; Intro and Closing Are Extra" />
                <Field label="Audience" value={audience} onChange={setAudience} maxLength={300} isRequired hint="For Example: Curious Beginners, Students" />
              </FormRow>
              <div className="field">
                <span className="field__label">Voice Provider</span>
                <RadioCards label="Voice Provider" value={tts} onChange={setTts} options={PROVIDERS} />
              </div>
            </>
          ) : null}
          {at.id === "review" ? <><p className="note"><Said moment="review" /></p><p className="note">Starting Checks This Computer, Saves Your Template and Opens the Run</p></> : null}
          {foot}
          <Notice note={note} />
        </div>
        {summary}
      </div>
    );
  }

  return (
    <Page title="Start a Run">
      <Journey label="Start a Run" current={at.id}
        stages={STAGE_STEPS.map((stage) => ({
          id: stage.id, label: stage.label, optional: stage.optional,
          state: stage.id === at.stage ? "current" : stage.id === "template" ? "done" : "upcoming",
        }))}
        steps={STEPS.map((candidate, index) => ({ ...candidate, index })).filter((candidate) => candidate.stage === at.stage).map((candidate) => ({
          id: candidate.id, label: candidate.label, open: canReach(candidate.index),
          state: candidate.index < step ? "done" : candidate.index === step ? "current" : "upcoming",
        }))}
        onStep={(id) => {
          const target = STEPS.findIndex((candidate) => candidate.id === id);
          if (canReach(target)) setStep(target);
        }} />
      <p className="save-state note" role="status" aria-live="polite">{saveState}</p>
      {body}
      <Modal isOpen={naming} onOpenChange={setNaming} title="Name Your Run" description="Optional: Skip It and the Run Is Named From Its Topic and Date"
        footer={<Button icon={<ArrowRight />} onPress={() => { setName(typed.trim()); setNaming(false); }}>{typed.trim() ? "Enter" : "Skip"}</Button>}>
        <form onSubmit={(event) => { event.preventDefault(); setName(typed.trim()); setNaming(false); }}>
          <Field label="Run Name" value={typed} onChange={setTyped} maxLength={120}
            placeholder={`Untitled Run — ${new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`} />
        </form>
      </Modal>
    </Page>
  );
}
