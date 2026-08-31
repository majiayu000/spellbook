---
name: clash-routes
description: >
  查看本机进程的 Mihomo 实时代理链。当用户问 Claude、Codex、Gemini、ChatGPT、
  浏览器或其他进程走哪个代理时使用。只读。Profile 拓扑和写入使用 clash-doctor，
  出口 IP 质量使用 ip-check。
allowed-tools: Bash
metadata:
  argument-hint: "[process，默认显示全部]"
---

# Clash 线路查看工具

查看本机当前活跃连接，确认指定进程命中的规则、策略组与真实出口。不接受 SSH 参数；远程机器应先通过 Tailscale SSH 登录，再在目标机器执行同一只读流程。

用户传入的参数：$ARGUMENTS。没有参数时列出所有活跃连接。诊断 Gemini、ChatGPT 或浏览器流量时，先不加过滤获取实际 `metadata.process`，再使用观察到的进程名；不要假定它们属于 `claude`。

## 获取凭证

读取 Clash Verge 配置，但不要打印 secret：

```bash
SECRET=$(grep '^secret:' "$HOME/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/clash-verge.yaml" 2>/dev/null | awk '{print $2}')
[ -z "$SECRET" ] && SECRET=$(grep '^secret:' "$HOME/.config/clash/config.yaml" 2>/dev/null | awk '{print $2}')
[ -n "$SECRET" ] && echo "API secret: configured" || echo "API secret: not configured"
```

## 查询与回退

请求成功才采用该 endpoint。`/tmp` socket 存在但失效时继续尝试 `/var/tmp`，最后尝试配置的 HTTP controller。所有 endpoint 都失败时明确报错，不返回空数据。

```bash
request_connections() {
  for socket_path in \
    /tmp/verge/verge-mihomo.sock \
    /var/tmp/verge/verge-mihomo.sock
  do
    [ -S "$socket_path" ] || continue
    if curl --fail --silent --show-error \
      --unix-socket "$socket_path" \
      "http://localhost/connections" \
      -H "Authorization: Bearer $SECRET"
    then
      return 0
    fi
  done

  controller=$(grep '^external-controller:' "$HOME/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/clash-verge.yaml" 2>/dev/null | awk '{print $2}' | tr -d "'\"")
  [ -n "$controller" ] || controller="127.0.0.1:9090"
  curl --fail --silent --show-error \
    "http://$controller/connections" \
    -H "Authorization: Bearer $SECRET"
}

if ! DATA=$(request_connections); then
  echo "无法从 Mihomo Unix socket 或 HTTP controller 获取连接数据" >&2
  exit 1
fi

if ! printf '%s' "$DATA" | python3 -c 'import json, sys; value=json.load(sys.stdin); assert isinstance(value.get("connections"), list)' 2>/dev/null; then
  echo "Mihomo 返回了无效的 connections JSON" >&2
  exit 1
fi
```

## 解析并展示

通过环境变量传递过滤值，避免把用户输入插进 Python 源码：

```bash
printf '%s' "$DATA" | FILTER="$ARGUMENTS" python3 -c '
import json
import os
import sys
from collections import defaultdict

data = json.load(sys.stdin)
process_filter = os.environ.get("FILTER", "").strip().lower()
results = []

for connection in data.get("connections", []):
    metadata = connection.get("metadata", {})
    process = metadata.get("process", "unknown")
    if process_filter and process_filter not in process.lower():
        continue
    host = metadata.get("host", "") or metadata.get("destinationIP", "")
    port = metadata.get("destinationPort", "")
    rule = connection.get("rule", "")
    payload = connection.get("rulePayload", "")
    if payload:
        rule += "/" + payload
    chains = connection.get("chains", [])
    chain_text = " → ".join(reversed(chains)) if chains else "DIRECT"
    results.append({
        "process": process,
        "host": f"{host}:{port}" if port else host,
        "rule": rule,
        "chain": chain_text,
    })

grouped = defaultdict(list)
for result in results:
    grouped[result["process"]].append(result)

if not grouped:
    target = process_filter or "任何进程"
    print(f"未找到 {target} 的活跃连接")
    raise SystemExit(0)

for process, connections in sorted(grouped.items()):
    print(f"\n进程: {process} ({len(connections)} 个连接)")
    route_stats = defaultdict(lambda: {"count": 0, "hosts": set()})
    for connection in connections:
        key = "{} → {}".format(connection["rule"], connection["chain"])
        route_stats[key]["count"] += 1
        route_stats[key]["hosts"].add(connection["host"])
    for route, info in sorted(route_stats.items(), key=lambda item: -item[1]["count"]):
        hosts = sorted(info["hosts"])
        shown = ", ".join(hosts[:5])
        suffix = f" ... (+{len(hosts) - 5})" if len(hosts) > 5 else ""
        print(f"  线路: {route}")
        print("  连接数: {}".format(info["count"]))
        print(f"  目标: {shown}{suffix}")
'
```

## 解释结果

- `chains[-1]` 是命中的策略组，`chains[0]` 是真实出口；展示时反转为“策略组 → 出口”。
- Claude 常见进程是 `claude` 或 `Claude Helper`；Codex CLI 常见进程是 `codex`。
- Gemini CLI、ChatGPT 桌面端和浏览器的进程名以未过滤连接表为准。
- Host 只有裸 IP 时，检查 `sniffer.parse-pure-ip` 和系统 DNS 是否绕过 Clash，不要直接改 AI 策略组。
- 当前 profile 不是预期 Hub，或出口仍是原始订阅节点时，报告 drift；本 skill 不修改 YAML。

## 完成条件

- 至少一个 Mihomo endpoint 返回合法 connections JSON。
- 输出明确显示进程、规则、策略组和出口，或明确说明目标进程当前没有活跃连接。
- 全程只读且没有打印 API secret。
