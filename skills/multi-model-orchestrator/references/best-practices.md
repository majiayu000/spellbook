# Best Practices

Part of the `multi-model-orchestrator` skill. Patterns that keep handoffs
high-signal and traceable. Load this when authoring or reviewing subtasks.

### 1. **Clear Subtask Descriptions**

Bad:
```yaml
- id: task-1
  input: "fix the code"
```

Good:
```yaml
- id: task-1
  input: |
    The authentication middleware in src/auth.ts has a race condition
    when multiple requests arrive simultaneously.

    Current behavior: requests can bypass the token refresh check
    Expected behavior: all requests wait for token refresh to complete

    Code reference: src/auth.ts:45-62
    Test: tests/auth.race-condition.test.ts
```

### 2. **Specific Acceptance Criteria**

Bad:
```yaml
acceptance: "it should work"
```

Good:
```yaml
acceptance: |
  - Token refresh completes within 100ms
  - No requests can bypass the mutex
  - All 100 concurrent requests pass the test suite
  - Performance regression < 5% vs baseline
```

### 3. **Declare Dependencies Explicitly**

```yaml
depends_on: ["task-1", "task-2"]  # Clear ordering
```

Not:
```yaml
# Implicitly assumes task-1 was done first (bad)
```

### 4. **Record Everything**

Even if a task fails, record it:

```yaml
- round: 2
  task_id: "task-2"
  status: "blocked"
  result: "Attempt failed due to missing dependency"
  issues: |
    Task-1 output was incomplete.
    Need to ask Opus to redo task-1.
  next_step: "Re-execute task-1 with clearer requirements"
```

### 5. **Keep Handoffs in Git**

```bash
# Commit your handoff
git add .claude/handoffs/my-task.yaml
git commit -m "WIP: multi-agent task execution for feature X"

# Later you can see the full evolution:
git log -p .claude/handoffs/my-task.yaml
```
