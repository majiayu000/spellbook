---
name: vscode-doctor
description: Diagnose slow or freezing VS Code-compatible editors with evidence-first, zero-hardcoded-assumption workflow. Use when the user reports editor lag, typing delay, UI freezes, extension host stalls, file watcher noise, high editor CPU/RSS, uses VS Code/Cursor as a file browser over a large folder, or wants a safe editor performance audit.
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
- Do not treat whole-machine load as the editor diagnosis. Record it as context, but keep conclusions and actions focused on editor evidence.
- Treat collector output as sensitive. It can expose local paths, project names, process command lines, workspace names, log paths, and extension identifiers. Redact sensitive details before sharing externally.
- No write operations by default. Do not edit settings, disable extensions, delete caches, run system defaults, change environment variables, or kill processes without explicit confirmation.

## Default Simple Mode

Default to a non-technical user experience unless the user asks for details.

- Treat this skill as invisible to the user: they cannot see the collector, logs, or settings changes unless you explain them.
- Start with one plain-language sentence: `现在看起来是：<正常 / 忙 / 可疑 / 还不确定>` and immediately say what you checked or will check.
- Ask at most one question before collecting evidence. Prefer discovering the editor/workspace automatically.
- Avoid leading with terms like RSS, extension host, FSEvents, renderer, or language server. Put those under `Technical details`.
- Translate technical causes into user-facing labels:
  - file watcher or rescans -> "background file scanning"
  - extension host -> "plugin background process"
  - renderer/UI process -> "editor window rendering"
  - language server or linter -> "code intelligence"
  - workspace surface -> "the folder range the editor is watching"
- Never present a long table as the main answer for a non-technical user.
- Do not use process names such as `systemstatusd`, `WindowServer`, or `coreaudiod` as the headline. Translate them first, for example: "主要压力来自系统后台/窗口渲染/音频服务，不是编辑器本体".
- Present two or three choices as actions, each with:
  - what it changes
  - whether it is reversible
  - what the user might notice
  - how to verify it helped
- Keep "do nothing and observe" as a valid option when evidence is weak.
- If you ran commands or changed files, the final answer must begin with a plain-language action log, not only a diagnosis.
- Never claim the optimization helped unless there is a fresh after-snapshot or user-visible verification. If there is no clean before/after, say the expected effect is a hypothesis and give the next verification step.

Diagnosis-only report shape:

```markdown
现在看起来是：...

我检查了：...

建议先做：...

可选操作：
1. 只观察，不改设置
   适合：...
   会影响：不会
   验证：...
2. 轻量降噪，只处理明显的生成/缓存目录
   适合：...
   会影响：这些目录仍能打开编辑，但外部变化可能需要手动刷新
   撤回：删掉这几条 workspace 设置
3. 深度排查插件
   适合：...
   会影响：先不禁用插件，只做 profiling / bisect 建议

Technical details:
- ...
```

After-action report shape:

```markdown
我刚刚做了：
- 看了什么：...
- 改了哪里：...
- 为什么改：...

你可能会感受到：
- ...

不会发生什么：
- ...

副作用：
- ...

怎么确认有效：
- ...

怎么撤回：
- ...

Technical details:
- ...
```

Rules for after-action reports:
- "看了什么" should name evidence in user terms, such as "editor logs", "current CPU list", "workspace settings", or "large generated folders".
- "改了哪里" must include exact file paths when files were edited.
- "为什么改" must connect each change to observed evidence, not generic optimization folklore.
- "你可能会感受到" must be phrased as possible outcomes, not guaranteed improvement.
- "不会发生什么" must call out important non-effects, for example "files are not deleted" or "folders are not hidden" when true.
- "副作用" must include search/watch/editing tradeoffs for settings changes.
- "怎么确认有效" must include a concrete user action or command and a time window when observation is needed.
- "怎么撤回" must include a backup path or exact rollback command when a file was changed.

## Risk Boundaries

Make these risks explicit before changing settings, disabling extensions, deleting caches, changing system/editor launch flags, or preparing public posts:

