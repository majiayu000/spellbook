---
name: clash-doctor
description: Clash Verge 诊断与配置管理。网络诊断、配置 AI 工具路由规则（Claude/Codex/Cursor/Warp）、查看/克隆订阅配置、切换配置文件。当用户遇到网络问题、要配置代理规则、切换订阅、查看 Clash 配置时使用
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
metadata:
  argument-hint: '[诊断域名 | profiles | clone <源> <目标> | setup-ai <订阅名> | switch <订阅名>]'
---

# Clash Verge Diagnostics

Use this skill for Clash Verge / Mihomo profile inspection, AI-tool route setup, active profile switching, and connectivity diagnosis.

## Routing

- Start here to confirm scope, safety boundaries, and the minimum workflow.
- Load `references/full-guide.md` before executing detailed commands, applying templates, or relying on examples from this skill.
- Keep the work limited to the user-requested target; do not add adjacent improvements unless the user asks.

## Quick Workflow

1. Confirm the target, available context, constraints, and done-when signal.
2. Read the relevant section of `references/full-guide.md` for task-specific details.
3. Execute the smallest reversible action that satisfies the request.
4. Verify with profile JSON/YAML parsing, Mihomo API or local connectivity probes, and a clear rollback path for any profile write.
5. Report changed files, commands run, evidence collected, and any remaining risk.

## References

- `references/full-guide.md` - complete command patterns, examples, checklists, and edge cases.
