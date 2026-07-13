# Governance schema

Use one machine- or workspace-specific JSON document as the declared input to
the deterministic validator. Keep facts in the document and workflow rules in
`SKILL.md`.

## Required fields

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | integer | Must be `1`. |
| `source_policy` | object | Canonical local registry and active projection roots. |
| `source_policy.local_only_canonical_registry` | string | Registry root that contains a `skills/` directory. `~` is expanded. |
| `source_policy.projection_roots` | string array | Existing runtime directories to audit. Include only in-scope roots. |

## Optional governance fields

| Field | Meaning |
|---|---|
| `retired_skills` | Entry points that must not exist or be referenced in active Skills. |
| `quarantined_skills` | Sources that may remain stored but must not be projected. |
| `projection_denials` | Named policy records whose `projection` is `deny`. |
| `pinned_materializations` | Physical runtime copies verified against an exact source. |
| `retired_reference_allowlist` | Narrow `(skill, retired_name)` exceptions for non-invocation text. |
| `external_actions` | Account, remote, history, or review actions outside local proof. |

Arrays default to empty. Do not invent a value to make validation pass.
Unknown top-level or `source_policy` fields are errors so misspelled safety
controls cannot silently become no-ops.

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
- Keep plugin caches and package-manager projections outside writable source
  policy unless their owner explicitly documents a safe mutation path.
- Never put credentials or credential values in the governance document.
