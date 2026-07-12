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
import argparse
import gzip
import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
import struct
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import zlib

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


def _recv_exact(sock, size):
    """Read exactly ``size`` bytes or fail on a truncated SOCKS frame."""
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise OSError(f"socks5 响应截断: 需要 {size} 字节, 只收到 {len(data)}")
        data.extend(chunk)
    return bytes(data)


def _socks5_connect(sock, host, port, user, pw):
    """在已连接 sock 上完成 socks5 握手，连到 host:port。"""
    if user:
        sock.sendall(b"\x05\x02\x00\x02")
    else:
        sock.sendall(b"\x05\x01\x00")
    resp = _recv_exact(sock, 2)
    if resp[0] != 5:
        raise OSError("socks5 握手失败")
    if resp[1] == 2:  # 需要认证
        if user is None or pw is None:
            raise OSError("socks5 服务端要求用户名密码")
        u = user.encode(); p = pw.encode()
        if len(u) > 255 or len(p) > 255:
            raise ValueError("socks5 用户名或密码超过 255 字节")
        sock.sendall(b"\x01" + bytes([len(u)]) + u + bytes([len(p)]) + p)
        a = _recv_exact(sock, 2)
        if a[1] != 0:
            raise OSError("socks5 认证失败")
    elif resp[1] != 0:
        raise OSError(f"socks5 不支持的认证方法 {resp[1]}")
    h = host.encode("idna")
    if len(h) > 255:
        raise ValueError("socks5 目标主机名超过 255 字节")
    sock.sendall(b"\x05\x01\x00\x03" + bytes([len(h)]) + h + struct.pack(">H", port))
    rep = _recv_exact(sock, 4)
    if rep[0] != 5 or rep[1] != 0:
        raise OSError(f"socks5 连接目标失败 rep={rep[1]}")
    # 读掉 BND.ADDR + PORT
    atyp = rep[3]
    if atyp == 1:
        _recv_exact(sock, 6)
    elif atyp == 3:
        ln = _recv_exact(sock, 1)[0]
        _recv_exact(sock, ln + 2)
    elif atyp == 4:
        _recv_exact(sock, 18)
    else:
        raise OSError(f"socks5 返回未知地址类型 {atyp}")


def _read_http_response(sock):
    """Parse one HTTP response, including chunked framing and compression."""
    response = http.client.HTTPResponse(sock, method="GET")
    response.begin()
    status = response.status
    body = response.read(65537)
    if len(body) > 65536:
        raise ValueError("HTTP 响应超过 64 KiB 上限")
    encoding = (response.getheader("Content-Encoding") or "").lower()
    if encoding == "gzip":
        body = gzip.decompress(body)
    elif encoding == "deflate":
        body = zlib.decompress(body)
    elif encoding not in {"", "identity"}:
        raise ValueError(f"不支持的 HTTP Content-Encoding: {encoding}")
    content_type = response.getheader("Content-Type") or ""
    charset_match = re.search(r"charset=([^;\s]+)", content_type, re.I)
    charset = charset_match.group(1).strip('"\'') if charset_match else "utf-8"
    return status, body.decode(charset, "replace")


