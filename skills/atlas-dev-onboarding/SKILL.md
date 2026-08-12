---
name: atlas-dev-onboarding
description: Use when a user asks to log in to Atlas dev, access the dev server or bastion, deploy aiproxy, run dev DMS/MySQL SQL, onboard a model or provider, refresh route caches, or test provider routing and VSR/ESR. Uses the verified origin-IP transport for console.dev.atlascloud.ai and guards deployment, credentials, and runtime proof.
---

# Atlas Dev Onboarding

Use the bundled transport for every Atlas dev SSH or SCP operation. Do not call
`ssh ... console.dev.atlascloud.ai` directly and do not try Cloudflare A records.

## Connect

Run:

```bash
"$SKILL_DIR/scripts/atlas-dev-ssh" '<remote command>'
"$SKILL_DIR/scripts/atlas-dev-scp" local-file /remote/path/
```

Resolve `SKILL_DIR` as this skill directory. The scripts use the verified origin
`47.251.103.202:30022` and host-key alias
`[console.dev.atlascloud.ai]:30022`. This bypasses both Clash fake IPs in
`198.18.0.0/15` and Cloudflare HTTP-only addresses.

If the connection fails, report the exact failure. Do not rediscover DNS, add
Clash rules, try `104.26.*`/`172.67.*`, or fall back to browser/cloud consoles.
Only override `ATLAS_DEV_SSH_HOST` when an operator supplies a new origin IP.

## Gotchas

- `198.18.*` is a Clash fake IP, not the dev server.
- `104.26.*` and `172.67.*` are Cloudflare HTTP proxy addresses, not SSH
  origins for port 30022.
- A successful TCP connect followed by an empty banner is not SSH access.
- `/api/v1/generateVideo` is not the aiproxy route; use
  `/api/v1/model/generateVideo`.
- Router selector values see the normalized request, so public `2K` is `2k`.
- A processing API response does not prove VSR submission or completion.

## Deploy safely

Before changing dev:

1. Inspect the remote repo status and current Deployment image.
2. Stop if `/root/code/aiproxy` has unrelated uncommitted changes.
3. Record the current image as the rollback point.
4. Deploy only a merged commit unless the user explicitly requests a branch build.
5. Confirm the image push succeeded before changing the Deployment.
6. Wait for rollout completion and inspect pod/image state.

If the live Deployment comes from a commit that is not in `origin/main`, preserve
that commit and integrate it with the requested merged main commit. Check the
merge base and file conflicts first. A feature commit may depend on foundation
files already present on main; do not cherry-pick it onto an older live branch
when Git reports modify/delete conflicts. Build the explicit integration commit
and record both parent SHAs.

For aiproxy, prefer the remote repository's `update.sh <unique-dev-tag>` workflow.
Use a tag containing the feature and short commit SHA.

## Apply SQL

- Dev only unless production is explicitly requested.
- Prefer DMS-compatible SQL: no temporary tables and no transaction dependency.
- Run read-only preflight queries first.
- Check collations for string columns used in cross-table joins. Atlas dev may
  mix `utf8mb4_unicode_ci` and `utf8mb4_0900_ai_ci`; use an explicit common
  collation instead of waiting for a mutation script to fail mid-run.
- Check request normalization before writing case-sensitive router selectors.
  Video generation lowercases `resolution` before selector evaluation, so a
  public `2K` request is matched as `2k` at routing time.
- Never print credentials, bearer tokens, database passwords, or signed URLs.
- Never print Kubernetes Secret data, ConfigMap contents, Pod environment values,
  or generic recursively transformed configuration: list-valued config can bypass
  naive key-based redaction. Extract required connection fields inside the remote
  process and print only safe fields plus secret lengths.
- After mutations, refresh model/router cache using the repository/runbook method.
- Run postflight queries and preserve sanitized evidence for production-style
  investigations.

## Verify runtime

Do not treat `/model/calculate=200` as route proof. Send a real request and verify
the selected provider and terminal result. For VSR/ESR, additionally prove a
non-empty `model_history.vsr_task_id` and inspect the matching `vsr_task` processor,
target resolution, and final status.

For aiproxy API smoke tests, follow the repository `AGENTS.md`: source the user's
shell environment, use the dev API base/key plus gateway header, and never print
secret values. The video submit path is
`POST /api/v1/model/generateVideo`; do not omit the `/model` segment.

Read [references/dev-deploy.md](references/dev-deploy.md) before a deployment or
database mutation.
