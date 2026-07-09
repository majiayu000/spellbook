#!/usr/bin/env python3
"""IP 质量检测 — 确定性层。

分层检测一个 IP（可选带 socks5 代理凭证）的质量，输出结构化 JSON 供 skill 判定层裁决。
纯 stdlib，无第三方依赖。任何单项数据源失败不影响其它项（不静默降级，失败项显式标 error）。

用法:
  python3 ipcheck.py <IP>
  python3 ipcheck.py socks5://user:pass@host:port      # 带凭证，多跑代理实测层
  python3 ipcheck.py <IP> --proxy socks5://user:pass@host:port  # IP 和代理分开
  环境变量 IPQS_KEY / ABUSEIPDB_KEY 存在时自动启用对应检测
"""
import json
import os
import re
import socket
import ssl
import struct
import subprocess
import sys
import time
import urllib.request

TIMEOUT = 12
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# 真 ISP 白名单（ASN 主体关键词）
REAL_ISP = ["comcast", "at&t", "att ", "verizon", "charter", "spectrum",
            "cox ", "t-mobile", "centurylink", "frontier", "lumen",
            "google fiber", "sonic", "windstream"]

# AWS 区域端点（非 anycast，位置确定）用于延迟三角测量
AWS_REGIONS = [
    ("us-west-2", "美西俄勒冈"), ("us-east-1", "美东弗吉尼亚"),
    ("us-east-2", "美东俄亥俄"), ("eu-west-3", "巴黎"),
    ("eu-central-1", "法兰克福"), ("eu-south-2", "西班牙"),
    ("eu-west-1", "爱尔兰"), ("ap-northeast-1", "东京"),
    ("sa-east-1", "巴西圣保罗"), ("ap-southeast-1", "新加坡"),
]

# 目标服务探测：host, 期望路径, 区块特征关键词
# 目标服务探测：host, label, url, 区块特征关键词（必须是精确短语，避免 SPA 空壳误报）。
# 首页 GET 拿到的多是 SPA shell，region_blocked 只是弱启发信号；cf_loc / http_status 才是硬信号。
SERVICE_PROBES = [
    ("grok.com", "grok.com", "https://grok.com/", ["grok is not available in your", "not available in your country or region"]),
    ("chatgpt.com", "OpenAI ChatGPT", "https://chatgpt.com/cdn-cgi/trace", []),
    ("api.anthropic.com", "Anthropic API", "https://api.anthropic.com/v1/messages", []),
]

DNSBL_ZONES = [
    ("zen.spamhaus.org", "Spamhaus ZEN"),
    ("b.barracudacentral.org", "Barracuda"),
    ("dnsbl.sorbs.net", "SORBS"),
    ("bl.spamcop.net", "SpamCop"),
]


def _get(url, proxy=None, host_header=None):
    """HTTP GET，返回 (status, body_text)。proxy 为 socks5 tuple 时走代理。"""
    if proxy:
        return _get_via_socks5(url, proxy, host_header)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, f"__err__:{e}"


def _socks5_connect(sock, host, port, user, pw):
    """在已连接 sock 上完成 socks5 握手，连到 host:port。"""
    if user:
        sock.sendall(b"\x05\x02\x00\x02")
    else:
        sock.sendall(b"\x05\x01\x00")
    resp = sock.recv(2)
    if len(resp) < 2 or resp[0] != 5:
        raise OSError("socks5 握手失败")
    if resp[1] == 2:  # 需要认证
        u = user.encode(); p = pw.encode()
        sock.sendall(b"\x01" + bytes([len(u)]) + u + bytes([len(p)]) + p)
        a = sock.recv(2)
        if len(a) < 2 or a[1] != 0:
            raise OSError("socks5 认证失败")
    elif resp[1] != 0:
        raise OSError(f"socks5 不支持的认证方法 {resp[1]}")
    h = host.encode()
    sock.sendall(b"\x05\x01\x00\x03" + bytes([len(h)]) + h + struct.pack(">H", port))
    rep = sock.recv(4)
    if len(rep) < 2 or rep[1] != 0:
        raise OSError(f"socks5 连接目标失败 rep={rep[1] if len(rep)>1 else '?'}")
    # 读掉 BND.ADDR + PORT
    atyp = rep[3] if len(rep) >= 4 else 1
    if atyp == 1:
        sock.recv(6)
    elif atyp == 3:
        ln = sock.recv(1)[0]; sock.recv(ln + 2)
    elif atyp == 4:
        sock.recv(18)


