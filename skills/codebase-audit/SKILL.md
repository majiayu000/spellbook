---
name: codebase-audit
description: "全面代码库审计 — 自适应并行深度分析（前后端契约、数据完整性、异常处理/安全、架构/技术债、配置/缓存），输出按严重程度排序的统一报告和修复路线图。Use when user asks to audit, analyze, or review an entire codebase for design issues, find hidden bugs, check architecture health, or asks '全面审查', '代码库审计', '分析设计问题', 'audit codebase', 'health check', '有哪些问题'. Also trigger when user asks to find silent degradation, data flow breakpoints, type mismatches between frontend and backend, or wants to understand technical debt across a project."
---

# Codebase Audit — Adaptive Deep Analysis

A comprehensive codebase audit that adapts its agent configuration to the project's tech stack. Each agent uses the highest-tier model for maximum thoroughness. Findings are verified before compilation, then compiled into a unified report sorted by severity with a phased repair roadmap.

## Core Principles

1. **Highest-tier model** — All audit agents MUST use the highest-capability model available in the current environment (e.g. `fable`; `opus` acceptable as fallback). Never use lightweight tiers (haiku) for audit agents. If the highest tier is unavailable, fall back one tier and note the downgrade in the report header.
2. **Depth over breadth** — Fewer agents with broader scope and deeper analysis beats many shallow agents. Each agent should trace issues across file boundaries.
3. **Adaptive** — Agent count and focus areas vary by project type. Don't waste an agent on "frontend rendering" for a backend-only project.
4. **Verify before report** — No Critical/High finding enters the report unverified. LLM audit agents misreport intentional patterns (deliberate fallbacks, feature gates) as defects; Phase 1.5 exists to catch that.

## When to Use

- User asks to audit/review/analyze an entire codebase
- User wants to find hidden bugs, silent degradation, or design inconsistencies
- User asks about technical debt, architecture health, or "what's broken"
- Before a major refactor or after inheriting an unfamiliar codebase
- Periodic health check (monthly/quarterly) — see Phase 3 for baseline diffing

## Workflow

### Phase 0: Tech Stack Detection & Deterministic Scans

Detect the project's tech stack to determine the agent configuration:

```
Detection checklist:
- package.json / tsconfig.json → TypeScript/JavaScript (React, Next.js, Vue, etc.)
- pyproject.toml / requirements.txt / setup.py → Python (FastAPI, Django, Pydantic, etc.)
- Cargo.toml → Rust (serde, axum, actix, etc.)
- go.mod → Go (gin, echo, gorm, etc.)
- Multiple stacks → Full-stack project (frontend + backend)
- Async runtime signals: Cargo.toml contains tokio/async-std, go.mod present,
  asyncio imports → enable the Concurrency & Async Hygiene section for the
  Data Integrity agent (see agent-prompts.md)
```

After stack detection, run the matching dependency audit from the target project root, never from the assistant's incidental current working directory. If the user supplied an explicit target path, use it as `{TARGET_DIR}` before invoking the tool. For Python projects, run each matching audit input that exists and feed all outputs to the security agent (deterministic, zero LLM cost):

```
- Rust → cd "{TARGET_DIR}" && cargo audit
- Node → cd "{TARGET_DIR}" && npm audit
- Python project metadata (`pyproject.toml` / `setup.py`) → cd "{TARGET_DIR}" && pip-audit .
- Python requirements (`requirements.txt`) → cd "{TARGET_DIR}" && pip-audit -r requirements.txt
- Python environment fallback (no project files found) → cd "{TARGET_DIR}" && pip-audit .
- Go → cd "{TARGET_DIR}" && govulncheck ./...
```

Feed the raw output to the Error Handling & Security agent (frontend-only: to Agent 2) for classification: Critical = RCE-grade CVE with PoC on a reachable path; High = known vuln on a reachable path. If the tool is unavailable, the report MUST state "依赖审计降级跳过" — never omit silently.

### Phase 1: Launch Agents (Adaptive)

