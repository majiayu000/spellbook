# Atlas dev deployment reference

## Transport invariant

- SSH origin: `47.251.103.202`
- Port: `30022`
- Default user: `root`
- Host-key alias: `[console.dev.atlascloud.ai]:30022`

The hostname is behind Cloudflare and local Clash may resolve it to a fake IP.
Cloudflare's public A records do not proxy SSH on port 30022. A TCP connection
followed by `kex_exchange_identification` or an empty SSH banner is therefore not
evidence that the bastion is down.

Never use these as SSH destinations:

- `console.dev.atlascloud.ai`
- `198.18.*` fake IPs
- `104.26.*` or `172.67.*` Cloudflare addresses

## Read-only preflight

```bash
scripts/atlas-dev-ssh '
  set -eu
  cd /root/code/aiproxy
  git status --short --branch
  git rev-parse --short HEAD
  kubectl get deployment -n atlascloud-dev aiproxy \
    -o jsonpath="{.spec.template.spec.containers[0].image}{\"\\n\"}"
'
```

Record the current image before deployment.

If the Deployment annotation points at a commit outside main, inspect that
commit and its containing branch. Preserve the live hotfix by merging current
main into it (or use an equivalent isolated integration worktree). Do not deploy
plain main if doing so would remove the hotfix. Do not force a cherry-pick when
the requested change modifies files absent from the live baseline; that means
its foundation dependencies are missing.

## Deployment

On the bastion, verify the repo is clean, fetch the merged commit, and invoke
`update.sh` with a unique dev image tag. Do not run `kubectl set image` after a
failed build or push. Wait for:

```bash
kubectl rollout status deployment/aiproxy -n atlascloud-dev --timeout=300s
```

Then inspect the actual pod image IDs, readiness, and recent logs.

## SQL and cache

Run SQL only after its preflight expectations match the live dev topology. Use
the secured server-side database environment or DMS; never expose passwords in
command output. After route/model mutations, restart or refresh aiproxy according
to the current runbook and wait for readiness.

Do not dump `aiproxy-config` or Pod environment JSON for discovery. YAML lists can
carry secrets under nested keys and defeat simple top-level redaction. Parse the
specific MySQL entry inside an SSH process, assign host/user/password to process
variables, and expose only host, username, and password length.

Before executing a multi-statement rollout, inspect `information_schema.COLUMNS`
for cross-table string joins. In the current dev schema, `model.name` uses
`utf8mb4_unicode_ci`, while `model_router.model` uses
`utf8mb4_0900_ai_ci`; explicitly collate comparisons to one side.

Router selectors are exclusion rules and string comparisons are case-sensitive.
Inspect middleware normalization order before choosing selector values. The
aiproxy video path lowercases `resolution` before routing (`2K` becomes `2k`).

## Acceptance

For model routing, capture:

- request session ID;
- selected provider;
- terminal status and reachable output;
- billing amount when applicable;
- for VSR/ESR, `model_history.vsr_task_id` and matching `vsr_task` source,
  processor, target resolution, and final status.

Do not claim deployment success from SQL rows, `/calculate`, or a processing
response alone.
