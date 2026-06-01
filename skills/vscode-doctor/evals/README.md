# vscode-doctor Eval Plan

## Goal

Verify that the skill diagnoses editor performance without hardcoded local paths, fixed root-cause rankings, fixed extension blocklists, fixed generated-directory lists, or fixed benefit percentages.

## Core Checks

- Uses the collector with case-specific inputs instead of assuming defaults.
- Runs the collector from the script file, not through stdin, so editor CLI status probes cannot consume the rest of the script.
- Preserves a large workspace when the user asks to optimize that experience.
- Preserves file-browser visibility/editability by default, and distinguishes watcher, search, and Explorer excludes.
- Ranks findings only from evidence present in the current prompt/output.
- Treats operating-system, renderer, watcher, extension, and cache issues as candidate classes, not as guaranteed causes.
- Uses placeholders for paths and commands in examples.
- Avoids applying changes until the user confirms.
- States when impact cannot be quantified because baseline data is missing.
- Keeps social/shareable summaries evidence-bound and avoids long-term improvement claims from short observation windows.
- Routes advanced cases into explicit probes for rendering/input, extension internals, language services, system-pressure context, upstream editor candidates, and remote/container workspaces.
- Treats upstream editor, OS, extension, and remote issues as diagnoses or experiments, not guaranteed direct fixes.
- Requires redaction before external sharing because collector output can contain local paths, project names, process command lines, log paths, and extension identifiers.
- Requires explicit risk boundaries before action: privacy, overclaiming, workspace setting side effects, extension disablement, cache cleanup, system/process experiments, and remote-environment blind spots.

## Manual Eval Prompts

The prompts live in `evals.json`. They intentionally use placeholders and generic categories so the skill must ask for or discover the missing context.
