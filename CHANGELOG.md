# Changelog

All notable changes to Spellbook are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/):
latest changes first, ISO dates, and grouped change types. Spellbook does not
have published version tags yet, so entries are grouped by dated snapshots
instead of SemVer releases. When versioned releases are introduced, use
`MAJOR.MINOR.PATCH` release headings and keep the same change categories.

History before this file was reconstructed from `git log`; it is intentionally
curated for user-facing impact instead of being a raw commit dump.

## [Unreleased]

Use this section for notable changes after the latest dated snapshot.

### Added

- Added the `gemma4-local-deploy` skill for local Gemma 4 12B deployment with
  `llama.cpp`, GGUF quantization, Apple Metal, tmux background service
  management, OpenAI-compatible API verification, and resource reporting.

### Changed

- Updated the installable skill count from 80 to 81.
- Expanded `gemma4-local-deploy` with an Ollama-specific route covering
  official `gemma4:12b` pull checks, manual GGUF import, Homebrew sidecar binary
  workarounds, and verification commands.
- Documented 12B long-context operation in `gemma4-local-deploy`, including
  64K/128K context selection, restart commands, `n_ctx` verification, and
  memory/speed caveats.

## [2026-06-03]

### Added

- Added the `threads` skill for Codex-native parallel thread workflows,
  including lane maps, disjoint file ownership, independent review lanes, merge
  gates, and cleanup reporting.
- Added this changelog and linked it from the English and Chinese READMEs.

### Changed

- Updated the installable skill count from 79 to 80.

### Fixed

- Fixed pytest root collection behavior through PR #23.

## [2026-06-02]

### Fixed

- Configured pytest root collection so validation does not collect unintended
  test trees.

## [2026-06-01]

### Changed

- Added a simple user mode to `vscode-doctor`.
- Clarified browser-mode exclusions for `vscode-doctor`.
- Salvaged and documented useful progressive skill guidance.

### Fixed

- Fixed broken links in the HarmonyOS extended reference.

## [2026-05-31]

### Added

- Added two personal pain point skills plus Codex adapters.

### Changed

- Hardened personal lifecycle and netfeel guardian skills.
- Merged the personal skill hardening branch through PR #18.

### Fixed

- Replaced hardcoded personal paths in skills with `$HOME` or placeholders.
- Removed hardcoded diagnostic assumptions from `vscode-doctor`.

## [2026-05-30]

### Added

- Added the `vscode-doctor` skill.
- Added migration SEO assets for the Spellbook rename.
- Added VS Code extension guidance.

### Changed

- Rebranded the project from Claude Arsenal to Spellbook and documented runtime
  targets for Claude Code and Codex.
- Hardened the `github-trending` skill.
- Clarified that `vscode-doctor` asks before disabling extensions.

### Fixed

- Removed workspace path hardcoding from `vscode-doctor`.

## [2026-05-29]

### Fixed

- Required explicit Xiaohongshu image environment configuration.
- Rejected symlinks when packaging `skill-creator`.
- Hardened `cliproxy-newapi-stack` maintenance scripts.
- Addressed Xiaohongshu configuration review feedback.

## [2026-05-28]

### Added

- Added the `codex-fluent` skill.
- Added the `codex-retrospective` skill.

### Changed

- Regenerated the skill registry and updated the count to 76 after adding the
  two Codex skills.

## [2026-05-25]

### Changed

- Refreshed `disk-cleaner` with parallel scan support and a numbered menu.

### Fixed

- Resolved dynamic scan root handling in `disk-cleaner`.

## [2026-05-24]

### Added

- Added the proxy-safe network optimizer skill.

### Changed

- Split oversized skill references for progressive disclosure.
- Merged skill governance and progressive disclosure updates through PR #4 and
  PR #6.

## [2026-05-16]

### Added

- Added registry tag-based search, language detection, and offline CLI support
  through PR #3.

## [2026-05-07]

### Added

- Added Codex-facing skill registry validation through PR #2.

## [2026-04-29]

### Fixed

- Handled skill upgrade validation issues.

## [2026-04-28]

### Added

- Added skill registry validation.

## [2026-04-27]

### Added

