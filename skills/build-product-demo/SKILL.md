---
name: build-product-demo
description: Plan, produce, or diagnose evidence-backed product demo videos and screen-recorded promotional walkthroughs. Use when the user asks to make a product demo, launch video, feature showcase, app walkthrough, demo reel, or polished recording; wants every important capability shown without a slow feature tour; asks to remove dead time or fix narration-to-action pacing; or needs a repeatable script, capture plan, and verified final media. Do not use for fictional commercials with no real product proof, general-purpose video editing, or documentation-only tutorials that do not need a promotional narrative.
---

# Build Product Demo

Turn verified product behavior into a compact proof story. Treat the final media
as an executable claim about the product, not as a decorated feature list.

## Choose the mode

- **Plan**: inspect the product and produce the brief, evidence inventory,
  feature coverage, director treatment, script, and beat plan.
- **Produce**: complete the plan, create deterministic setup and capture
  tooling, record, edit, and verify the final media.
- **Diagnose**: inspect an existing demo, identify the first broken layer, and
  revise the smallest responsible artifact. Check truth, story, visible state
  change, attention, narration/action alignment, capture, then encoding.

If the user asks to “make” or “finish” the demo, default to Produce. Do not stop
at a script while safe, in-scope production work remains.

## Establish the boundary

1. Resolve the exact product repository, revision, runtime, audience, channel,
   target duration, aspect ratio, language, available assets, and publishing
   scope. Inspect before guessing.
2. Read repository instructions and existing demos, screenshots, tests,
   fixtures, launch scripts, and marketing claims. Search before adding a new
   recorder or seed path.
3. Separate immutable product facts, creative choices, and missing production
   facts. Do not turn an unknown into a visual claim.
4. Choose one audience doubt and one proof proposition. Complete:

   `The audience doubts whether [product claim]. The demo proves [outcome] by showing [observable change].`

5. Define the opening and landing state. Reject a concept whose product or
   audience state is materially unchanged at the end.

Read [directing.md](references/directing.md) before selecting features or
writing beats. Read [production.md](references/production.md) before recording,
generating narration, or using deterministic fixtures.

## Build the evidence inventory

Classify every candidate claim:

| Level | Evidence | Demo use |
|---|---|---|
| E1 | Fresh live execution with retained output | May be shown as working |
| E2 | Current code plus focused passing test or fixture replay | May support a bounded claim; disclose fixture use |
| E3 | Current documentation or marketing copy only | Treat as a lead; verify before showing as working |
| E4 | Plan, issue, mockup, or unfinished path | Exclude or label explicitly as planned |

Create `feature-coverage.md` and rank each capability as:

- **core proof**: complete cause → action → result;
- **differentiator**: memorable evidence supporting the proposition;
- **supporting evidence**: fast proof that reduces doubt;
- **exception entry**: show a truthful state or recovery entry without
  deliberately damaging the product;
- **excluded**: unfinished, redundant, unverifiable, visually unreadable, or
  outside the audience decision.

Do not modify product behavior merely to make the demo pass unless the user
also asked for that product change.

## Direct the proof story

Write a compact treatment with:

```text
Audience doubt:
Proof proposition:
Opening state:
Turning proof:
Landing state:
Point of view:
Information strategy:
Visual progression:
Sound strategy:
Truth boundary:
Production simplification rule:
```

Lead with the strongest result when it is legible without setup, then return to
a credible starting state. Organize chapters by user outcome or proof question,
not by toolbar location. Require each chapter to leave visible accumulated
state or decisive new knowledge.

Write one beat for each meaningful tactic, product action, reveal, consequence,
or attention shift. A click is not a beat unless it changes the proof. Pair
narration about value or consequence with an observable action; do not read the
interface aloud.

Save the plan as `beat-plan.json` using
[artifact-contract.md](references/artifact-contract.md), then run:

```bash
python3 <skill-dir>/scripts/validate_demo_plan.py <demo-dir>/beat-plan.json
```

Fix plan failures before recording. Do not hide gaps in post-production.

## Prepare and capture

1. Build a disposable, repeatable starting state. Preserve user data and
   existing recordings.
2. Prefer repository-native APIs, scripts, fixtures, and automation over manual
   UI control. Use a browser or desktop controller only when the product proof
   genuinely depends on that surface and no lower-level route can execute it.
