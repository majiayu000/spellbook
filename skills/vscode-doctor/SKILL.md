---
name: vscode-doctor
description: Diagnose slow or freezing VS Code-compatible editors with evidence-first, zero-hardcoded-assumption workflow. Use when the user reports editor lag, typing delay, UI freezes, extension host stalls, file watcher noise, high editor CPU/RSS, uses VS Code for browsing files in a large folder, or wants a safe editor performance audit.
allowed-tools: Bash, Read
metadata:
  argument-hint: "[workspace-root optional]"
---

# VS Code Doctor

Diagnose editor performance from the current machine state. Do not import old observations, fixed paths, fixed extension names, fixed OS bugs, or fixed generated-directory lists into the diagnosis.

## Non-Negotiables

- No hardcoded local paths. Use the user's stated workspace, discovered editor status, or explicit placeholders.
- No fixed root cause order. Rank only by fresh evidence from this run.
- No fixed extension blocklist. Treat extension names as evidence only when they appear in live output or user-provided screenshots.
- No fixed generated-directory list. Discover ignored/generated paths from the workspace, editor settings, repository metadata, or user-provided patterns.
- No fixed benefit percentages. If there is no before/after baseline, say the impact cannot be reliably quantified.
- Do not treat whole-machine load as the diagnosis. Record it as context, but keep conclusions and actions focused on editor evidence.
- Treat collector output as potentially sensitive. It may contain local paths, project names, process command lines, workspace names, log paths, and extension identifiers. Redact sensitive details before sharing externally.
- No write operations by default. Do not edit settings, disable extensions, delete caches, run system defaults, change environment variables, or kill processes without explicit confirmation.

## Risk Boundaries

Make these risks explicit before changing settings, disabling extensions, deleting caches, changing system/editor launch flags, or preparing public posts:

- **Privacy leakage**: collector output can expose local paths, private project names, process command lines, workspace names, log paths, extension identifiers, remote host names, or container paths. Share redacted summaries, not raw collector output.
- **Misdiagnosis**: short after-snapshots are immediate checks, not proof of long-term performance improvement. Do not claim the skill fixed all VS Code lag or fixed unrelated system load.
- **Workspace setting side effects**: `files.exclude`, `search.exclude`, watcher excludes, and language-tool excludes can hide files, reduce search coverage, or suppress diagnostics. Prefer workspace-scoped settings, show the diff first, and include rollback.
- **Extension side effects**: disabling an extension can remove formatting, linting, IntelliSense, auth helpers, or remote tooling. Prefer profiling, Extension Bisect, or workspace-scoped disablement of extensions named by evidence.
- **Cache/log cleanup side effects**: deleting caches or storage can force reindexing, relogin, or loss of local UI state. Inspect sizes first; do not delete as a generic optimization.
- **System/process side effects**: killing processes, changing GPU/input-method behavior, or changing editor launch flags can interrupt active work. Treat them as explicit experiments with verification and rollback.
- **Remote environment blind spots**: local `code --status` and local process samples do not prove Remote SSH, WSL, Dev Container, or network filesystem root causes. Collect remote-side evidence before recommending remote changes.

## Intent Gate

Before proposing a fix, identify which workflow the user wants:

- **Preserve large workspace**: keep the current parent/workspace open and reduce watcher/search/language-service noise.
- **File browser workspace**: keep a large folder visible for browsing/editing while reducing editor background work.
- **Narrow workspace**: open only a smaller project root to reduce workspace surface.
- **Extension profiling**: profile or bisect extensions because live evidence points at extension-host work.
- **Maintenance**: inspect caches/log volume only when data size is plausibly relevant.

If the user explicitly asks to optimize a large workspace, do not close it, replace it with a narrower folder, or present that as the fix. Treat narrowing the workspace only as an optional alternative with its own tradeoff.

Use this routing table before analysis:

