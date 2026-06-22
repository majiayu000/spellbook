# Advanced: Handoff Sync (Optional)

Part of the `multi-model-orchestrator` skill. The core skill works with manual
YAML editing. Load this only if you want to automate handoff updates.

If you want to automate handoff updates (instead of manual YAML editing):

1. **Python script** (if you need it):
   ```python
   import yaml

   with open('.claude/handoffs/task.yaml') as f:
       handoff = yaml.safe_load(f)

   handoff['execution']['rounds'].append({
       'round': 2,
       'task_id': 'task-1',
       'executor': 'Opus',
       'status': 'done',
       'result': '...',
       'timestamp': '2026-06-12T12:00:00Z'
   })

   with open('.claude/handoffs/task.yaml', 'w') as f:
       yaml.dump(handoff, f)
   ```

2. **CLI wrapper** (if you have one):
   ```bash
   handoff-update task-1 --executor opus --status done \
     --result "What was delivered" \
     --next-step "What's next"
   ```

3. **No automation**: just edit the YAML manually (perfectly fine).