def _get_via_socks5(url, proxy, host_header=None):
    host, port, user, pw = proxy
    m = re.match(r"https?://([^/]+)(/.*)?$", url)
    thost = m.group(1); path = m.group(2) or "/"
    tport = 443 if url.startswith("https") else 80
    try:
        raw = socket.create_connection((host, port), timeout=TIMEOUT)
        _socks5_connect(raw, thost, tport, user, pw)
        if tport == 443:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            s = ctx.wrap_socket(raw, server_hostname=thost)
        else:
            s = raw
        req = (f"GET {path} HTTP/1.1\r\nHost: {thost}\r\n"
               f"User-Agent: {UA}\r\nAccept: */*\r\nConnection: close\r\n\r\n")
        s.sendall(req.encode())
        buf = b""
        while len(buf) < 65536:
            try:
                chunk = s.recv(4096)
            except Exception:
                break
            if not chunk:
                break
            buf += chunk
        s.close()
        text = buf.decode("utf-8", "replace")
        status = None
        mm = re.match(r"HTTP/[\d.]+ (\d+)", text)
        if mm:
            status = int(mm.group(1))
        body = text.split("\r\n\r\n", 1)[1] if "\r\n\r\n" in text else text
        return status, body
    except Exception as e:
        return None, f"__err__:{e}"


def parse_target(arg):
    """解析 IP 或 socks5://user:pass@host:port，返回 (ip_or_host, proxy_tuple_or_None)。"""
    m = re.match(r"socks5h?://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)", arg)
    if m:
        user, pw, host, port = m.group(1), m.group(2), m.group(3), int(m.group(4))
        return host, (host, port, user, pw)
    return arg, None


# ---------- 第 1 层：RDAP 注册库 ----------
def layer_rdap(ip):
    out = {"layer": "rdap", "status": "ok"}
    st, body = _get(f"https://rdap.org/ip/{ip}")
    if st != 200 or body.startswith("__err__"):
        # 回退到 arin rdap
        st, body = _get(f"https://rdap.arin.net/registry/ip/{ip}")
    try:
        d = json.loads(body)
    except Exception:
        out["status"] = "error"; out["error"] = body[:200]; return out
    out["handle"] = d.get("handle")
    out["name"] = d.get("name")
    out["country"] = d.get("country")
    # 注册库：从 port43 或 links 判断
    port43 = d.get("port43", "")
    rir = "?"
    for tag, r in [("arin", "ARIN"), ("ripe", "RIPE"), ("apnic", "APNIC"),
                   ("lacnic", "LACNIC"), ("afrinic", "AFRINIC")]:
        if tag in port43.lower() or tag in json.dumps(d.get("links", [])).lower():
            rir = r; break
    out["rir"] = rir
    ents = json.dumps(d.get("entities", []))
    out["mnt_lease_flag"] = bool(re.search(r"interlir|lease|ip.?broker|ip.?xo", ents, re.I))
    org = None
    for e in d.get("entities", []):
        va = e.get("vcardArray")
        if va and len(va) > 1:
            for item in va[1]:
                if item[0] == "fn":
                    org = item[3]; break
        if org:
            break
    out["org"] = org
    return out