Based on the detected stack, choose the appropriate agent configuration below. Launch ALL agents in a SINGLE message, each with the model tier defined in Core Principles #1.

Read `references/agent-prompts.md` for complete prompt templates. Every prompt MUST be self-contained: target path, stack info, and the Unified Output Contract (defined at the top of agent-prompts.md) — sub-agents cannot see this file.

Before launching, verify every agent Type against the available subagent registry. If a type is not registered, STOP and report the missing type — do NOT substitute a similar one.

---

#### Full-Stack Projects (5 agents)

When both frontend and backend exist (e.g., React + FastAPI, Next.js + Go).

| # | Agent | Type | Scope (merged dimensions) |
|---|-------|------|---------------------------|
| 1 | **Frontend-Backend Contract** | `senior-code-reviewer` | Type consistency (field names, types, missing fields) + Rendering pipeline (layout/block/card routing completeness, dead slots, unrendered fields) + Serialization boundaries (models that silently drop fields). This agent reads BOTH sides and traces data across the API boundary. |
| 2 | **Data Integrity & Flow** | `senior-code-reviewer` | Data pipeline end-to-end: from input through every transformation layer to output. Covers: field resolver filters, serialization/deserialization, model_validate/model_dump, cache read/write symmetry, registry key-set alignment (sole owner — Agent 4 must not re-check). Also covers: declaration-execution gaps (registered but unwired handlers, enum without config), and Concurrency & Async Hygiene when an async runtime is detected. |
| 3 | **Error Handling & Security** | `security-auditor` | Exception patterns (bare except, debug-level errors, warning+fallback), security (hardcoded secrets, injection, unsafe deserialization), silent degradation (error paths that produce user-visible wrong output instead of failing), classification of Phase 0 dependency-audit output. |
| 4 | **Architecture & Code Quality** | `code-archaeologist` | Layer violations, circular dependencies, god objects (files >800 lines), code duplication (parallel systems, scattered mapping tables), extension cost analysis (how many files to add a new type), DI pattern consistency, test quality (coverage gaps, weakened assertions, skip markers, stale tests). |
| 5 | **Config & Persistence** | `code-archaeologist` | Config completeness (template/schema vs code expectations, conflicting defaults), cache key completeness (missing code version dimension), DB schema consistency, temp file cleanup, state persistence across restarts. |

---

#### Backend-Only Projects (4 agents)

When only backend exists (Python API, Rust service, Go microservice, etc.)

| # | Agent | Type | Scope |
|---|-------|------|-------|
| 1 | **API Contract & Data Integrity** | `senior-code-reviewer` | API schema vs internal models, serialization boundaries, data pipeline tracing, field dropping, registry key-set alignment, declaration-execution gaps, concurrency hygiene when async runtime detected. |
| 2 | **Error Handling & Security** | `security-auditor` | Same as full-stack Agent 3. |
| 3 | **Architecture & Code Quality** | `code-archaeologist` | Same as full-stack Agent 4. |
| 4 | **Config & Persistence** | `code-archaeologist` | Same as full-stack Agent 5. |

---

#### Frontend-Only Projects (3 agents)

When only frontend exists (React SPA, Vue app, etc.)

| # | Agent | Type | Scope |
|---|-------|------|-------|
| 1 | **Component Architecture & Rendering** | `senior-code-reviewer` | Type routing completeness, component registration gaps, dead props/slots, state management consistency, API consumption patterns, minimal accessibility checks (alt/label/keyboard reachability). |
| 2 | **Error Handling & Code Quality** | `senior-code-reviewer` | Unhandled promise rejections, error boundaries, catch-and-ignore patterns, god components, code duplication, test quality, dependency-audit classification. |
| 3 | **Config & Build** | `code-archaeologist` | Build config consistency, env variable management, bundle analysis, dead dependencies. |

---

### Phase 1.5: Verify Findings

For every Critical and High finding:

