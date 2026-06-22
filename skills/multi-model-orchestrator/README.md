# multi-model-orchestrator Skill

**Decompose complex tasks into agent-executable subtasks. Execute in parallel. Synthesize results.**

A lightweight framework for coordinating work across multiple AI agents (Claude, Opus, Haiku, Codex, etc.) using a centralized handoff document.

## Quick Start

1. **Create a handoff from the bundled template**:
   Ask your agent to load this skill's `templates/handoff-template.yaml` and write it to `.claude/handoffs/my-task.yaml`.

   From a Spellbook checkout, you can run:
   ```bash
   mkdir -p .claude/handoffs
   cp skills/multi-model-orchestrator/templates/handoff-template.yaml .claude/handoffs/my-task.yaml
   ```

2. **Fill in your goal and subtasks** — describe what you want to accomplish

3. **Ask Fable/Claude to decompose** — provide the handoff, ask it to break down into concrete subtasks

4. **Execute each subtask** — assign to Opus, Haiku, Codex, etc.

5. **Record results** — add execution results to the handoff

6. **Review and iterate** — analyze what worked, what didn't, what's next

See `references/add-auth-to-api.yaml` for a complete real-world example.

## What's Inside

```
.
├── SKILL.md                           # Entry point: trigger, core concepts, loop
├── README.md                          # This file
├── templates/
│   └── handoff-template.yaml         # Copy this for your task
├── references/
│   ├── quick-start.md                # Full 5-step walkthrough with templates
│   ├── handoff-structure.md          # Handoff YAML field reference
│   ├── workflow-patterns.md          # Parallel / sequential / sync-point layouts
│   ├── best-practices.md             # High-signal subtask authoring
│   ├── advanced-sync.md              # Optional handoff automation
│   ├── faq.md                        # Common questions
│   └── add-auth-to-api.yaml          # Complete example: JWT auth for REST API
└── LICENSE
```

## Core Concepts

### Handoff Document

A YAML file that records:
- **Goal** — what we're trying to accomplish
- **Subtasks** — specific work items with executor assignments
- **Execution** — who did what and what was the result
- **Feedback** — learnings and improvements

### The Loop

```
Goal → Fable decomposes → Subtasks → Agents execute in parallel → Results → Review & iterate
```

## When to Use

✅ Use when:
- You need to coordinate multiple agents on a complex task
- You want to parallelize work
- You need full traceability of decisions and changes
- You're exploring multiple approaches (A/B/C)

❌ Don't use when:
- A single agent can handle it
- The task is simple and sequential
- You don't need to track history

## Example Workflow

### 1. Create Handoff
```yaml
metadata:
  name: "add-authentication"
  goal: "Add JWT auth to REST API"

goal:
  summary: "Protect API endpoints with JWT tokens"
  acceptance_criteria:
    - "Login endpoint returns valid JWT"
    - "Protected endpoints require auth"

subtasks:
  - id: task-1
    title: "Design JWT flow"
    executor: "Opus"
    input: "Design JWT architecture..."
    depends_on: []
```

### 2. Get Fable to Decompose
```
Please decompose this goal into subtasks for:
- Design (use Opus)
- Implementation (use Codex)
- Testing (use Claude Code)
```

### 3. Execute in Dependency Order
- Opus completes the design first
- Codex implements from the approved design
- Claude Code tests after the implementation exists

Run tasks in parallel only when their `depends_on` fields are empty and they do
not need each other's outputs.

### 4. Record Results
```yaml
execution:
  rounds:
    - task_id: task-1
      status: done
      result: "Design doc created at docs/AUTH_DESIGN.md"
      timestamp: "2026-06-12T10:00:00Z"
```

### 5. Synthesize
```yaml
feedback:
  synthesis: "All tasks completed. Design → Code → Test pipeline worked well."
  improvements:
    - "Consider adding OAuth2 for future integrations"
```

## Key Features

