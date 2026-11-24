// Faraday (Text-2-Shorts) frontend: reads and writes the API of `text-2-shorts serve`; renders with DOM nodes only
// (run data is never parsed as HTML). Routes: #/signin, #/ (all runs) and #/runs/<run>. Everything but the sign-in
// page needs a session, opened with the Claude account Claude Code is signed in to on this machine.

const STATUS_WORDS = {
  pending: "Not started",
  in_progress: "In progress",
  completed: "Done",
  failed: "Failed",
  requires_refactoring: "Being fixed",
  requires_user_approval: "Waiting for you",
  approved: "Approved",
};
const STAGES = [
  ["requirements", "Requirements"],
  ["template", "Template"],
  ["outline", "Outline"],
  ["script", "Script"],
  ["plan", "Scene plans"],
  ["scenes", "Scenes"],
  ["final", "Final video"],
];
// The workflow's stage labels, in plain words.
const STAGE_NAMES = {
  "1 requirements": "Requirements", "1 template": "Template", "2 outline": "Outline", "3 script": "Script",
  "4 plans": "Scene plans", "5 production": "Making the scenes", final: "Final video",
  "change requests": "Applying your changes", done: "Done",
};
const stageName = (stage) => STAGE_NAMES[stage] || stage;

// Scenes as one stage, from the real scene statuses: nothing is called done unless every scene is approved.
function scenesStage(run) {
  const states = run.scenes.map((scene) => scene.status);
  if (!states.length) return "pending";
  if (states.every((state) => state === "approved")) return "approved";
  for (const state of ["failed", "requires_user_approval", "requires_refactoring"]) if (states.includes(state)) return state;
  return states.every((state) => state === "pending") && run.stages.plan !== "approved" ? "pending" : "in_progress";
}
const DOING = { write: "You write", subagent: "Subagent", command: "Run", ask_user: "Ask the user" };
const KINDS = [
  ["wording", "Wording: what is said"],
  ["visual", "Visuals: what is shown"],
  ["audio-timing", "Audio timing"],
  ["accuracy", "Accuracy: a claim is wrong"],
  ["structure", "Structure: order or scenes"],
  ["style", "Style: look or tone"],
  ["other", "Something else"],
];

const app = document.getElementById("app");
const accountBar = document.getElementById("account");
let account = null;