1. Spawn 1-2 verifier agents (same model tier). Input = ONLY the finding's claim + involved file paths (minimal context).
2. The verifier must actively search for counter-evidence: test coverage, feature flags, intentional-design comments, call sites that handle the "missing" case.
3. Verdict: confirm / refute / uncertain, with reasons.
4. Refuted findings move to a report appendix "已排除项" with the refutation reason (do NOT delete).
5. Medium findings: spot-check ≥30%.

Critical findings MUST be 已复核 before entering "Fix Immediately".

### Phase 2: Compile Unified Report

After verification completes, compile findings into a single report.

> 报告正文（问题描述、影响分析、修复建议）一律使用中文；代码片段、文件路径、标识符、错误消息保留原文。
>
> 每条发现按三层呈现：发现本体 = 事实（带 file:line）；影响分析 = 推断（带置信度，evidence_type 为 inferred 的不得高于 medium）；修复建议 = 建议（带前提假设）。

```markdown
# [Project Name] Codebase Audit Report

> Audit date: YYYY-MM-DD
> Target: path
> Tech stack: detected stack
> Agents: N (list agent names) | Model tier: (note any downgrade)
> Dependency audit: ran / 依赖审计降级跳过

## Summary
| Level | Count | Key Areas |
|-------|-------|-----------|
| Critical | N | ... |
| High | N | ... |
| Medium | N | ... |
| Low | N | ... |

## Critical (Fix Immediately)
| # | Problem | Agent | Impact | evidence_type | confidence | 验证状态 |
|---|---------|-------|--------|---------------|------------|----------|
For each: file:line, code snippet, risk description (推断需标注置信度), fix suggestion (标注前提).

## High (Fix This Week)
### [Category]
[Same columns as Critical]

## Medium (Plan to Fix)
[Same structure]

## Low (Informational)
[Same structure; include only if Low findings exist]

## 已排除项 (Refuted in Phase 1.5)
| # | Original claim | Refutation reason |
|---|----------------|-------------------|

## Repair Roadmap
| Phase | Scope | Est. Files |
|-------|-------|------------|
| Phase 0 (urgent) | Critical fixes | ~N files |
| Phase 1 (this week) | High priority | ~N files |
| Phase 2 (next week) | Medium priority | ~N files |
| Phase 3 (ongoing) | Low / Architecture | ~N files |

Est. Files = 该级别所有发现 files 字段去重并集大小；若修复涉及发现位置之外的文件，可追加估算但必须标注「推断，置信度低」。
```

### Deduplication

All agents emit the Unified Output Contract table (see agent-prompts.md), so the severity scale and the `files` dedup key are consistent across agents:

- Same file + same line → merge
- Same root cause found by multiple agents → keep the most detailed one, note cross-agent confirmation (this actually increases confidence)
- Severity conflicts → use the highest (scales are unified, so this is mechanical)

### Severity Classification

The authoritative severity rubric lives in the **Unified Output Contract** at the top of `references/agent-prompts.md` — it must be inside the prompts because sub-agents cannot see this file. Do not redefine it here; Phase 2 uses the same four levels (Critical / High / Medium / Low).

### Phase 3: Baseline Diff (periodic health checks)

Persist artifacts after every audit:

- `<target>/.audit/report-YYYY-MM-DD.md`
- `<target>/.audit/findings-YYYY-MM-DD.json` — the structured finding table
- Stable finding ID: `hash(category + 归一化文件路径 + title 关键词)` (robust to line drift)
- `<target>/.audit/false-positives.json` — user-marked false positives; filter or downweight matching findings during the next compile step

When a previous `findings-*.json` exists, add a baseline diff section:

| 状态 | 定义 |
|---|---|
| 已修复 | 上次有、本次无（需复核确认，不默认已修） |
| 仍存在 | 两次都有（标注存活轮数） |
| 新增 | 本次新出现 |

Summary 表增加环比列。

## Stack-Specific Patterns

Read `references/stack-patterns.md` for technology-specific search patterns.

## Evals

`evals/evals.json` contains trigger/output test cases — keep `expected_output` in sync whenever the agent configuration or report format changes (a past 10-agent → 5-agent refactor left them stale and permanently failing).
