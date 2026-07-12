"""Focused regression tests for the ip-check network protocol helpers."""

from __future__ import annotations

import importlib.util
import io
import json
import socket
import ssl
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "ip-check" / "scripts" / "ipcheck.py"
SPEC = importlib.util.spec_from_file_location("ipcheck", SCRIPT)
ipcheck = importlib.util.module_from_spec(SPEC)
sys.modules["ipcheck"] = ipcheck
SPEC.loader.exec_module(ipcheck)


class FragmentedSocket:
    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.sent = []
        self.closed = False

    def recv(self, size):
        if not self.chunks:
            return b""
        chunk = self.chunks.pop(0)
        if len(chunk) > size:
            self.chunks.insert(0, chunk[size:])
            return chunk[:size]
        return chunk

    def sendall(self, data):
        self.sent.append(data)

    def close(self):
        self.closed = True


class SocksProtocolTests(unittest.TestCase):
    def test_recv_exact_reassembles_fragmented_frames(self):
        sock = FragmentedSocket([b"a", b"bc", b"def"])

        self.assertEqual(ipcheck._recv_exact(sock, 6), b"abcdef")

    def test_recv_exact_rejects_truncated_frames(self):
        sock = FragmentedSocket([b"ab"])

        with self.assertRaisesRegex(OSError, "响应截断"):
            ipcheck._recv_exact(sock, 3)

    def test_socks_handshake_reads_every_frame_exactly(self):
        sock = FragmentedSocket([
            b"\x05", b"\x00",
            b"\x05\x00", b"\x00", b"\x01",
            b"\x7f", b"\x00\x00", b"\x01\x1f\x90",
        ])

        ipcheck._socks5_connect(sock, "example.com", 443, None, None)

        self.assertEqual(sock.sent[0], b"\x05\x01\x00")
        self.assertIn(b"example.com", sock.sent[1])

    def test_socks_username_password_and_domain_reply(self):
        sock = FragmentedSocket([
            b"\x05\x02", b"\x01\x00",
            b"\x05\x00\x00\x03", b"\x03", b"abc\x1f\x90",
        ])

        ipcheck._socks5_connect(sock, "example.com", 443, "user", "pass")

        self.assertEqual(sock.sent[0], b"\x05\x02\x00\x02")
        self.assertIn(b"user", sock.sent[1])

    def test_socks_rejects_auth_and_connect_failures(self):
        cases = [
            [b"\x04\x00"],
            [b"\x05\xff"],
            [b"\x05\x02"],
            [b"\x05\x00", b"\x05\x05\x00\x01"],
        ]
        for frames in cases:
            with self.subTest(frames=frames), self.assertRaises(OSError):
                ipcheck._socks5_connect(
                    FragmentedSocket(frames), "example.com", 443, None, None
                )

    def test_socks_rejects_oversized_credentials(self):
        sock = FragmentedSocket([b"\x05\x02"])

        with self.assertRaises(ValueError):
            ipcheck._socks5_connect(sock, "example.com", 443, "u" * 256, "p")

    def test_chunked_http_response_is_deframed(self):
        client, server = socket.socketpair()
        body = b'{"ip":"1.2.3.4"}'
        first, second = body[:7], body[7:]
        response = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json; charset=utf-8\r\n"
            b"Transfer-Encoding: chunked\r\n\r\n"
            + f"{len(first):X}\r\n".encode() + first + b"\r\n"
            + f"{len(second):X}\r\n".encode() + second + b"\r\n"
            + b"0\r\n\r\n"
        )
        try:
            server.sendall(response)
            server.shutdown(socket.SHUT_WR)

            status, decoded = ipcheck._read_http_response(client)
        finally:
            client.close()
            server.close()

        self.assertEqual(status, 200)
        self.assertEqual(json.loads(decoded)["ip"], "1.2.3.4")

    def test_http_response_decodes_gzip_and_rejects_unknown_encoding(self):
        for encoding, encoded in [
            ("gzip", ipcheck.gzip.compress(b"payload")),
            ("deflate", ipcheck.zlib.compress(b"payload")),
        ]:
            client, server = socket.socketpair()
            response = (
                b"HTTP/1.1 200 OK\r\nContent-Encoding: " + encoding.encode()
                + f"\r\nContent-Length: {len(encoded)}\r\n\r\n".encode() + encoded
            )
            try:
                server.sendall(response)
                server.shutdown(socket.SHUT_WR)
                self.assertEqual(ipcheck._read_http_response(client), (200, "payload"))
            finally:
                client.close()
                server.close()

        client, server = socket.socketpair()
        try:
            server.sendall(
                b"HTTP/1.1 200 OK\r\nContent-Encoding: br\r\n"
                b"Content-Length: 1\r\n\r\nx"
            )
            server.shutdown(socket.SHUT_WR)
            with self.assertRaisesRegex(ValueError, "Content-Encoding"):
                ipcheck._read_http_response(client)
        finally:
            client.close()
            server.close()

    def test_plain_http_socks_path_uses_real_http_parser(self):
        client, server = socket.socketpair()
        try:
            server.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok")
            server.shutdown(socket.SHUT_WR)
            with (
                mock.patch.object(ipcheck.socket, "create_connection", return_value=client),
                mock.patch.object(ipcheck, "_socks5_connect"),
            ):
                status, body = ipcheck._get_via_socks5(
                    "http://example.com:443/x?q=1", ("proxy", 1080, None, None)
                )
        finally:
            server.close()

        self.assertEqual((status, body), (200, "ok"))
        self.assertTrue(client._closed)

    def test_socks_http_rejects_invalid_target_url(self):
        status, body = ipcheck._get_via_socks5(
            "file:///tmp/secret", ("proxy", 1080, None, None)
        )

        self.assertIsNone(status)
        self.assertIn("无效", body)

    def test_https_probe_keeps_default_certificate_verification(self):
        raw = FragmentedSocket([])

        class GuardContext:
            @property
            def check_hostname(self):
                return True

            @check_hostname.setter
            def check_hostname(self, _value):
                raise AssertionError("hostname verification must stay enabled")

            @property
            def verify_mode(self):
                return ssl.CERT_REQUIRED

            @verify_mode.setter
            def verify_mode(self, _value):
                raise AssertionError("certificate verification must stay enabled")

            def set_alpn_protocols(self, protocols):
                self.protocols = protocols

            def wrap_socket(self, _raw, server_hostname):
                self.server_hostname = server_hostname
                raise ssl.SSLCertVerificationError("self-signed certificate")

        context = GuardContext()
        with (
            mock.patch.object(ipcheck.socket, "create_connection", return_value=raw),
            mock.patch.object(ipcheck, "_socks5_connect"),
            mock.patch.object(ipcheck.ssl, "create_default_context", return_value=context),
        ):
            status, body = ipcheck._get_via_socks5(
                "https://example.com:8443/data", ("proxy.example", 1080, None, None)
            )

        self.assertIsNone(status)
        self.assertIn("self-signed certificate", body)
        self.assertEqual(context.server_hostname, "example.com")
        self.assertEqual(context.protocols, ["http/1.1"])
        self.assertTrue(raw.closed)


