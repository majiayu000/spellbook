# Runtime and ownership contracts

Use these as discovery hints, then verify actual paths, links, Git history, and
installer behavior on the current machine.

## Ownership classes

| Class | Evidence | Default treatment |
|---|---|---|
| Independent Git source | `.git`, remote or explicit local ownership, source tests | Canonical when ownership is verified. Edit in a clean worktree. |
| Local registry source | Registry metadata plus tracked Skill directory | Canonical for local-only Skills. |
| Managed projection | Symlink, copy record, lock, or installer manifest | Regenerate from source; do not edit directly. |
| Generated/plugin cache | Package-manager or plugin-owned path | Read-only evidence; change the upstream package or plugin. |
| Unknown physical copy | No source record or exact pin | Warn, preserve, and resolve ownership before mutation. |

## Common discovery candidates

- Codex: user Skill roots reported by the current installation, commonly
  `~/.codex/skills` or `~/.agents/skills`.
- Claude Code: the active user or project Skill roots, commonly
  `~/.claude/skills`.
- Loom: its configured workspace, commonly `~/.loom-registry`, plus registered
  targets, bindings, projections, provenance locks, and `workspace doctor`.
- VibeGuard: installed snapshot, source revision, manifest, rules, workflows,
  and install verification command.
- Spellbook: Git source under `skills/`, generated registry files, installer,
  and runtime symlinks.
- Plugin bundles: cache directories exposed by the runtime. Treat them as
  package-owned unless the plugin contract says otherwise.

Never assume that a common candidate exists or is active. Use runtime commands,
link resolution, registry records, and fresh state queries.

## Source precedence

1. Prefer a verified independent Git source over a copied local directory.
2. Prefer an explicit local registry record over an untracked runtime copy.
3. Treat an exact pinned materialization as a projection, not a second source.
4. Treat equal names with different digests as unresolved until ownership and
   tests identify the intended source.
5. Keep restricted, expired, or unreviewed third-party content retained but
   unprojected when reuse rights or runtime behavior are uncertain.

## Repository boundaries

- Read every applicable high-context instruction file before editing.
- Preserve dirty user work; do not stage or commit unrelated files.
- Use the repository's own generator for registry, lock, or manifest output.
- Run source-specific tests before replacing runtime projections.
- Commit or push only when the current request grants that exact action and any
  repository review gate is satisfied.

## Handoff fields

Record at least:

```yaml
handoff:
  mode: plan_first
  objective:
  artifacts: []
  runtime_snapshot:
  writable_paths: []
  verification_owner:
  stop_conditions: []
  external_actions: []
```

Blank means unknown or not applicable. Do not fill it with a plausible guess.
