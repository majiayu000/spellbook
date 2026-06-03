# Changelog

Release history for Spellbook, formerly Claude Arsenal.

## 2026-06-03 - Current Main

Spellbook is in pre-1.0 release-readiness mode. No numbered GitHub release tag
has been cut yet; use the repository `main` branch as the current install source.

### Added

- Added the `threads` skill for Codex-native parallel issue, PR, review, and
  implementation workflows.
- Added cross-runtime install support for Claude Code, Codex, and the combined
  `--target all` path.
- Added migration documentation for the rename from Claude Arsenal to Spellbook.
- Added issue templates for bug reports and feature requests.

### Changed

- Renamed the project from Claude Arsenal to Spellbook while preserving Claude
  Code as a first-class runtime target.
- Repositioned `codex-agent` as optional second-opinion review and
  cross-verification support.

### Verification

- Skill registry validation target: `python3 scripts/validate_skills.py --check`
- Test target: `python3 -m pytest`

## Release Notes

- GitHub releases have not started yet. When the first release is tagged, add a
  numbered section above this entry and link the release artifact.
- Security reports should use GitHub Security Advisories, not public issues.
- General bugs and feature requests should use the GitHub issue templates.