def _get_via_socks5(url, proxy, host_header=None):
    host, port, user, pw = proxy
    target = urllib.parse.urlsplit(url)
    if target.scheme not in {"http", "https"} or not target.hostname:
        return None, "__err__:无效 HTTP(S) URL"
    thost = target.hostname
    tport = target.port or (443 if target.scheme == "https" else 80)
    path = urllib.parse.urlunsplit(("", "", target.path or "/", target.query, ""))
    default_port = 443 if target.scheme == "https" else 80
    if host_header:
        request_host = host_header
    elif ":" in thost:
        request_host = f"[{thost}]" + (f":{tport}" if tport != default_port else "")
    else:
        request_host = thost + (f":{tport}" if tport != default_port else "")
    raw = None
    sock = None
    try:
        raw = socket.create_connection((host, port), timeout=TIMEOUT)
        _socks5_connect(raw, thost, tport, user, pw)
        if target.scheme == "https":
            ctx = ssl.create_default_context()
            ctx.set_alpn_protocols(["http/1.1"])
            sock = ctx.wrap_socket(raw, server_hostname=thost)
        else:
            sock = raw
        req = (f"GET {path} HTTP/1.1\r\nHost: {request_host}\r\n"
               f"User-Agent: {UA}\r\nAccept: */*\r\nConnection: close\r\n\r\n")
        sock.sendall(req.encode())
        return _read_http_response(sock)
    except Exception as e:
        return None, f"__err__:{e}"
    finally:
        if sock is not None:
            sock.close()
        elif raw is not None:
            raw.close()


def _parse_proxy(arg):
    """Parse one complete socks5 URL without ever echoing credentials."""
    try:
        parsed = urllib.parse.urlsplit(arg)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("无效 socks5 代理地址") from exc
    if parsed.scheme not in {"socks5", "socks5h"}:
        raise ValueError("代理必须使用 socks5:// 或 socks5h://")
    if not parsed.hostname or port is None or not 1 <= port <= 65535:
        raise ValueError("socks5 代理必须包含有效 host:port")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("socks5 代理地址不能包含 path、query 或 fragment")
    if (parsed.username is None) != (parsed.password is None):
        raise ValueError("socks5 用户名和密码必须同时提供")
    user = urllib.parse.unquote(parsed.username) if parsed.username is not None else None
    pw = urllib.parse.unquote(parsed.password) if parsed.password is not None else None
    return parsed.hostname, port, user, pw


def parse_target(arg):
    """解析 IP 或完整 socks5 URL，返回 (ip_or_host, proxy_tuple_or_None)。"""
    if "://" in arg:
        proxy = _parse_proxy(arg)
        return proxy[0], proxy
    return arg, None


def _validated_ip(value):
    try:
        return str(ipaddress.ip_address(value))
    except ValueError as exc:
        raise ValueError("检测目标必须是有效 IP 地址") from exc