| Mode | User intent signal | Allowed first actions | Do not do | Verify with |
|---|---|---|---|---|
| Preserve large workspace | "keep the parent folder", "optimize big workspace", "do not close workspace" | watcher/search/language-service exclusions scoped to the workspace; extension profiling; settings proposals | close the parent workspace, open only a child folder, claim file count should shrink | `--status` still shows the large workspace; no new watcher storm; quieter search/language-service processes |
| File browser workspace | "use VS Code as a file browser", "I still want to see/edit files", "can it keep listening without lag" | explain workspace semantics; keep Explorer visibility by default; propose selective watcher/search exclusions for noisy paths; offer a tiered lightweight/file-browser profile when the user is willing to trade coding intelligence for browsing speed | hide folders with `files.exclude`, shrink the workspace, or silently disable coding features as the default fix | excluded paths remain openable/editable if visible; non-excluded paths still update; no new watcher storm for noisy paths |
| Narrow workspace | "open only this project", "I do not need the parent folder" | open/reuse a smaller folder after confirmation; compare workspace surface | present narrowing as the default fix for large-workspace optimization | `--status` shows the intended smaller folder; file/project-root count drops |
| Extension profiling | "extensions are slow", Running Extensions evidence, extension-host CPU/RSS | profile, bisect, or workspace-disable named extensions seen in evidence | use a fixed extension blocklist or global disablement without confirmation | extension-host CPU/RSS, Running Extensions output, before/after profile |
| Cache/log maintenance | large data dir, corrupt cache/log evidence, user asks cleanup | inspect sizes; propose cache/log cleanup with rollback or regeneration notes | delete caches/logs as a generic first fix | data sizes, startup behavior, error recurrence |

If the user's wording is ambiguous, ask one concise question about which mode they want. If their wording is explicit, route directly and continue.

## Collection

Run the collector with values discovered for this case. Leave unknown values empty instead of inventing them.

```bash
cd <path-to-vscode-doctor-skill>
EDITOR_COMMANDS="<space-separated editor cli commands, if known>" \
EDITOR_PROCESS_QUERY="<process regex, if known>" \
EDITOR_DATA_DIRS="<colon-separated data dirs, if known>" \
EDITOR_SETTINGS_FILES="<colon-separated settings files, if known>" \
EDITOR_LOG_DIRS="<colon-separated log dirs, if known>" \
RENDER_PROCESS_QUERY="<rendering/input process regex, if relevant>" \
LANGUAGE_PROCESS_QUERY="<language service process regex, if relevant>" \
REMOTE_MARKER_PATHS="<colon-separated remote/container marker paths, if relevant>" \
WORKSPACE_SIZE_PATHS="<colon-separated cache/build paths to size, if relevant>" \
LOG_FILE_GLOB="<log file glob, if known>" \
LOG_SIGNAL_QUERY="<log regex, if known>" \
GENERATED_DIR_PATTERNS="<colon-separated generated directory names, if user/project supplied>" \
./scripts/collect_vscode_diagnostics.sh "<workspace-root>"
```

Run the collector from the script file. Do not pipe it into `bash` through stdin; some editor CLIs read stdin during `--status`, which can truncate the collector run.

Discovery rules:
- If the user gives the opened workspace, pass it as the script argument.
- If the user does not give the workspace, infer it from editor status output, visible state, or ask a concise question.
- If an editor CLI/path/log directory cannot be discovered, skip that probe and state that the evidence is missing.
- If a signal comes from logs, include the log path and timestamp.

## Analysis

Classify each finding by evidence strength:

- **High priority**: current CPU/RSS/log/status evidence directly explains the symptom and the next experiment is low risk.
- **Medium priority**: plausible contributor with partial evidence, or a safe optimization whose current impact is not proven.
- **Low priority**: maintenance or cleanup item without direct evidence of causing the symptom.

