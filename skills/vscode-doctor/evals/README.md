# vscode-doctor Eval Plan

## Goal

Verify that the skill diagnoses editor performance without hardcoded local paths, fixed root-cause rankings, fixed extension blocklists, fixed generated-directory lists, or fixed benefit percentages.

## Core Checks

- Uses the collector with case-specific inputs instead of assuming defaults.
- Ranks findings only from evidence present in the current prompt/output.
- Treats operating-system, renderer, watcher, extension, and cache issues as candidate classes, not as guaranteed causes.
- Uses placeholders for paths and commands in examples.
- Avoids applying changes until the user confirms.
- States when impact cannot be quantified because baseline data is missing.
- Separates file-browser mode from normal coding mode when a broad parent directory is open.
- Explains `files.watcherExclude`, `search.exclude`, and `files.exclude` with their editing/search/visibility tradeoffs.
- Treats Python, Ruff, Git, and Copilot setting changes as optional experiments with explicit feature costs, not default fixes.

## Manual Eval Prompts

The prompts live in `evals.json`. They intentionally use placeholders and generic categories so the skill must ask for or discover the missing context.
