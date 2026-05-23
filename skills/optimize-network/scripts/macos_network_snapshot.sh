#!/usr/bin/env bash
set -u

section() {
  printf '\n## %s\n\n' "$1"
}

run() {
  printf '```bash\n$ %s\n' "$*"
  "$@" 2>&1 || true
  printf '```\n'
}

run_shell() {
  local label="$1"
  shift
  printf '```bash\n$ %s\n' "$label"
  "$@" 2>&1 || true
  printf '```\n'
}

mihomo_configs_summary() {
  python3 -c '
import json
import sys

data = json.load(sys.stdin)
tun = data.get("tun") or {}
summary = {
    "mode": data.get("mode"),
    "mixed_port": data.get("mixed-port"),
    "tun": {
        "enable": tun.get("enable"),
        "device": tun.get("device"),
        "stack": tun.get("stack"),
        "auto-route": tun.get("auto-route"),
        "auto-detect-interface": tun.get("auto-detect-interface"),
        "mtu": tun.get("mtu"),
        "dns-hijack": tun.get("dns-hijack"),
        "route-exclude-address-count": len(tun.get("route-exclude-address") or []),
    },
}
print(json.dumps(summary, ensure_ascii=False, indent=2))
'
}

mihomo_connections_summary() {
  python3 -c '
import json
import sys

data = json.load(sys.stdin)
summary = {
    "downloadTotal": data.get("downloadTotal"),
    "uploadTotal": data.get("uploadTotal"),
    "connectionCount": len(data.get("connections") or []),
}
print(json.dumps(summary, ensure_ascii=False, indent=2))
'
}

export -f mihomo_configs_summary
export -f mihomo_connections_summary

gateway="$(route -n get default 2>/dev/null | awk '/gateway:/ {print $2; exit}')"
run_networkquality="${RUN_NETWORKQUALITY:-0}"

printf '# macOS Network Snapshot\n\n'
printf -- '- Timestamp: %s\n' "$(date '+%Y-%m-%d %H:%M:%S %z')"
printf -- '- Host: %s\n' "$(hostname 2>/dev/null || true)"
printf -- '- RUN_NETWORKQUALITY: %s\n' "$run_networkquality"

section "System"
run uname -a
run sw_vers

section "Tool Availability"
run_shell 'for tool in networkQuality speedtest-cli speedtest dig scutil networksetup system_profiler nettop lsof curl jq; do command -v "$tool" || true; done' \
  bash -lc 'for tool in networkQuality speedtest-cli speedtest dig scutil networksetup system_profiler nettop lsof curl jq; do command -v "$tool" || true; done'

section "Route Proxy DNS State"
run scutil --nwi
run scutil --proxy
run_shell "scutil --dns | sed -n '1,120p'" bash -lc "scutil --dns | sed -n '1,120p'"
run route -n get default
run networksetup -getcurrentlocation
run networksetup -listlocations
run networksetup -listnetworkserviceorder

section "Interfaces"
run networksetup -listallhardwareports
run_shell "ifconfig | sed -n '/^[a-z].*flags=/p'" bash -lc "ifconfig | sed -n '/^[a-z].*flags=/p'"

section "Wi-Fi"
run_shell "system_profiler SPAirPortDataType | sed -n '/Current Network Information:/,/Other Local Wi-Fi Networks:/p'" \
  bash -lc "system_profiler SPAirPortDataType | sed -n '/Current Network Information:/,/Other Local Wi-Fi Networks:/p'"

section "Gateway Ping"
if [[ -n "$gateway" ]]; then
  printf 'Detected gateway: `%s`\n\n' "$gateway"
  run ping -c 20 "$gateway"
else
  printf 'No default gateway detected.\n'
fi

section "Public Ping"
run ping -c 10 223.5.5.5
run ping -c 10 1.1.1.1

section "MTU Probe"
if [[ -n "$gateway" ]]; then
  run ping -D -s 1472 -c 3 "$gateway"
fi
run ping -D -s 1472 -c 3 223.5.5.5

section "DNS Timing"
run_shell 'for host in chatgpt.com api.openai.com github.com www.baidu.com www.apple.com.cn; do dig +tries=1 +time=2 +stats "$host" A | egrep "HEADER|ANSWER|Query time|SERVER"; done' \
  bash -lc 'for host in chatgpt.com api.openai.com github.com www.baidu.com www.apple.com.cn; do printf "\n# %s\n" "$host"; dig +tries=1 +time=2 +stats "$host" A | egrep "HEADER|ANSWER|Query time|SERVER"; done'

section "HTTP Timing"
run_shell 'for url in https://chatgpt.com https://github.com https://api.openai.com https://www.baidu.com https://www.apple.com.cn; do curl -o /dev/null -s -L --max-time 10 -w ... "$url"; done' \
  bash -lc 'for url in https://chatgpt.com https://github.com https://api.openai.com https://www.baidu.com https://www.apple.com.cn; do printf "\n# %s\n" "$url"; curl -o /dev/null -s -L --max-time 10 -w "http=%{http_code} dns=%{time_namelookup} connect=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total}\n" "$url"; done'

section "Network Processes"
run_shell "nettop -P -L 1 -J bytes_in,bytes_out -m tcp | head -60" \
  bash -lc "nettop -P -L 1 -J bytes_in,bytes_out -m tcp | head -60"

section "Mihomo Read-only State"
if [[ -S /tmp/verge/verge-mihomo.sock ]]; then
  run_shell "curl --unix-socket /tmp/verge/verge-mihomo.sock http://localhost/configs" \
    bash -c 'curl -s --max-time 2 --unix-socket /tmp/verge/verge-mihomo.sock http://localhost/configs | mihomo_configs_summary 2>/dev/null || echo "Unable to parse Mihomo configs summary; raw config intentionally not printed."'
  run_shell "curl --unix-socket /tmp/verge/verge-mihomo.sock http://localhost/connections" \
    bash -c 'curl -s --max-time 2 --unix-socket /tmp/verge/verge-mihomo.sock http://localhost/connections | mihomo_connections_summary 2>/dev/null || echo "Unable to parse Mihomo connection summary; raw connections intentionally not printed."'
else
  printf 'Mihomo Unix socket not found at /tmp/verge/verge-mihomo.sock.\n'
fi

if [[ "$run_networkquality" == "1" ]]; then
  section "networkQuality"
  run networkQuality -v
else
  section "networkQuality"
  printf 'Skipped. Re-run with RUN_NETWORKQUALITY=1 to include bandwidth/responsiveness metrics.\n'
fi
