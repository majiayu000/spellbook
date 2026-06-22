# Workflow Patterns

Part of the `multi-model-orchestrator` skill. Common subtask dependency
layouts. Load this when you are designing the `depends_on` graph for a handoff.

## Pattern 1: Parallel Execution

All subtasks with no dependencies run simultaneously:

```yaml
subtasks:
  - id: task-1
    title: "Analyze requirements"
    executor: "Claude"
    depends_on: []

  - id: task-2
    title: "Design architecture"
    executor: "Opus"
    depends_on: []  # No dependency on task-1

  - id: task-3
    title: "Set up project"
    executor: "Claude Code"
    depends_on: []  # Independent
```

→ Run all three agents at the same time, then sync results.

## Pattern 2: Sequential with Dependency Chain

Each task waits for the previous one:

```yaml
subtasks:
  - id: task-1
    title: "Understand the problem"
    executor: "Fable"
    depends_on: []

  - id: task-2
    title: "Write the code"
    executor: "Codex"
    depends_on: ["task-1"]  # Waits for task-1

  - id: task-3
    title: "Test and validate"
    executor: "Claude Code"
    depends_on: ["task-2"]  # Waits for task-2
```

→ Run sequentially, using output of each as input to the next.

## Pattern 3: Parallel with Sync Point

Some tasks run in parallel; others converge:

```yaml
subtasks:
  - id: task-1a
    executor: "Opus"
    depends_on: []

  - id: task-1b
    executor: "Haiku"
    depends_on: []

  - id: task-2
    title: "Synthesize results"
    executor: "Claude"
    depends_on: ["task-1a", "task-1b"]  # Waits for both
```

→ 1a and 1b run in parallel; 2 waits for both to finish.
