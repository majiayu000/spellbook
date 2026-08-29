# Product Demo Production

Use this reference before seeding data, recording product surfaces, generating
narration, or editing the final media.

## 1. Establish production truth

Record the exact repository, revision, executable or service version, runtime
configuration, and test data boundary. Classify every captured capability:

- **live**: the current product performs the action and produces the result;
- **deterministic**: a fixture or local provider stabilizes an input or external
  dependency while the real product path still runs;
- **composite**: multiple real captures are editorially combined;
- **title**: explanatory graphics that make no product-execution claim.

Do not label a bypass, static mockup, or manually edited result as live.

## 2. Use disposable state

- Prefer a temporary home, data directory, database, project, browser profile,
  or workspace.
- Seed only synthetic information. Do not record private memories, messages,
  credentials, filesystem history, notifications, or unrelated windows.
- Make setup rerunnable and explicit. Validate the seed before opening the
  recorder.
- Keep user worktrees and databases unchanged unless modification is expressly
  part of the request.
- Record cleanup instructions. Do not delete existing artifacts to make room.

## 3. Select the capture route

| Product surface | Preferred route |
|---|---|
| CLI or terminal | Repository script, VHS, asciinema, PTY capture, or direct command evidence |
| Browser-rendered app | Repository server plus Playwright or equivalent automation |
| Desktop-native app | App-owned automation or API first; bounded UI control only when required |
| API or service | Real request/response capture plus a legible presentation layer |
| Generated media | Preserve prompts, inputs, provider/model identity, outputs, and boundary frames |

Use the product's real interaction surface for the final proof. Lower-level
commands may prepare state or verify results, but should not replace a claimed
user-facing path.

## 4. Rehearse cheaply

Run a fast rehearsal without paid narration or full-duration holds. Verify:

- every command, selector, and endpoint resolves;
- the seeded state matches the opening frame;
- every beat produces the planned exit state;
- the exact claimed consumer surface receives the result; storage, search,
  indexing, preview, and final delivery are separate gates;
- external waits have a bounded timeout and a visible failure;
- no secret or unrelated user data enters the frame;
- the estimated duration fits the delivery target.

After two empty long-running polls, continue independent work and inspect later.
Do not build a production loop around blind repeated retries.

## 5. Record narration

- Write narration after visible action and timing are stable.
- Say value, consequence, contrast, or context; let the screen show mechanics.
- Generate short per-beat files so one change does not invalidate the full mix.
- Audition the exact language with representative technical terms and product
  names. Reject pronunciation, accent, cadence, and energy mismatch.
- Measure every clip. A beat must accommodate its narration or be rewritten;
  truncation and silent fallback are failures.
- Keep narration, action sound, ambience, and music separable until the mix.

Do not infer a voice's accent or naturalness from its display name, locale, or
marketing label.

## 6. Handle waits honestly

When a real operation is slow, choose one explicit treatment:

- show a meaningful progress state;
- compress elapsed time and label the compression;
- use a sound or visual bridge while state continues to change;
- cut to evidence produced during the wait;
- redesign the demonstration around a deterministic local dependency;
- keep a motivated hold because reading or consequence is the event.

Never leave narration finished over an unchanged screen without a recorded
reason. Never fake completion because the provider or product path failed.

## 7. Edit from causality

- Preserve cause before consequence.
- Enter a shot late enough to remove setup noise and early enough to orient.
- Leave after the result registers, not after an arbitrary duration.
- Use hard cuts for clear state changes; use a transition only when it expresses
  time, location, comparison, or chapter change.
- Keep product text legible at delivery resolution and normal playback speed.
- Use music to shape the whole progression, not to disguise static footage.

## 8. Verify the delivery

Check mechanically:

- container, video codec, audio codec, dimensions, frame rate, and duration;
- presence of the expected video and audio streams;
- exact output path and nonzero file size.

Check editorially:

- opening hook and landing are legible;
- every core proof appears and produces a visible result;
- no unplanned gap, freeze, blank frame, clipped UI, or abrupt narration exists;
- cursor, highlights, captions, and crops point to the intended evidence;
- disclosure matches live, deterministic, and composite footage;
- no secret, personal data, or unrelated application surface is visible.

Use a contact sheet or full playback review. A successful `ffprobe` is not a
substitute for watching the sequence.
