# Governance schema

Use one machine- or workspace-specific JSON document as the declared input to
the deterministic validator. Keep facts in the document and workflow rules in
`SKILL.md`.

## Required fields

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | integer | Must be `1`. |
| `source_policy` | object | Canonical local registry, active projections, and additional inventory roots. |
| `source_policy.local_only_canonical_registry` | string | Registry root that contains a `skills/` directory. `~` is expanded. |
| `source_policy.projection_roots` | string array | Existing runtime directories to audit. Include only in-scope roots. |
| `projection_runtimes` | string array | Optional (legacy schema). Runtimes receiving automatic global/project projections, from `codex`, `claude`, `agents`, `gemini`, `cursor`. Defaults to `["codex", "claude"]`, so omitting it preserves existing behaviour. Set it explicitly to `[]` to disable automatic links; `managed_global_sources` remain explicit per-Skill exceptions. Drives `projection_roots` and the per-project `<dir>/skills` globs. |
| `source_policy.projection_globs` | string array | Optional absolute path patterns for dynamic project/worktree projection roots. A pattern matching nothing is an error. |
| `source_policy.inventory_roots` | object array | Additional roots with explicit `path`, `kind`, and `owner`. |
| `source_policy.managed_physical_skills` | object | Exact physical runtime Skills mapped to the installer or source owner that manages them. |

## Optional governance fields

| Field | Meaning |
|---|---|
| `retired_skills` | Entry points that must not exist or be referenced in active Skills. |
| `quarantined_skills` | Sources that may remain stored but must not be projected. |
| `projection_denials` | Named policy records whose `projection` is `deny`. |
| `pinned_materializations` | Physical runtime copies verified against an exact source. |
| `retired_reference_allowlist` | Narrow `(skill, retired_name)` exceptions for non-invocation text. |
| `external_actions` | Account, remote, history, or review actions outside local proof. |
| `skill_decisions` | One evidence-backed decision per discovered name; when present, incomplete coverage is an error. |

Arrays default to empty. Do not invent a value to make validation pass.
Unknown top-level or `source_policy` fields are errors so misspelled safety
controls cannot silently become no-ops.

## Existing Loom-style policy

`ecosystem_doctor.py` also accepts an existing
`SKILL_GOVERNANCE_POLICY.json` containing trigger boundaries, project scopes,
worktree globs, cold storage, retired names, runtime mirrors, managed global
sources, and split declarations. It normalizes that document in memory for
auditing; it does not rewrite or migrate the file.

Legacy policy may also declare top-level `inventory_roots` using the same
`path`/`kind`/`owner` objects as `source_policy.inventory_roots`. Use this with
`projection_runtimes: []` to audit a package-managed physical catalog such as
`~/.agents/skills` without turning it into a symlink destination. Leave
`managed_global_sources` empty as well when the required plan is zero-link.

Deployed exposure fields are:

| Field | Meaning |
|---|---|
| `default_scope` | `global` for backward compatibility or `review` for explicit exposure. |
| `global_allowlist` | Canonical registry Skills allowed in every managed runtime. |
| `profiles` | Named, mutually exclusive groups retained for on-demand or project use. |
| `profile_scopes` | Exact project roots mapped to profile names. |
| `profile_scope_globs` | Dynamic project/worktree globs mapped to profile names. |
| `exposure_budget` | Maximum managed-global Skill count and description characters. |
| `plugin_states` | Exact configured plugin IDs mapped to enabled booleans. |
| `evidence_policy` | Read-only evidence controls such as the bulk-audit threshold. |

Every canonical registry Skill must resolve to one class: global, project,
profile, cold, review, or hidden. Profile names may not overlap. With
`default_scope: "review"`, undeclared Skills stay retained but unprojected.

Use `ecosystem_reconcile.py` for dry-run/apply exposure changes and
`ecosystem_split.py` for declared progressive-disclosure moves. These commands
consume the same policy, so do not create a second machine policy carrying
competing scope or retirement decisions.

## Additional inventory roots

Each root requires a path, a role, and the component responsible for it:

```json
{
  "path": "~/src/spellbook/skills",
  "kind": "canonical_source",
  "owner": "spellbook"
}
```

Supported `kind` values are:

- `canonical_source`: a writable source collection; every visible child
  directory must contain a usable `SKILL.md`
- `repository_source`: an independent repository whose root `SKILL.md` is a
  Skill and whose immediate child directories may also contain Skills; the root
  entry point is required and unrelated repository directories are ignored
- `managed_projection`: active runtime content owned by a package manager or
  runtime; physical copies do not require local source pins
- `managed_cache`: inactive package cache retained for provenance and conflict
  discovery
- `archive`: inactive recovery or evidence collection; archives are scanned
  recursively because dated recovery layouts add container directories, but
  archived content is never treated as active

Do not list the canonical Loom `skills/` path or a normal projection twice.
Managed roles document ownership; they do not authorize editing package caches.

## Per-Skill decisions

Each `skill_decisions` record requires `name`, `decision`, `reason`, and
`owner`:

```json
{
  "name": "example-skill",
  "decision": "keep",
  "reason": "Distinct capability with a maintained source and passing checks.",
  "owner": "spellbook",
  "canonical_path": "~/src/spellbook/skills/example-skill",
  "evidence": ["source review", "fresh validator run"]
}
```

Allowed decisions are `keep`, `repair`, `merge`, `quarantine`, `retire`,
`managed`, and `archive`. Optional `target` and string-array `evidence` fields
record the chosen source and proof. Use `canonical_path` when reviewed same-name
source variants intentionally coexist. The validator requires that path to
match a discovered instance; a verified declaration turns inactive divergence
into an informational finding, while divergent active projections remain an
error. Unknown ownership must be recorded as unresolved rather than guessed.

## Pinned materializations

Each item requires:

```json
{
  "name": "example-skill",
  "path": "~/.codex/skills/example-skill",
  "source_path": "~/src/example/skills/example-skill",
  "reason": "Installed by a source-controlled generator."
}
```

For composite installers, add exact file mappings:

```json
{
  "name": "queue-skill",
  "path": "~/.codex/skills/queue-skill",
  "source_path": "~/src/example/skills/queue-skill",
  "reason": "Skill plus a locked shared resource.",
  "resource_mappings": [
    {
      "source_path": "~/src/example/integrations/shared.md",
      "destination_path": "references/shared.md"
    }
  ]
}
```

`destination_path` must be relative and remain inside the materialization.
Duplicate destinations, self-sources, missing source files, or digest drift are
errors.

`source_path` may identify either a directory Skill or a canonical
`skills/<name>.SKILL.md` file Skill. File sources materialize as `SKILL.md` in
the pinned runtime directory.

## Projection denials

Use denials for sources that may be retained for evidence but cannot be active:

```json
{
  "name": "experimental-skill",
  "status": "expired_experimental",
  "projection": "deny",
  "reason": "Access contract and redistribution rights are not current."
}
```

Keep reasons factual. A denial does not authorize deleting the retained source.

## Path rules

- Use discovered paths, not copied machine assumptions.
- Prefer `~` to embedding a username when the path is user-relative.
- Add only roots that should be required for this run; configured missing roots
  are errors.
- Declare plugin caches as `managed_cache` and package-manager runtime roots as
  `managed_projection`; keep both outside writable source policy.
- Use `projection_globs` for repeated project worktrees instead of copying a
  changing list of roots. Globs are expanded without a shell and every match is
  scanned as an active managed projection.
- Never put credentials or credential values in the governance document.
