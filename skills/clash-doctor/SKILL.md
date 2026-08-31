---
name: clash-doctor
description: >
  Clash Verge 与 mihomo 诊断和 profile 管理。当用户遇到代理失败、需要配置
  AI 工具路由、本地 Hub 拓扑、多机对齐、TUN 绕过、克隆或切换订阅，或同步后
  配置未生效时使用。进程线路使用 clash-routes，出口 IP 质量使用 ip-check。
  普通网络测速不使用。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
metadata:
  argument-hint: '[host | profiles | status | hub | align | roles | switch-check <name> | clone <src> <dst> | setup-ai <name> | switch <name> | rustdesk <IP> | bypass <IP>]'
---

# Clash Verge Diagnostics

Inspect Clash Verge or mihomo, manage profile-specific routing, and diagnose connectivity.

## Routing

- Confirm the target profile, constraints, requested access path, and done-when signal.
- Load `references/full-guide.md` for commands, templates, and diagnosis matrices.
- Load `references/local-hub.md` before `hub`, `align`, `roles`, `clone`, `setup-ai`, or `switch`, and whenever the user says a previous sync did not apply.
- Keep the change limited to the requested target.

## Safety

- Diagnose and align are read-only. Writes require a shown summary and explicit confirmation.
- Edit enhancement overlays or the confirmed local-hub YAML. Do not edit raw subscription dumps.
- `tun.route-exclude-address` is union-only. `DIRECT` is not a TUN bypass.
- Never invent or print node IPs, credentials, subscription UIDs, or machine hostnames.
- After an overlay or hub-YAML write, quit and reopen Clash Verge. `PUT /configs` does not re-merge overlays.

## Modes

| Argument | Mode |
|---|---|
| empty or a hostname | diagnose |
| `profiles` / `list` / `ls` | list local and remote profiles |
| `status` | live kernel, TUN, and selected nodes |
| `hub` / `roles` | local-hub topology |
| `align` / `sync-check` | read-only multi-machine comparison |
| `switch-check` / `health` | pre-switch health |
| `clone` / `setup-ai` / `switch` | confirmed profile writes |
| `rustdesk` / `bypass` | TUN exclusion for a relay IP |

Resolve the named target before `setup-ai`. Apply airport-style enhancement overlays only when that target is `type: remote`; edit the named hub YAML when it is `type: local`.

## Verify

- Parse the target YAML after every write.
- Query mihomo by trying both Unix sockets and then the configured HTTP controller; fall back on request failure, not socket existence alone.
- For routes, `chains[-1]` is the matched group and `chains[0]` is the dialed node.
- Report files changed, commands run, evidence, and remaining risk.

## References

- `references/full-guide.md` — commands, templates, and diagnosis matrix
- `references/local-hub.md` — hub ownership, node roles, alignment, and landmines
