# Showcase

These examples are quick checks after installing Spellbook. Pick one workflow, paste the prompt into Claude Code or Codex, and inspect the plan or file changes before letting the agent edit.

## Codebase Audit

Install:

```bash
npx skills add majiayu000/spellbook --skill codebase-audit --skill flowguard --skill systematic-debugging --skill review-gate
```

Prompt:

```text
Use codebase-audit on this repository. Find the top 5 risks by severity, focus on security, data integrity, error handling, and build/test gaps. Do not edit files yet; give me file references, root causes, and a repair order.
```

Expected output:

- Severity-ranked findings with file references.
- Root cause for each issue, not just symptoms.
- A repair order that starts with build/test failures if any exist.

## Frontend Build

Install:

```bash
npx skills add majiayu000/spellbook --skill frontend-design --skill app-ui-design --skill ui-design-system --skill figma-to-react
```

Prompt:

```text
Use frontend-design to build a dense SaaS dashboard for incident response. The first screen should show open incidents, service health, owner handoff, and recent deploys. Match the existing frontend stack in this repo and verify it in the browser.
```

Expected output:

- A working first screen, not a marketing landing page.
- UI controls and states a real operator would expect.
- Browser verification or clear explanation if no frontend runtime exists.

## Release and Server Safety

Install:

```bash
npx skills add majiayu000/spellbook --skill release-engineering --skill server-security --skill clash-doctor --skill system-doctor
```

Prompt:

```text
Use release-engineering to prepare a release plan for this app and server-security to identify the Linux hardening gates. Detect the stack, list required environment variables, define rollback and verification, and do not SSH or deploy.
```

Expected output:

- Stack detection from local files.
- Release steps with rollback and verification.
- Explicit security gates without remote mutation.

## Product Spec

Install:

```bash
npx skills add majiayu000/spellbook --skill product-discovery --skill prd-master --skill technical-spec --skill product-analytics
```

Prompt:

```text
Use product-discovery and prd-master to turn this idea into a one-page PRD: a skill dashboard that shows installed skills, stale descriptions, validation status, and suggested bundles. Include success metrics and out-of-scope items.
```

Expected output:

- Problem, user, solution, scope, and non-goals.
- Acceptance criteria and measurable success metrics.
- Follow-up technical-spec outline when implementation detail is needed.

## Agent Workflows

Install:

```bash
npx skills add majiayu000/spellbook --skill codex-agent --skill multi-ai-research --skill flowguard --skill vibeguard
```

Prompt:

```text
Use codex-agent to review this repository's current change, then use flowguard and vibeguard to separate verified findings from assumptions. Do not edit or delegate yet. Return the three highest-impact risks, the evidence for each, and the smallest safe verification plan.
```

Expected output:

- Evidence-backed risks instead of generic review advice.
- Clear separation between verified facts, inferences, and unknowns.
- A bounded verification plan before any implementation or delegation.
