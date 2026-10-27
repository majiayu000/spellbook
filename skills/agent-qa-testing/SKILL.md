---
name: agent-qa-testing
description: Use when a project uses agent-qa and the user asks to validate its YAML, run a selected regression test, or triage a failed/healed run with memidex evidence. For a general app feature inventory, use app-user-story-qa.
license: MIT
---

# agent-qa testing

Use agent-qa for web, Android, and iOS regression tests with advanced memidex memory and self-improvement. Work with the project's existing tests, targets, and model configuration.

## When to Use

- Validate or run a selected agent-qa regression test in an initialized project.
- Investigate a failed or healed agent-qa run using recorded evidence.
- Inspect the memidex knowledge associated with that run.


This is a product-verification skill for an existing agent-qa workflow. For a whole-app feature inventory and user-story tracker, use `app-user-story-qa`.

## Operating Contract

Direct actions: Inspect configuration and recorded evidence, validate YAML, and perform dry runs within the requested workspace. Run application tests only against the user-authorized target and data.

Escalate before: Production actions, paid execution, credential changes, or scope expansion unless the user has already explicitly authorized them.

A testing request does not authorize application repairs. Preserve failures and propose an evidence-based fix unless the user has also requested changes.

Evidence-backed pushback: If a request broadens execution beyond the configured target, cite that mismatch and propose a scoped dry run until the target is resolved.

Feedback loop: When a setup or triage mistake recurs, record the verified symptom and correction in the project's existing QA notes, with secrets removed; use that evidence to improve the next run.

## Core Process

### 1. Establish the test scope

- Locate `agent-qa.config.yaml` and the requested test or suite. Run from that project directory; a global `--config <path>` must appear before the command.
- Use the project's installed version and package manager. The examples below assume an npm installation and use `--no-install` to avoid downloading a different version. Replace `tests/checkout.yaml` with the selected test path.
- agent-qa requires Node.js 24+. If it is not installed or initialized, use the [official quickstart](https://vostride.com/docs/agent-qa/quickstart) and the user's chosen provider; preserve existing configuration and credentials.

```sh
npx --no-install agent-qa --version
npx --no-install agent-qa run --help
```

### 2. Validate before executing

```sh
npx --no-install agent-qa validate tests/checkout.yaml
npx --no-install agent-qa run tests/checkout.yaml --dry-run
```

Validation checks configuration, test structure, and references. A dry run lists the selected tests without executing them. Neither proves that an application flow passes. Check the selected target and test files before running; omitting the path runs all discovered tests.

For suite selection or mobile device overrides, consult the installed command's help and existing project configuration. `doctor` can help diagnose setup failures, but its checks may contact the configured model provider.

### 3. Run the selected flow

Run against the environment and test data authorized by the user. Application actions can change data, and configured providers may charge for execution.

```sh
npx --no-install agent-qa run tests/checkout.yaml --junit-output results.xml
```

Preserve the exit status and report path. Exit `0` means passed or healed; `1` covers failed or timed-out tests and missing required files; `2` means agent-qa could not run; `130` means cancelled. Inspect the verdict to distinguish a clean pass from a healed run; treat setup failures as unresolved execution, not application failures.

### 4. Triage from recorded evidence

```sh
npx --no-install agent-qa runs list --verdict failed --limit 10 --json
npx --no-install agent-qa runs overview RUN_ID --json
npx --no-install agent-qa runs knowledge RUN_ID --json
npx --no-install agent-qa knowledge inspect --json
```

Replace `RUN_ID` with the relevant recorded run ID. Use `runs list --json` without the verdict filter when investigating a healed run or another outcome.

If a run has no completed verdict or its knowledge view reports `evidence-incomplete`, report that gap. Do not infer a completed application outcome from an incomplete record.

Read the failed step and available evidence before proposing a correction. Edit tests or application code only when the user has authorized that change. Distinguish an application defect, a test expectation problem, and an environment/provider failure. Use the run's knowledge view to see what memidex supplied or learned. Do not erase the cache or knowledge store merely to obtain a passing result.

### 5. Verify and report

Rerun the selected flow after an evidence-based correction. Stop and report an unchanged failure when no new corrective action is justified. Report the command, run ID, verdict, relevant evidence/report paths, and what remains unverified; redact credentials and sensitive application data.

## Gotchas and recovery

- A dry run confirms selection, not application behavior. Capture a completed run verdict before claiming a flow passed.
- Exit `0` includes healed runs. Inspect the recorded verdict instead of equating every zero exit with a clean pass.
- An empty failed-run list does not establish that an interrupted run passed. Inspect the requested run directly and report missing evidence.
- If an installed command differs from these examples, use its help and record the version; do not guess flags or silently install an update.

## Done when

- The selected test and target are recorded, with validation, dry-run and execution results clearly separated.
- The report gives the command, exit status, run ID, verdict and evidence paths. A requested but unexecuted flow remains unverified.
- Any correction has a fresh scoped rerun, or the precise reason it could not be rerun is stated.

## References

- [CLI commands and exit codes](https://vostride.com/docs/agent-qa/cli)
- [Inspect and correct memory](https://vostride.com/docs/agent-qa/memory/inspect)
- [agent-qa repository](https://github.com/vostride/agent-qa)

These original skill instructions use this repository's MIT license. The separately installed agent-qa package uses FSL-1.1-ALv2. Model, browser, and device providers have their own requirements and costs.