- **Privacy leakage**: collector output can expose local paths, private project names, process command lines, workspace names, log paths, extension identifiers, remote host names, or container paths. Share redacted summaries, not raw collector output.
- **Misdiagnosis**: short after-snapshots are immediate checks, not proof of long-term improvement. Do not claim the skill fixed all editor lag or unrelated system load.
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
- **Extension profiling**: profile or bisect extensions because live evidence points at plugin background work.
- **Maintenance**: inspect caches/log volume only when data size is plausibly relevant.

If the user explicitly asks to optimize a large workspace, do not close it, replace it with a narrower folder, or present that as the default fix. Treat narrowing the workspace only as an optional alternative with its own tradeoff.

| Mode | User intent signal | Allowed first actions | Do not do | Verify with |
|---|---|---|---|---|
| Preserve large workspace | "keep the parent folder", "optimize big workspace", "do not close workspace" | watcher/search/language-service exclusions scoped to the workspace; extension profiling; settings proposals | close the parent workspace, open only a child folder, claim file count should shrink | `--status` still shows the large workspace; no new watcher storm; quieter search/language-service processes |
| File browser workspace | "use VS Code as a file browser", "I still want to see/edit files", "can it keep listening without lag" | explain workspace semantics; keep Explorer visibility by default; propose selective watcher/search exclusions for noisy paths; offer a lightweight profile when the user accepts reduced coding intelligence | hide folders with `files.exclude`, shrink the workspace, or silently disable coding features as the default fix | excluded paths remain openable/editable if visible; non-excluded paths still update; no new watcher storm for noisy paths |
| Narrow workspace | "open only this project", "I do not need the parent folder" | open/reuse a smaller folder after confirmation; compare workspace surface | present narrowing as the default fix for large-workspace optimization | `--status` shows the intended smaller folder; file/project-root count drops |
| Extension profiling | "extensions are slow", Running Extensions evidence, plugin background CPU/RSS | profile, bisect, or workspace-disable named extensions seen in evidence | use a fixed extension blocklist or global disablement without confirmation | plugin background CPU/RSS, Running Extensions output, before/after profile |
| Cache/log maintenance | large data dir, corrupt cache/log evidence, user asks cleanup | inspect sizes; propose cleanup with rollback or regeneration notes | delete caches/logs as a generic first fix | data sizes, startup behavior, error recurrence |

If the user's wording is ambiguous, ask one concise question about which mode they want. If their wording is explicit, route directly and continue.

## Collection

Run the collector with values discovered for this case. Leave unknown values empty instead of inventing them.

