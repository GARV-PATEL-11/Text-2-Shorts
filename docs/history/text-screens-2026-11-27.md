# Faraday — how the new wording looks (2026-11-27)

Screenshots of the website after adding every proposal in `text-references-2026-11-27.txt`. Taken on a demo server (port 8790) with five demo runs built by the test helpers, never your real runs. The demo videos are placeholder files, so they don't play.

**How the shuffle works:** wherever a screen names a *moment*, one of that moment's lines is chosen at random once per visit (`useLine` / `usePick` in `components/ui/Said.tsx`), so a reload can show a different one. The plain instruction next to it never changes. Every line a moment can show is listed in [All moments and their lines](#all-moments-and-their-lines) below. Equal-meaning titles (e.g. loading messages) shuffle the same way: see [All title variants](#all-title-variants).

Every run page also shows the **readyToBegin** line in the Claude panel (“Ready to Begin”).

## Sign In

The welcome quote above the Continue button; the session now says 24 hours.

Shuffles here: [welcome](#moment-welcome)

![Sign In](text-screens-2026-11-27/01-signin.png)

## Sign In, server not answering

Plain cause first (`text-2-shorts serve` shown as code), then a server-down line.

Shuffles here: [welcome](#moment-welcome), [serverSilent](#moment-serversilent)

![Sign In, server not answering](text-screens-2026-11-27/02-signin-server-down.png)

## Home: three visits, three picks

Same page loaded three times: the lead quote, the usage card's quote and the closing quote each shuffle once per visit.

Shuffles here: [homeLead](#moment-homelead), [notYet](#moment-notyet), [closing](#moment-closing)

![Home: three visits, three picks](text-screens-2026-11-27/03-home-a.png)

![Home: three visits, three picks](text-screens-2026-11-27/04-home-b.png)

![Home: three visits, three picks](text-screens-2026-11-27/32-home-pick-mid.png)

## Home, runs failed to load

Plain error with Try Again, plus a calm line.

Shuffles here: [loadFailed](#moment-loadfailed)

![Home, runs failed to load](text-screens-2026-11-27/05-home-runs-failed.png)

## Home, usage failed to load

Plain error with Try Again, plus a calm line.

Shuffles here: [loadFailed](#moment-loadfailed)

![Home, usage failed to load](text-screens-2026-11-27/06-home-usage-failed.png)

## Home, usage at 87%

The usage card with a window near its limit.

![Home, usage at 87%](text-screens-2026-11-27/33-usage-high-home.png)

## Ongoing Runs

Nav label is now “Ongoing Runs”; status pills use the site's words.

![Ongoing Runs](text-screens-2026-11-27/07-ongoing.png)

## Ongoing Runs, search finds nothing

Shuffled empty title plus a quote.

Shuffles here: [noMatches](#moment-nomatches)

![Ongoing Runs, search finds nothing](text-screens-2026-11-27/08-ongoing-no-match.png)

## Previous Runs

![Previous Runs](text-screens-2026-11-27/09-previous.png)

## Previous Runs, empty

Empty state with a Start a Run button.

![Previous Runs, empty](text-screens-2026-11-27/10-previous-empty.png)

## Start a Run

The first step asks for a name; it can be skipped.

![Start a Run](text-screens-2026-11-27/11-new-run.png)

## Start a Run, draft not found

“Draft Not Found: Starting a New One” plus a not-found line.

Shuffles here: [notFound](#moment-notfound), [chooseLook](#moment-chooselook)

![Start a Run, draft not found](text-screens-2026-11-27/12-new-run-unknown-draft.png)

## Run page, Requirements → Topics (not written yet)

Shuffles here: [notYet](#moment-notyet), [readyToBegin](#moment-readytobegin)

![Run page, Requirements → Topics (not written yet)](text-screens-2026-11-27/13-run-requirements-topics.png)

## Run page, Outline (not written yet)

Shuffles here: [writingScript](#moment-writingscript), [readyToBegin](#moment-readytobegin)

![Run page, Outline (not written yet)](text-screens-2026-11-27/14-run-outline-not-yet.png)

## Run page, Template

Shuffles here: [chooseLook](#moment-chooselook)

![Run page, Template](text-screens-2026-11-27/15-run-template.png)

## Template → Build Your Own

Element names and notes, without developer words.

![Template → Build Your Own](text-screens-2026-11-27/31-run-template-build-your-own.png)

## Run page, Script

The decision bar (no more “Scenes Is Waiting”).

Shuffles here: [readyToBegin](#moment-readytobegin)

![Run page, Script](text-screens-2026-11-27/16-run-script.png)

## Script checkpoint, nothing blocking

Button is now “Approve and Continue”.

![Script checkpoint, nothing blocking](text-screens-2026-11-27/17-run-script-checkpoint.png)

## Script checkpoint with an open problem

The problem in plain words: “Accuracy problem in Scene 2: it reflects sunlight” (Claude still gets the original “accuracy ERROR in s02: …”).

![Script checkpoint with an open problem](text-screens-2026-11-27/30-run-checkpoint-open-problems.png)

## Claude's Next Step, in plain words

A person's sentence instead of “CP1: show the scene table…”.

![Claude's Next Step, in plain words](text-screens-2026-11-27/35-run-next-step-plain.png)

## Script → Critique (not made yet)

Shuffles here: [critiquing](#moment-critiquing)

![Script → Critique (not made yet)](text-screens-2026-11-27/18-run-script-critique.png)

## Scene Plans → Critiques

![Scene Plans → Critiques](text-screens-2026-11-27/19-run-plan-critiques.png)

## Scenes, clips still building

Shuffles here: [buildingClips](#moment-buildingclips)

![Scenes, clips still building](text-screens-2026-11-27/20-run-scenes.png)

## Claude's Next Step at 87% usage

“Your Claude usage is at 87% of the 5-hour limit. It resets Friday at 16:52. The next step is: … Continue now, or wait?”

![Claude's Next Step at 87% usage](text-screens-2026-11-27/34-usage-high-next-step.png)

## Final Video (demo file cannot play)

A quote above the video, and a calm line under “Could Not Play This Video”.

Shuffles here: [complete](#moment-complete), [loadFailed](#moment-loadfailed)

![Final Video (demo file cannot play)](text-screens-2026-11-27/21-run-final-video.png)

## Final Video → Media Checks, all passed

Shuffles here: [checksPassed](#moment-checkspassed)

![Final Video → Media Checks, all passed](text-screens-2026-11-27/22-run-final-checks-passed.png)

## Final Video → Media Checks, one error

Check codes in Title Case.

![Final Video → Media Checks, one error](text-screens-2026-11-27/23-run-final-checks-error.png)

## Reshuffle

Shuffles here: [reshuffling](#moment-reshuffling)

![Reshuffle](text-screens-2026-11-27/24-run-reshuffle.png)

## Console, no messages yet

Shuffles here: [consoleIdle](#moment-consoleidle)

![Console, no messages yet](text-screens-2026-11-27/25-console-empty.png)

## Request a Change

![Request a Change](text-screens-2026-11-27/26-change-modal.png)

## Your Profile

![Your Profile](text-screens-2026-11-27/27-profile.png)

## A run that does not exist

Shuffles here: [notFound](#moment-notfound)

![A run that does not exist](text-screens-2026-11-27/28-run-not-found.png)

## A run that failed to load

Shuffles here: [loadFailed](#moment-loadfailed)

![A run that failed to load](text-screens-2026-11-27/29-run-load-failed.png)

## Command line

Human-facing lines only (`serve`, `new`, `final`, `--help`); one is printed at random. Parsed commands (`approve`, `status`, `next`, …) print nothing extra.

```
serve:
  Curiosity, Illustrated.
  "I have arranged certain apparatus, the use of which you will see as I go on." — Michael Faraday
  "But first let us see that our instrument is in order." — Michael Faraday
  "Hello and, again, welcome to the Aperture Science computer-aided enrichment center." — Portal
new:
  "Make it so!" — Star Trek: The Next Generation
  "let us make an experiment or two." — Michael Faraday
final:
  "Work, Finish, Publish." — Michael Faraday
  "Yes! We have proved it by combustion" — Michael Faraday
  "We're made of star-stuff. We are a way for the cosmos to know itself." — Carl Sagan
help:
  Curiosity, Illustrated.
  "What I cannot create, I do not understand." — Richard Feynman
  "I am no poet, but if you think for yourselves, as I proceed, the facts will form a poem in your minds." — Michael Faraday
```

## All moments and their lines

<a id="moment-welcome"></a>
**welcome**

- “There is no better, there is no more open door by which you can enter into the study of natural philosophy, than by considering the physical phenomena of a candle.” — Michael Faraday
- “Hello and, again, welcome to the Aperture Science computer-aided enrichment center.” — Portal

<a id="moment-homelead"></a>
**homeLead**

- “What is the cause? Why does it occur?” — Michael Faraday
- “I am no poet, but if you think for yourselves, as I proceed, the facts will form a poem in your minds.” — Michael Faraday
- “I am among those who think that science has great beauty.” — Marie Curie
- “What I cannot create, I do not understand.” — Richard Feynman

<a id="moment-nothinginprogress"></a>
**nothingInProgress**

- “Nothing is too wonderful to be true, if it be consistent with the laws of nature” — Michael Faraday
- “Do it all, everything!” — Minecraft
- “What I cannot create, I do not understand.” — Richard Feynman

<a id="moment-noruns"></a>
**noRuns**

- “It's dangerous to go alone! Take this.” — The Legend of Zelda
- “This is only the beginning.” — Dune
- “It's a secret to everybody.” — The Legend of Zelda
- “We will light one or two, and set them at work in the performance of their proper functions.” — Michael Faraday

<a id="moment-chooselook"></a>
**chooseLook**

- “See how beautifully these are coloured” — Michael Faraday
- “Now, let us look a little at the form of the flame as you see it under the glass shade.” — Michael Faraday
- “It is not the best looking thing, but the best acting thing, which is the most advantageous to us.” — Michael Faraday
- “This good-looking candle is a bad burning one.” — Michael Faraday

<a id="moment-question"></a>
**question**

- “We come here to be philosophers” — Michael Faraday
- “Science isn't about why, it's about why not.” — Portal 2
- “What I cannot create, I do not understand.” — Richard Feynman
- “Now, why is this?” — Michael Faraday

<a id="moment-audience"></a>
**audience**

- “I claim the privilege of speaking to juveniles as a juvenile myself.” — Michael Faraday

<a id="moment-review"></a>
**review**

- “let us make an experiment or two.” — Michael Faraday
- “All we have to decide is what to do with the time that is given to us.” — The Lord of the Rings
- “The first principle is that you must not fool yourself — and you are the easiest person to fool.” — Richard Feynman
- “You may make these experiments yourselves.” — Michael Faraday

<a id="moment-readytobegin"></a>
**readyToBegin**

- “This is only the beginning.” — Dune
- “let us make an experiment or two.” — Michael Faraday
- “Engage!” — Star Trek: The Next Generation
- “Make it so!” — Star Trek: The Next Generation

<a id="moment-openingrun"></a>
**openingRun**

- “We have now some very interesting points to study.” — Michael Faraday
- “Hey, you. You're finally awake.” — The Elder Scrolls V: Skyrim
- “I shall shew you of what it is composed, and where it gets its elements from.” — Michael Faraday
- “Now, you will begin to understand what I am about to say.” — Michael Faraday

<a id="moment-loading"></a>
**loading**

- “This waiting is a curious and wonderful thing.” — Michael Faraday
- “It is curious to see how different substances wait” — Michael Faraday
- Vectors included! *(plain)*
- “But first let us see that our instrument is in order.” — Michael Faraday
- “We will light one or two, and set them at work in the performance of their proper functions.” — Michael Faraday
- “Any computer is a laptop if you're brave enough!” — Minecraft

<a id="moment-processing"></a>
**processing**

- “You solve one problem... and you solve the next one... and then the next.” — The Martian
- “I was taught that the way of progress was neither swift nor easy.” — Marie Curie
- “We will light one or two, and set them at work in the performance of their proper functions.” — Michael Faraday
- “Whoa, this is heavy.” — Back to the Future

<a id="moment-pending"></a>
**pending**

- “It is curious to see how different substances wait” — Michael Faraday
- Ask why. Then ask again! *(plain)*
- “We shall presently examine that” — Michael Faraday
- “Now, why is this?” — Michael Faraday

<a id="moment-rendering"></a>
**rendering**

- “This waiting is a curious and wonderful thing.” — Michael Faraday
- Every frame is code! *(plain)*
- “We may say most aptly that the Analytical Engine weaves algebraical patterns just as the Jacquard-loom weaves flowers and leaves.” — Ada Lovelace
- “Now, look at that. Is not that a very pretty experiment?” — Michael Faraday
- “It is a curious thing to see how wax candles are made.” — Michael Faraday
- “Whoa, this is heavy.” — Back to the Future

<a id="moment-asks"></a>
**asks**

- “Help me, Obi-Wan Kenobi. You're my only hope.” — Star Wars
- “You have asked me several times, and I am very glad you have” — Michael Faraday

<a id="moment-nothingtodecide"></a>
**nothingToDecide**

- “Wake me, when you need me.” — Halo 3

<a id="moment-approved"></a>
**approved**

- “Yes! We have proved it by combustion” — Michael Faraday
- “You're doing very well.” — Portal
- “Work, Finish, Publish.” — Michael Faraday
- “We get to the peak together, or we don't get there at all.” — Hidden Figures

<a id="moment-complete"></a>
**complete**

- “We're made of star-stuff. We are a way for the cosmos to know itself.” — Carl Sagan
- “Even the smallest person can change the course of the future.” — The Lord of the Rings
- “that you may, like it, shine as lights to those about you” — Michael Faraday
- “Work, Finish, Publish.” — Michael Faraday
- “We get to the peak together, or we don't get there at all.” — Hidden Figures
- “Every new set of discoveries raises a host of questions which we were never before wise enough even to ask.” — Carl Sagan
- “All my life through, the new sights of Nature made me rejoice like a child.” — Marie Curie
- “The cinema is truth twenty-four times per second.” — Jean-Luc Godard
- “It is the nature of science that answers automatically pose new and more subtle questions.” — Isaac Asimov

<a id="moment-nochanges"></a>
**noChanges**

- “Mostly harmless” — The Hitchhiker's Guide to the Galaxy
- “I will shew you; it is very simple, and easily done.” — Michael Faraday

<a id="moment-failed"></a>
**failed**

- “Houston, we have a problem.” — Apollo 13
- “But still try, for who knows what is possible...” — Michael Faraday
- “Data, things are only impossible until they're not.” — Star Trek: The Next Generation
- “I don't care what anything was designed to do. I care about what it can do.” — Apollo 13
- “Let's work the problem, people. Let's not make things any worse by guessing.” — Apollo 13
- “I like this player. It played well. It did not give up.” — Minecraft

<a id="moment-renderfailed"></a>
**renderFailed**

- “Still examine it by a few experiments.” — Michael Faraday
- “Data, things are only impossible until they're not.” — Star Trek: The Next Generation
- “Houston, we have a problem.” — Apollo 13

<a id="moment-offline"></a>
**offline**

- “DON'T PANIC” — The Hitchhiker's Guide to the Galaxy
- “Have you tried turning it off and on again?” — The IT Crowd

<a id="moment-restricted"></a>
**restricted**

- “I'm sorry, Dave. I'm afraid I can't do that.” — 2001: A Space Odyssey
- “You shall not pass!” — The Lord of the Rings

<a id="moment-lost"></a>
**lost**

- “This is not the web page you are looking for” — GitHub
- “These aren't the droids you're looking for.” — Star Wars

<a id="moment-closing"></a>
**closing**

- “There is no better, there is no more open door by which you can enter into the study of natural philosophy, than by considering the physical phenomena of a candle.” — Michael Faraday
- “We're made of star-stuff. We are a way for the cosmos to know itself.” — Carl Sagan
- “that you may, like it, shine as lights to those about you” — Michael Faraday
- “If I have seen further it is by standing on ye sholders of Giants.” — Isaac Newton
- “We may say most aptly that the Analytical Engine weaves algebraical patterns just as the Jacquard-loom weaves flowers and leaves.” — Ada Lovelace

<a id="moment-loadfailed"></a>
**loadFailed**

- “But still try, for who knows what is possible...” — Michael Faraday
- “Data, things are only impossible until they're not.” — Star Trek: The Next Generation
- “I like this player. It played well. It did not give up.” — Minecraft
- “Well, we will examine it.” — Michael Faraday
- “Still examine it by a few experiments.” — Michael Faraday

<a id="moment-saved"></a>
**saved**

- “Yes! We have proved it by combustion” — Michael Faraday
- “Once again, excellent work.” — Portal
- “Thank you for helping us help you help us all.” — Portal

<a id="moment-nomatches"></a>
**noMatches**

- “These aren't the droids you're looking for.” — Star Wars
- “This is not the web page you are looking for” — GitHub
- “It's a secret to everybody.” — The Legend of Zelda

<a id="moment-notfound"></a>
**notFound**

- “This is not the web page you are looking for” — GitHub
- “These aren't the droids you're looking for.” — Star Wars
- “DON'T PANIC” — The Hitchhiker's Guide to the Galaxy

<a id="moment-startingrun"></a>
**startingRun**

- “But first let us see that our instrument is in order.” — Michael Faraday
- “Make it so!” — Star Trek: The Next Generation
- “Rise and shine, Mr. Freeman, rise and … shine.” — Half-Life 2
- “Roads? Where we're going, we don't need roads.” — Back to the Future

<a id="moment-checking"></a>
**checking**

- “But first let us see that our instrument is in order.” — Michael Faraday
- “We will light one or two, and set them at work in the performance of their proper functions.” — Michael Faraday
- “This waiting is a curious and wonderful thing.” — Michael Faraday

<a id="moment-asking"></a>
**asking**

- “Now, why is this?” — Michael Faraday
- “Well, we will examine it.” — Michael Faraday
- “Let us see whether that which goes out is steam or not.” — Michael Faraday

<a id="moment-notyet"></a>
**notYet**

- “We shall presently examine that” — Michael Faraday
- “It's a secret to everybody.” — The Legend of Zelda
- “Here is one only half-finished.” — Michael Faraday
- “I shall shew you of what it is composed, and where it gets its elements from.” — Michael Faraday
- “I attempt to pour a little of this gas into that glass; I wonder whether any has gone in or not.” — Michael Faraday

<a id="moment-draft"></a>
**draft**

- “Here is one only half-finished.” — Michael Faraday

<a id="moment-serversilent"></a>
**serverSilent**

- “DON'T PANIC” — The Hitchhiker's Guide to the Galaxy
- “Have you tried turning it off and on again?” — The IT Crowd

<a id="moment-signinsteps"></a>
**signInSteps**

- “Make it so!” — Star Trek: The Next Generation
- “You may make these experiments yourselves.” — Michael Faraday

<a id="moment-elapsed"></a>
**elapsed**

- “Time is an illusion. Lunchtime doubly so.” — Douglas Adams

<a id="moment-stalepage"></a>
**stalePage**

- “I cannot tell by the appearance, but I can in this way” — Michael Faraday
- “Still examine it by a few experiments.” — Michael Faraday

<a id="moment-changerecorded"></a>
**changeRecorded**

- “Make it so!” — Star Trek: The Next Generation
- “Engage!” — Star Trek: The Next Generation
- “We will light one or two, and set them at work in the performance of their proper functions.” — Michael Faraday

<a id="moment-claudefinished"></a>
**claudeFinished**

- Turn finished. *(plain)*
- Claude has finished. Over to you. *(plain)*
- Claude is waiting for you. *(plain)*
- “I have another experiment here, which I think will explain to you more about it.” — Michael Faraday
- “I will shew you; it is very simple, and easily done.” — Michael Faraday
- “Now you will see the power.” — Michael Faraday
- “Make it so!” — Star Trek: The Next Generation

<a id="moment-consoleidle"></a>
**consoleIdle**

- “You have asked me several times, and I am very glad you have” — Michael Faraday
- “I have far more confidence in the one man who works mentally and bodily at a matter than in the six who merely talk about it” — Michael Faraday
- “Engage!” — Star Trek: The Next Generation

<a id="moment-checkspassed"></a>
**checksPassed**

- “There is, you see, pure air down to the bottom; the jar is full of it.” — Michael Faraday
- “Very very good.” — Portal
- “The Fact Sphere is not defective. Its facts are wholly accurate and very interesting.” — Portal 2
- “I put that spark into the jar, it will tell you whether we have oxygen here or not.” — Michael Faraday

<a id="moment-writingscript"></a>
**writingScript**

- “Drama is life with the dull bits cut out.” — Alfred Hitchcock
- “Omit needless words.” — The Elements of Style
- “Truth is ever to be found in simplicity, and not in the multiplicity and confusion of things.” — Isaac Newton
- “I am no poet, but if you think for yourselves, as I proceed, the facts will form a poem in your minds.” — Michael Faraday

<a id="moment-critiquing"></a>
**critiquing**

- “The first principle is that you must not fool yourself — and you are the easiest person to fool.” — Richard Feynman
- “Nature is our kindest friend and best critic in experimental science if we only allow her intimations to fall unbiassed on our minds.” — Michael Faraday
- “The Fact Sphere is not defective. Its facts are wholly accurate and very interesting.” — Portal 2
- “Still examine it by a few experiments.” — Michael Faraday

<a id="moment-planningscenes"></a>
**planningScenes**

- “I shall shew you of what it is composed, and where it gets its elements from.” — Michael Faraday
- “In order that you may understand that, let me shew you a very pretty, but very common-place experiment.” — Michael Faraday
- “Now, you will begin to understand what I am about to say.” — Michael Faraday
- “Drama is life with the dull bits cut out.” — Alfred Hitchcock

<a id="moment-buildingclips"></a>
**buildingClips**

- “Here is one only half-finished.” — Michael Faraday
- “It is wonderful how it accumulates when you come to larger volumes.” — Michael Faraday
- “Whoa, this is heavy.” — Back to the Future
- “I was taught that the way of progress was neither swift nor easy.” — Marie Curie

<a id="moment-syncing"></a>
**syncing**

- “Time is an illusion. Lunchtime doubly so.” — Douglas Adams
- “I put that spark into the jar, it will tell you whether we have oxygen here or not.” — Michael Faraday

<a id="moment-scenecode"></a>
**sceneCode**

- “We may say most aptly that the Analytical Engine weaves algebraical patterns just as the Jacquard-loom weaves flowers and leaves.” — Ada Lovelace
- “I was at first almost frightened when I saw such mathematical force made to bear upon the subject, and then wondered to see that the subject stood it so well.” — Michael Faraday

<a id="moment-reshuffling"></a>
**reshuffling**

- “I have coloured the fluid, that you may see the action better.” — Michael Faraday
- “What a beautifully coloured gas I have obtained in this way, shewing me the presence of the oxygen!” — Michael Faraday
- “I love fools' experiments. I am always making them.” — Charles Darwin
- “Innovating innovation!” — Minecraft

<a id="moment-recordingvoice"></a>
**recordingVoice**

- “Time is an illusion. Lunchtime doubly so.” — Douglas Adams
- “I was taught that the way of progress was neither swift nor easy.” — Marie Curie
- “I attempt to pour a little of this gas into that glass; I wonder whether any has gone in or not.” — Michael Faraday
- “I will shew you; it is very simple, and easily done.” — Michael Faraday

<a id="moment-usagehigh"></a>
**usageHigh**

- “This waiting is a curious and wonderful thing.” — Michael Faraday
- “It is curious to see how different substances wait” — Michael Faraday
- “A wizard is never late, Frodo Baggins. Nor is he early; he arrives precisely when he means to.” — The Lord of the Rings
- “I love deadlines. I love the whooshing noise they make as they go by.” — Douglas Adams
- “Light thinks it travels faster than anything but it is wrong.” — Terry Pratchett

<a id="moment-servererror"></a>
**serverError**

- Something went wrong on our side. Try again in a moment. *(plain)*
- “Houston, we have a problem.” — Apollo 13
- “But still try, for who knows what is possible...” — Michael Faraday
- “Experiment is the best test of such consistency.” — Michael Faraday

## All title variants

`frontend/src/config/titles.ts`

- **opening**: Opening Your Workspace… · Lighting the Candle… · Setting Up the Table… · Preparing the Demonstration Table… · Arranging the Apparatus…
- **openingText**: Checking Which Claude Account This Computer Uses · Checking Your Sign-In · Looking for Your Claude Account
- **signingIn**: Checking Your Sign-In… · Looking for Your Claude Account… · Checking This Computer…
- **loadingRuns**: Loading Your Runs · Gathering Your Runs · Laying Out Your Runs · Fetching Your Runs · Opening the Ledger
- **nothingInProgress**: Nothing in Progress · No Run Under Way · The Table Is Clear
- **loadingRun**: Loading This Run · Opening This Run · Bringing Up This Run
- **loadingUsage**: Loading Usage · Reading the Meters · Checking Your Limits
- **asking**: Asking Claude Code · Putting the Question to Claude Code
- **notChecked**: Not Checked Yet · Not Measured Yet
- **copying**: Checking This Computer, Then Copying the Run… · Copying the Run… · Making a Copy of the Run…
- **noMatches**: No Matches · Nothing Found · No Run Matches That
- **loadingTemplates**: Loading Templates · Laying Out the Templates · Setting Out the Templates · Opening the Template Shelf

`frontend/src/pages/run/titles.ts`

- **openingRun**: Opening the Run · Loading This Run · Opening Your Run · Setting Out the Run
- **decision**: Decision Needed: {step} · {step}: Waiting for Your Decision · Your Decision Is Needed on {step} · Waiting for You: {step}
- **noFinalVideo**: No Final Video Yet · Final Video Not Made Yet · Final Video: Not Made Yet
- **noFinalRendered**: No Final Video Yet · Final Video Not Made Yet · Final Video: Not Rendered Yet
- **stale**: Not Up to Date · This Page May Be Out of Date · Showing the Last Version Received
- **noDecision**: Nothing to Decide Yet · No Decision Due Yet · Not Ready for a Decision
- **noDecisionBody**: Claude Asks When This Stage Is Ready · Claude Will Ask You When This Stage Is Ready · Your Decision Is Asked For When This Stage Is Ready
- **loadingMessages**: Loading Claude's Messages · Opening the Conversation · Connecting
- **waitingForClaude**: Waiting for Claude · Claude Has Not Replied Yet
- **noReply**: No Reply · No Reply Yet
- **connecting**: Connecting · Connecting to Claude · Opening the Console
- **noMessages**: No Messages Yet · Nothing Said Yet · No Messages in This Run Yet
- **critiqueBody**: Critiqued When You Request a Change at Its Checkpoint · Critique Runs When You Request a Change at Its Checkpoint
- **objectivesUnset**: Not Set Yet: Claude Proposes Them With You · Not Set Yet: You and Claude Settle Them Together · Not Made Yet: Claude Proposes Them With You
- **loadingExecution**: Loading the Execution Plan for {scene} · Opening the Execution Plan of {scene} · Loading {scene}'s Execution Plan
- **loadingPlan**: Loading the Plan for {scene} · Opening the Plan of {scene} · Loading {scene}'s Plan
- **noPreview**: No Preview Yet · Preview Not Made Yet · Nothing to Preview Yet
- **previewSeed**: No Preview Yet · Preview Not Made Yet · Preview a Seed to See It
- **reshufflePreviewing**: Reshuffling, Then Rendering One Frame… · Reshuffling the Look, Then Rendering One Frame… · Drawing One Frame of the New Look…
- **recoloring**: Recoloring Every Built Clip… · Recoloring the Built Clips… · Recoloring Clip by Clip…
- **loadingOptions**: Loading Options · Loading Looks and Sounds · Gathering the Options
- **voiceSample**: Synthesizing a Few Seconds… · Making a Few Seconds of Voice… · Recording a Short Voice Sample… · Generating a Few Seconds of Voice…
- **renderingLook**: Rendering the Whole Look… · Rendering One Full-Size Frame… · Drawing the Whole Look…
- **nothingRendered**: Nothing Rendered Yet · Not Rendered Yet · Whole Look Not Rendered Yet
- **renderingOption**: Rendering in Your Look… · Rendering This Option… · Drawing This Option in Your Look…
