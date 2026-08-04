#!/usr/bin/env python3
"""Read-only scanner for known npm supply-chain compromise indicators."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path


LOCKFILE_NAMES = {
    "package-lock.json",
    "npm-shrinkwrap.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lock",
    "bun.lockb",
}
DEPENDENCY_SECTIONS = {
    "dependencies",
    "devDependencies",
    "optionalDependencies",
    "peerDependencies",
}
SKIP_DIRS = {".git", ".hg", ".svn"}
DEEP_TEXT_SUFFIXES = {".js", ".mjs", ".cjs", ".json", ".yaml", ".yml"}
MAX_DEEP_FILE_BYTES = 5 * 1024 * 1024


def relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def load_iocs(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("schema_version") != 1:
        raise ValueError("IOC file must use schema_version 1")
    for required in ("incident", "affected_packages", "files", "strings"):
        if required not in data:
            raise ValueError(f"IOC file is missing {required!r}")
    return data


def affected_map(iocs: dict[str, object]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    packages = iocs["affected_packages"]
    if not isinstance(packages, list):
        raise ValueError("affected_packages must be a list")
    for entry in packages:
        if not isinstance(entry, dict):
            raise ValueError("affected package entries must be objects")
        name = entry.get("name")
        versions = entry.get("versions")
        if not isinstance(name, str) or not isinstance(versions, list):
            raise ValueError("affected package entries require name and versions")
        if not all(isinstance(version, str) for version in versions):
            raise ValueError(f"affected versions for {name} must be strings")
        result[name] = set(versions)
    return result


def file_ioc_map(iocs: dict[str, object]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    entries = iocs["files"]
    if not isinstance(entries, list):
        raise ValueError("files must be a list")
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("file IOC entries must be objects")
        name = entry.get("name")
        hashes = entry.get("sha256")
        if not isinstance(name, str) or not isinstance(hashes, list):
            raise ValueError("file IOC entries require name and sha256")
        if not all(isinstance(digest, str) for digest in hashes):
            raise ValueError(f"sha256 values for {name} must be strings")
        result[name] = {digest.lower() for digest in hashes}
    return result


def add_finding(
    findings: list[dict[str, str]],
    seen: set[tuple[str, str, str, str]],
    *,
    severity: str,
    kind: str,
    path: str,
    evidence: str,
) -> None:
    key = (severity, kind, path, evidence)
    if key in seen:
        return
    seen.add(key)
    findings.append(
        {
            "severity": severity,
            "kind": kind,
            "path": path,
            "evidence": evidence,
        }
    )


def exact_version_hits(
    package: str,
    version: str,
    affected: dict[str, set[str]],
) -> bool:
    return package in affected and version in affected[package]


def dependency_spec_mentions(spec: object, bad_versions: set[str]) -> str | None:
    if not isinstance(spec, str):
        return None
    for version in sorted(bad_versions):
        if re.search(rf"(?<![0-9A-Za-z]){re.escape(version)}(?![0-9A-Za-z])", spec):
            return version
    return None


def scan_manifest(
    path: Path,
    root: Path,
    affected: dict[str, set[str]],
    preinstall_markers: list[str],
    findings: list[dict[str, str]],
    seen: set[tuple[str, str, str, str]],
    warnings: list[str],
) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        warnings.append(f"could not parse {relative(path, root)}: {exc}")
        return
    if not isinstance(data, dict):
        warnings.append(f"ignored non-object manifest {relative(path, root)}")
        return

    name = data.get("name")
    version = data.get("version")
    rel_path = relative(path, root)
    if isinstance(name, str) and isinstance(version, str):
        if exact_version_hits(name, version, affected):
            installed = "node_modules" in path.parts
            add_finding(
                findings,
                seen,
                severity="critical" if installed else "high",
                kind="installed_affected_package" if installed else "affected_package_manifest",
                path=rel_path,
                evidence=f"{name}@{version}",
            )

    for section in sorted(DEPENDENCY_SECTIONS):
        dependencies = data.get(section)
        if not isinstance(dependencies, dict):
            continue
        for package, spec in dependencies.items():
            if not isinstance(package, str) or package not in affected:
                continue
            matched = dependency_spec_mentions(spec, affected[package])
            if matched is not None:
                add_finding(
                    findings,
                    seen,
                    severity="medium",
                    kind="affected_dependency_declaration",
                    path=rel_path,
                    evidence=f"{section}: {package} declares {spec!r} and references {matched}",
                )

    scripts = data.get("scripts")
    preinstall = scripts.get("preinstall") if isinstance(scripts, dict) else None
    if isinstance(preinstall, str):
        for marker in preinstall_markers:
            if marker.lower() in preinstall.lower():
                add_finding(
                    findings,
                    seen,
                    severity="high",
                    kind="ioc_preinstall",
                    path=rel_path,
                    evidence=f"preinstall references {marker}",
                )


def package_name_from_lock_path(lock_path: str) -> str | None:
    marker = "node_modules/"
    if marker not in lock_path:
        return None
    tail = lock_path.rsplit(marker, 1)[1]
    parts = tail.split("/")
    if not parts or not parts[0]:
        return None
    if parts[0].startswith("@") and len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return parts[0]


def walk_package_lock_entries(data: dict[str, object]):
    packages = data.get("packages")
    if isinstance(packages, dict):
        for lock_path, entry in packages.items():
            if not isinstance(lock_path, str) or not isinstance(entry, dict):
                continue
            name = entry.get("name")
            if not isinstance(name, str):
                name = package_name_from_lock_path(lock_path)
            version = entry.get("version")
            if isinstance(name, str) and isinstance(version, str):
                yield name, version

    def recurse(dependencies: object):
        if not isinstance(dependencies, dict):
            return
        for name, entry in dependencies.items():
            if not isinstance(name, str) or not isinstance(entry, dict):
                continue
            version = entry.get("version")
            if isinstance(version, str):
                yield name, version
            yield from recurse(entry.get("dependencies"))

    yield from recurse(data.get("dependencies"))


def scan_json_lock(
    path: Path,
    root: Path,
    affected: dict[str, set[str]],
    findings: list[dict[str, str]],
    seen: set[tuple[str, str, str, str]],
    warnings: list[str],
) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        warnings.append(f"could not parse lockfile {relative(path, root)}: {exc}")
        return
    if not isinstance(data, dict):
        warnings.append(f"ignored non-object lockfile {relative(path, root)}")
        return
    for package, version in walk_package_lock_entries(data):
        if exact_version_hits(package, version, affected):
            add_finding(
                findings,
                seen,
                severity="high",
                kind="affected_lockfile_version",
                path=relative(path, root),
                evidence=f"{package}@{version}",
            )


def scan_text_lock(
    path: Path,
    root: Path,
    affected: dict[str, set[str]],
    findings: list[dict[str, str]],
    seen: set[tuple[str, str, str, str]],
    warnings: list[str],
) -> None:
    if path.name == "bun.lockb":
        warnings.append(
            f"unsupported binary lockfile {relative(path, root)}; resolve it with Bun tooling"
        )
        return
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        warnings.append(f"could not read lockfile {relative(path, root)}: {exc}")
        return

    blocks = re.split(r"\n\s*\n", text)
    for package, versions in affected.items():
        package_token = re.escape(package)
        for version in versions:
            direct = re.compile(
                rf"(?<![0-9A-Za-z._/-])/?{package_token}@(?:npm:)?{re.escape(version)}"
            )
            yarn_version = re.compile(
                rf"(?:^|\n)\s*version\s*(?::\s*|\s+['\"]){re.escape(version)}(?:['\"])?\s*(?:\n|$)"
            )
            hit = direct.search(text) is not None
            if not hit:
                hit = any(package in block and yarn_version.search(block) for block in blocks)
            if hit:
                add_finding(
                    findings,
                    seen,
                    severity="high",
                    kind="affected_lockfile_version",
                    path=relative(path, root),
                    evidence=f"{package}@{version}",
                )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def scan_ioc_file(
    path: Path,
    root: Path,
    hashes: set[str],
    findings: list[dict[str, str]],
    seen: set[tuple[str, str, str, str]],
    warnings: list[str],
) -> None:
    rel_path = relative(path, root)
    try:
        digest = sha256(path)
    except OSError as exc:
        warnings.append(f"could not hash {rel_path}: {exc}")
        return
    if digest in hashes:
        add_finding(
            findings,
            seen,
            severity="critical",
            kind="known_malicious_sha256",
            path=rel_path,
            evidence=f"sha256={digest}",
        )
    else:
        severity = "high" if path.name.lower() in {"math_symbol.js", "math_init.js"} else "low"
        add_finding(
            findings,
            seen,
            severity=severity,
            kind="ioc_filename_hash_mismatch",
            path=rel_path,
            evidence=f"filename matched but sha256={digest} is not in the baseline",
        )


def scan_deep_strings(
    path: Path,
    root: Path,
    string_iocs: list[tuple[str, str]],
    findings: list[dict[str, str]],
    seen: set[tuple[str, str, str, str]],
    warnings: list[str],
) -> None:
    try:
        if path.stat().st_size > MAX_DEEP_FILE_BYTES:
            return
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        warnings.append(f"could not inspect {relative(path, root)}: {exc}")
        return
    for kind, value in string_iocs:
        if value in text:
            add_finding(
                findings,
                seen,
                severity="high",
                kind=f"ioc_{kind}_string",
                path=relative(path, root),
                evidence=f"contains indicator {value!r}",
            )


def build_result(target: Path, ioc_path: Path, deep: bool) -> dict[str, object]:
    iocs = load_iocs(ioc_path)
    affected = affected_map(iocs)
    file_iocs = file_ioc_map(iocs)
    preinstall_raw = iocs.get("preinstall_markers", [])
    if not isinstance(preinstall_raw, list) or not all(
        isinstance(value, str) for value in preinstall_raw
    ):
        raise ValueError("preinstall_markers must be a list of strings")
    preinstall_markers = list(preinstall_raw)

    strings_raw = iocs["strings"]
    if not isinstance(strings_raw, list):
        raise ValueError("strings must be a list")
    string_iocs: list[tuple[str, str]] = []
    for entry in strings_raw:
        if not isinstance(entry, dict):
            raise ValueError("string IOC entries must be objects")
        kind = entry.get("kind")
        value = entry.get("value")
        if not isinstance(kind, str) or not isinstance(value, str):
            raise ValueError("string IOC entries require string kind and value")
        string_iocs.append((kind, value))

    findings: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    warnings: list[str] = []
    scanned = {"files": 0, "manifests": 0, "lockfiles": 0, "ioc_filenames": 0}

    for dirpath, dirnames, filenames in os.walk(target, followlinks=False):
        dirnames[:] = sorted(name for name in dirnames if name not in SKIP_DIRS)
        current = Path(dirpath)
        for filename in sorted(filenames):
            path = current / filename
            if path.is_symlink():
                continue
            scanned["files"] += 1
            if filename == "package.json":
                scanned["manifests"] += 1
                scan_manifest(
                    path,
                    target,
                    affected,
                    preinstall_markers,
                    findings,
                    seen,
                    warnings,
                )
            if filename in LOCKFILE_NAMES:
                scanned["lockfiles"] += 1
                if filename in {"package-lock.json", "npm-shrinkwrap.json"}:
                    scan_json_lock(path, target, affected, findings, seen, warnings)
                else:
                    scan_text_lock(path, target, affected, findings, seen, warnings)
            if filename in file_iocs:
                scanned["ioc_filenames"] += 1
                scan_ioc_file(
                    path,
                    target,
                    file_iocs[filename],
                    findings,
                    seen,
                    warnings,
                )
            is_baseline = path.resolve() == ioc_path
            if deep and not is_baseline and filename != "bun.lockb" and (
                path.suffix.lower() in DEEP_TEXT_SUFFIXES or filename in LOCKFILE_NAMES
            ):
                scan_deep_strings(path, target, string_iocs, findings, seen, warnings)

    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings.sort(
        key=lambda item: (
            severity_order.get(item["severity"], 9),
            item["path"],
            item["kind"],
            item["evidence"],
        )
    )
    incident = iocs["incident"]
    if not isinstance(incident, dict):
        raise ValueError("incident must be an object")
    return {
        "schema_version": 1,
        "target": target.as_posix(),
        "baseline": {
            "name": incident.get("name"),
            "updated_at": incident.get("updated_at"),
            "source_url": incident.get("source_url"),
            "ioc_file": ioc_path.as_posix(),
        },
        "result": "affected" if any(item["severity"] in {"critical", "high"} for item in findings)
        else "suspicious" if findings
        else "clean",
        "findings": findings,
        "warnings": sorted(set(warnings)),
        "scanned": scanned,
        "deep": deep,
        "limits": [
            "Results are limited to the target and bundled IOC baseline.",
            "A dependency reference does not prove package installation or code execution.",
            "No secret values are read or printed intentionally.",
        ],
    }


def print_text(result: dict[str, object]) -> None:
    baseline = result["baseline"]
    scanned = result["scanned"]
    if not isinstance(baseline, dict) or not isinstance(scanned, dict):
        raise ValueError("invalid result structure")
    print("# NPM Supply-Chain Check")
    print(f"scope: {result['target']}")
    print(f"baseline: {baseline.get('name')} ({baseline.get('updated_at')})")
    print(f"result: {result['result']}")
    print(
        "scanned: "
        f"{scanned.get('files')} files, {scanned.get('manifests')} manifests, "
        f"{scanned.get('lockfiles')} lockfiles, {scanned.get('ioc_filenames')} IOC filenames"
    )
    print()
    print("## Findings")
    findings = result["findings"]
    if not isinstance(findings, list) or not findings:
        print("- none")
    else:
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            print(
                f"- {str(finding.get('severity')).upper()} "
                f"[{finding.get('kind')}] {finding.get('path')}: {finding.get('evidence')}"
            )
    print()
    print("## Warnings")
    warnings = result["warnings"]
    if not isinstance(warnings, list) or not warnings:
        print("- none")
    else:
        for warning in warnings:
            print(f"- {warning}")
    print()
    print("## Limits")
    limits = result["limits"]
    if isinstance(limits, list):
        for limit in limits:
            print(f"- {limit}")


def parse_args() -> argparse.Namespace:
    default_iocs = Path(__file__).resolve().parent.parent / "references" / "shai-hulud-2026-iocs.json"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", nargs="?", default=".", help="directory to scan")
    parser.add_argument(
        "--ioc-file",
        type=Path,
        default=default_iocs,
        help="reviewed schema_version 1 IOC JSON file",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--deep",
        action="store_true",
        help="also scan small JavaScript, JSON, YAML, and lockfiles for IOC strings",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = Path(args.target).expanduser().resolve()
    ioc_path = args.ioc_file.expanduser().resolve()
    if not target.is_dir():
        print(f"error: target is not a directory: {target}", file=sys.stderr)
        return 2
    try:
        result = build_result(target, ioc_path, args.deep)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print_text(result)
    return 1 if result["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