function el(tag, attributes = {}, ...children) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    if (value === null || value === undefined || value === false) continue;
    if (name === "class") node.className = value;
    else node.setAttribute(name, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

// `code` spans in the workflow's text, as code (text nodes only, never HTML).
const withCode = (text) => text.split("`").map((part, index) => (index % 2 ? el("code", {}, part) : part));
const status = (value) => el("span", { class: "status", "data-status": value }, STATUS_WORDS[value] || value);
const wrap = (...children) => el("div", { class: "wrap" }, ...children);
const section = (className, ...children) => el("section", { class: `sec ${className}` }, wrap(...children));
const head = (title, lead) => el("div", { class: "sec__head" }, el("h2", {}, title), lead && el("p", { class: "lead" }, lead));

class SignedOut extends Error {}

async function load(path) {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (response.status === 401) throw new SignedOut("sign in first");
  if (!response.ok) throw new Error(`${path} answered ${response.status}`);
  return response.json();
}

function show(...nodes) {
  app.removeAttribute("aria-busy");
  app.replaceChildren(...nodes.filter(Boolean));
  window.scrollTo(0, 0);
}

// Static, no motion: where the content will appear, before it arrives.
function loading(what) {
  app.setAttribute("aria-busy", "true");
  app.replaceChildren(el("section", { class: "hero" }, wrap(el("p", { class: "note" }, `Loading ${what}…`))));
}

async function send(path, body, method = "POST") {
  const response = await fetch(path, {
    method,
    headers: body === null ? { Accept: "application/json" } : { "Content-Type": "application/json", Accept: "application/json" },
    body: body === null ? undefined : JSON.stringify(body),
  });
  const answer = await response.json().catch(() => ({}));
  if (response.status === 401 && path !== "/api/session") throw new SignedOut("sign in first");
  if (!response.ok) {
    const error = new Error(answer.error || `${path} answered ${response.status}`);
    error.problems = answer.problems || [];
    throw error;
  }
  return answer;
}

// After a write: re-read the run and keep the reader where they were, with a message for screen readers too.
let notice = "";
async function refresh(id, message) {
  const top = window.scrollY;
  notice = message;
  await runPage(id, true);
  window.scrollTo(0, top);
}

function message(node, text, isError) {
  node.replaceChildren(text);
  node.className = isError ? "message message--error" : "message";
}

function failure(error) {
  if (error instanceof SignedOut) {
    account = null;
    location.hash = "#/signin";
    return;
  }
  show(
    el("section", { class: "hero" }, wrap(
      el("h1", {}, "The runs could not be loaded"),
      el("p", { class: "lead" }, `${error.message}. Check that \`text-2-shorts serve\` is still running, then reload.`),
    )),
  );
}

// ── sign in ───────────────────────────────────────────────────────────────────────────────────────────
function renderAccount() {
  if (!account) {
    accountBar.replaceChildren();
    return;
  }
  const signOut = el("button", { class: "btn btn--ghost btn--sm", type: "button" }, "Sign out");
  signOut.addEventListener("click", async () => {
    await send("/api/session", null, "DELETE").catch(() => null);
    account = null;
    location.hash = "#/signin";
  });
  accountBar.replaceChildren(el("span", {}, account.email), signOut);
}

async function signInPage() {
  const session = await load("/api/session");
  if (session.signed_in) {
    account = session.account;
    location.hash = "#/";
    return;
  }
  const status_ = el("p", { class: "message", role: "status" });
  const steps = el("ol", {},
    el("li", {}, "Open a terminal on this computer."),
    el("li", {}, "Run ", el("code", {}, "claude auth login"), ". It opens claude.ai so you can sign in."),
    el("li", {}, "Come back here and continue."),
  );
  const help = el("div", { class: "card", hidden: session.claude_code_signed_in },
    el("h4", {}, "Claude Code is not signed in here"), steps);
  const proceed = el("button", { class: "btn btn--wide", type: "button" }, "Continue with Claude");
  proceed.addEventListener("click", async () => {
    proceed.disabled = true;
    try {
      const signed = await send("/api/session", null);
      account = signed.account;
      location.hash = "#/";
    } catch (error) {
      proceed.disabled = false;
      help.hidden = false;
      message(status_, error.message, true);
    }
  });
  show(el("section", { class: "signin" }, el("div", { class: "signin__box" },
    el("div", { class: "sec__head" },
      el("p", { class: "signin__brand" }, el("strong", {}, "Faraday"), el("span", {}, "Curiosity, Illustrated.")),
      el("h1", {}, "Sign in"),
      el("p", { class: "lead" }, "Use the Claude account your Claude Code is signed in to on this computer."),
    ),
    el("div", { class: "card" },
      proceed,
      el("p", { class: "note" }, "No password is entered here: Faraday asks Claude Code which Claude account this computer uses. You stay signed in for 12 hours, or until you sign out."),
      status_,
    ),
    help,
  )));
}

// ── a new run ─────────────────────────────────────────────────────────────────────────────────────────
function newRunForm() {
  const status_ = el("p", { class: "message", role: "status" });
  const field = (label, control) => el("div", {}, el("label", { for: control.id }, label), control);
  const form = el("form", { class: "newrun card", "aria-label": "Start a run" },
    el("label", { for: "new-topic" }, "faraday new  (what should the video explain?)"),
    el("textarea", { id: "new-topic", name: "requirement", rows: "2", required: true, minlength: "3", maxlength: "2000", placeholder: "Why is the sky blue, and why are sunsets red?" }),
    el("label", { for: "new-objectives" }, "Objectives  (one per line: what the viewer can do afterwards)"),
    el("textarea", { id: "new-objectives", name: "objectives", rows: "3", placeholder: "explain Rayleigh scattering\nsay why sunsets are red" }),
    el("div", { class: "row2" },
      field("Approach", el("select", { id: "new-approach", name: "approach" },
        ["zoom", "arc", "linear", "creative"].map((value) => el("option", { value }, value)))),
      field("Minutes", el("input", { id: "new-minutes", name: "minutes", type: "number", min: "0.5", max: "12", step: "0.5", value: "2" })),
      field("Voice", el("select", { id: "new-tts", name: "tts" }, el("option", { value: "polly" }, "AWS Polly"), el("option", { value: "google" }, "Google"))),
    ),
    el("label", { for: "new-audience" }, "Audience"),
    el("input", { id: "new-audience", name: "audience", value: "curious beginners", maxlength: "300" }),
    el("div", { class: "row" }, el("button", { class: "btn", type: "submit" }, "Start the run")),
    status_,
  );
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const button = form.querySelector("button");
    button.disabled = true;
    message(status_, "Checking this computer (Manim, LaTeX, ffmpeg, voice credentials)…", false);
    try {
      const run = await send("/api/runs", {
        requirement: String(data.get("requirement")).trim(),
        objectives: String(data.get("objectives")).split("\n").map((line) => line.trim()).filter(Boolean),
        approach: data.get("approach"),
        minutes: Number(data.get("minutes")),
        audience: String(data.get("audience")).trim() || "curious beginners",
        tts: data.get("tts"),
      });
      location.hash = `#/runs/${encodeURIComponent(run.id)}`;
    } catch (error) {
      if (error instanceof SignedOut) return failure(error);
      button.disabled = false;
      message(status_, error.message, true);
    }
  });
  return section("", head("Start a run", "Describe the video. Faraday checks this computer, creates the run, and opens its console."), form);
}