class ProxyInputTests(unittest.TestCase):
    def test_proxy_parser_requires_a_complete_socks_url(self):
        invalid = [
            "socks://host:1080",
            "host:1080",
            "socks5://host",
            "socks5://user@host:1080",
            "socks5://host:1080/path",
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                ipcheck._parse_proxy(value)

        self.assertEqual(
            ipcheck._parse_proxy("socks5://user:p%40ss@host:1080"),
            ("host", 1080, "user", "p@ss"),
        )

    def test_main_rejects_missing_proxy_value_with_json_error(self):
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = ipcheck.main(["1.1.1.1", "--proxy"])

        self.assertEqual(code, 2)
        self.assertIn("error", json.loads(stdout.getvalue()))

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = ipcheck.main(["1.1.1.1", "--proxy", ""])
        self.assertEqual(code, 2)
        self.assertIn("error", json.loads(stdout.getvalue()))

    def test_main_rejects_conflicting_proxy_sources(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = ipcheck.main([
                "socks5://one.example:1080",
                "--proxy", "socks5://two.example:1080",
            ])

        self.assertEqual(code, 2)
        self.assertIn("不能同时", json.loads(stdout.getvalue())["error"])

    def test_invalid_plain_target_is_rejected_before_network_calls(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = ipcheck.main(["not-an-ip"])

        self.assertEqual(code, 2)
        self.assertIn("有效 IP", json.loads(stdout.getvalue())["error"])

    def test_exit_discovery_rejects_missing_or_invalid_data(self):
        failures = [
            (None, "__err__:timeout"),
            (200, "not-json"),
            (200, "[]"),
            (200, "{}"),
            (200, '{"ip":"not-an-ip"}'),
        ]
        for response in failures:
            with self.subTest(response=response), mock.patch.object(
                ipcheck, "_get", return_value=response
            ), self.assertRaises(RuntimeError):
                ipcheck._discover_exit_ip(("192.0.2.10", 1080, None, None))

    def test_proxy_target_always_uses_discovered_exit_even_for_ipv4_gateway(self):
        empty_layer = {"layer": "test", "status": "ok"}
        layer_names = [
            "layer_rdap", "layer_geo", "layer_asn", "layer_reputation",
            "layer_dnsbl", "layer_ptr", "layer_bgp", "layer_services",
            "layer_exit", "layer_latency",
        ]
        patches = [mock.patch.object(ipcheck, name, return_value=empty_layer) for name in layer_names]
        stdout = io.StringIO()
        with mock.patch.object(ipcheck, "_discover_exit_ip", return_value="203.0.113.9"):
            for patcher in patches:
                patcher.start()
            try:
                with redirect_stdout(stdout):
                    code = ipcheck.main(["socks5://192.0.2.10:1080"])
            finally:
                for patcher in reversed(patches):
                    patcher.stop()

        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["ip"], "203.0.113.9")


class ReliabilityLayerTests(unittest.TestCase):
    def test_ptr_nonzero_exit_is_an_error_not_a_record(self):
        result = subprocess.CompletedProcess(
            args=["dig"], returncode=9, stdout="no servers could be reached\n", stderr=""
        )
        with mock.patch.object(ipcheck.subprocess, "run", return_value=result):
            output = ipcheck.layer_ptr("1.1.1.1")

        self.assertEqual(output["status"], "error")
        self.assertFalse(output["has_ptr"])
        self.assertIsNone(output["ptr"])

    def test_spamhaus_query_error_is_unreliable_not_listed(self):
        def lookup(query):
            if "invalid-probe" in query:
                return "not_found", None
            if query.endswith("zen.spamhaus.org"):
                return "answer", "127.255.255.254"
            return "not_found", None

        with mock.patch.object(ipcheck, "_dns_lookup", side_effect=lookup):
            output = ipcheck.layer_dnsbl("1.2.3.4")

        self.assertEqual(output["status"], "unreliable")
        self.assertEqual(output["listed"], [])
        self.assertIn("查询错误码", output["error"])

    def test_dns_probe_failure_cannot_report_a_clean_result(self):
        with mock.patch.object(
            ipcheck, "_dns_lookup", return_value=("error", "temporary failure")
        ):
            output = ipcheck.layer_dnsbl("1.2.3.4")

        self.assertEqual(output["status"], "unreliable")
        self.assertEqual(output["checked"], [])

    def test_dnsbl_zone_failures_and_invalid_answers_are_unreliable(self):
        answers = iter([
            ("not_found", None),
            ("error", "temporary failure"),
            ("answer", "192.0.2.4"),
            ("not_found", None),
            ("not_found", None),
        ])
        with mock.patch.object(ipcheck, "_dns_lookup", side_effect=lambda _query: next(answers)):
            output = ipcheck.layer_dnsbl("1.2.3.4")

        self.assertEqual(output["status"], "unreliable")
        self.assertIn("DNS 查询失败", output["error"])
        self.assertIn("非法返回码", output["error"])

    def test_incomplete_exit_samples_are_not_stable(self):
        responses = [
            (200, '{"ip":"203.0.113.9"}'),
            (200, '{"ip":"203.0.113.9"}'),
            (None, "__err__:timeout"),
        ]
        with (
            mock.patch.object(ipcheck, "_get", side_effect=responses),
            mock.patch.object(ipcheck.time, "sleep"),
        ):
            output = ipcheck.layer_exit(("proxy.example", 1080, None, None))

        self.assertFalse(output["stable"])
        self.assertEqual(output["status"], "unreliable")
        self.assertIn(None, output["samples"])

    def test_non_object_exit_samples_are_explicit_errors(self):
        with (
            mock.patch.object(ipcheck, "_get", return_value=(200, "[]")),
            mock.patch.object(ipcheck.time, "sleep"),
        ):
            output = ipcheck.layer_exit(("proxy.example", 1080, None, None))

        self.assertEqual(output["status"], "error")
        self.assertEqual(output["samples"], [None, None, None])


class DataLayerTests(unittest.TestCase):
    class Response:
        def __init__(self, body, status=200):
            self.body = body if isinstance(body, bytes) else body.encode()
            self.status = status

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return self.body

    def test_get_handles_direct_proxy_http_and_transport_paths(self):
        with mock.patch.object(
            ipcheck.urllib.request, "urlopen", return_value=self.Response("ok", 200)
        ):
            self.assertEqual(ipcheck._get("https://example.com"), (200, "ok"))

        error = ipcheck.urllib.error.HTTPError(
            "https://example.com", 429, "rate", {}, io.BytesIO(b"limited")
        )
        with mock.patch.object(ipcheck.urllib.request, "urlopen", side_effect=error):
            self.assertEqual(ipcheck._get("https://example.com"), (429, "limited"))

        with mock.patch.object(
            ipcheck.urllib.request, "urlopen", side_effect=OSError("offline")
        ):
            status, body = ipcheck._get("https://example.com")
        self.assertIsNone(status)
        self.assertIn("offline", body)

        with mock.patch.object(ipcheck, "_get_via_socks5", return_value=(204, "")):
            self.assertEqual(
                ipcheck._get("https://example.com", proxy=("p", 1, None, None)),
                (204, ""),
            )

    def test_rdap_geo_asn_and_bgp_happy_paths(self):
        rdap_payload = {
            "handle": "NET-1",
            "name": "TEST-NET",
            "country": "US",
            "port43": "whois.arin.net",
            "entities": [{"vcardArray": ["vcard", [["fn", {}, "text", "Comcast Cable"]]]}],
        }
        with mock.patch.object(ipcheck, "_get", return_value=(200, json.dumps(rdap_payload))):
            rdap = ipcheck.layer_rdap("1.1.1.1")
        self.assertEqual(rdap["rir"], "ARIN")
        self.assertEqual(rdap["org"], "Comcast Cable")

        geo_responses = [
            (200, json.dumps({"country": "US", "region": "VA", "city": "A", "org": "AS1 Comcast"})),
            (200, json.dumps({"countryCode": "US", "regionName": "VA", "city": "A", "isp": "Comcast", "proxy": False, "hosting": False})),
            (200, json.dumps({"country_code": "US", "region": "VA", "city": "A", "connection": {"isp": "Comcast"}})),
        ]
        with mock.patch.object(ipcheck, "_get", side_effect=geo_responses):
            geo = ipcheck.layer_geo("1.1.1.1")
        self.assertTrue(geo["consensus"])
        self.assertFalse(geo["split"])

        asn = ipcheck.layer_asn(geo, rdap)
        self.assertTrue(asn["is_real_isp"])
        self.assertTrue(asn["org_matches_asn"])

        bgp_payload = {"data": {"asns": [{"asn": 1, "holder": "TEST"}], "resource": "1.1.1.0/24"}}
        with mock.patch.object(ipcheck, "_get", return_value=(200, json.dumps(bgp_payload))):
            bgp = ipcheck.layer_bgp("1.1.1.1")
        self.assertEqual(bgp["announced_by"][0]["asn"], 1)

    def test_rdap_fallback_and_parse_errors_are_explicit(self):
        payload = {"handle": "NET-2", "country": "US", "links": [{"href": "https://rdap.arin.net"}]}
        with mock.patch.object(
            ipcheck, "_get", side_effect=[(500, "__err__:down"), (200, json.dumps(payload))]
        ):
            self.assertEqual(ipcheck.layer_rdap("1.1.1.1")["rir"], "ARIN")

        with mock.patch.object(ipcheck, "_get", return_value=(200, "not-json")):
            self.assertEqual(ipcheck.layer_rdap("1.1.1.1")["status"], "error")
            self.assertEqual(ipcheck.layer_bgp("1.1.1.1")["status"], "error")

    def test_reputation_sources_include_keyed_and_unkeyed_results(self):
        proxycheck = {"1.1.1.1": {"proxy": "no", "vpn": "no", "type": "Residential", "risk": 0}}
        ipapi = {
            "is_datacenter": False, "is_tor": False, "is_proxy": False,
            "is_vpn": False, "is_abuser": False,
            "company": {"type": "isp"}, "asn": {"type": "isp"},
        }
        ipqs = {"fraud_score": 0, "proxy": False, "vpn": False, "tor": False}
        abuse = {"data": {"abuseConfidenceScore": 0, "totalReports": 0, "usageType": "ISP"}}
        with (
            mock.patch.dict(ipcheck.os.environ, {"ABUSEIPDB_KEY": "a", "IPQS_KEY": "q"}, clear=True),
            mock.patch.object(
                ipcheck, "_get",
                side_effect=[(200, json.dumps(proxycheck)), (200, json.dumps(ipapi)), (200, json.dumps(ipqs))],
            ),
            mock.patch.object(
                ipcheck.urllib.request, "urlopen", return_value=self.Response(json.dumps(abuse))
            ),
        ):
            output = ipcheck.layer_reputation("1.1.1.1")
        self.assertEqual(output["sources"]["proxycheck"]["risk"], 0)
        self.assertEqual(output["sources"]["abuseipdb"]["score"], 0)
        self.assertEqual(output["sources"]["ipqs"]["fraud_score"], 0)

        with (
            mock.patch.dict(ipcheck.os.environ, {}, clear=True),
            mock.patch.object(ipcheck, "_get", return_value=(200, "{}")),
        ):
            skipped = ipcheck.layer_reputation("1.1.1.1")
        self.assertIn("skipped", skipped["sources"]["abuseipdb"])
        self.assertIn("skipped", skipped["sources"]["ipqs"])

    def test_services_latency_and_ptr_success_paths(self):
        probes = [
            ("a", "blocked", "https://a/", ["blocked here"]),
            ("b", "trace", "https://b/", []),
            ("c", "down", "https://c/", []),
        ]
        with (
            mock.patch.object(ipcheck, "SERVICE_PROBES", probes),
            mock.patch.object(
                ipcheck, "_get",
                side_effect=[(200, "blocked here"), (200, "loc=US\n"), (None, "__err__:down")],
            ),
        ):
            services = ipcheck.layer_services(("p", 1, None, None))
        self.assertTrue(services["results"]["blocked"]["region_blocked"])
        self.assertEqual(services["results"]["trace"]["cf_loc"], "US")
        self.assertFalse(services["results"]["down"]["reachable"])

        ticks = iter(range(20))
        with (
            mock.patch.object(ipcheck, "AWS_REGIONS", [("west", "West"), ("east", "East")]),
            mock.patch.object(ipcheck, "_get", return_value=(200, "")),
            mock.patch.object(ipcheck.time, "time", side_effect=lambda: next(ticks)),
        ):
            latency = ipcheck.layer_latency(("p", 1, None, None))
        self.assertIn(latency["closest"], {"West", "East"})

        result = subprocess.CompletedProcess(
            args=["dig"], returncode=0, stdout="c-1-2-3-4.hsd1.va.comcast.net.\n", stderr=""
        )
        with mock.patch.object(ipcheck.subprocess, "run", return_value=result):
            ptr = ipcheck.layer_ptr("1.2.3.4")
        self.assertTrue(ptr["has_ptr"])
        self.assertTrue(ptr["residential_pattern"])

    def test_dns_lookup_and_dnsbl_result_classes(self):
        with mock.patch.object(ipcheck.socket, "gethostbyname", return_value="127.0.0.2"):
            self.assertEqual(ipcheck._dns_lookup("listed.example"), ("answer", "127.0.0.2"))
        with mock.patch.object(
            ipcheck.socket, "gethostbyname",
            side_effect=socket.gaierror(socket.EAI_NONAME, "not found"),
        ):
            self.assertEqual(ipcheck._dns_lookup("none.example"), ("not_found", None))
        with mock.patch.object(ipcheck.socket, "gethostbyname", side_effect=socket.timeout("slow")):
            self.assertEqual(ipcheck._dns_lookup("slow.example")[0], "error")

        with mock.patch.object(ipcheck, "_dns_lookup", return_value=("answer", "198.18.0.1")):
            hijacked = ipcheck.layer_dnsbl("1.2.3.4")
        self.assertTrue(hijacked["dns_hijack_detected"])

        answers = iter([
            ("not_found", None),
            ("answer", "127.0.0.2"),
            ("not_found", None),
            ("not_found", None),
            ("not_found", None),
        ])
        with mock.patch.object(ipcheck, "_dns_lookup", side_effect=lambda _query: next(answers)):
            listed = ipcheck.layer_dnsbl("1.2.3.4")
        self.assertEqual(listed["listed"], ["Spamhaus ZEN"])
        self.assertEqual(ipcheck.layer_dnsbl("2001:db8::1")["status"], "skip")

    def test_main_no_proxy_runs_all_core_layers(self):
        empty_layer = {"layer": "test", "status": "ok"}
        core_names = [
            "layer_rdap", "layer_geo", "layer_asn", "layer_reputation",
            "layer_dnsbl", "layer_ptr", "layer_bgp",
        ]
        patches = [mock.patch.object(ipcheck, name, return_value=empty_layer) for name in core_names]
        stdout = io.StringIO()
        for patcher in patches:
            patcher.start()
        try:
            with redirect_stdout(stdout):
                code = ipcheck.main(["1.1.1.1"])
        finally:
            for patcher in reversed(patches):
                patcher.stop()

        report = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertFalse(report["has_proxy"])
        self.assertNotIn("services", report["layers"])


if __name__ == "__main__":
    unittest.main()