```bash
cd <path-to-vscode-doctor-skill>
EDITOR_COMMANDS="<space-separated editor cli commands, if known>" \
EDITOR_PROCESS_QUERY="<process regex, if known>" \
EDITOR_DATA_DIRS="<colon-separated data dirs, if known>" \
EDITOR_SETTINGS_FILES="<colon-separated settings files, if known>" \
SETTINGS_QUERY="<settings regex, if known>" \
EDITOR_LOG_DIRS="<colon-separated log dirs, if known>" \
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
- If the user is using a broad parent directory as a file browser, label that intent explicitly before recommending changes.

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
- remote/container/network-filesystem markers when the workspace is not purely local

When the user wants a file-browser-like workspace:
- Treat the goal as "keep files visible and editable while reducing background work."
- Prefer narrowing the active workspace to the current repo when editing deeply.
- If the broad workspace must stay open, recommend targeted workspace-level exclusions for noisy generated or dependency paths.
- Do not assume that hiding files is acceptable; ask or present it as a separate option.

When recommending extension changes:
- Use only extension names seen in live output, user screenshots, or logs.
- Prefer workspace-scoped disablement or profiling over global disablement.
- If the evidence only shows “extension host high,” recommend profiling or bisecting before naming a culprit.

When recommending workspace exclusions:
- Prefer exclusions derived from the project's own ignored/generated paths.
- If you propose a generic pattern, label it as a template for user review, not as evidence.
- Prefer workspace settings over global settings when the issue is tied to one workspace.
- For a preserved large workspace, prefer workspace-scoped settings such as `files.watcherExclude`, `search.exclude`, and supported language-tool excludes. Use `files.exclude` only when the user wants paths hidden from Explorer.
- Keep recommendation and execution separate: first show the proposed setting diff, evidence, expected effect, verification command, and rollback. Apply it only after explicit user confirmation.
- Distinguish the VS Code settings clearly:
  - `files.watcherExclude`: stops continuous file-change watching for matching paths; files can still be opened, edited, and saved, but external changes may need manual refresh or reopen.
  - `search.exclude`: removes matching paths from default global search; files remain visible and editable, and users can temporarily search them by disabling exclude/ignore settings in the search UI.
  - `files.exclude`: hides matching paths from Explorer; avoid this for file-browser mode unless the user explicitly wants the directory hidden.
- For "visible but less noisy" workflows, prefer `files.watcherExclude` plus `search.exclude`, not `files.exclude`.
- Verify watcher changes with fresh watcher logs, editor process CPU/RSS, and user-visible responsiveness; do not expect `code --status` file counts to prove the benefit by itself.

When recommending language, lint, Git, or AI-assistant settings:
- Treat settings such as `python.languageServer`, `ruff.*`, `git.autorefresh`, `git.autoRepositoryDetection`, and `github.copilot.*` as optional load-reduction experiments, not default fixes.
- State the feature cost before recommending them. For example: disabling a language server reduces diagnostics/completion; disabling Git auto-detection reduces Source Control discovery; disabling Copilot removes AI assistance in that workspace.
- Prefer profile-scoped or workspace-scoped experiments over global user settings.
- If the user says they only care about watcher/search pressure, do not propose these settings.

## File Browser Option Ladder

Use this when the user treats VS Code or Cursor primarily as a file browser over a large folder. Present options explicitly before any write:

1. **Conservative browsing**: keep coding features on; add only evidence-backed `files.watcherExclude` and `search.exclude` for high-churn/generated paths. This is the default when the user still edits code and wants IntelliSense, linting, Git refresh, or AI assistance.
2. **Large-folder quiet mode**: keep files visible and editable, but reduce background analysis with workspace-scoped language-tool excludes or Git auto-detection/auto-refresh reductions when those tools are installed or already active. Validate exact setting names from installed extension schemas or current settings before proposing JSON.
3. **File-browser profile**: for users who explicitly say they only browse/edit files and do not need coding intelligence, offer a separate VS Code/Cursor profile or workspace-scoped proposal that disables or quiets language servers, linting, AI code search, dependency scanners, test discovery, minimap, and motion-heavy UI. Name the lost features plainly.

Do not require live evidence of high CPU from Ruff, Copilot, Dependi, Python, Rust, or Git before offering option 3 when the user's intent is explicitly a lightweight file-browser experience. Still do not apply it automatically. Show the proposed diff, say what capability is removed, and include rollback.

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
| Editor/Electron candidate | editor version, `--status`, fresh renderer/main logs, temporary profile comparison if user agrees | launch a temporary profile or stable/insiders comparison; do not mutate current profile | same workspace/action on both profiles, renderer/main log delta |
| Rendering/input candidate | GPU status from editor CLI if available, UI/render/input process CPU/RSS, timestamps of typing lag or renderer unresponsive logs | temporary GPU/input-method isolation only after explicit confirmation | typing latency observation, renderer logs, UI process CPU/RSS before/after |
| Extension internal bug | Running Extensions output, plugin background CPU/RSS, profile output, extension names from evidence | Extension Bisect or workspace-scoped disable of named extensions | profile or CPU/RSS delta, same editor action repeated |
| Extreme project/language service | language-service processes, project-root counts from `--status`, schema-supported language-tool excludes | workspace-scoped language-tool excludes, project root partitioning, tool-specific config changes | language-service CPU/RSS, diagnostics latency, no new watcher/search regressions |
| System pressure context | load, memory, swap, disk free, top CPU/RSS | do not fix system issues inside this skill unless user explicitly changes scope | decide whether editor evidence still explains the symptom |
| Remote/container/network filesystem | remote/container markers, remote logs, local vs remote process split, workspace path type | remote-side collector or narrower remote experiment after confirmation | remote CPU/RSS/logs, network/filesystem latency evidence |

When a probe points to an editor/Electron, OS, extension, or remote upstream issue, report it as a diagnosis with a workaround or next experiment. Do not claim the skill can directly fix upstream bugs.

## Report Template

Use the simple report shape by default. Use this technical structure only when the user asks for a detailed report or the situation is complex:

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

Regression prompts and expected behaviors are documented in `evals/README.md` and `evals/evals.json`; use them when changing the collector or diagnosis workflow.
