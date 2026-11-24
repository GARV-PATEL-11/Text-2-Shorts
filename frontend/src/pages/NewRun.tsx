// Start a run, one step after another, under the journey strip (every stage of a run; the current one's steps below
// it): the template's steps (starter, build your own, sound, whole look), then the requirements' (the question, who it
// is for and how long, review). Starting saves and approves the template, so the run opens at the requirements.
import { type Dispatch, type SetStateAction, useEffect, useState } from "react";
import { navigate } from "../app/routes";
import { Notice } from "../components/feedback/Notice";
import { SystemMessage } from "../components/feedback/SystemMessage";
import { Page } from "../components/layout/Page";
import { Breadcrumbs } from "../components/navigation/Breadcrumbs";
import { Journey } from "../components/navigation/Journey";
import { Button } from "../components/ui/Button";
import { Field, FormRow, MarkdownField, RadioCards } from "../components/ui/fields";
import { ArrowLeft, ArrowRight, Check } from "../components/ui/icons";
import { Markdown } from "../components/ui/Markdown";
import { titleCase } from "../components/ui/text";
import { useAction } from "../hooks/useAction";
import { STAGE_STEPS } from "../config/stages";
import { useApi } from "../hooks/useApi";
import { send } from "../services/http";
import { runHash } from "../services/runs";
import type { LookCatalogue, LookChoice, RunSummary } from "../types/api";
import { starterChoice, useTemplateEditor } from "./run/stages/look/useTemplateEditor";

const APPROACHES = [
  { id: "zoom", label: "Conceptual Zoom", hint: "Big picture first, then closer and closer to the detail." },
  { id: "arc", label: "Problem → Solution", hint: "A puzzle or tension, then the idea that resolves it." },
  { id: "linear", label: "Classic Lesson", hint: "Step by step, each idea building on the last." },
  { id: "creative", label: "Designed for the Topic", hint: "Claude designs a structure for this subject (or follows yours)." },
];
const PROVIDERS = [
  { id: "polly", label: "AWS Polly", hint: "Uses your ~/.aws credentials." },
  { id: "google", label: "Google Cloud", hint: "Uses your gcloud application-default login." },
];
/** The steps of Start a Run, in order: the template stage's, then the requirements stage's. */
const STEPS = [
  { id: "starters", stage: "template", label: "Starter Templates" },
  { id: "look", stage: "template", label: "Build Your Own" },
  { id: "sound", stage: "template", label: "Sound" },
  { id: "whole", stage: "template", label: "Whole Look" },
  { id: "question", stage: "requirements", label: "The Question" },
  { id: "audience", stage: "requirements", label: "Audience & Length" },
  { id: "review", stage: "requirements", label: "Review" },
];

