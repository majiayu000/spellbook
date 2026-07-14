# Lifecycle drift review

Use this reference when a Skill stopped triggering after a runtime upgrade,
contains time-sensitive dependencies, or has not been verified recently.

## Evidence order

1. Identify the canonical owner and every active projection.
2. Read Git history, package or plugin version records, installer pins, current
   runtime configuration, and fresh test output.
3. Record optional metadata such as `version`, `last_verified`, `tested_on`,
   `external_deps`, or `provenance` when it exists. An absent field means
   `unknown`; it is not a failure by itself.
4. For an external repository, API, package, or model, verify the current
   contract through an authoritative source before claiming it is live, changed,
   or gone. If network evidence is unavailable, mark the dependency `unverified`.
5. For trigger drift, compare the current frontmatter description with current
   runtime discovery behavior and reproduce the missed trigger when possible.
   Do not infer a runtime matching rule from an old model name or anecdote.

## Status vocabulary

- `verified`: fresh source-specific tests and runtime resolution support the
  current contract.
- `needs_verification`: the source is coherent, but fresh behavioral evidence
  is missing.
- `stale`: current evidence proves a dependency, trigger, or runtime assumption
  no longer holds.
- `blocked_external`: verification or repair requires an unavailable account,
  service, license, or remote permission.
- `unknown`: required evidence was not found; do not convert this to a score.

## Report fields

For each affected Skill report:

- declared name and canonical owner;
- source and active projection paths;
- most recent verifiable test, commit, package, and usage evidence;
- external dependency status with the supporting source;
- trigger reproduction evidence;
- status and concrete risk;
- smallest repair, rollback path, and fresh verification command.

Do not require every Skill to embed a copied health block, an arbitrary number
of trigger phrases, or speculative version metadata. Update maintenance fields
only after the corresponding test or source check actually ran.
