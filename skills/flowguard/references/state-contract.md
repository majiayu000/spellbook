# Flowguard State Contract

Use these compact formats when a task needs durable state across long loops, compaction, session boundaries, or automation. Keep entries factual and evidence-backed.

## Preflight

```text
route: execute_direct | plan_first | clarify_first
goal:
context:
constraints:
done_when:
out_of_scope:
verification_commands:
stop_conditions:
handoff_location:
```

Use `clarify_first` when missing data would cause destructive, expensive, security-sensitive, or large-scope work.

## Checkpoint

```text
checkpoint_time:
current_step:
modified_files:
commands_run:
fresh_evidence:
decisions:
blockers:
next_step:
scope_change:
```

Create a checkpoint before compaction, after a meaningful verification result, before changing execution direction, and after any user correction.

## Handoff

```text
task:
latest_user_request:
cwd:
repo_root:
branch:
head:
dirty_state_summary:
modified_files:
constraint_set_or_spec:
l1_l7_summary:
key_decisions:
current_priority:
verification_commands:
fresh_verification_evidence:
blockers:
next_action:
stop_conditions:
lane_map:
artifacts:
memory_used:
staleness_checks:
```

Required fields for compaction safety: `modified_files`, `constraint_set_or_spec`, `verification_commands`, `key_decisions`, `current_priority`, and `l1_l7_summary` when VibeGuard applies.

## Resume Checklist

1. Re-read applicable `AGENTS.md` before editing.
2. Read the handoff or prior checkpoint.
3. Run the installed Flowguard snapshot script with an explicit target repo path, for example `/path/to/installed/flowguard/scripts/workflow_state_snapshot.sh /path/to/target/repo`.
4. Compare cwd, repo root, branch, head, dirty files, and artifacts against the handoff.
5. Treat memory as a hint until verified against current files, git, runtime, or remote truth.
6. Reconcile any newer user instruction before continuing older work.
7. Re-establish the current route: `execute_direct`, `plan_first`, or `clarify_first`.

If the handoff and local truth disagree, update the plan before editing. If the disagreement changes goal, scope, safety, or done-when, stop and ask.

## Loop Guard

Stop the autonomous loop and reassess when:

- The same hypothesis or fix fails 3 times.
- Tool results contradict the active plan.
- The work crosses into files or systems not named in scope.
- A dependency, runtime, remote service, or test fixture changed underneath the task.
- The next step requires credentials, secrets, payment/auth logic, destructive data changes, deploys, force-push, or production writes.
- Cost or time exceeds the stated budget.

When stopped, report: current hypothesis, evidence for and against it, changed files, commands run, and the smallest next decision needed.

## Verification Evidence

Evidence must come from the current session. Acceptable examples:

- command output with command name and result
- test/build/lint summary
- HTTP response or health check with URL and status
- screenshot or visual check for UI work
- git status/diff summary for file state

Do not use "earlier passed", "should work", or stale memory as completion evidence.

## Automation Readiness

Do not schedule an agent workflow until the manual form has succeeded repeatedly.

Read-only automation candidates:

- state snapshot
- stale worktree report
- handoff draft
- verification summary
- failed-log digest

Require explicit user confirmation or a separate trusted contract for:

- code edits
- dependency upgrades
- database writes
- credential or secret changes
- deploys
- PR submission or merge
- force push
