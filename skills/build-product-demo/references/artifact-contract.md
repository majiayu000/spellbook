# Product Demo Artifact Contract

Use a dedicated demo directory outside generated build output. Preserve raw
captures and validation evidence so the result can be reviewed or recut.

## Recommended package

```text
<demo-dir>/
├── brief.md
├── feature-coverage.md
├── SCRIPT.md
├── beat-plan.json
├── evidence/
├── recording/
├── final/
│   └── <product>-demo.mp4
└── verification.json
```

Planning mode requires the four top-level planning files. Production mode also
requires raw evidence or pointers, the final artifact, and verification output.
Do not create empty placeholder directories.

## `brief.md`

Record:

- public or sanitized product repository identity, exact revision, runtime, and
  date; keep the operational checkout path outside the production package;
- audience, distribution channel, duration, aspect ratio, and language;
- audience doubt and proof proposition;
- opening, turning, and landing state;
- truth boundary and production simplification rule;
- assumptions, blockers, exclusions, credentials, paid-provider, publishing,
  and destructive-action boundaries.

## `feature-coverage.md`

Use one row per candidate capability:

| Capability | Audience value | Evidence level | Demo role | Visible proof | Included | Reason |
|---|---|---|---|---|---|---|

Do not treat documentation copy as live evidence.

## `SCRIPT.md`

Include the director treatment, chapter summaries, one narration block per
beat, on-screen text, sound intent, and disclosure language. Keep narration and
visible action adjacent for review.

## `beat-plan.json`

Use this shape:

```json
{
  "schema_version": 2,
  "product": {
    "name": "Example",
    "repository": "public URL or sanitized repository identity",
    "revision": "exact revision"
  },
  "audience": "specific audience",
  "proof_proposition": "observable claim the demo will prove",
  "reference_benchmark": "path or identity of the comparison artifact",
  "duration_seconds": 5,
  "max_information_gap_seconds": 5,
  "max_attention_gap_seconds": 3,
  "first_product_action_seconds": 4,
  "native_surface_target_ratio": 0.7,
  "delivery": {
    "width": 1440,
    "height": 900,
    "fps": 30,
    "container": "mp4"
  },
  "truth_boundary": {
    "live": ["real product paths shown"],
    "deterministic": ["fixtures or providers used only for stability"],
    "composite": ["editorial combinations"],
    "excluded": ["claims not made"]
  },
  "beats": [
    {
      "id": "result-hook",
      "type": "normal",
      "start_seconds": 0,
      "end_seconds": 5,
      "claim": "The product produces a real result.",
      "visible_action": "Show the finished result, then reveal its source.",
      "audience_before": "The audience does not know whether the product works.",
      "audience_after": "The audience has seen the concrete outcome.",
      "entry_state": "Result hidden.",
      "exit_state": "Result visible and attributable.",
      "narration": "Start with the outcome.",
      "audio_intent": "Narration resolves as the result lands.",
      "truth_mode": "live",
      "surface": "native",
      "events": [
        {"at_seconds": 0.8, "kind": "product_action", "description": "Command executes"},
        {"at_seconds": 2.2, "kind": "result", "description": "Native result appears"}
      ],
      "evidence": ["evidence/result.json"],
      "cut_reason": "Return to the starting state to explain the cause."
    }
  ]
}
```

Required top-level fields:

- `schema_version`: integer `2`;
- `product.name`, `product.repository`, `product.revision`: non-empty strings;
- `audience`, `proof_proposition`, `reference_benchmark`: non-empty strings;
- `duration_seconds`, `max_information_gap_seconds`,
  `max_attention_gap_seconds`: positive numbers;
- `first_product_action_seconds`: number from zero through five;
- `native_surface_target_ratio`: number from `0.6` through `1.0`; a lower target
  is allowed only when `native_surface_exception` is a non-empty explanation of
  why the medium makes the ratio inapplicable;
- `native_surface_exception`: omit it normally; use a non-empty string only for
  the documented lower-target exception;
- `delivery.width`, `delivery.height`: positive integers;
- `delivery.fps`: positive number;
- `delivery.container`: non-empty string;
- `truth_boundary.live`, `deterministic`, `composite`, `excluded`: arrays;
- `beats`: non-empty ordered array.

Required beat fields:

- `id`: unique non-empty string;
- `type`: `normal`, `title`, or `hold`;
- `start_seconds`, `end_seconds`: contiguous, non-overlapping times;
- `claim`, `visible_action`, `audience_before`, `audience_after`,
  `entry_state`, `exit_state`, `audio_intent`, `cut_reason`: non-empty strings;
- `narration`: string; it may be empty when sound or silence carries the beat;
- `truth_mode`: `live`, `deterministic`, `composite`, or `title`;
- `surface`: `native`, `composite`, or `title`;
- `events`: ordered array of observable events. Normal beats require at least
  one event. Each event has an absolute `at_seconds`, `kind`, and description;
  kinds are `product_action`, `input`, `result`, `reveal`, `cut`, `sound`, or
  `hold`;
- `evidence`: array of non-empty strings; it may be empty only for `title`;
- `hold_reason`: required for `hold` beats.

The first beat starts at zero. Beats cover the declared duration without gaps
or overlaps. Every beat changes audience knowledge or product state. A normal
beat may not exceed `max_information_gap_seconds`; split it at the next real
action, reveal, or consequence instead of adding decorative cuts.

The native-surface duration must meet `native_surface_target_ratio`, and title
plus composite surfaces must stay below 20% unless
`native_surface_exception` records why the medium makes those ratios
inapplicable. The first
`product_action` event on a normal native-surface beat must occur by
`first_product_action_seconds`; title and composite events do not satisfy this
gate. Consecutive non-hold events may not exceed
`max_attention_gap_seconds`.

## `verification.json`

Record the plan validation result, media probe output, pacing analyzer output,
native/title/composite duration ratios, dense-frame and continuous-playback
review, exact motivated-hold intervals and their analyzer exemptions, retained
evidence paths, known limitations, and final verdict. Do not
mark the demo complete when any required check is missing.
