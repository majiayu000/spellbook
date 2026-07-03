---
name: codebase-audit
description: "全面代码库审计 — 自适应并行深度分析（前后端契约、数据完整性、异常处理/安全、架构/技术债、配置/缓存），结构化 findings + 对抗验证 + 基线对比，输出按严重程度排序的统一报告和修复路线图。支持 quick 快速体检模式。Use when user asks to audit, analyze, or review an entire codebase for design issues, find hidden bugs, check architecture health, or asks '全面审查', '代码库审计', '分析设计问题', 'audit codebase', 'health check', '有哪些问题', '快速体检'. Also trigger when user asks to find silent degradation, data flow breakpoints, type mismatches between frontend and backend, or wants to understand technical debt across a project."
---

# Codebase Audit — Adaptive Deep Analysis

Comprehensive codebase audit that adapts its agent configuration to the project's tech stack, forces structured findings, adversarially verifies Critical/High findings before they enter the report, diffs against the previous audit's ledger (resolved / still-open / new), and outputs a severity-sorted report plus a phased repair roadmap.

## Core Principles

1. **READ-ONLY** — Audit agents must never create, modify, or delete files in the target. Every agent prompt starts with the read-only preamble in `references/agent-prompts.md`.
2. **Inherit the session model** — Omit the `model` param on all agents so they inherit the session model (usually the strongest available). Only override *upward* if the session model is clearly weak for cross-file reasoning. Never hardcode a specific model name in this skill.
3. **Depth over breadth** — Fewer agents with broader merged scopes beat many shallow agents. Each agent traces issues across file boundaries.
4. **Adaptive** — Agent count and dimensions vary by stack and mode.
5. **Verified findings** — Critical/High findings must survive an adversarial verify pass. Medium findings pass through but are labeled `unverified` in the report.

## Operating Contract

- Direct actions: read-only inspection, local dependency audits, report writing under the target, and ledger updates under `<target>/.audit/` after the user invokes this skill.
- Escalate before: editing audited project source files, dependency manifests, `.gitignore`, CI config, remote issues, PR state, or anything outside the requested audit/report scope.
- Evidence-backed pushback: challenge "all clear" or "resolved" only with file evidence, dependency-audit output, verifier results, or ledger spot-checks.
- Feedback loop: promote repeated misses into prompt updates, ledger matching rules, or fixture eval cases rather than leaving them as session-only notes.

## Gotchas

- Dependency-audit commands must run from `{TARGET_DIR}`, not the assistant's incidental cwd.
- Finder agents must not read `evals/expected-findings.json` or eval README files when auditing the planted-bug fixture.
- A previous ledger miss is not proof that a finding was resolved; spot-check the file before marking an old finding `resolved`.

## Modes

| Mode | Trigger | Agents | Verify pass | Ledger |
|------|---------|--------|-------------|--------|
| **full** (default) | plain invocation, "全面审查" | 3–5 by stack (+ optional dims) | yes | yes |
| **quick** | "quick" in args, "快速体检" | 2 (Silent Degradation & Security; Data Integrity & Registry) | no — all findings labeled `unverified` | yes |

**Optional dimensions** (full mode only, enable when user asks or the repo obviously needs them):
- `tests` — test quality: assertion strength, skip markers, coverage of critical paths (Agent 6)
- `concurrency` — races, blocking calls in async, leaked tasks/goroutines (Agent 7)

## Workflow

### Phase 0: Detect & Prepare