// ── all runs ──────────────────────────────────────────────────────────────────────────────────────────
async function runsPage() {
  loading("your runs");
  const runs = await load("/api/runs");
  const latest = runs.find((run) => run.readable);
  const hero = el("section", { class: "hero" }, wrap(
    el("h1", {}, "Curiosity, Illustrated."),
    el("p", { class: "lead" }, "Each run turns a question into a narrated, animated explainer. See where every run stands, decide what it needs, and watch its scenes as they are made."),
    el("div", { class: "hero__actions" },
      latest && el("a", { class: "btn", href: `#/runs/${encodeURIComponent(latest.id)}` }, "Open the latest run"),
    ),
  ));
  const list = runs.length
    ? el("ul", { class: "runs" }, runs.map((run) => el("li", {},
        el("a", { href: `#/runs/${encodeURIComponent(run.id)}` },
          el("h3", {}, run.topic),
          el("span", { class: "meta" }, run.created),
          el("span", { class: "meta" }, run.readable ? `Now: ${stageName(run.stage)}` : "Older version: final video only"),
          el("span", { class: "meta" }, run.has_final ? "Final video ready" : "No final video yet"),
        ),
      )))
    : el("p", { class: "empty" }, "No runs yet. Start one above.");
  show(hero, newRunForm(), section("", head("Runs", `${runs.length} run${runs.length === 1 ? "" : "s"}, newest first.`), list));
}

// ── the console: the run's Claude Code session, one message at a time ────────────────────────────────
function consoleLine(entry) {
  return el("li", { class: entry.role }, entry.text);
}