3. Use deterministic data only to stabilize inputs or external dependencies.
   Keep the real product path active and record the boundary in the plan.
4. Run a fast, silent rehearsal. Confirm selectors, commands, product results,
   duration, and exit states before paying for narration or a full recording.
5. Audition narration with the actual language and script. Voice labels and
   locale names are not evidence of accent, naturalness, or timing.
6. Record clean picture, UI/action sound, narration, and music as separable
   elements when practical. Retain raw evidence and logs.
7. If a production path fails, report the failure and repair that path. Do not
   silently substitute screenshots, fake progress, or a different capability.

## Edit and diagnose pacing

For every cut, finish:

`Cut from [state/action] to [new state/action] because the audience now needs to [learn/feel/locate/compare/anticipate].`

Shorter is not automatically faster. Remove unexplained waiting, duplicated
information, cursor travel with no consequence, and narration that finishes
before the corresponding action begins. Preserve enough time to orient, see the
action, register the result, and anticipate the next beat.

When diagnosing “slow” or “stuck” pacing, locate the first mismatch:

1. no new product or audience state;
2. action begins too late after narration;
3. action finishes but the result is not framed;
4. capture contains real processing with no readable status;
5. edit holds a redundant image;
6. audio or encoding creates apparent freezes.

Repair the mismatch instead of globally speeding up the video.

## Verify and package

Run the plan validator again after the edit reflects any timing changes. Probe
the final video with:

```bash
python3 <skill-dir>/scripts/probe_demo_media.py <final-video> \
  --expect-width <width> --expect-height <height> --require-audio
```

Also inspect the full video or a contact sheet for frozen frames, clipped UI,
unreadable type, secret leakage, missing chapters, broken focus, abrupt audio,
and claims whose evidence is not visible. A playable file with valid codecs is
necessary but not sufficient.

Deliver the files defined in [artifact-contract.md](references/artifact-contract.md)
and state which claims used live execution, deterministic fixtures, or
compositing.

## Autonomy boundary

- Perform read-only inspection, local planning, disposable seeding, local
  capture, editing, and validation directly when requested.
- Ask before using credentials not already approved for the task, incurring
  paid API usage, changing production data, deploying, publishing externally,
  deleting or overwriting existing media, or changing product code outside the
  requested scope.
- Remote commit, push, PR, or publication requires explicit approval unless the
  current request already grants that exact action.
- Never record private memories, tokens, account data, notifications, unrelated
  windows, or user-identifying paths when a sanitized fixture can prove the
  same capability.

## Done when

- The exact product revision and truth boundary are recorded.
- One audience doubt is answered by a visible opening-to-landing change.
- Core claims have E1 or bounded E2 evidence; exclusions are explicit.
- The beat plan passes `validate_demo_plan.py` with no unexplained gap, overlap,
  idle interval, or missing state change.
- A fresh rehearsal proves the complete path before the final capture.
- The final media passes `probe_demo_media.py` and a visual/audio review.
- The delivery package includes the final artifact, plan, script, evidence,
  and verification result appropriate to the selected mode.

## Gotchas

- A feature inventory is source material, not a script.
- A mock that bypasses the product path cannot prove that path.
- A deterministic provider is acceptable only when the surrounding real state,
  command, task, persistence, and result paths still execute and the boundary
  is disclosed.
- Evidence from one product surface does not prove another. A record that is
  searchable, stored, or visible in diagnostics may still be ineligible for
  automatic injection, export, playback, or another claimed path. Exercise the
  exact surface named in the proposition.
- A title card, cursor highlight, zoom, or music cue cannot repair an undefined
  product result.
- “No dead time” does not mean compressing every pause. A motivated hold lets
  the audience read a consequential result; an unmotivated hold is a defect.
- Do not choose a voice from its advertised nationality or name. Audition the
  exact text and reject accent, cadence, or pronunciation mismatch.
- Do not claim completion from a plan, a raw recording, or successful encoding
  alone.

## Feedback loop

Representative prompts live in [evals/evals.json](evals/evals.json). When a
real run exposes a repeated false-success signal, pacing gap, truth-boundary
mistake, or missing verification, patch the smallest responsible instruction,
reference, validator, or eval before treating the workflow as mature.
