# Handoff Structure Reference

Part of the `multi-model-orchestrator` skill. Field-by-field reference for the
handoff YAML. Load this when you need to recall an exact field name, type, or
purpose.

### `metadata`

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `name` | string | yes | Human-readable task name |
| `created` | date | yes | When the handoff was created |
| `goal` | string | yes | Summary of what we are doing |
| `status` | enum | yes | planning \| executing \| review \| complete |

### `goal`

| Field | Type | Purpose |
|-------|------|---------|
| `summary` | string | Detailed description of the goal |
| `acceptance_criteria` | array | Testable completion conditions |
| `context` | string | Background, constraints, prior decisions |

### `subtasks`

| Field | Type | Purpose |
|-------|------|---------|
| `id` | string | Unique identifier (e.g. task-1, task-auth-setup) |
| `title` | string | Short, clear description |
| `type` | enum | code \| analysis \| design \| research \| validation |
| `executor` | string | Which agent: Opus, Haiku, Codex, Claude, Claude Code |
| `input` | string | Everything the executor needs to know |
| `acceptance` | string | How to verify completion |
| `depends_on` | array | List of task IDs this depends on |
| `status` | enum | pending \| in-progress \| done \| blocked |

### `execution.rounds`

| Field | Type | Purpose |
|-------|------|---------|
| `round` | number | Iteration number |
| `task_id` | string | Which subtask was executed |
| `executor` | string | Which agent did it |
| `status` | enum | done \| blocked \| partial |
| `result` | string | What was delivered |
| `issues` | string | Blockers or concerns |
| `next_step` | string | Recommendation for next action |
| `timestamp` | ISO 8601 | When it was executed |

### `feedback`

| Field | Type | Purpose |
|-------|------|---------|
| `synthesis` | string | Overall assessment: what worked, what didn't, what changed |
| `improvements` | array | List of ideas for next iteration |
| `decision_log` | string | Why we made certain choices and tradeoffs |