# ---------- 第 2 层：地理三库 ----------
def layer_geo(ip):
    out = {"layer": "geo", "status": "ok", "sources": {}}
    st, b = _get(f"https://ipinfo.io/{ip}/json")
    try:
        d = json.loads(b); out["sources"]["ipinfo"] = {"country": d.get("country"), "region": d.get("region"), "city": d.get("city"), "org": d.get("org")}
    except Exception:
        out["sources"]["ipinfo"] = {"error": b[:120]}
    st, b = _get(f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,regionName,city,isp,org,as,proxy,hosting")
    try:
        d = json.loads(b); out["sources"]["ip-api"] = {"country": d.get("countryCode"), "region": d.get("regionName"), "city": d.get("city"), "isp": d.get("isp"), "proxy": d.get("proxy"), "hosting": d.get("hosting")}
    except Exception:
        out["sources"]["ip-api"] = {"error": b[:120]}
    st, b = _get(f"https://ipwho.is/{ip}")
    try:
        d = json.loads(b); out["sources"]["ipwho"] = {"country": d.get("country_code"), "region": d.get("region"), "city": d.get("city"), "connection": (d.get("connection") or {}).get("isp")}
    except Exception:
        out["sources"]["ipwho"] = {"error": b[:120]}
    countries = [v.get("country") for v in out["sources"].values() if isinstance(v, dict) and v.get("country")]
    out["countries"] = countries
    out["consensus"] = len(set(countries)) == 1 and len(countries) >= 2
    out["split"] = len(set(countries)) > 1
    return out


# ---------- 第 3 层：ASN/org 一致性 ----------
def layer_asn(geo, rdap):
    out = {"layer": "asn", "status": "ok"}
    ipinfo = geo.get("sources", {}).get("ipinfo", {})
    asn_org = (ipinfo.get("org") or "")
    out["asn_org"] = asn_org
    out["is_real_isp"] = any(k in asn_org.lower() for k in REAL_ISP)
    rdap_org = (rdap.get("org") or "")
    out["rdap_org"] = rdap_org
    # ASN 主体 vs org 是否一致（org 陌生 = 租赁段特征）
    asn_body = re.sub(r"^AS\d+\s*", "", asn_org).lower()
    out["org_matches_asn"] = bool(rdap_org and asn_body and (
        rdap_org.lower()[:6] in asn_body or asn_body[:6] in rdap_org.lower()))
    return out


# ---------- 第 4 层：风控库 ----------
def layer_reputation(ip):
    out = {"layer": "reputation", "status": "ok", "sources": {}}
    # proxycheck.io（免费无 key 100/天）
    st, b = _get(f"https://proxycheck.io/v2/{ip}?vpn=3&asn=1&risk=2")
    try:
        d = json.loads(b).get(ip, {})
        out["sources"]["proxycheck"] = {"proxy": d.get("proxy"), "vpn": d.get("vpn"), "type": d.get("type"), "risk": d.get("risk")}
    except Exception:
        out["sources"]["proxycheck"] = {"error": b[:120]}
    # ipapi.is（免费）
    st, b = _get(f"https://api.ipapi.is/?q={ip}")
    try:
        d = json.loads(b)
        out["sources"]["ipapi_is"] = {k: d.get(k) for k in ("is_datacenter", "is_tor", "is_proxy", "is_vpn", "is_abuser")}
        out["sources"]["ipapi_is"]["company_type"] = (d.get("company") or {}).get("type")
        out["sources"]["ipapi_is"]["asn_type"] = (d.get("asn") or {}).get("type")
    except Exception:
        out["sources"]["ipapi_is"] = {"error": b[:120]}
    # AbuseIPDB（需 key）
    key = os.environ.get("ABUSEIPDB_KEY")
    if key:
        req = urllib.request.Request(
            f"https://api.abuseipdb.com/api/v2/check?ipAddress={ip}&maxAgeInDays=90",
            headers={"Key": key, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                d = json.loads(r.read()).get("data", {})
            out["sources"]["abuseipdb"] = {"score": d.get("abuseConfidenceScore"), "reports": d.get("totalReports"), "usage": d.get("usageType")}
        except Exception as e:
            out["sources"]["abuseipdb"] = {"error": str(e)[:120]}
    else:
        out["sources"]["abuseipdb"] = {"skipped": "no ABUSEIPDB_KEY"}
    # IPQualityScore（需 key）
    qkey = os.environ.get("IPQS_KEY")
    if qkey:
        st, b = _get(f"https://ipqualityscore.com/api/json/ip/{qkey}/{ip}")
        try:
            d = json.loads(b)
            out["sources"]["ipqs"] = {k: d.get(k) for k in ("fraud_score", "proxy", "vpn", "tor", "recent_abuse", "bot_status", "connection_type")}
        except Exception:
            out["sources"]["ipqs"] = {"error": b[:120]}
    else:
        out["sources"]["ipqs"] = {"skipped": "no IPQS_KEY"}
    return out


# ---------- 第 5 层：DNSBL 黑名单 ----------
def layer_dnsbl(ip):
    out = {"layer": "dnsbl", "status": "ok", "listed": [], "checked": []}
    parts = ip.split(".")
    if len(parts) != 4:
        out["status"] = "skip"; out["error"] = "非 IPv4"; return out
    rev = ".".join(reversed(parts))
    # 自检：DNSBL 命中的标准返回是 127.0.0.0/8。若环境有 fake-ip DNS 劫持
    # （如 Clash TUN 返回 198.18.x.x），任何查询都会"解析成功"，必须靠
    # 127.* 校验区分真命中；同时用一个不可能被列入的探针检测劫持。
    def _resolve(q):
        try:
            socket.setdefaulttimeout(6)
            return socket.gethostbyname(q)
        except socket.gaierror:
            return None
        except Exception:
            return None
        finally:
            socket.setdefaulttimeout(None)

    probe = _resolve(f"{rev}.zen.spamhaus.org.invalid-probe.")  # 应永远解析失败
    fakeip_hijack = probe is not None
    out["dns_hijack_detected"] = fakeip_hijack
    if fakeip_hijack:
        out["status"] = "unreliable"
        out["error"] = f"DNS 被劫持（探针返回 {probe}），DNSBL 不可信；请在非 TUN 网络重跑"
        return out
    for zone, label in DNSBL_ZONES:
        res = _resolve(f"{rev}.{zone}")
        if res and res.startswith("127."):
            out["listed"].append(label)
        out["checked"].append(label)
    return out


# ---------- 第 6 层：住宅真实性（反向 DNS）----------
def layer_ptr(ip):
    out = {"layer": "ptr", "status": "ok"}
    try:
        r = subprocess.run(["dig", "+short", "-x", ip], capture_output=True, text=True, timeout=10)
        ptr = r.stdout.strip().rstrip(".")
        out["ptr"] = ptr or None
        # 真住宅特征：hsd1 / dsl / cable / dyn / res 等
        out["residential_pattern"] = bool(ptr and re.search(
            r"hsd1|dsl|cable|dyn|res|broadband|fios|\.comcast\.|\.rr\.com|\.charter\.", ptr, re.I))
        out["has_ptr"] = bool(ptr)
    except Exception as e:
        out["status"] = "error"; out["error"] = str(e)[:120]
    return out


# ---------- 第 7 层：BGP 宣告 / RPKI（RIPEstat）----------
def layer_bgp(ip):
    out = {"layer": "bgp", "status": "ok"}
    st, b = _get(f"https://stat.ripe.net/data/prefix-overview/data.json?resource={ip}")
    try:
        d = json.loads(b).get("data", {})
        asns = d.get("asns", [])
        out["announced_by"] = [{"asn": a.get("asn"), "holder": a.get("holder")} for a in asns]
        out["prefix"] = d.get("resource")
    except Exception:
        out["status"] = "error"; out["error"] = b[:120]
    return out


# ---------- 第 8 层：目标服务实测（需代理）----------
def layer_services(proxy):
    out = {"layer": "services", "status": "ok", "results": {}}
    for host, label, url, block_kw in SERVICE_PROBES:
        st, body = _get(url, proxy=proxy)
        entry = {"http_status": st}
        low = (body or "").lower()
        if st is None:
            entry["reachable"] = False; entry["note"] = body[:80]
        else:
            entry["reachable"] = True
            entry["region_blocked"] = any(k in low for k in block_kw) if block_kw else None
            m = re.search(r"loc=([A-Z]{2})", body)  # cloudflare trace 有 loc=US
            if m:
                entry["cf_loc"] = m.group(1)
        out["results"][label] = entry
    return out


# ---------- 第 9 层：延迟三角测量 + 出口稳定性（需代理）----------
def layer_latency(proxy):
    out = {"layer": "latency", "status": "ok", "regions": {}}
    for region, label in AWS_REGIONS:
        best = None
        for _ in range(3):
            t0 = time.time()
            st, _b = _get(f"https://ec2.{region}.amazonaws.com/", proxy=proxy)
            if st is not None:
                dt = (time.time() - t0) * 1000
                best = dt if best is None else min(best, dt)
        if best is not None:
            out["regions"][label] = round(best)
    if out["regions"]:
        ranked = sorted(out["regions"].items(), key=lambda kv: kv[1])
        out["closest"] = ranked[0][0]
        out["ranked"] = ranked
    return out


def layer_exit(proxy):
    out = {"layer": "exit", "status": "ok", "samples": []}
    for _ in range(3):
        st, b = _get("https://ipinfo.io/json", proxy=proxy)
        try:
            out["samples"].append(json.loads(b).get("ip"))
        except Exception:
            out["samples"].append(None)
        time.sleep(0.5)
    ips = [s for s in out["samples"] if s]
    out["stable"] = len(set(ips)) == 1 and len(ips) >= 2
    out["exit_ip"] = ips[0] if ips else None
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(json.dumps({"error": "用法: ipcheck.py <IP|socks5://user:pass@host:port> [--proxy socks5://...]"}))
        sys.exit(1)
    target = args[0]
    ip, proxy = parse_target(target)
    # 显式 --proxy 覆盖
    for i, a in enumerate(sys.argv):
        if a == "--proxy" and i + 1 < len(sys.argv):
            _, proxy = parse_target(sys.argv[i + 1])
    # 如果 target 是代理且没解析出裸 IP，先通过代理拿出口 IP 当作被检测 IP
    if proxy and not re.match(r"^\d+\.\d+\.\d+\.\d+$", ip):
        st, b = _get("https://ipinfo.io/json", proxy=proxy)
        try:
            ip = json.loads(b).get("ip", ip)
        except Exception:
            pass

    report = {"ip": ip, "has_proxy": bool(proxy), "layers": {}}
    rdap = layer_rdap(ip); report["layers"]["rdap"] = rdap
    geo = layer_geo(ip); report["layers"]["geo"] = geo
    report["layers"]["asn"] = layer_asn(geo, rdap)
    report["layers"]["reputation"] = layer_reputation(ip)
    report["layers"]["dnsbl"] = layer_dnsbl(ip)
    report["layers"]["ptr"] = layer_ptr(ip)
    report["layers"]["bgp"] = layer_bgp(ip)
    if proxy:
        report["layers"]["services"] = layer_services(proxy)
        report["layers"]["exit"] = layer_exit(proxy)
        report["layers"]["latency"] = layer_latency(proxy)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
