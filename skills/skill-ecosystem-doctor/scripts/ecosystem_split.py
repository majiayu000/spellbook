#!/usr/bin/env python3
"""Move exact SKILL.md sections into references using governance policy."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path


class SplitError(RuntimeError):
    """Raised when a split boundary or destination is unsafe."""


@dataclass(frozen=True)
class SplitPlan:
    skills: tuple[str, ...]
    references: tuple[str, ...]
    final_lines: dict[str, int]

    def to_dict(self) -> dict:
        return {
            "skills": list(self.skills),
            "references": list(self.references),
            "final_lines": self.final_lines,
        }


def _load_policy(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SplitError(f"policy does not exist: {path}") from exc
    except OSError as exc:
        raise SplitError(f"policy cannot be read: {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SplitError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SplitError(f"{path} must contain a JSON object")
    return value


def _line_index(lines: list[str], heading: str, start: int = 0) -> int | None:
    return next((index for index in range(start, len(lines)) if lines[index] == heading), None)


def _skill_source(registry: Path, skill: str) -> Path:
    relative = Path(skill)
    if (
        relative.is_absolute()
        or len(relative.parts) != 1
        or relative.name != skill
        or relative.name in {".", ".."}
    ):
        raise SplitError(f"split skill name must be one directory segment: {skill!r}")
    source = registry / "skills" / relative / "SKILL.md"
    if not source.is_file():
        raise SplitError(f"missing split source: {source}")
    skills_root = (registry / "skills").resolve(strict=True)
    skill_root = source.parent.resolve(strict=True)
    if source.parent.is_symlink() or skill_root.parent != skills_root:
        raise SplitError(f"split source must be a physical registry Skill: {source}")
    return skill_root / "SKILL.md"


def _reference_path(source: Path, reference_name: str) -> Path:
    relative = Path(reference_name)
    if not relative.parts or relative.is_absolute() or ".." in relative.parts:
        raise SplitError(
            "split reference must stay inside its Skill directory: "
            f"{reference_name!r}"
        )
    skill_root = source.parent.resolve(strict=True)
    reference = (skill_root / relative).resolve(strict=False)
    if not reference.is_relative_to(skill_root):
        raise SplitError(
            "split reference must stay inside its Skill directory: "
            f"{reference_name!r}"
        )
    return reference


def build_split_plan(
    registry: Path,
    policy: dict,
    *,
    max_lines: int = 800,
) -> tuple[SplitPlan, dict[Path, str]]:
    raw_splits = policy.get("splits", {})
    if not isinstance(raw_splits, dict):
        raise SplitError("splits must be an object")
    updates: dict[Path, str] = {}
    changed_skills: list[str] = []
    references: list[str] = []
    final_lines: dict[str, int] = {}

    for skill, moves in raw_splits.items():
        if not isinstance(skill, str) or not isinstance(moves, list):
            raise SplitError("splits must map skill names to move arrays")
        source = _skill_source(registry, skill)
        original = source.read_text(encoding="utf-8")
        text = original
        for move in moves:
            if not isinstance(move, dict):
                raise SplitError(f"invalid move for {skill}")
            start_heading = move.get("start")
            end_heading = move.get("end")
            reference_name = move.get("reference")
            title = move.get("title")
            intro = move.get("intro")
            replacement = move.get("replacement")
            required = (start_heading, reference_name, title, intro, replacement)
            if not all(isinstance(value, str) and value for value in required):
                raise SplitError(f"incomplete split move for {skill}")
            if end_heading is not None and not isinstance(end_heading, str):
                raise SplitError(f"invalid end heading for {skill}: {start_heading}")
            if start_heading in replacement.splitlines():
                raise SplitError(
                    f"replacement repeats the start heading for {skill}: {start_heading}"
                )
            reference = _reference_path(source, reference_name)
            lines = text.splitlines()
            start_index = _line_index(lines, start_heading)
            if start_index is None:
                if reference.is_file() and replacement in text:
                    continue
                raise SplitError(f"start heading not found in {source}: {start_heading}")
            end_index = len(lines)
            if end_heading is not None:
                found = _line_index(lines, end_heading, start_index + 1)
                if found is None:
                    raise SplitError(f"end heading not found in {source}: {end_heading}")
                end_index = found
            if reference.exists() or reference in updates:
                raise SplitError(f"refusing to overwrite split reference: {reference}")
            extracted = "\n".join(lines[start_index:end_index]).rstrip() + "\n"
            reference_text = f"# {title}\n\n{intro}\n\n{extracted}"
            lines[start_index:end_index] = replacement.splitlines()
            text = "\n".join(lines).rstrip() + "\n"
            updates[reference] = reference_text
            references.append(str(reference))
        count = len(text.splitlines())
        final_lines[skill] = count
        if count > max_lines:
            raise SplitError(f"{source} would remain over {max_lines} lines ({count})")
        if text != original:
            updates[source] = text
            changed_skills.append(skill)

    return (
        SplitPlan(
            skills=tuple(changed_skills),
            references=tuple(references),
            final_lines=final_lines,
        ),
        updates,
    )


def _atomic_write(path: Path, text: str, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.split-{os.getpid()}")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


def apply_split_plan(registry: Path, updates: dict[Path, str]) -> None:
    skills_root = (registry / "skills").resolve(strict=True)
    for path, text in sorted(
        updates.items(), key=lambda item: len(item[0].parts), reverse=True
    ):
        try:
            relative = path.relative_to(skills_root)
        except ValueError as exc:
            raise SplitError(f"split target escaped the registry: {path}") from exc
        if len(relative.parts) < 2:
            raise SplitError(f"invalid split target: {path}")
        skill_root_path = skills_root / relative.parts[0]
        if skill_root_path.is_symlink():
            raise SplitError(f"split target uses a symlinked Skill root: {path}")
        skill_root = skill_root_path.resolve(strict=True)
        resolved_path = path.resolve(strict=False)
        if not resolved_path.is_relative_to(skill_root):
            raise SplitError(f"split target escaped its Skill directory: {path}")
        source_mode = (skill_root / "SKILL.md").stat().st_mode
        _atomic_write(resolved_path, text, source_mode)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--max-lines", type=int, default=800)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    registry = args.registry.expanduser().resolve()
    try:
        policy = _load_policy(args.policy.expanduser().resolve())
        plan, updates = build_split_plan(registry, policy, max_lines=args.max_lines)
        if args.apply:
            apply_split_plan(registry, updates)
    except (OSError, SplitError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(
        json.dumps(
            {"ok": True, "applied": args.apply, **plan.to_dict()},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
