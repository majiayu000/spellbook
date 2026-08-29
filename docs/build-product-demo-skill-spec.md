# Build Product Demo Skill Spec

## Goal

Add a reusable `build-product-demo` workflow that turns verified product
behavior into a concise promotional demo plan, production package, and
validated media artifact. The first dogfood case is remem, but no remem-specific
commands or claims belong in the reusable workflow.

## Problem

Product demos often fail in predictable ways: they enumerate controls instead
of proving an outcome, narrate while the screen is idle, hide unstable or fake
paths, and declare completion without checking the final media. General video
advice does not tell an agent how to inspect a product, select truthful evidence,
design state-changing beats, produce a repeatable recording, and verify delivery.

## Scope

The skill must:

- inspect the exact product revision, runtime, assets, and existing demo paths;
- define one audience doubt and one proof proposition before scripting;
- rank capabilities as core proof, differentiator, supporting evidence,
  exception entry, or excluded;
- require every normal beat to change audience knowledge or visible product
  state;
- align narration, action, result, and exit state without unexplained waiting;
- distinguish real product execution from deterministic fixtures and disclose
  the boundary;
- support planning-only, production, and diagnosis/re-cut modes;
- produce a structured beat-plan JSON that can be mechanically validated;
- verify final media with `ffprobe` when a video is produced;
- define explicit autonomy and publishing boundaries.

The skill must not:

- require a particular browser, recorder, TTS vendor, product category, fixed
  chapter count, or fixed duration;
- claim a feature from documentation alone when live or code evidence is
  available;
- manufacture success states or silently replace failed product paths;
- bundle an application-specific recorder.

## Files

- `skills/build-product-demo/SKILL.md`: workflow router, boundaries, modes, and
  done-when contract.
- `skills/build-product-demo/agents/openai.yaml`: generated interface metadata.
- `skills/build-product-demo/references/directing.md`: audience question,
  feature proof, beat design, attention, narration, and pacing guidance.
- `skills/build-product-demo/references/production.md`: deterministic setup,
  capture, audio, edit, and delivery guidance.
- `skills/build-product-demo/references/artifact-contract.md`: output directory
  and beat-plan schema.
- `skills/build-product-demo/scripts/validate_demo_plan.py`: deterministic
  structural and timing checks for the beat plan.
- `skills/build-product-demo/scripts/probe_demo_media.py`: deterministic
  `ffprobe` wrapper with delivery assertions.
- `skills/build-product-demo/evals/evals.json`: representative trigger and
  boundary cases.

## Beat Plan Contract

The JSON plan contains product identity, revision, audience, proof proposition,
duration, delivery constraints, truth boundary, exclusions, and ordered beats.
Each beat contains an identifier, start/end time, claim, visible action,
audience knowledge before/after, entry/exit state, narration, evidence, and cut
reason. Optional idle intervals must be explicitly marked and motivated.

Validation fails for malformed timing, gaps or overlaps, empty state changes,
missing evidence, unmotivated idle intervals, invalid delivery values, or a
normal beat longer than the configured maximum information gap.

## Verification

Run:

```bash
python3 skills/build-product-demo/scripts/validate_demo_plan.py \
  <representative-plan.json>
python3 skills/build-product-demo/scripts/probe_demo_media.py \
  <representative-video.mp4> --expect-width 1440 --expect-height 900
python3 scripts/validate_skills.py --write
python3 scripts/validate_skills.py --check
python3 scripts/audit_skill_quality.py build-product-demo
```

Dogfood the skill on remem. Use only disposable demo data, show the real recall
path, retain raw evidence, and feed any false-success signal back into the
smallest responsible instruction, script, or eval before publishing.
