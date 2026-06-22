# FAQ

Part of the `multi-model-orchestrator` skill. Common questions. Load this when
something about the workflow is unclear.

**Q: Can I use this with Claude, Opus, Haiku, Grok, Mistral, etc.?**

A: Yes. The skill is agent-agnostic. Use any LLM model. The `executor` field is just a label.

**Q: Should I commit handoffs to git?**

A: Commit handoffs only when the repository is private or the file has been
reviewed for secrets, customer data, internal plans, and copied prompts/logs.
For sensitive work, keep handoffs outside git or commit a redacted summary.

**Q: Can I parallelize execution?**

A: Yes. If subtasks have no dependencies, execute them simultaneously. Record results when they finish.

**Q: What if a subtask blocks?**

A: Record it in `execution.rounds` with `status: blocked`. Decide whether to:
1. Fix the blocker and retry
2. Reassign to a different agent
3. Escalate to human review

**Q: How long should a subtask be?**

A: Aim for 15-60 minute chunks. If a subtask would take 4+ hours, break it down further.

**Q: Can I have multiple handoffs active?**

A: Yes. Use separate files: `task-1.yaml`, `task-2.yaml`. Each one is independent.

**Q: How is this different from running agents sequentially?**

A: This skill structures the work so:
- Multiple agents can work in parallel
- Results are centralized in one document
- Changes and decisions are all traceable
- You can review and optimize the overall plan, not just individual agent outputs
