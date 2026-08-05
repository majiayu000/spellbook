from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCANNER = SKILL_ROOT / "scripts" / "scan_npm_supply_chain.py"
BASELINE = SKILL_ROOT / "references" / "shai-hulud-2026-iocs.json"


class ScanNpmSupplyChainTests(unittest.TestCase):
    def run_scan(
        self,
        root: Path,
        *,
        ioc_file: Path = BASELINE,
        deep: bool = False,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object] | None]:
        command = [
            "python3",
            str(SCANNER),
            str(root),
            "--ioc-file",
            str(ioc_file),
            "--format",
            "json",
        ]
        if deep:
            command.append("--deep")
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        payload = json.loads(completed.stdout) if completed.stdout else None
        return completed, payload

    def test_clean_manifest_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(
                json.dumps({"name": "safe", "dependencies": {"keyv": "5.6.0"}}),
                encoding="utf-8",
            )
            completed, payload = self.run_scan(root)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIsNotNone(payload)
            self.assertEqual(payload["result"], "clean")
            self.assertEqual(payload["findings"], [])

    def test_package_lock_detects_affected_transitive_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = {
                "name": "fixture",
                "lockfileVersion": 3,
                "packages": {
                    "": {"name": "fixture"},
                    "node_modules/keyv": {"version": "6.0.0"},
                },
            }
            (root / "package-lock.json").write_text(json.dumps(lock), encoding="utf-8")
            completed, payload = self.run_scan(root)
            self.assertEqual(completed.returncode, 1, completed.stderr)
            self.assertIsNotNone(payload)
            evidence = [item["evidence"] for item in payload["findings"]]
            self.assertIn("keyv@6.0.0", evidence)

    def test_pnpm_and_yarn_locks_detect_affected_versions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pnpm-lock.yaml").write_text(
                "lockfileVersion: '9.0'\npackages:\n  keyv@6.0.0: {}\n",
                encoding="utf-8",
            )
            (root / "yarn.lock").write_text(
                'flat-cache@^6.1.0:\n  version "6.1.24"\n  resolved "fixture"\n',
                encoding="utf-8",
            )
            completed, payload = self.run_scan(root)
            self.assertEqual(completed.returncode, 1, completed.stderr)
            self.assertIsNotNone(payload)
            evidence = {item["evidence"] for item in payload["findings"]}
            self.assertIn("keyv@6.0.0", evidence)
            self.assertIn("flat-cache@6.1.24", evidence)

    def test_yarn_version_does_not_cross_match_dependency_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "yarn.lock").write_text(
                'unrelated-package@^6.0.0:\n'
                '  version "6.0.0"\n'
                '  dependencies:\n'
                '    keyv "^5.0.0"\n',
                encoding="utf-8",
            )
            completed, payload = self.run_scan(root)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIsNotNone(payload)
            self.assertEqual(payload["findings"], [])

    def test_legacy_pnpm_slash_key_detects_affected_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pnpm-lock.yaml").write_text(
                "lockfileVersion: 5.4\npackages:\n  /keyv/6.0.0:\n"
                "    resolution: {integrity: fixture}\n",
                encoding="utf-8",
            )
            completed, payload = self.run_scan(root)
            self.assertEqual(completed.returncode, 1, completed.stderr)
            self.assertIsNotNone(payload)
            evidence = {item["evidence"] for item in payload["findings"]}
            self.assertIn("keyv@6.0.0", evidence)

    def test_installed_manifest_and_preinstall_are_distinct_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package_dir = Path(directory) / "node_modules" / "keyv"
            package_dir.mkdir(parents=True)
            (package_dir / "package.json").write_text(
                json.dumps(
                    {
                        "name": "keyv",
                        "version": "6.0.0",
                        "scripts": {"preinstall": "node setup.mjs"},
                    }
                ),
                encoding="utf-8",
            )
            completed, payload = self.run_scan(Path(directory))
            self.assertEqual(completed.returncode, 1, completed.stderr)
            self.assertIsNotNone(payload)
            kinds = {item["kind"] for item in payload["findings"]}
            self.assertIn("installed_affected_package", kinds)
            self.assertIn("ioc_preinstall", kinds)

    def test_custom_hash_and_deep_string_iocs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = b"fixture payload"
            (root / "payload.js").write_bytes(content)
            (root / "trace.mjs").write_text(
                "const endpoint = 'evil.example/router';\n", encoding="utf-8"
            )
            digest = hashlib.sha256(content).hexdigest()
            iocs = {
                "schema_version": 1,
                "incident": {
                    "name": "fixture",
                    "updated_at": "2026-08-04T00:00:00Z",
                    "source_url": "https://example.invalid",
                },
                "affected_packages": [],
                "files": [{"name": "payload.js", "sha256": [digest]}],
                "preinstall_markers": ["payload.js"],
                "strings": [{"kind": "network", "value": "evil.example/router"}],
            }
            ioc_file = root / "iocs.json"
            ioc_file.write_text(json.dumps(iocs), encoding="utf-8")
            completed, payload = self.run_scan(root, ioc_file=ioc_file, deep=True)
            self.assertEqual(completed.returncode, 1, completed.stderr)
            self.assertIsNotNone(payload)
            kinds = {item["kind"] for item in payload["findings"]}
            self.assertIn("known_malicious_sha256", kinds)
            self.assertIn("ioc_network_string", kinds)
            network_hits = [
                item for item in payload["findings"] if item["kind"] == "ioc_network_string"
            ]
            self.assertEqual(len(network_hits), 1)
            self.assertEqual(network_hits[0]["path"], "trace.mjs")

    def test_invalid_ioc_file_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ioc_file = root / "invalid.json"
            ioc_file.write_text("{}", encoding="utf-8")
            completed, payload = self.run_scan(root, ioc_file=ioc_file)
            self.assertEqual(completed.returncode, 2)
            self.assertIsNone(payload)
            self.assertIn("schema_version", completed.stderr)


if __name__ == "__main__":
    unittest.main()