async function consoleSection(run) {
  const id = run.summary.id;
  const view = await load(`/api/runs/${encodeURIComponent(id)}/console`);
  const log = el("ol", { class: "term__log", "aria-live": "polite", "aria-label": "Conversation with Claude" },
    view.entries.length
      ? view.entries.map(consoleLine)
      : el("li", { class: "term__empty" }, "Nothing said yet. Start production, or tell Claude what you want."));
  const status_ = el("p", { class: "message", role: "status" }, view.busy ? "Claude is working on an earlier message. Reload to see its replies." : "");
  const input = el("textarea", { id: "console-input", rows: "2", maxlength: "8000", placeholder: view.entries.length ? "Reply to Claude, or ask for anything in this run" : view.kickoff, "aria-label": "Message to Claude" });
  const send = el("button", { class: "btn btn--sm", type: "submit" }, view.entries.length ? "Send" : "Start");
  const form = el("form", { class: "term__input" }, el("span", { class: "term__prompt", "aria-hidden": "true" }, "›"), input, send);
  const busy = (on) => { input.disabled = on; send.disabled = on; };
  busy(view.busy);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = input.value.trim() || (view.entries.length ? "" : view.kickoff);
    if (!text) return;
    if (log.querySelector(".term__empty")) log.replaceChildren();
    busy(true);
    input.value = "";
    message(status_, "Claude is working. Replies appear as they come; long steps (renders, voice) can take minutes.", false);
    try {
      const response = await fetch(`/api/runs/${encodeURIComponent(id)}/console`, {
        method: "POST", headers: { "Content-Type": "application/json", Accept: "application/x-ndjson" },
        body: JSON.stringify({ message: text }),
      });
      if (response.status === 401) throw new SignedOut("sign in first");
      if (!response.ok) throw new Error((await response.json().catch(() => ({}))).error || `the console answered ${response.status}`);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffered = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffered += decoder.decode(value, { stream: true });
        const lines = buffered.split("\n");
        buffered = lines.pop();
        for (const line of lines.filter(Boolean)) {
          log.append(consoleLine(JSON.parse(line)));
          log.scrollTop = log.scrollHeight;
        }
      }
      await refresh(id, "Claude finished its turn.");
    } catch (error) {
      if (error instanceof SignedOut) return failure(error);
      busy(false);
      message(status_, error.message, true);
    }
  });
  input.addEventListener("keydown", (event) => {  // Enter sends, Shift+Enter starts a new line
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });
  queueMicrotask(() => { log.scrollTop = log.scrollHeight; });
  return section("", head("Console", "Talk to the run's Claude Code session. Every message is one turn; Claude stops when it needs you."),
    el("div", { class: "term" },
      el("div", { class: "term__bar" }, el("span", {}, "claude code"), el("span", {}, id)),
      log, form, el("div", { class: "term__status" }, status_),
    ),
  );
}

// ── one run ───────────────────────────────────────────────────────────────────────────────────────────
function approvalPanel(run, checkpoint) {
  const notes = el("textarea", { id: `notes-${checkpoint.target}`, rows: "2", maxlength: "4000" });
  const status_ = el("p", { class: "message", role: "status" });
  const blocked = checkpoint.problems.length > 0;
  return el("article", { class: "card card--strong panel", "aria-labelledby": `cp-${checkpoint.target}` },
    el("h3", { id: `cp-${checkpoint.target}` }, checkpoint.label),
    blocked
      ? el("div", {},
          el("p", {}, "Open problems:"),
          el("ul", { class: "problems" }, checkpoint.problems.map((problem) => el("li", {}, problem))),
          el("p", { class: "note" }, "Approving anyway records that you accepted these."),
        )
      : el("p", { class: "note" }, "Nothing blocks this checkpoint. Ask Claude in the console to show it, then decide."),
    el("label", { for: `notes-${checkpoint.target}` }, "Notes (optional)"),
    notes,
    el("div", { class: "row" },
      el("button", { class: blocked ? "btn btn--ghost" : "btn", type: "button" }, blocked ? "Approve anyway" : "Approve"),
      el("button", { class: "btn btn--ghost", type: "button", "data-ask": "" }, "Ask for changes"),
    ),
    status_,
  );
}

