---
name: vscode-doctor
description: Diagnose slow or freezing VS Code-compatible editors with evidence-first, zero-hardcoded-assumption workflow. Use when the user reports editor lag, typing delay, UI freezes, extension host stalls, file watcher noise, high editor CPU/RSS, or wants a safe editor performance audit.
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
