# Architecture Foundation Spec Template

Use this template for a repo-facing architecture artifact. Keep it specific:
name files, modules, APIs, validation commands, and issue/PR links when known.

## Objective

State the product or engineering goal in one paragraph.

## Current Evidence

| Area | Evidence | Implication |
| --- | --- | --- |
| Entrypoints |  |  |
| Core models |  |  |
| Runtime/lifecycle |  |  |
| Adapters/backends |  |  |
| Generated/config artifacts |  |  |
| Errors/diagnostics |  |  |
| Tests/headless |  |  |
| Open issues/PRs |  |  |

## Reference Models Considered

| Reference | Borrow | Do not copy | Source |
| --- | --- | --- | --- |
|  |  |  |  |

## Chosen Shape

```text
product/app
  - 

core/domain
  - 

runtime/application
  - 

adapters/backends
  - 

plugins/components
  - 

testing/headless
  - 
```

## Source Of Truth And Migration Debt

| Contract | Current source of truth | Consumers | Duplicates or forks | Action |
| --- | --- | --- | --- | --- |
| Public API/schema |  |  |  |  |
| Runtime/workflow state |  |  |  |  |
| Billing/accounting state |  |  |  |  |
| Config/resources |  |  |  |  |
| Generated docs/examples |  |  |  |  |

## Boundary Contracts

| Contract | Owner | Allowed dependencies | Forbidden dependencies | Tests |
| --- | --- | --- | --- | --- |
| State ownership |  |  |  |  |
| Lifecycle |  |  |  |  |
| Events/actions |  |  |  |  |
| Effects/IO |  |  |  |  |
| Errors |  |  |  |  |
| Config/resources |  |  |  |  |
| Observability |  |  |  |  |
| Compatibility/API |  |  |  |  |

## Issue And PR Map

| Issue/PR | Contract served | Status | Gap or follow-up |
| --- | --- | --- | --- |
|  |  |  |  |

## Compatibility And Deletion Plan

| Path or shim | Why it exists | Owner | Keep until | Delete or converge when |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## P0/P1/P2 Roadmap

| Priority | Work | Files/modules | Done when | Verification |
| --- | --- | --- | --- | --- |
| P0 |  |  |  |  |
| P1 |  |  |  |  |
| P2 |  |  |  |  |

## Non-Goals

- 

## Open Questions

- 

## Readiness Language

Use precise claims. Prefer:

- "The architecture spec is complete enough to sequence P0 work."
- "The runtime contract is implemented for headless tests."
- "The platform adapter exists for macOS only; other platforms return explicit
  unsupported errors."

Avoid:

- "Equivalent to X" without a feature matrix and fresh verification.
- "Production-ready" without tests, platform matrix, error policy, and docs.