function awaitingSection(run) {
  if (!run.awaiting.length) return null;
  return section("", head("Waiting for you", "Approve to let the run continue, or ask for changes first."),
    el("div", { class: "panels" }, run.awaiting.map((checkpoint) => {
      const panel = approvalPanel(run, checkpoint);
      const button = panel.querySelector("button");
      button.addEventListener("click", async () => {
        button.disabled = true;
        const force = checkpoint.problems.length > 0;
        const notes = panel.querySelector("textarea").value.trim();
        const status_ = panel.querySelector(".message");
        try {
          const decision = await send(`/api/runs/${encodeURIComponent(run.summary.id)}/approve`, {
            checkpoint: checkpoint.target, notes, force,
          });
          await refresh(run.summary.id, `${checkpoint.label} approved${decision.forced ? " with its open problems" : ""}.`);
        } catch (error) {
          button.disabled = false;
          message(status_, `${error.message}${error.problems.length ? `: ${error.problems.join("; ")}` : ""}`, true);
        }
      });
      panel.querySelector("[data-ask]").addEventListener("click", () => {
        const form = document.getElementById("ask");
        form.querySelector("[name=checkpoint]").value = checkpoint.target.startsWith("start:") ? "" : checkpoint.target;
        const target = form.querySelector("[name=target]");
        if ([...target.options].some((option) => option.value === checkpoint.target)) target.value = checkpoint.target;
        form.scrollIntoView();
        form.querySelector("textarea").focus();
      });
      return panel;
    })),
  );
}

function stageStrip(run) {
  const stages = { ...run.stages, scenes: scenesStage(run) };
  const current = STAGES.findIndex(([key]) => stages[key] !== "approved");
  return el("ol", { class: "stages", "aria-label": "Stages, in order" }, STAGES.map(([key, name], index) => el("li",
    { class: index === current ? "is-current" : null, "aria-current": index === current ? "step" : null },
    el("span", { class: "step" }, String(index + 1), index === current && el("span", { class: "now" }, "now")),
    el("h4", {}, name),
    status(stages[key] || "pending"),
  )));
}

// Counts the run's files really hold; nothing estimated.
function counts(run) {
  const clips = run.scenes.flatMap((scene) => scene.clips);
  const built = clips.filter((clip) => ["completed", "approved"].includes(clip.status)).length;
  const scenesDone = run.scenes.filter((scene) => scene.status === "approved").length;
  const open = run.requests.filter((request) => request.status === "open").length;
  const figure = (value, label) => el("div", { class: "figure" }, el("dt", {}, label), el("dd", {}, value));
  return el("dl", { class: "figures" },
    figure(`${STAGES.filter(([key]) => ({ ...run.stages, scenes: scenesStage(run) })[key] === "approved").length} of ${STAGES.length}`, "Stages approved"),
    figure(run.scenes.length ? `${scenesDone} of ${run.scenes.length}` : "–", "Scenes approved"),
    figure(clips.length ? `${built} of ${clips.length}` : "–", "Clips built"),
    figure(String(open), open === 1 ? "Open change request" : "Open change requests"),
  );
}

function nextSection(run) {
  const batch = run.next;
  const offered = new Set(run.awaiting.map((checkpoint) => checkpoint.target));
  if (batch && batch.actions.length && batch.actions.every((action) => offered.has(action.checkpoint))) return null;  // the panel above asks it
  if (!batch || !batch.actions.length) {
    return section("", head("What happens next", "Nothing: the final video is approved."));
  }
  return section("",
    head("What happens next", `${stageName(batch.stage)}. Claude does this when you send it a message in the console.`),
    el("ul", { class: "actions" }, batch.actions.map((action) => el("li", { class: "card" },
      el("div", { class: "who" }, DOING[action.do] || action.do, action.agent && el("div", { class: "id" }, action.agent)),
      el("div", {},
        el("p", {}, action.target && el("span", { class: "id" }, `${action.target}: `), withCode(action.what)),
        action.command && el("p", { class: "reads" }, el("code", {}, action.command)),
        action.before && el("p", { class: "reads" }, "First ", el("code", {}, action.before), ", then ", el("code", {}, action.after)),
        action.read.length > 0 && el("p", { class: "reads" }, `Reads ${action.read.map((path) => path.split("/").pop()).join(", ")}`),
      ),
    ))),
  );
}