1. **Stack detection**: `package.json`/`tsconfig.json` → TS/JS; `pyproject.toml`/`requirements.txt` → Python; `Cargo.toml` → Rust; `go.mod` → Go; multiple → full-stack.
2. **Size estimate**: `tokei <target>` (fallback: `find <target> -name '*.<ext>' | xargs wc -l`), excluding vendored/generated code. If effective size ≥ 400K LOC, split each agent's scope by top-level directory and note the split in the report.
3. **Exclusions** (always, in every agent prompt): `node_modules/`, `vendor/`, `target/`, `dist/`, `build/`, `.git/`, lockfiles, generated code.
4. **Ledger**: read `<target>/.audit/findings.json` if it exists — this is the previous audit baseline (format: `references/ledger-format.md`).
5. **Deterministic dependency audit**: from `{TARGET_DIR}` (never the assistant's incidental cwd), run each matching tool and feed raw output to the Error Handling & Security prompt:
   - Rust: `cargo audit`
   - Node: `npm audit`
   - Python metadata (`pyproject.toml` / `setup.py`): `pip-audit .`
   - Python requirements (`requirements.txt`): `pip-audit -r requirements.txt`
   - Python fallback with no project files: `pip-audit .`
   - Go: `govulncheck ./...`
   If a required tool is unavailable, the report must state `依赖审计降级跳过: <tool>`; never omit the degradation silently.

### Phase 1: Assemble Dimensions

Pick the configuration by detected stack. Full prompt templates in `references/agent-prompts.md`; prepend the read-only preamble and inject `{TARGET_DIR}` / `{STACK_INFO}` into each.

**Full-Stack (5 agents)** — frontend + backend both present:

| # | Dimension | Scope (merged) |
|---|-----------|----------------|
| 1 | Frontend-Backend Contract | Type consistency + rendering pipeline + serialization boundaries. Reads BOTH sides. |
| 2 | Data Integrity & Flow | End-to-end pipeline tracing, field dropping, declaration-execution gaps, registry coverage alignment. |
| 3 | Error Handling & Security | Silent degradation, exception patterns, secrets, injection, unsafe deserialization. |
| 4 | Architecture & Code Quality | Layer violations, god objects, duplication/drift, extension cost, registry cross-reference. |
| 5 | Config & Persistence | Config completeness, cache key/integrity, DB schema, temp files, state persistence. |

**Backend-Only (4 agents)**: replace #1 with "API Contract & Data Integrity" (which absorbs #2's data-flow/registry scope — do NOT also dispatch #2); keep #3–#5.
**Frontend-Only (3 agents)**: Component Architecture & Rendering; Error Handling & Code Quality; Config & Build.
**Quick mode (2 agents)**: Silent Degradation & Security (= #3); Data Integrity & Registry (= #2 core).

Fallback-path agent types (when using the Agent tool instead of Workflow): agent availability is environment-specific — check the subagent registry visible in the current session and use only type names that appear there. Never invent aliases (there is no generic `reviewer` type). If no specialized type matches, use `general-purpose` (or the environment's default catch-all) for every dimension; the prompts are self-contained. See the example mapping in `references/agent-prompts.md`.

### Phase 2: Orchestrate

**Preferred — Workflow tool** (skill invocation is the user's opt-in): use the script in `references/workflow-template.md`. It schema-forces every finder's output into structured findings, then pipelines each dimension's Critical/High findings straight into adversarial verify agents (no barrier — verification starts while other dimensions are still scanning).

**Fallback — Agent tool** (if Workflow is unavailable): launch all finder agents in a SINGLE message; prompts already demand the same JSON output. After they return, launch one verify agent per Critical/High finding (also batched in one message), using the verify prompt from `references/workflow-template.md`.

### Phase 3: Dedup & Ledger Diff

Dedup:
- Same file + same line → merge.
- Same root cause found by multiple agents → keep the most detailed, note cross-agent confirmation (raises confidence).
- Severity conflicts → use the highest.

Verification results:
- `confirmed=false` findings do NOT enter the main report; list them in an appendix "Refuted by verification" with the refutation reason (keeps the work auditable).
- Verifier failed/absent → keep the finding, label `unverified`.

Ledger diff (skip if no previous ledger — everything is `new`):
- Match previous ↔ current findings by **(category, file, root-cause summary)** — never by line number (lines drift).
- Previous finding with no current match → open the file and spot-check before marking `resolved`; if still present but missed, re-add as `still-open`.
- Classify every current finding: `new` / `still-open`.
- Write the updated ledger to `<target>/.audit/findings.json`. If the repo is tracked and `.audit/` isn't ignored, suggest adding it to `.gitignore` (don't edit `.gitignore` yourself).

### Phase 4: Report

Write the full report to `<target>/audit-report-YYYY-MM-DD.md`, then post a chat summary: counts per severity, top Criticals, ledger delta (N resolved / N still-open / N new), dependency-audit status, and the roadmap.

Report body requirements:
- Use Chinese for problem descriptions, impact analysis, and repair advice; keep code identifiers, paths, and error messages in their original form.
- Separate each finding into fact / inference / recommendation: the finding itself is a fact with `file:line`; impact is an inference with confidence; repair advice is a recommendation with stated assumptions.
- Inferred-only findings cannot be higher than Medium unless a verifier confirms user-visible or security impact.

Report structure:

```markdown
# [Project] Codebase Audit Report
> Date / Target / Stack / Mode / Agents / Dependency audit / Previous audit: date or "none"

## Summary
| Level | Count | Verified | Key Areas |

## Delta vs Previous Audit   (omit if first audit)
Resolved: N (list) | Still-open: N | New: N

## Critical (Fix Immediately)
Per finding: file:line, code snippet, risk, fix suggestion, verify status.

## High / P1 (Fix This Week)     — grouped by category
## Medium / P2 (Plan to Fix)     — labeled unverified where applicable

## Refuted by Verification       — appendix: finding + refutation reason

## Repair Roadmap
| Phase | Scope | Est. Files |
```

## Severity Classification

| Level | Criteria |
|-------|----------|
| **Critical** | Data loss, rendering failure, security vulnerability, complete feature breakage affecting users NOW |
| **High/P1** | Silent degradation (user sees wrong/incomplete output), type mismatches causing data truncation, missing config causing empty output, architectural violations blocking development |
| **Medium/P2** | Code duplication, inconsistent patterns, suboptimal error handling, tech debt that slows development but doesn't break features |

## References

- `references/agent-prompts.md` — read-only preamble + prompt templates (Agents 1–7)
- `references/stack-patterns.md` — per-stack search patterns
- `references/workflow-template.md` — Workflow script, finding/verdict schemas, verify prompt
- `references/ledger-format.md` — ledger JSON schema and matching rules
- `evals/` — planted-bug fixture; evals measure recall against `evals/expected-findings.json`