function TemplateStep({ catalogue, choice, setChoice, step }: {
  catalogue: LookCatalogue; choice: LookChoice; setChoice: Dispatch<SetStateAction<LookChoice | null>>; step: string;
}) {
  const editor = useTemplateEditor({ catalogue, choice, setChoice });
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
  const [approach, setApproach] = useState("zoom");
  const [minutes, setMinutes] = useState("2");
  const [audience, setAudience] = useState("curious beginners");
  const [tts, setTts] = useState("polly");
  const { run, busy, note } = useAction();
  useEffect(() => {
    if (catalogue.data && !choice) setChoice(starterChoice(catalogue.data, "standard") ?? starterChoice(catalogue.data, catalogue.data.templates[0].name));
  }, [catalogue.data, choice]);

  const goals = objectives.split("\n").map((line) => line.trim()).filter(Boolean);
  const ready: Record<string, boolean> = {
    starters: choice !== null, look: true, sound: true, whole: true, question: topic.trim().length >= 3,
    audience: Number(minutes) >= 0.5 && Number(minutes) <= 12 && audience.trim().length > 0, review: true,
  };
  const at = STEPS[step];
  const canReach = (index: number) => index <= step || STEPS.slice(0, index).every((candidate) => ready[candidate.id]);
  const changed = choice && catalogue.data
    ? Object.entries(choice.elements).filter(([element, value]) => starterChoice(catalogue.data!, choice.template)?.elements[element] !== value).length + Object.keys(choice.custom).length
    : 0;
  const start = () =>
    run("Checking this computer (Manim, LaTeX, ffmpeg, voice credentials) and creating the run…", async () => {
      const created = await send<RunSummary>("/api/runs", {
        requirement: topic.trim(), objectives: goals, approach, minutes: Number(minutes), audience: audience.trim(), tts, look: choice,
      });
      navigate(runHash(created.id));  // the template is approved: the run opens at its next stage
    });

  const summary = (
    <aside className="card summary" aria-label="Your run so far">
      <h2 className="section-header__title">Your Run</h2>
      <dl className="facts">
        <div><dt>Template</dt><dd>{choice ? `${titleCase(choice.template)}${changed ? ` · ${changed} Changed` : ""}` : "—"}</dd></div>
        <div><dt>Explain</dt><dd>{topic.trim() ? <Markdown text={topic} compact /> : "—"}</dd></div>
        <div><dt>Objectives</dt><dd>{goals.length ? <ul>{goals.map((goal) => <li key={goal}>{goal}</li>)}</ul> : "Claude Proposes Them with You"}</dd></div>
        <div><dt>Approach</dt><dd>{APPROACHES.find((candidate) => candidate.id === approach)?.label}</dd></div>
        <div><dt>Length</dt><dd>{minutes} Min</dd></div>
        <div><dt>Audience</dt><dd>{titleCase(audience)}</dd></div>
        <div><dt>Voice Provider</dt><dd>{PROVIDERS.find((candidate) => candidate.id === tts)?.label}</dd></div>
      </dl>
    </aside>
  );
  const foot = (
    <div className="form-foot">
      {step > 0 ? <Button variant="secondary" icon={<ArrowLeft />} onPress={() => setStep(step - 1)} isDisabled={busy}>Back</Button> : <span />}
      {step < STEPS.length - 1
        ? <Button onPress={() => setStep(step + 1)} isDisabled={!ready[at.id]} icon={<ArrowRight />}>{`Continue: ${STEPS[step + 1].label}`}</Button>
        : <Button icon={<Check />} onPress={start} isDisabled={busy}>Start the Run</Button>}
    </div>
  );

  let body;
  if (at.stage === "template") {
    body = catalogue.error ? <SystemMessage kind="unavailable" title="The Templates Could Not Be Read">{catalogue.error.message}</SystemMessage>
      : !catalogue.data || !choice ? <SystemMessage kind="loading" title="Laying Out Every Template…" />
      : <div className="stack"><TemplateStep catalogue={catalogue.data} choice={choice} setChoice={setChoice} step={at.id} />{foot}</div>;
  } else {
    body = (
      <div className="split">
        <div className="card stack">
          {at.id === "question" ? (
            <>
              <MarkdownField label="What Should the Video Explain?" value={topic} onChange={setTopic} rows={5} isRequired maxLength={2000}
                placeholder="Why is the sky blue, and why are sunsets red?" hint="In your own words: a question works best." />
              <Field label="Objectives" value={objectives} onChange={setObjectives} multiline rows={4}
                placeholder={"explain Rayleigh scattering\nsay why sunsets are red"} hint="One per line: what the viewer can do afterwards. Optional." />
            </>
          ) : null}
          {at.id === "audience" ? (
            <>
              <div className="field">
                <span className="field__label">How Should It Be Told?</span>
                <RadioCards label="Approach" value={approach} onChange={setApproach} options={APPROACHES} />
              </div>
              <FormRow>
                <Field label="Length (Minutes)" type="number" value={minutes} onChange={setMinutes} min={0.5} max={12} step={0.5} isRequired />
                <Field label="Audience" value={audience} onChange={setAudience} maxLength={300} isRequired hint="e.g. curious beginners, students" />
              </FormRow>
              <div className="field">
                <span className="field__label">Voice Provider</span>
                <RadioCards label="Voice Provider" value={tts} onChange={setTts} options={PROVIDERS} />
              </div>
            </>
          ) : null}
          {at.id === "review" ? <p className="note">Check the summary. Starting checks this computer, saves your template and opens the run at its next stage, the requirements.</p> : null}
          {foot}
          <Notice note={note} />
        </div>
        {summary}
      </div>
    );
  }

  return (
    <Page title="Start a Run">
      <Breadcrumbs trail={[{ label: "Start a Run" }]} />
      <Journey label="Start a Run" current={at.id}
        stages={STAGE_STEPS.map((stage) => ({
          id: stage.id, label: stage.label, icon: stage.icon, optional: stage.optional,
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
      {body}
    </Page>
  );
}