Common evidence types to look for, without assuming any one must exist:
- editor main/renderer/extension-host process CPU or RSS
- language service or extension child-process CPU/RSS
- file watcher errors or repeated workspace rescans
- large workspace surface area from editor status, VCS metadata, or ignored/generated paths
- repeated extension-host unresponsive signals
- UI process pressure that correlates with editor renderer activity
- cache or storage size only when it is large enough to plausibly matter
- rendering/input context such as editor GPU status, UI process pressure, input-method process pressure, or editor logs that mention renderer hangs
- remote/container/network-filesystem markers when the workspace is not purely local

When recommending extension changes:
- Use only extension names seen in live output, user screenshots, or logs.
- Prefer workspace-scoped disablement or profiling over global disablement.
- If the evidence only shows “extension host high,” recommend profiling or bisecting before naming a culprit.

When recommending workspace exclusions:
- Prefer exclusions derived from the project's own ignored/generated paths.
- If you propose a generic pattern, label it as a template for user review, not as evidence.
- Prefer workspace settings over global settings when the issue is tied to one workspace.
- For a preserved large workspace, prefer workspace-scoped settings such as `files.watcherExclude`, `search.exclude`, and language-tool excludes supported by installed extensions. Use `files.exclude` only when the user wants paths hidden from Explorer. Validate extension setting types from the installed extension schema before suggesting exact JSON.
- Keep recommendation and execution separate: first show the proposed setting diff, evidence, expected effect, verification command, and rollback. Apply it only after explicit user confirmation.

Workspace setting semantics to explain when relevant:
- `files.watcherExclude` reduces background file watching for matched paths. Files can still be opened and edited, but external changes may need manual refresh or reopen to appear.
- `search.exclude` removes matched paths from default workspace search. Files can still be opened and edited; users can temporarily include them by overriding exclude settings in the search UI.
- `files.exclude` hides matched paths from Explorer. Do not recommend it for file-browser workflows unless the user explicitly wants those paths hidden.
- Fully live-watching every high-churn directory in a very large workspace while guaranteeing no lag is not a realistic promise. Recommend selective watching: keep normal source paths watched and exclude only evidence-backed noisy/generated/high-churn paths.

## File Browser Option Ladder

Use this when the user treats VS Code primarily as a file browser over a large folder. Present options explicitly so the user can choose the tradeoff before any write:

1. **Conservative browsing**: keep coding features on; add only evidence-backed `files.watcherExclude` and `search.exclude` for high-churn/generated paths. This is the default when the user still edits code and wants IntelliSense, linting, Git refresh, or AI assistance.
2. **Large-folder quiet mode**: keep files visible and editable, but reduce background analysis with workspace-scoped language-tool excludes such as Python analysis excludes, Rust analyzer exclude dirs, and Git auto-detection/auto-refresh reductions when those tools are installed or already active. Validate exact setting names from installed extension schemas or current settings before proposing JSON.
3. **File-browser profile**: for users who explicitly say they only browse/edit files and do not need coding intelligence, offer a separate VS Code profile or workspace-scoped proposal that disables or quiets language servers, linting, AI code search, dependency scanners, test discovery, minimap, and motion-heavy UI. Name the lost features plainly: IntelliSense/diagnostics, lint/fix/imports, Copilot/code search context, dependency alerts, Git auto-refresh, and test discovery.

Do not require live evidence of high CPU from Ruff, Copilot, Dependi, Python, Rust, or Git before offering option 3 when the user's intent is explicitly a lightweight file-browser experience. Still do not apply it automatically. Show the proposed diff, say what capability is removed, and include rollback. If the user's goal is performance diagnosis rather than a browsing profile, keep extension and language-service disablement evidence-driven.

## Large Workspace Playbook

Use this when the user wants to keep a parent directory open.

1. Confirm the active editor still reports the large workspace in `--status`.
2. Identify noisy paths only from fresh evidence:
   - file watcher log paths and timestamps
   - current search/index processes such as ripgrep
   - ignored/generated directories found in the workspace
   - language service child processes and installed extension schemas
