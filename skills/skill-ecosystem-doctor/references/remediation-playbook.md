# Remediation playbook

Use this reference only after the read-only audit identifies concrete findings.

## Priority order

1. Embedded credentials, injection, destructive path handling, or unauthorized
   remote actions.
2. Logic that silently produces missing or wrong output.
3. Canonical-source and projection conflicts.
4. Retired or denied entry points that remain active.
5. Broken resources, names, metadata, or advisory quality issues.

Fix a red build or failing source test before adding new behavior.

## Security findings

- Reproduce the unsafe path without printing secret values.
- Clear active literals and change loading to an environment or secret manager.
- Prevent credentials from entering argv, logs, URLs, reports, or redirect
  targets.
- Parameterize SQL and pass OS commands as argument arrays.
- Isolate unreviewed deployment or publishing Skills from active projections.
- Record account-side rotation as external until the platform confirms it.
- Treat history rewriting as a separate destructive action requiring explicit
  authorization.

## Source and projection conflicts

- Resolve every candidate path and inspect Git history, registry records,
  installer ownership, locks, tests, and current runtime links.
- Do not select by modification time alone.
- Patch the canonical source, run its tests, regenerate outputs, then replace
  the projection.
- For a physical copy that must remain, pin its source and every generated or
  shared resource that contributes to its installed digest.
- Quarantine superseded physical copies with a dated path and record their
  original location and digest.

## Retirement

1. Search registrations, rules, docs, aliases, installer sources, manifests,
   projections, and active references.
2. Identify neutral assets still used by maintained workflows and migrate only
   those assets to a neutral owner.
3. Remove the old entry point without a compatibility alias.
4. Regenerate registries and installer state.
5. Reinstall from the modified source in an isolated environment.
6. Require zero active paths and zero invocation references for the retired
   name. Allow only exact, documented non-invocation text exceptions.

## Safe quarantine

Prefer quarantine to recursive deletion:

- use a unique dated directory outside active roots
- reject symlink or traversal ambiguity before moving
- preserve file mode and content
- record source path, destination path, timestamp, reason, and digest
- verify the active path is gone and the quarantine copy is readable
- do not clean quarantine automatically during the same workflow

## High-risk semantic review

Inspect Skills that can deploy, publish, delete, modify databases, change
credentials, edit high-context files, or operate unattended. Require:

- read-only or report-only defaults
- explicit current-turn authorization for mutations
- bounded targets and batch sizes
- fail-closed behavior for missing data or failed validation
- backups and integrity checks before destructive local maintenance
- exact postconditions and non-zero failure exits

If semantics remain uncertain, deny projection and document reconsideration
conditions instead of inventing a safe rewrite.

## Review and delivery

- Keep unrelated user changes unstaged.
- Run `git diff --check`, targeted tests, full relevant tests, registry checks,
  and the ecosystem audit.
- Prepare a review pack that lists high-context files, generated outputs,
  security-sensitive changes, warnings, and rollback paths.
- Push a feature branch rather than a protected branch unless the request
  explicitly requires and authorizes the latter.
- Never claim completion while required external rotation, review, or remote
  synchronization is presented as locally verified.
