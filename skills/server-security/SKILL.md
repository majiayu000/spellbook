---
name: server-security
description: 服务器安全审计与加固。扫描 SSH、防火墙、端口暴露、文件权限、暴力破解等安全问题，生成报告并提供一键修复。当用户说服务器安全、安全审计、安全检查、安全加固时使用
allowed-tools: Bash, AskUserQuestion
metadata:
  argument-hint: "<ssh连接串> 如 root@1.2.3.4"
---

# Server Security Audit

Use this skill for server security audits and reversible hardening plans across SSH, firewall, users, services, file permissions, and update posture.

## Routing

- Start here to confirm scope, safety boundaries, and the minimum workflow.
- Load `references/full-guide.md` before executing detailed commands, applying templates, or relying on examples from this skill.
- Keep the work limited to the user-requested target; do not add adjacent improvements unless the user asks.

## Quick Workflow

1. Confirm the target, available context, constraints, and done-when signal.
2. Read the relevant section of `references/full-guide.md` for task-specific details.
3. Execute the smallest reversible action that satisfies the request.
4. Verify with read-only evidence first, then document every applied change with rollback commands and post-change validation.
5. Report changed files, commands run, evidence collected, and any remaining risk.

## References

- `references/full-guide.md` - complete command patterns, examples, checklists, and edge cases.
