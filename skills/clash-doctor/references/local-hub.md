# Local Hub Profile

Load this before `hub`, `align`, `roles`, `clone`, `setup-ai`, or `switch`, and whenever the user says the config did not take effect.

Do not copy personal node names, hostnames, IP addresses, credentials, or profile UIDs into this file. Ask the user for the live values needed by the current task.

## Source of truth

Some setups use a local hub profile rather than a remote subscription YAML as the live configuration. In that case:

- `profiles.yaml` points `current` at a `type: local` profile.
- Nodes and groups live in that local YAML body.
- Empty enhancement files do not mean the hub is unconfigured.
- `setup-ai <target>` must inspect the named target's type. A local target uses its hub YAML; a remote target uses its own enhancement overlays, regardless of the current profile.

After an enhancement or hub-YAML write, quit and reopen Clash Verge. `PUT /configs` reloads the merged output but does not re-merge overlays.

## Node roles

There is no single best egress. Split by job:

| Job | Typical egress | Do not treat it as |
|---|---|---|
| Login-sensitive AI | Clean residential or ISP-looking exit | A high-bandwidth download pipe |
| Daily browsing and nearby latency | Nearby VPS | An AI identity |
| Stable US-ISP identity | Consumer-ISP VPS with consistent geo | The only required node |
| US bulk download | US datacenter VPS | An identity exit when geo databases disagree |

Typical hub groups are `Proxies` for nearby latency and `AI`, `Codex`, or `X` for identity-sensitive traffic. Confirm live group names from `/proxies`; do not invent them. Keep `ipv6: false` unless every group has a clean IPv6 path because dual-stack splits can trigger abnormal-traffic checks.

## Recurring landmines

1. `tun.route-exclude-address` is union-only. Never replace the list with one service's IPs.
2. `DIRECT` still traverses TUN. If `route get <IP>` shows `utun*` or `198.18.0.1`, Clash still owns the packet. Self-hosted relays may need a `/32` exclusion on every live profile merge.
3. Excluding a proxy-node server IP from TUN can break the path to that node and make every dependent group fail. Require explicit confirmation after explaining the impact.
4. `sniffer.parse-pure-ip: true` is required for connection-table hostnames. Restart Clash Verge after changing it.
5. Large downloads should not share an identity exit. Keep identity-sensitive APIs on the clean exit and use a bandwidth node for update or CDN traffic.

Use placeholders in reports and examples:

```text
<RELAY_IP>/32
<EXIT_SERVER_IP>/32
<LOCAL_HUB_NAME>
<REMOTE_MAC_A>
<REMOTE_MAC_B>
```

## Align, read-only

For other computers in the user's tailnet, use Tailscale SSH and command-line inspection. Print a comparison table and do not call the machines aligned when any cell fails.

| Check | Local | Remote A | Remote B |
|---|---|---|---|
| `current` is the intended local hub | | | |
| Required role nodes exist in `/proxies` | | | |
| Identity groups select the intended exit | | | |
| `Proxies` selects the nearby exit | | | |
| Merge retains required relay and tailnet CIDRs | | | |
| `parse-pure-ip` has the intended value | | | |
| A mihomo endpoint answers successfully | | | |

## Switch, clone, and setup-ai

- Run `switch-check` first. Missing required CIDRs, role nodes, or groups blocks the switch.
- `clone` copies enhancement overlays only between remote profiles. For a local profile, show and patch the hub YAML instead.
- Resolve the named `setup-ai` target and inspect its type before selecting a write path.
- Custom nodes must not exist only in a duplicate remote profile that Clash Verge can delete.
- Never paste the user's live profile UID, credentials, or inventory into git.