3. Propose the smallest workspace-scoped change:
   - `files.watcherExclude` for paths causing watcher drops or generated directories
   - `search.exclude` for generated/cache directories that pollute search
   - `files.exclude` only for paths the user should not browse in Explorer
   - language-tool excludes only when the running tool and schema support them
4. Do not disable extensions or clear caches unless current evidence points there and the user confirms the specific experiment.
5. Verify without changing the goal: after the change, confirm the large workspace is still open and compare watcher/search/language-service evidence.

Avoid saying the workspace file count should drop after watcher/search excludes. `code --status` may still report the same workspace surface; the expected improvement is fewer watcher storms, less noisy search/index work, or quieter language-service processes.

## Advanced Probe Playbooks

Use these modules when baseline evidence or user wording points beyond simple watcher/search cleanup.

| Probe | Evidence to collect | Safe experiments after confirmation | Verification |
|---|---|---|---|
| VS Code / Electron candidate | editor version, `--status`, fresh renderer/main logs, temporary profile comparison if user agrees | launch a temporary profile or Insiders/current stable comparison; do not mutate current profile | same workspace/action on both profiles, renderer/main log delta |
| Rendering / macOS input candidate | GPU status from editor CLI, UI/render/input process CPU/RSS via `RENDER_PROCESS_QUERY`, timestamps of typing lag or renderer unresponsive logs | temporary `--disable-gpu` or input-method isolation only after explicit confirmation | typing latency observation, renderer logs, UI process CPU/RSS before/after |
| Extension internal bug | Running Extensions output, extension-host CPU/RSS, extension-host profile, extension names from evidence | Extension Bisect or workspace-scoped disable of named extensions | extension-host profile or CPU/RSS delta, same editor action repeated |
| Extreme project / language service | language-service processes via `LANGUAGE_PROCESS_QUERY`, project-root counts from `--status`, schema-supported language-tool excludes | workspace-scoped language-tool excludes, project root partitioning, tool-specific config changes | language-service CPU/RSS, diagnostics latency, no new watcher/search regressions |
| System pressure context | load, memory, swap, disk free, top CPU/RSS | do not fix system issues inside this skill unless user explicitly changes scope | decide whether VS Code evidence still explains the symptom |
| Remote / container / network filesystem | remote/container markers, remote extension-host logs, local vs remote process split, workspace path type | remote-side collector or narrower remote experiment after confirmation | remote extension-host CPU/RSS/logs, network/filesystem latency evidence |

When a probe points to a VS Code/Electron, OS, extension, or remote upstream issue, report it as a diagnosis with a workaround or next experiment. Do not claim the skill can directly fix upstream bugs.

## Report Template

Use this concise structure:

```markdown
## Editor Performance Diagnosis

### Evidence
| Signal | Current value | Source | Confidence |
|----|----|----|----|
| ... | ... | ... | high/medium/low |

### Priority
#### High
1. ...

#### Medium
1. ...

#### Low
1. ...

### Options
| Option | When to use | Expected impact | Cost | Verify | Roll back |
|----|----|----|----|----|----|
| ... | ... | Cannot quantify without baseline / based on observed delta | ... | ... | ... |

### Next Step
Ask the user which option to run first. Do not apply changes until they confirm.
```

If the user wants a social-media record, add a compact section:

```markdown
### Shareable Summary
- Goal: ...
- Baseline evidence: ...
- One change: ...
- After evidence: ...
- Caveat: ...
- Redaction: local paths/project names/process command lines reviewed before sharing.
```

Only include measured deltas. If the after window is short, say it is an immediate check rather than proof of long-term improvement.

## Verification

Before claiming improvement, collect a fresh after-snapshot with the same collector inputs used for the baseline. Compare only observed values:

```markdown
## Before / After

| Metric | Before | After | Result |
|----|----:|----:|----|
| ... | ... | ... | improved / unchanged / worse / unknown |

Conclusion:
- Experiment result: ...
- Remaining evidence: ...
- Next step: ...
- Rollback: ...
```

If the before snapshot is missing, write: `缺少调整前 baseline，无法可靠量化收益`.
