# Showcase

These examples are quick checks after installing Spellbook. Pick one workflow, paste the prompt into Claude Code or Codex, and inspect the plan or file changes before letting the agent edit.

## Codebase Audit

Install:

```bash
./install.sh --target all --skills codebase-audit,systematic-debugging,comprehensive-testing
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
./install.sh --target all --skills frontend-design,app-ui-design,ui-design-system
```

Prompt:

```text
Use frontend-design to build a dense SaaS dashboard for incident response. The first screen should show open incidents, service health, owner handoff, and recent deploys. Match the existing frontend stack in this repo and verify it in the browser.
```

Expected output:

- A working first screen, not a marketing landing page.
- UI controls and states a real operator would expect.
- Browser verification or clear explanation if no frontend runtime exists.

## Product Spec

Install:

```bash
./install.sh --target all --skills product-discovery,prd-master,technical-spec,product-analytics
```

Prompt:

```text
Use product-discovery and prd-master to turn this idea into a one-page PRD: a skill dashboard that shows installed skills, stale descriptions, validation status, and suggested bundles. Include success metrics and out-of-scope items.
```

Expected output:

- Problem, user, solution, scope, and non-goals.
- Acceptance criteria and measurable success metrics.
- Follow-up technical-spec outline when implementation detail is needed.
