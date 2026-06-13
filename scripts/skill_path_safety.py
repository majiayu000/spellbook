"""Repo-level wrapper for skill-creator path safety helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path


HELPER_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "skill-creator"
    / "scripts"
    / "path_safety.py"
)

spec = importlib.util.spec_from_file_location("spellbook_skill_creator_path_safety", HELPER_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load path safety helpers from {HELPER_PATH}")
_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_module)

UnsafePathError = _module.UnsafePathError
is_relative_to = _module.is_relative_to
safe_archive_name = _module.safe_archive_name
safe_kebab_name = _module.safe_kebab_name
safe_output_path = _module.safe_output_path
