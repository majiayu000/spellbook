# Skill Taxonomy

Use this taxonomy to place a candidate skill into one primary category. A good
skill usually fits cleanly into one category. If it does not, narrow the scope or
split the skill.

## 1. Library And API Reference

Use for libraries, CLIs, SDKs, internal APIs, or platform wrappers that agents
often misuse.

Include:
- Correct invocation patterns
- Edge cases and footguns
- Required imports, auth, environment variables, and version notes
- Small reference snippets

Avoid:
- Repeating public docs without repo-specific gotchas
- Mixing unrelated libraries into one broad reference skill

## 2. Product Verification

Use for proving product behavior works, especially user flows, UI flows, CLI
flows, and state transitions.

Include:
- Exact verification steps
- Programmatic assertions
- Test accounts, fixtures, or safe data
- Screenshots, traces, logs, or videos when useful

Avoid:
- Only saying "test it"
- Leaving verification subjective when the state can be asserted

## 3. Data Fetching And Analysis

Use for querying data stores, dashboards, event streams, logs, or monitoring
systems.

Include:
- Canonical tables, event names, IDs, and joins
- Credential and environment setup
- Common query patterns
- Statistical or data quality checks

Avoid:
- Letting the agent invent fields, dashboards, or joins
- Hiding missing data behind fallback narratives

## 4. Business Process And Team Automation

Use for repeatable team workflows such as standups, ticket creation, release
notes, weekly recaps, or queue processing.

Include:
- Input sources
- Output schema
- Ordering and escalation rules
- Memory or logs for previous runs when deltas matter

Avoid:
- Encoding one person's temporary preference as a global workflow
- Automating before the manual workflow is stable

## 5. Code Scaffolding And Templates

Use for creating repeatable code structures, services, migrations, app shells,
or framework-specific boilerplate.

Include:
- File tree
- Templates
- Naming rules
- Required wiring and validation commands

Avoid:
- Scaffolding code that is not wired into startup, routing, or tests
- Treating natural-language requirements as if pure templates are enough

## 6. Code Quality And Review

Use for review, linting, style, testing practices, adversarial critique, or
quality gates.

Include:
- Prioritized findings criteria
- Deterministic checks where possible
- Review templates
- Rules that target known agent failure modes

Avoid:
- Broad "make it better" guidance
- Weakening tests or replacing root-cause analysis with cosmetic cleanup

## 7. CI/CD And Deployment

Use for building, releasing, deploying, rollback, PR babysitting, or
environment-specific delivery workflows.

Include:
- Exact commands and environments
- Smoke tests
- Rollback criteria
- CI status handling and flaky-test policy

Avoid:
- Destructive deployment steps without guardrails
- Claiming success without fresh command output

## 8. Runbooks

Use for symptom-driven investigations such as incidents, alerts, error
signatures, failed jobs, or support escalations.

Include:
- Symptom-to-tool routing
- Query patterns
- Structured report format
- Stop conditions and escalation path

Avoid:
- A vague checklist that does not narrow the search space
- Letting the agent stop after the first plausible explanation

## 9. Infrastructure Operations

Use for routine operational work with resources, networking, secrets, accounts,
quotas, storage, or cost investigations.

Include:
- Safety checks
- Dry-run behavior when possible
- Confirmation points for destructive operations
- Audit trail and rollback notes

Avoid:
- Hiding destructive actions inside convenience commands
- Combining unrelated infrastructure tasks into one large skill