- 📄 **Single Source of Truth** — one handoff YAML tracks everything
- 🚀 **Parallel Execution** — subtasks without dependencies run simultaneously
- 🔗 **Dependency Management** — explicit task ordering when needed
- 📊 **Full Traceability** — every decision, change, and result recorded
- 🎯 **Agent Agnostic** — use any LLM (Claude, Opus, Haiku, Codex, Grok, etc.)
- 💾 **Git-Friendly** — YAML diffs show exactly what changed

## File Formats

### Handoff YAML Schema

See `templates/handoff-template.yaml` for full schema.

Key sections:
- `metadata` — task name, status, goal summary
- `goal` — detailed goal, acceptance criteria, context
- `subtasks` — list of work items (id, title, type, executor, input, acceptance, dependencies)
- `execution.rounds` — execution history (what was done, by whom, with what result)
- `feedback` — synthesis, improvements, decision log

## Usage Patterns

### Pattern 1: Parallel Execution
All subtasks with no dependencies run simultaneously.

```yaml
subtasks:
  - id: task-1
    title: "Analyze"
    depends_on: []  # No dependency

  - id: task-2
    title: "Design"
    depends_on: []  # Can start immediately
```

### Pattern 2: Sequential
Tasks run one after another.

```yaml
subtasks:
  - id: task-1
    depends_on: []

  - id: task-2
    depends_on: ["task-1"]  # Wait for task-1

  - id: task-3
    depends_on: ["task-2"]  # Wait for task-2
```

### Pattern 3: Merge Point
Some tasks run in parallel; others converge.

```yaml
subtasks:
  - id: task-1a
    depends_on: []

  - id: task-1b
    depends_on: []

  - id: task-2
    depends_on: ["task-1a", "task-1b"]  # Wait for both
```

## Best Practices

1. **Clear Descriptions** — be specific about what you want done
2. **Testable Acceptance Criteria** — "it works" is not enough
3. **Explicit Dependencies** — declare ordering clearly
4. **Record Everything** — even failures teach us something
5. **Commit Carefully** — keep sensitive handoffs out of git, or commit only after reviewing for secrets, customer data, internal plans, copied prompts, and logs

## Examples

### Real-World: Add JWT Auth to REST API
See `references/add-auth-to-api.yaml` for a complete walkthrough of:
- Decomposing the goal into 5 subtasks
- Assigning to Opus (design), Codex (code), Haiku (protect endpoints), Claude Code (testing)
- Executing in 5 rounds
- Recording all results
- Final synthesis and learnings

## FAQ

**Q: Can I use this with any AI model?**
A: Yes. The skill is model-agnostic. Assign subtasks to Claude, Opus, Haiku, Codex, or any LLM.

**Q: Do I need to commit handoffs to git?**
A: Recommended only when the repository is private or the handoff has been reviewed for secrets, customer data, internal plans, copied prompts, and logs. Otherwise keep it outside git or commit a redacted summary.

**Q: How do I know when a subtask is done?**
A: Define acceptance criteria clearly. When all criteria are met, it's done.

**Q: Can tasks run in parallel?**
A: Yes. If subtasks have no dependencies, execute them simultaneously.

**Q: What if a subtask blocks?**
A: Record it as `status: blocked` and explain why. Then decide to retry, reassign, or escalate.

## Integration with Claude Code

When using Claude Code interactively:

1. Keep handoff in `.claude/handoffs/my-task.yaml`
2. Run: `cat .claude/handoffs/my-task.yaml` to load it
3. Ask Claude Code to execute a subtask
4. Update handoff manually or via script

## Integration with Codex

Codex can work from handoffs when the task is passed through `codex exec`:

```bash
codex exec "Read .claude/handoffs/task.yaml. Execute subtask task-1 only. Return the result, blockers, files changed, and verification evidence."
```

(Optional CLI workflow — handoffs work without it.)

## License

MIT

## Contributing

This skill is designed to be simple and flexible. Share handoff examples or improvements.

---

**Status**: Production ready
**Last Updated**: 2026-06-12
**Version**: 1.0.0
