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

- exact product repository, revision, runtime, and date;
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
  "schema_version": 1,
  "product": {
    "name": "Example",
    "repository": "/absolute/or/public/repository/identity",
    "revision": "exact revision"
  },
  "audience": "specific audience",
  "proof_proposition": "observable claim the demo will prove",
  "duration_seconds": 60,
  "max_information_gap_seconds": 6,
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
      "evidence": ["evidence/result.json"],
      "cut_reason": "Return to the starting state to explain the cause."
    }
  ]
}
```

Required top-level fields:

- `schema_version`: integer `1`;
- `product.name`, `product.repository`, `product.revision`: non-empty strings;
- `audience`, `proof_proposition`: non-empty strings;
- `duration_seconds`, `max_information_gap_seconds`: positive numbers;
- `delivery.width`, `delivery.height`, `delivery.fps`: positive numbers;
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
- `evidence`: array of non-empty strings; it may be empty only for `title`;
- `hold_reason`: required for `hold` beats.

The first beat starts at zero. Beats cover the declared duration without gaps
or overlaps. Every beat changes audience knowledge or product state. A normal
beat may not exceed `max_information_gap_seconds`; split it at the next real
action, reveal, or consequence instead of adding decorative cuts.

## `verification.json`

Record the plan validation result, media probe output, visual/audio review,
retained evidence paths, known limitations, and final verdict. Do not mark the
demo complete when any required check is missing.
