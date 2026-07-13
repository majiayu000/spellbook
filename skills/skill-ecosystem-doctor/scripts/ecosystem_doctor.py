#!/usr/bin/env python3
"""Validate local Skill sources, projections, governance, and security signals."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ecosystem_checks import validate_ecosystem


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--governance",
        type=Path,
        required=True,
        help="Path to a schema-version 1 governance JSON file",
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--skip-loom", action="store_true")
    parser.add_argument("--loom-binary", default="loom")
    parser.add_argument("--fail-on-warn", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    options = build_parser().parse_args(argv)
    try:
        result = validate_ecosystem(
            options.governance,
            run_loom=not options.skip_loom,
            loom_binary=options.loom_binary,
        )
    except ValueError as exc:
        if options.json_output:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if options.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        summary = result["summary"]
        state = "PASS" if result["ok"] else "FAIL"
        print(
            f"{state}: {summary['instances']} instances, "
            f"{summary['declared_names']} names, "
            f"{summary['errors']} errors, {summary['warnings']} warnings"
        )
        for finding in result["findings"]:
            location = f" {finding['path']}" if finding["path"] else ""
            print(
                f"[{finding['severity'].upper()}] {finding['code']}{location}: "
                f"{finding['message']}"
            )
    if not result["ok"]:
        return 1
    if options.fail_on_warn and result["summary"]["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
