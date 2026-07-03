# Workflow Orchestration Template

Preferred orchestration path. The caller (main agent) assembles the fully-rendered dimension prompts
(preamble + template + `{TARGET_DIR}`/`{STACK_INFO}` substituted) and passes them via `args`:

```
Workflow({
  script: <the script below>,
  args: {
    target: "/abs/path/to/project",
    dimensions: [ { key: "contract", prompt: "<full prompt>" }, ... ]
  }
})
```

Do not pass `model` or `agentType` — agents inherit the session model, and the prompts are
self-contained (they don't rely on a specialized agent's system prompt).

## Script

```js
export const meta = {
  name: 'codebase-audit',
  description: 'Parallel codebase audit: structured findings per dimension, adversarial verify for critical/high',
  phases: [
    { title: 'Find', detail: 'one finder agent per dimension' },
    { title: 'Verify', detail: 'one adversarial verifier per critical/high finding' },
  ],
}

const FINDINGS_SCHEMA = {
  type: 'object',
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['category', 'severity', 'file', 'summary', 'evidence', 'evidence_type', 'confidence'],
        properties: {
          category: { type: 'string' },
          severity: { enum: ['critical', 'high', 'medium'] },
          file: { type: 'string' },
          line: { type: 'integer' },
          summary: { type: 'string' },
          evidence: { type: 'string' },
          evidence_type: { enum: ['observed', 'inferred'] },
          confidence: { enum: ['high', 'medium', 'low'] },
          fix_suggestion: { type: 'string' },
        },
      },
    },
  },
}

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['confirmed', 'reason'],
  properties: {
    confirmed: { type: 'boolean' },
    reason: { type: 'string' },
  },
}

function verifyPrompt(target, f) {
  return 'READ-ONLY adversarial verification — do not modify any file.\n' +
    'Target project: ' + target + '\n' +
    'Finding under review: [' + f.severity + '/' + f.category + '] ' + f.summary + '\n' +
    'Claimed location: ' + f.file + ':' + (f.line || '?') + '\n' +
    'Claimed evidence: ' + f.evidence + '\n\n' +
    'Open the file and its callers/guards/config. Actively try to REFUTE the finding: ' +
    'is there a guard clause, configuration, caller-side handling, or dead-code condition ' +
    'that makes this a non-issue? Set confirmed=false unless the code clearly supports the claim. ' +
    'In reason, cite file:line for whatever you found.'
}

const results = await pipeline(
  args.dimensions,
  d => agent(d.prompt, { label: 'find:' + d.key, phase: 'Find', schema: FINDINGS_SCHEMA }),
  (res, d) => {
    if (!res) {
      log('dim ' + d.key + ': finder FAILED — dimension incomplete')
      return { dim: d.key, failed: true, findings: [] }
    }
    const findings = res.findings || []
    const toVerify = findings.filter(f => f.severity === 'critical' || f.severity === 'high')
    const mediums = findings.filter(f => f.severity === 'medium')
    log('dim ' + d.key + ': ' + findings.length + ' findings, verifying ' + toVerify.length)
    return parallel(toVerify.map(f => () =>
      agent(verifyPrompt(args.target, f), {
        label: 'verify:' + (f.file || d.key),
        phase: 'Verify',
        schema: VERDICT_SCHEMA,
      }).then(v => Object.assign({}, f, {
        verified: v ? v.confirmed : null,
        verify_reason: v ? v.reason : 'verifier unavailable',
      })).catch(() => Object.assign({}, f, {
        verified: null,
        verify_reason: 'verifier failed — kept unverified',
      }))
    )).then(verified => ({
      dim: d.key,
      failed: false,
      findings: verified.filter(Boolean).concat(
        mediums.map(f => Object.assign({}, f, { verified: null, verify_reason: 'medium — not verified' }))
      ),
    }))
  }
)

return { dims: results.filter(Boolean) }
```

Notes:
- `pipeline` (not `parallel`) between Find and Verify: dimension A's findings verify while dimension B is still scanning.
- A finder that dies returns `null`; stage 2 converts it into `{ dim, failed: true, findings: [] }` so the failure survives into the result. The report MUST list every `failed: true` dimension as "dimension X did not complete" — never present it as zero findings / clean coverage.
- Each verifier thunk carries a `.catch` that maps the finding to `verified: null` — a flaky verifier keeps its finding as `unverified` instead of dropping it (matches the SKILL.md Phase 3 rule).
- Quick mode: pass only the 2 quick dimensions and replace the second pipeline stage with
  `(res, d) => res ? { dim: d.key, failed: false, findings: (res.findings || []).map(f => Object.assign({}, f, { verified: null, verify_reason: 'quick mode — not verified' })) } : { dim: d.key, failed: true, findings: [] }`.

## Fallback verify prompt (Agent tool path)

Use the same text as `verifyPrompt()` above, appending:
"Output ONLY a JSON object: {\"confirmed\": bool, \"reason\": str}."
Launch all verifiers for one round in a single message; use `subagent_type: "general-purpose"`.