function scenesSection(scenes) {
  if (!scenes.length) {
    return section("", head("Scenes", "Scenes appear here once their visual plans are written."));
  }
  return section("", head("Scenes", "Made in order: a scene starts after the one before it is approved."),
    el("div", { class: "scenes" }, scenes.map((scene) => el("article", { class: "card scene", "aria-labelledby": `scene-${scene.scene_id}` },
      el("div", { class: "scene__head" },
        el("span", { class: "id" }, scene.scene_id),
        el("h3", { id: `scene-${scene.scene_id}` }, scene.title),
        status(scene.status),
        el("table", { class: "clips" },
          el("thead", {}, el("tr", {}, el("th", { scope: "col" }, "Clip"), el("th", { scope: "col" }, "What it shows"), el("th", { scope: "col" }, "Status"))),
          el("tbody", {}, scene.clips.map((clip) => el("tr", {},
            el("td", { class: "id" }, clip.clip_id), el("td", {}, clip.objective), el("td", {}, status(clip.status)),
          ))),
        ),
        scene.sync_problems.length > 0 && el("ul", { class: "problems" }, scene.sync_problems.map((problem) => el("li", {}, problem))),
      ),
      scene.preview
        ? el("video", { src: scene.preview, controls: true, preload: "metadata", "aria-label": `Preview of ${scene.title}` })
        : el("p", { class: "placeholder" }, "No preview yet. It is rendered once every clip of this scene is built."),
    ))),
  );
}

function finalSection(run) {
  const checks = run.final_checks;
  return el("section", { class: "sec" }, wrap(
    head("Final video", run.final_checked ? "2560×1440, as delivered and checked." : run.final_video ? "As delivered." : null),
    el("div", { class: run.final_video ? "final" : null },
      run.final_video
        ? el("video", { src: run.final_video, controls: true, preload: "metadata", "aria-label": `Final video: ${run.summary.topic}` })
        : el("p", { class: "placeholder" }, "No final video yet. It is rendered after every scene is approved."),
      run.final_video && el("div", { class: "card" },
        el("h4", {}, "Media checks"),
        checks.length
          ? el("ul", { class: "checks" }, checks.map((check) => el("li", {},
              el("span", { class: `sev${check.severity === "ERROR" ? " sev--error" : ""}` }, check.severity === "ERROR" ? "Error" : "Warning"),
              el("span", {}, `${check.code.replaceAll("_", " ").toLowerCase()}: ${check.message}`),
            )))
          : el("p", { class: "note" }, run.final_checked ? "Every check passed." : "No media checks were recorded for this video."),
      ),
    ),
  ));
}

function changeForm(run) {
  const id = run.summary.id;
  const targets = [
    ["outline", "The outline"],
    ["script", "The script"],
    ["plan", "All scene plans"],
    ...run.scenes.flatMap((scene) => [
      [scene.scene_id, `Scene ${scene.scene_id}: ${scene.title}`],
      ...scene.clips.map((clip) => [clip.clip_id, `Clip ${clip.clip_id}: ${clip.objective}`]),
    ]),
    ["final", "The final video"],
  ];
  const option = ([value, label]) => el("option", { value }, label);
  const status_ = el("p", { class: "message", role: "status" });
  const form = el("form", { class: "form", id: "ask" },
    el("label", { for: "ask-target" }, "What should change"),
    el("select", { id: "ask-target", name: "target" }, targets.map(option)),
    el("label", { for: "ask-kind" }, "Kind of change"),
    el("select", { id: "ask-kind", name: "kind" }, KINDS.map(option)),
    el("label", { for: "ask-text" }, "Describe the change"),
    el("textarea", { id: "ask-text", name: "text", rows: "4", required: true, maxlength: "4000" }),
    el("input", { type: "hidden", name: "checkpoint", value: "" }),
    el("div", { class: "row" }, el("button", { class: "btn", type: "submit" }, "Record change request")),
    status_,
  );
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const button = form.querySelector("button");
    button.disabled = true;
    try {
      const request = await send(`/api/runs/${encodeURIComponent(id)}/requests`, {
        target: data.get("target"),
        kind: data.get("kind"),
        text: String(data.get("text")).trim(),
        checkpoint: data.get("checkpoint") || null,
      });
      await refresh(id, `Change request ${request.id} recorded. The run's session applies it at its next step.`);
    } catch (error) {
      button.disabled = false;
      message(status_, error.message, true);
    }
  });
  return form;
}

