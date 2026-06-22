# Quick Start (10 minutes)

Part of the `multi-model-orchestrator` skill. The main `SKILL.md` keeps the
loop overview; load this reference when you are ready to create your first
handoff and run the full five-step walkthrough with templates.

## Step 1: Create Handoff Template

Copy the template below and save as `.claude/handoffs/my-task.yaml`:

```yaml
metadata:
  name: "descriptive name of task"
  created: "2026-06-12"
  goal: "What are we trying to accomplish?"
  status: "planning"  # planning → executing → review → complete

goal:
  summary: |
    Clear, specific goal statement.
  acceptance_criteria:
    - "Testable criterion 1"
    - "Testable criterion 2"
  context: |
    Any background, constraints, or prior decisions.

subtasks:
  - id: "task-1"
    title: "Clear description"
    type: "code | analysis | design | research | validation"
    executor: "Opus | Haiku | Codex | Claude | Claude Code"
    input: |
      What does the executor need to know?
      Include code refs, examples, constraints.
    acceptance: |
      How do we know this is done?
    depends_on: []  # other task IDs this depends on
    status: "pending"  # pending → in-progress → done → blocked

  - id: "task-2"
    title: "Another task"
    type: "code"
    executor: "Codex"
    input: |
      [...]
    depends_on: ["task-1"]
    status: "pending"

execution:
  rounds: []

feedback:
  synthesis: |
    Overall: what worked? what didn't? what changed?
  improvements:
    - "Improvement 1"
    - "Improvement 2"
  decision_log: |
    Why did we make X choice? What was the tradeoff?
```

## Step 2: Decompose with Fable/Claude

**Prompt for Fable/Claude:**

```
I have a complex goal that needs to be decomposed into subtasks for different agents.

Goal: [copy your goal from handoff]

Here's my context: [copy goal.context from handoff]

Please decompose this into 3-5 concrete subtasks that can be executed in parallel or sequence.
For each subtask:
1. Give it a clear title and type (code | analysis | design | research | validation)
2. Write the detailed input/requirements the executor needs
3. Define specific acceptance criteria
4. Suggest which agent type would be best (Opus for deep reasoning, Haiku for quick iteration, Codex for code, Claude for planning, Claude Code for interactive dev)
5. List any dependencies on other subtasks

Format as YAML subtasks I can copy into my handoff.yaml.
```

Fable generates the subtasks → you copy them into your handoff.

## Step 3: Execute One Subtask

Pick the first subtask. Copy its `input` section and give it to the assigned executor:

**For Opus/Haiku/Codex:**

```
[Copy the subtask.input here]

Success criteria:
[Copy the subtask.acceptance here]

Please execute and provide:
1. What you delivered
2. Any issues or blockers
3. What should happen next
```

**For Claude Code or interactive dev:**

```
I'm using the multi-model-orchestrator skill.

Subtask: [title]
Input: [input]
Acceptance: [acceptance]

Please execute this subtask. When done, I'll record the result in my handoff.yaml.
```

The executor completes the work.

## Step 4: Record Execution

Copy the result into your `execution.rounds` array:

```yaml
execution:
  rounds:
    - round: 1
      task_id: "task-1"
      executor: "Opus"
      status: "done"  # or "blocked" if it failed
      result: "[what was delivered]"
      issues: "[any blockers]"
      next_step: "[what's next]"
      timestamp: "2026-06-12T11:00:00Z"
```

## Step 5: Iterate or Complete

- **If blocked**: analyze the issue with the same executor or escalate to a different agent
- **If done**: move to the next subtask
- **If complete**: update `metadata.status` to "review" and optionally run a final review pass