def _discover_exit_ip(proxy):
    status, body = _get("https://ipinfo.io/json", proxy=proxy)
    if status != 200 or not body or body.startswith("__err__"):
        raise RuntimeError("无法通过代理确认出口 IP")
    try:
        data = json.loads(body)
    except (TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("代理出口 IP 响应不是有效 JSON") from exc
    if not isinstance(data, dict):
        raise RuntimeError("代理出口 IP JSON 根节点必须是 object")
    value = data.get("ip")
    if not value:
        raise RuntimeError("代理出口 IP 响应缺少 ip 字段")
    try:
        return str(ipaddress.ip_address(value))
    except ValueError as exc:
        raise RuntimeError("代理出口 IP 响应包含无效地址") from exc


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
    out["lease_flag"] = bool(re.search(r"interlir|lease|ip.?broker|ip.?xo", ents, re.I))
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
def _dns_lookup(query):
    """Return answer/not_found/error so outages cannot look like clean DNSBLs."""
    not_found_codes = {socket.EAI_NONAME}
    if hasattr(socket, "EAI_NODATA"):
        not_found_codes.add(socket.EAI_NODATA)
    try:
        socket.setdefaulttimeout(6)
        return "answer", socket.gethostbyname(query)
    except socket.gaierror as exc:
        if exc.errno in not_found_codes:
            return "not_found", None
        return "error", str(exc)
    except (socket.timeout, OSError) as exc:
        return "error", str(exc)
    finally:
        socket.setdefaulttimeout(None)


def layer_dnsbl(ip):
    out = {"layer": "dnsbl", "status": "ok", "listed": [], "checked": []}
    parts = ip.split(".")
    if len(parts) != 4:
        out["status"] = "skip"; out["error"] = "非 IPv4"; return out
    rev = ".".join(reversed(parts))
    # 自检：DNSBL 命中的标准返回是 127.0.0.0/8。若环境有 fake-ip DNS 劫持
    # （如 Clash TUN 返回 198.18.x.x），任何查询都会"解析成功"，必须靠
    # 127.* 校验区分真命中；同时用一个不可能被列入的探针检测劫持。
    probe_state, probe = _dns_lookup(f"{rev}.zen.spamhaus.org.invalid-probe.")
    fakeip_hijack = probe_state == "answer"
    out["dns_hijack_detected"] = fakeip_hijack
    if fakeip_hijack:
        out["status"] = "unreliable"
        out["error"] = f"DNS 被劫持（探针返回 {probe}），DNSBL 不可信；请在非 TUN 网络重跑"
        return out
    if probe_state == "error":
        out["status"] = "unreliable"
        out["error"] = "DNS 探针查询失败，无法区分未列入与解析器故障"
        return out
    errors = []
    for zone, label in DNSBL_ZONES:
        state, res = _dns_lookup(f"{rev}.{zone}")
        if state == "error":
            errors.append(f"{label}: DNS 查询失败")
            continue
        out["checked"].append(label)
        if state == "not_found":
            continue
        if not res.startswith("127."):
            errors.append(f"{label}: 非法返回码 {res}")
            continue
        if zone == "zen.spamhaus.org" and res.startswith("127.255.255."):
            errors.append(f"{label}: Spamhaus 查询错误码 {res}")
            continue
        if res:
            out["listed"].append(label)
    if errors:
        out["status"] = "unreliable"
        out["error"] = "; ".join(errors)
    return out


# ---------- 第 6 层：住宅真实性（反向 DNS）----------
def layer_ptr(ip):
    out = {"layer": "ptr", "status": "ok", "ptr": None, "has_ptr": False}
    try:
        r = subprocess.run(["dig", "+short", "-x", ip], capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            detail = (r.stderr or r.stdout or f"dig exit {r.returncode}").strip()
            out["status"] = "error"
            out["error"] = detail[:120]
            return out
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
    errors = []
    for _ in range(3):
        st, b = _get("https://ipinfo.io/json", proxy=proxy)
        if st != 200 or not b or b.startswith("__err__"):
            out["samples"].append(None)
            errors.append("出口查询失败")
            time.sleep(0.5)
            continue
        try:
            data = json.loads(b)
            if not isinstance(data, dict):
                raise ValueError("出口响应 JSON 根节点不是 object")
            value = data.get("ip")
            out["samples"].append(_validated_ip(value) if value else None)
            if not value:
                errors.append("出口响应缺少 ip")
        except (TypeError, ValueError, json.JSONDecodeError):
            out["samples"].append(None)
            errors.append("出口响应无效")
        time.sleep(0.5)
    ips = [s for s in out["samples"] if s]
    out["stable"] = len(ips) == 3 and len(set(ips)) == 1
    out["exit_ip"] = ips[0] if ips else None
    if errors:
        out["status"] = "unreliable" if ips else "error"
        out["error"] = "; ".join(errors)
    return out


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main(argv=None):
    parser = _JsonArgumentParser(add_help=True)
    parser.add_argument("target")
    parser.add_argument("--proxy")
    try:
        options = parser.parse_args(argv)
        ip, target_proxy = parse_target(options.target)
        explicit_proxy = _parse_proxy(options.proxy) if options.proxy is not None else None
        if target_proxy and explicit_proxy:
            raise ValueError("代理 URL target 与 --proxy 不能同时使用")
        proxy = explicit_proxy or target_proxy
        if target_proxy:
            ip = _discover_exit_ip(proxy)
        else:
            ip = _validated_ip(ip)
    except (ValueError, RuntimeError) as exc:
        sys.stdout.write(json.dumps({"error": str(exc)}, ensure_ascii=False) + "\n")
        return 2

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
    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