function resolveButtons(run, request) {
  const status_ = el("span", { class: "message", role: "status" });
  const resolve = (value, label) => {
    const button = el("button", { class: "btn btn--ghost btn--sm", type: "button" }, label);
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        await send(`/api/runs/${encodeURIComponent(run.summary.id)}/requests/${encodeURIComponent(request.id)}`, { status: value });
        await refresh(run.summary.id, `${request.id} ${value === "applied" ? "marked applied" : "declined"}.`);
      } catch (error) {
        button.disabled = false;
        message(status_, error.message, true);
      }
    });
    return button;
  };
  return el("div", { class: "row" }, resolve("applied", "Mark applied"), resolve("declined", "Decline"), status_);
}

function ledgerSection(run) {
  const requests = run.requests.length
    ? el("ul", {}, run.requests.map((request) => el("li", {},
        el("span", {}, request.text),
        el("span", { class: "meta" }, `${request.id}, ${request.kind} on ${request.target}: ${request.status}${request.note ? ` (${request.note})` : ""}`),
        request.status === "open" && resolveButtons(run, request),
      )))
    : el("p", { class: "empty" }, "No change requests.");
  const decisions = run.decisions.length
    ? el("ul", {}, run.decisions.map((decision) => el("li", {},
        el("span", {}, `${decision.checkpoint}: ${decision.decision.replaceAll("_", " ")}${decision.forced ? " (accepted with open issues)" : ""}`),
        el("span", { class: "meta" }, decision.decided_at.replace("T", " ")),
        decision.notes && el("span", {}, decision.notes),
      )))
    : el("p", { class: "empty" }, "No decisions yet.");
  return section("", head("Your changes and decisions", "Ask for a change to any stage, scene or clip. The run's session applies it and marks it done."),
    el("div", { class: "ledger" },
      el("div", { class: "card" }, el("h4", {}, "Ask for a change"), changeForm(run)),
      el("div", { class: "card" },
        el("h4", {}, "Change requests"), requests,
        el("h4", { class: "spaced" }, "Checkpoint decisions"), decisions,
      ),
    ),
  );
}

async function runPage(id, quiet = false) {
  if (!quiet) loading("the run");
  const run = await load(`/api/runs/${encodeURIComponent(id)}`);
  const facts = [run.approach && `${run.approach} approach`, run.minutes && `${run.minutes} min`, `started ${run.summary.created}`].filter(Boolean);
  const hero = el("section", { class: "hero hero--run" }, wrap(
    el("a", { class: "back", href: "#/" }, "All runs"),
    el("h1", {}, run.summary.topic),
    el("p", { class: "lead" }, facts.join(", ")),
    run.objectives.length > 0 && el("ul", { class: "objectives" }, run.objectives.map((objective) => el("li", {}, objective))),
    !run.problem && counts(run),
    !run.problem && stageStrip(run),
  ));
  if (run.problem) {
    show(hero, section("", el("p", { class: "card notice" }, withCode(run.problem))), finalSection(run));
    return;
  }
  const live = el("p", { class: "message live", role: "status" }, notice);
  notice = "";
  show(hero, live.textContent ? section("", live) : null, await consoleSection(run), awaitingSection(run), nextSection(run),
    scenesSection(run.scenes), finalSection(run), ledgerSection(run));
}

async function route() {
  if (location.hash === "#/signin") {
    account = null;
    renderAccount();
    return signInPage().catch(failure);
  }
  if (!account) {
    const session = await load("/api/session").catch(() => ({ signed_in: false }));
    if (!session.signed_in) {
      location.hash = "#/signin";
      return;
    }
    account = session.account;
  }
  renderAccount();
  const match = location.hash.match(/^#\/runs\/(.+)$/);
  document.querySelectorAll(".nav__links a").forEach((link) => link.toggleAttribute("aria-current", !match));
  return (match ? runPage(decodeURIComponent(match[1])) : runsPage()).catch(failure);
}

window.addEventListener("hashchange", route);
route();
