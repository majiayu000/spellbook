---
name: multi-model-orchestrator
description: Use when coordinating complex tasks across multiple AI agents with a centralized handoff document for planning, execution tracking, and feedback fusion.
---

# multi-model-orchestrator

**Decompose. Execute. Synthesize.**

A lightweight skill for coordinating work across multiple AI agents (Claude, Opus, Haiku, Codex, or any agent) using a single **handoff document** as the source of truth.

## Why This Skill

Complex work often requires:
1. **High-level planning** — breaking down a big goal into concrete subtasks
2. **Parallel execution** — different agents handling different task types simultaneously
3. **Feedback synthesis** — collecting results and iterating intelligently
4. **Full traceability** — understanding who did what, why, and what changed

This skill provides the **structure and templates** to do this cleanly.

## Operating Contract

Direct actions: create or update one handoff document as the source of truth, decompose the goal into executor-ready subtasks, assign explicit dependencies, record execution results, and synthesize feedback into next steps.

Escalate before: starting execution when the goal, constraints, executor choice, writable scope, or done criteria are ambiguous.

Evidence-backed pushback: reject unverified completion claims, vague agent outputs, missing acceptance criteria, or parallel assignments that touch shared writable files without explicit ordering.

Feedback loop: after each execution round, update the handoff with result, evidence, blockers, and next action before assigning follow-up work.

## When to Use

✅ **Use when:**
- A single-agent conversation would be too long or unfocused
- You want to parallelize work across multiple specialized agents
- You need to decompose a vague goal into specific, executor-ready tasks
- You want to track decisions, changes, and feedback in one place
- You're exploring multiple approaches simultaneously (A/B/C branches)

❌ **Don't use when:**
- The task is simple and one agent can handle it end-to-end
- You don't need to track who did what
- Execution is strictly sequential with no parallelization
- The task is exploratory with no clear structure

## Core Concepts

### Handoff Document (Handoff)

A **YAML file** that serves as the single source of truth. It contains:

- **Goal** — what are we trying to accomplish?
- **Subtasks** — who does what, and what does success look like?
- **Context** — code references, prior decisions, constraints
- **Execution Tracking** — who executed, what was the result, what blockers?
- **Feedback** — iterations, changes, and learnings

### Agent Roles

You choose which agents execute which subtasks. Examples:

| Agent | Best For |
|-------|----------|
| **Claude (or Fable)** | Planning, decomposition, architecture review, high-level strategy |
| **Opus** | Complex reasoning, deep analysis, novel problem-solving |
| **Haiku** | Fast iteration, simple fixes, quick validation |
| **Codex** | Code generation, refactoring, technical implementation |
| **Claude Code** | Interactive development, running code, verification |

### The Loop

```
1. Define Goal
    ↓
2. Fable/Claude decomposes into Handoff subtasks
    ↓
3. You assign subtasks to agents
    ↓
4. Agents execute in parallel or sequence
    ↓
5. You record results in Handoff
    ↓
6. Review, iterate, or complete
```

## Quick Start

The full five-step walkthrough with copy-paste templates lives in [`references/quick-start.md`](./references/quick-start.md). Summary:

1. **Create handoff** — copy [`templates/handoff-template.yaml`](./templates/handoff-template.yaml) to `.claude/handoffs/my-task.yaml`.
2. **Decompose** — ask Fable/Claude to break the goal into 3-5 subtasks; paste into `subtasks`.
3. **Execute** — give each subtask's `input` to its assigned executor.
4. **Record** — append the result to `execution.rounds`.
5. **Iterate or complete** — update `metadata.status` toward `complete`.

Field-by-field reference: [`references/handoff-structure.md`](./references/handoff-structure.md).

## Complete Example

See [`references/add-auth-to-api.yaml`](./references/add-auth-to-api.yaml) for a real-world multi-agent execution walkthrough.

## Using with Claude Code

1. Save your handoff to `.claude/handoffs/task.yaml`
2. Run: `cat .claude/handoffs/task.yaml` to load it in conversation
3. Ask Claude to execute a subtask
4. When done, update the handoff manually or using a script

For automation, see [`references/advanced-sync.md`](./references/advanced-sync.md).

## Using with Codex

Codex does not have handoff-specific subcommands. Use `codex exec` with a focused prompt that names the handoff file and the exact subtask:

```bash
codex exec "Read .claude/handoffs/task.yaml. Execute subtask task-1 only. Return the result, blockers, files changed, and verification evidence."
```

For decomposition:

```bash
codex exec "Read .claude/handoffs/task.yaml. Propose 3-5 YAML subtasks using goal.summary, goal.context, and goal.acceptance_criteria. Do not edit files."
```

## Resources

- **Templates**: [`templates/handoff-template.yaml`](./templates/handoff-template.yaml)
- **Real example**: [`references/add-auth-to-api.yaml`](./references/add-auth-to-api.yaml)
- **Detailed references**:
  - [`references/quick-start.md`](./references/quick-start.md) — full five-step walkthrough with templates
  - [`references/handoff-structure.md`](./references/handoff-structure.md) — handoff YAML field reference
  - [`references/workflow-patterns.md`](./references/workflow-patterns.md) — parallel / sequential / sync-point layouts
  - [`references/best-practices.md`](./references/best-practices.md) — high-signal subtask authoring
  - [`references/advanced-sync.md`](./references/advanced-sync.md) — optional handoff automation
  - [`references/faq.md`](./references/faq.md) — common questions
- **Companion tools**: Codex (code-focused multi-agent router), Claude Code (interactive execution)

---

**Status**: Production ready · **License**: MIT
