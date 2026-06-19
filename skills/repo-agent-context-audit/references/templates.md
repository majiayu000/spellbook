# Minimal Templates

Use these only when the user asks to scaffold or wants exact proposed contents. Adapt every command and path to the target repo.

## AGENTS.md

```markdown
# Agent Instructions

## Scope

This file applies to the whole repository unless a nested `AGENTS.md` overrides it.

## Start Here

1. Read this file.
2. Check the worktree with `git status --short`.
3. For substantial features, read or create `specs/<id>/PRODUCT.md` before implementation.
4. For implementation planning, read or create `specs/<id>/TECH.md`.
5. Use repo-local skills under `.agents/skills/` when a task matches one.

## Commands

- Build: `<repo build command>`
- Typecheck: `<repo typecheck command>`
- Test: `<repo test command>`
- Lint/format: `<repo lint command>`

## Spec Gate

| Change | Required Path |
|---|---|
| Small bugfix with clear root cause | Implement directly, add regression test |
| User-facing feature or ambiguous behavior | `specs/<id>/PRODUCT.md` first |
| Multi-module or risky implementation | `specs/<id>/TECH.md` before code |
| Generated files, migrations, auth, payments, secrets | Plan first and verify with fresh commands |

## Coding Rules

- Follow existing patterns before adding abstractions.
- Search for existing helpers before creating new ones.
- Do not silently swallow errors that change user-visible behavior.
- Keep changes scoped to the requested behavior.
- Do not edit generated files unless the generator workflow is part of the change.

## Verification

Before completion, run the narrowest command that proves the change. Before submission, run the repo's required full gate when practical.
```

## PRODUCT.md

```markdown
# <Feature Name> Product Spec

## Summary

<1-3 sentences describing the consumer-visible outcome.>

## Behavior

1. <Default or happy-path behavior.>
2. <Input and response behavior.>
3. <Empty/loading/error behavior if relevant.>
4. <Permission/offline/cancellation/race behavior if relevant.>
5. <Accessibility/focus/keyboard behavior if relevant.>
6. <Behavior that must not regress.>

## Non-Goals

- <Explicitly out-of-scope behavior, only if useful.>

## Open Questions

- <Question, owner, and decision needed. Omit section if none.>
```

## TECH.md

```markdown
# <Feature Name> Tech Spec

Product spec: `specs/<id>/PRODUCT.md`

## Context

- `<file>:<line>` - <current behavior or entrypoint>
- `<file>:<line>` - <related type, state, API, or test>

<Short explanation of current state and constraints.>

## Proposed Changes

1. <Module or boundary change.>
2. <New or changed type/API/state.>
3. <Data flow or lifecycle change.>
4. <Rejected alternative, if there is a real tradeoff.>

## Testing and Validation

| Product Behavior | Verification |
|---|---|
| Behavior 1 | <unit/integration/manual command or artifact> |
| Behavior 2 | <unit/integration/manual command or artifact> |

Commands:

- `<focused test command>`
- `<full gate if required>`

## Risks

- <Risk and mitigation. Omit section if no material risk.>

## Follow-Ups

- <Deferred work. Omit section if none.>
```

## Audit Report

```markdown
## Agent Context Audit

- state: <healthy/missing router/overloaded/specless/stale/unsafe>
- top-level router: <present/missing/overloaded>
- reusable skills: <present/missing/not needed>
- specs: <present/missing/inconsistent/not needed>
- main risk: <one sentence>

## Smallest Useful Change

1. <change> - <why> - <estimated effort>

## Evidence

- `<file>:<line>` - <what it proves>

## Optional Scaffold

- `<path>` - <why it would help>
```