- Added `cliproxy-deploy` and `cliproxy-newapi-stack` skills.

### Changed

- Added Cliproxy skills to the README catalog.

## [2026-04-09]

### Added

- Added `multi-ai-research` and `ask-opencli` skills.

### Fixed

- Sanitized personal data in the `multi-ai-research` skill.

## [2026-04-04]

### Changed

- Extended `clash-doctor setup-ai` with interactive residential proxy
  configuration support.

## [2026-04-01]

### Added

- Added the `vibeguard` skill.
- Added audit and workflow skills.

### Changed

- Upgraded `clash-doctor` from pure diagnostics into a broader configuration
  management workflow.
- Refreshed the skill catalog in the README.

## [2026-03-20]

### Added

- Added community files for repository health.
- Added the security policy.

## [2026-03-07]

### Added

- Added eight skills: `contributor`, `css-debug`, `gpu-use`, `humanizer`,
  `skill-creator`, `slides`, `strategic-compact`, and `vibeguard`.

### Removed

- Removed the `vibeguard` placeholder because VibeGuard is maintained
  separately.

## [2026-02-25]

### Added

- Added eight new skills, bringing the catalog to 56 skills.

## [2026-02-16]

### Added

- Added the `openclaw-deploy` skill for remote server deployment.

### Fixed

- Documented cookie persistence pitfalls and server login limitations in
  `openclaw-deploy`.

## [2026-02-12]

### Added

- Added the `auto-optimize` skill with dimension rotation scanning.

## [2026-02-06]

### Added

- Added six skills, bringing the catalog to 46 skills.

## [2026-01-23]

### Added

- Added the `figma-to-react` skill.
- Majorly updated `figma-to-code` with comprehensive rules.

### Changed

- Updated the README with `figma-to-react`, bringing the catalog to 40 skills.

## [2026-01-22]

### Added

- Added four skills.
- Revamped the README and added a one-click installer for GitHub Trending.

### Removed

- Removed `mcp-server-development`.
- Removed the One-Command Install row and comparison section from the README.

## [2026-01-15]

### Added

- Added seven skills and commands.

## [2025-12-24]

### Added

- Added the `github-trending` skill for exploring GitHub trends.

## [2025-12-19]

### Added

- Added the `harmonyos-app` skill for HarmonyOS development.
- Added the `app-ui-design` skill for mobile UI design.
- Added framework selection guides.

### Changed

- Migrated the `rust-project` skill guidance to SeaORM.

## [2025-12-18]

### Added

- Added `product-ux-expert`.
- Added six product lifecycle skills for end-to-end product coverage.
- Added hard rules to six product lifecycle skills.

### Changed

- Updated the README with the correct installation guide and all skills.

## [2025-12-17]

### Added

- Added TypeScript, Go, Rust, Python, and Zig project architecture skills.
- Added API, auth, database, and MCP development skills.
- Added a skill testing guide.
- Added a comprehensive skill design document for the new architecture skills.

### Changed

- Updated `typescript-project` with a no-backwards-compatibility principle,
  latest-version strategy, and LiteLLM as the default LLM API gateway.

## [2025-12-16]

### Added

- Added the structured logging skill.
- Added the `structured-logging-lite` variant with TypeScript implementation
  guidance.

## [2025-12-15]

### Added

- Added the `contribution-architect` skill for strategic open-source
  contributions.

## [2025-12-10]

### Added

- Added the `comprehensive-testing` skill.
- Added the `opensource-contributor` agent.
- Added the Issue-to-PR workflow specification.

### Changed

- Moved workflow documentation into the dedicated `workflows/` directory.
- Made AI signatures optional in commits and PRs.

### Fixed

- Corrected skills installation to use subdirectory structure.
- Added YAML frontmatter to the `opensource-contributor` agent.

## [2025-12-09]

### Added

- Initialized the Claude Arsenal repository with the Rust development plugin.
- Added high-priority skills for TDD, debugging, brainstorming, git commits,
  Playwright, and project health auditing.
- Added high-priority agents for tech lead orchestration, code archaeology,
  TypeScript architecture, senior review, Kubernetes, and security auditing.
- Added the `elegant-architecture` skill.
- Added comprehensive skills and agents analysis reports.
