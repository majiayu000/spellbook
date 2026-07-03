# Agent Prompt Templates

**Model**: omit the `model` param — agents inherit the session model. Only override upward if the session model is clearly weak for cross-file reasoning. Never hardcode a model name.

**Every prompt MUST begin with this preamble** (replace nothing):

```
READ-ONLY AUDIT — you must not create, modify, or delete any file. Your only output is findings.
Exclude from analysis: node_modules/, vendor/, target/, dist/, build/, .git/, lockfiles, and generated code.
Output ONLY a JSON object: {"findings": [{"category": str, "severity": "critical"|"high"|"medium",
"file": str, "line": int, "summary": str, "evidence": str (quote the actual code),
"evidence_type": "observed"|"inferred", "confidence": "high"|"medium"|"low",
"fix_suggestion": str}]}.
Critical requires direct observed evidence. Inference chains longer than two steps must be confidence <= medium.
No prose outside the JSON. (When launched via Workflow with a schema, the harness enforces this shape.)
```

Replace `{TARGET_DIR}` and `{STACK_INFO}` based on the detected stack. Adapt technology-specific sections accordingly.

---

## Full-Stack Configuration (5 agents)

### Agent 1: Frontend-Backend Contract

```
Deep audit of {TARGET_DIR} for frontend-backend contract consistency.

Tech stack: {STACK_INFO}

You are responsible for THREE merged dimensions: type consistency, rendering pipeline, and serialization boundaries. The key insight is that these are all about the same thing — does data survive the journey from backend to frontend intact?

### Type Definitions
For each shared data structure, compare frontend and backend:
1. Field names — identical after case conversion (snake_case ↔ camelCase)? Check aliases.
2. Field types — match? (str vs string, Optional vs undefined, int|str vs number|string)
3. Missing fields — exist on one side but not the other?
4. Enum/union values — all variants defined on both sides?
5. Serialization aliases — do backend alias names match frontend property names exactly?

### Rendering Pipeline
For each data type the backend can produce:
1. Is there a frontend renderer/component for it?
2. What happens with unknown types? Crash, blank, or graceful fallback?
3. Slots/props declared in types but never populated or consumed?
4. Fields backend sends but frontend never reads (wasted data)?
5. Fields frontend reads but backend never sends (always undefined)?

### Serialization Boundaries
For each model that participates in serialization/deserialization:
1. Does it silently drop unknown fields? (Pydantic extra="ignore", serde's default ignore-unknown
   behavior, Zod's DEFAULT strip mode — note Zod .strict() THROWS on unknown keys, it does not drop)
2. Is it on a cache/LLM/API hot path where field dropping causes user-visible issues?

For each finding: include BOTH file:line references (frontend AND backend).
```

### Agent 2: Data Integrity & Flow

```
Deep audit of {TARGET_DIR} for data pipeline integrity.

Tech stack: {STACK_INFO}

You are responsible for TWO merged dimensions: data flow breakpoints and declaration-execution integrity. Both are about "does what's declared actually work end-to-end?"

### Data Flow Tracing
Trace data from input to output through every transformation layer:

1. Input → extraction/validation → where do fields first get filtered?
   - Field resolvers that only pass declared fields (biggest silent-drop risk)
   - Schema validators that strip unknown fields

2. Extraction → context building → what gets injected vs what gets lost?
   - Are there TWO parallel injection mechanisms? (common in legacy+new system coexistence)
   - Fields injected by orchestrator but not declared in config → silently dropped by resolver

3. Context → builder/generator → does the builder get all the data it needs?
   - Search for context.get("field_name") calls in builders
   - Cross-reference with what's actually in the context at that point

4. Builder → serialization → what disappears during model_dump?
   - model_dump(exclude_none=True) drops None fields — is that always correct?
   - model_dump(by_alias=True) — are all aliases correct?

5. Serialization → cache → does the cache preserve everything?
   - Cache key completeness (includes code version? prompt version?)
   - Cache deserialization wrapped in try/except? Or crash on schema change?

### Declaration-Execution Integrity
1. Registered handlers/builders that don't have corresponding implementation
2. Enum values without config entries, config entries without code
3. Generation mode declarations (e.g., "deterministic" vs "llm") that contradict code behavior
4. Declared but never-called methods (persist/save/restore that no startup code invokes)

### Registry Coverage Alignment (critical — easy to miss)
This is the hardest class of bug to find: two dicts/maps/registries that SHOULD have the same key set but DON'T. The system works for the keys that overlap but silently does nothing for the missing ones.

Pattern to search for:
- Find all module-level dicts, frozensets, match/switch statements that use the same key type (e.g., section types, layout names, block types)
- Compare their key sets pairwise
- Flag any dict that has fewer keys than the "source of truth" dict

Examples of what this catches:
- SLOT_CAPACITIES has 24 layouts but LAYOUT_META only has 10 → 14 layouts get no budget info in prompts
- SectionType enum has 25 values but fieldConfig only has 20 → 5 sections get empty data from FieldResolver
- DETERMINISTIC_SECTION_BUILDERS has 18 entries but ROUTABLE_SECTION_BUILDERS has 14 → 4 sections can't route

For each registry-pair finding, the evidence field must include: registry A file:line + key count, registry B file:line + key count, the missing keys, and what happens when a key is in A but not B.

For each data-flow finding: evidence must include the full path (source file:line → transform file:line → destination file:line).
```

### Agent 3: Error Handling & Security

```
Deep audit of {TARGET_DIR} for exception handling and security issues.

Tech stack: {STACK_INFO}

### Silent Degradation (highest priority)
The most dangerous pattern: errors that produce WRONG output instead of failing. Search for:

1. except + fallback that produces user-visible wrong data:
   - except Exception → return default_value (where callers treat default as success)
   - except Exception → return placeholder/template content
   - warning + continue in loops (silently skips failed items)

2. Logging level mismatches:
   - logger.debug recording failures that affect user output → should be error
   - logger.warning + return default → if user sees the default, should be error
   - State machine violations logged as warning but still executed

3. Complete silence:
   - except Exception: pass
   - except Exception: continue
   - catch(e) {} (empty catch blocks)

### Security
1. Hardcoded secrets (api_key, secret, token, password as string literals)
2. Default credentials that work in production
3. SQL injection (string concatenation in queries)
4. Path traversal (user input in file paths)
5. Unsafe deserialization (pickle.loads, yaml.load not safe_load)
6. Sensitive data in logs
7. CORS misconfiguration (origins: ["*"] in production)

### Dependency Audit Classification (when Phase 0 output is provided)
Classify the attached dependency-audit tool output:
- critical = RCE-grade CVE with PoC on a reachable path
- high = known vulnerability on a reachable path
- medium = known vulnerability with unclear reachability
Mark dependency-audit findings as evidence_type = observed; the tool output is evidence.
```

### Agent 4: Architecture & Code Quality

```
Deep audit of {TARGET_DIR} for architectural issues and technical debt.

Tech stack: {STACK_INFO}

### Layer Violations & Circular Dependencies
1. Cross-context direct imports (context A importing context B's internals)
2. Bidirectional dependencies between modules
3. API routes containing business logic (should be in service layer)
4. Domain layer importing infrastructure

### God Objects
1. Files exceeding 800 lines — list each with line count
2. Classes with >15 methods
3. Functions >100 lines
4. Union types that keep growing (all-props-in-one-model pattern)

### Code Duplication & Drift
1. Parallel systems doing the same job (e.g., two data extraction pipelines)
2. Mapping tables (type → handler) maintained in 3+ places
3. Hardcoded values (colors, URLs, defaults) duplicated instead of centralized
4. Design tokens / constants defined in multiple tech stacks (Python + JSON + TypeScript)

### Extension Cost Analysis
Calculate: how many files must change to add a new [type/variant/feature]?
Report as ONE finding (category "extension-cost", severity medium) whose evidence lists the exact files for the most common extension operation.

### Registry Cross-Reference
Find all module-level dicts/maps that act as registries for the same key type. Compare their key sets. This catches "works for 10 items but silently skips 14" bugs — the hardest to find because no error is thrown.

### DI & Pattern Consistency
1. Multiple dependency injection patterns in use? (global state, factory, constructor mixed)
2. Inconsistent error handling patterns across modules
```

### Agent 5: Config & Persistence

```
Deep audit of {TARGET_DIR} for configuration and persistence issues.

Tech stack: {STACK_INFO}

### Config Completeness
1. Config entries used in code but missing from config files
2. Config entries in files but never read by code
3. Default values that are dangerous in production (localhost URLs, wildcard CORS, default secrets)
4. Environment variables used via os.getenv but not in Settings/config class
5. Conflicting defaults (same setting defined differently in two places)

### Template/Schema Config (if applicable)
1. Section/page/component types used in templates but missing from type enums
2. Field declarations in config that builders rely on — are all builder-used fields declared?
3. Generation mode / routing flags that contradict actual code behavior

### Cache Integrity
1. Cache key dimensions — does the key include everything that affects output?
   - Code/builder version? Prompt version? Template version?
2. Cache deserialization — wrapped in try/except for schema evolution?
3. Cache read/write symmetry — same serialization params on both sides?

### Database & Persistence
1. Schema migrations — are errors silently swallowed?
2. Job/task states — do they survive restarts?
3. Temp file cleanup — is there a finally block in error paths?
4. File paths — hardcoded relative paths that depend on cwd?
5. TTL cleanup — consistent semantics across all stores?
```

---

## Optional Dimensions (full mode, on request)

### Agent 6: Test Quality (`tests`)

```
Deep audit of {TARGET_DIR} for test quality and trustworthiness.

Tech stack: {STACK_INFO}

### Assertion Strength
1. Vacuous assertions: assert True, assertTrue(x is not None) as the ONLY check, expect(fn).not.toThrow() alone
2. Weakened assertions: exact match downgraded to containment, assertEqual → assertTrue
3. Tests that exercise code but assert nothing about the result

### Skips & Dead Tests
1. Skip markers (pytest.mark.skip/skipif, test.skip, #[ignore]) — is each reason still valid?
2. Tests that can never run (unreachable parametrize, always-false skipif)
3. Commented-out test bodies

### Coverage of Critical Paths
1. Error paths: are except/fallback branches tested, or only happy paths?
2. The modules with the most findings from other dimensions — do they have tests at all?
3. Test doubles that stub away the exact behavior under test (stub substitution)

### Test Infrastructure
1. conftest/setup that swallows failures or auto-retries
2. Snapshot tests auto-updated without review markers
```

### Agent 7: Concurrency (`concurrency`)

```
Deep audit of {TARGET_DIR} for concurrency and async correctness.

Tech stack: {STACK_INFO}

### Blocking in Async Contexts
1. time.sleep / requests / sync file IO / sync DB calls inside async def (Python)
2. Sync XHR or heavy sync loops on the main thread (JS)
3. std::thread::sleep or blocking IO inside async fn (Rust)

### Shared Mutable State
1. Module-level dicts/lists/counters mutated from multiple tasks/threads/goroutines without a lock
2. Check-then-act races (if key not in dict: dict[key] = ...)
3. Global singletons initialized lazily from concurrent paths

### Task/Resource Leaks
1. Fire-and-forget tasks (asyncio.create_task without reference/error handling, go func() without WaitGroup/errgroup)
2. Goroutines blocked forever on channels nobody reads
3. Unbounded queues or worker pools

### Cancellation & Timeouts
1. External calls (HTTP, DB, LLM) without timeouts
2. Cleanup paths that don't run on cancellation (missing finally/defer/Drop)
```

---

## Backend-Only Configuration (4 agents)

Use Agents 3, 4, 5 from the full-stack config. Replace Agent 1 with the merged prompt below
(it absorbs full-stack Agent 2's scope — do NOT also dispatch Agent 2, that duplicates the
data-flow/registry coverage and produces conflicting findings).

### Agent 1: API Contract & Data Integrity

```
Deep audit of {TARGET_DIR} for API contract and data integrity.

Tech stack: {STACK_INFO}

Combines: API schema consistency, serialization boundaries, data flow tracing, declaration-execution gaps.

### API Contract & Serialization
1. API response models vs internal domain models — field mismatches?
2. Serialization models (Pydantic/serde/Zod) — do they silently drop unknown fields?
   (Pydantic extra="ignore", serde's default ignore-unknown, Zod's DEFAULT strip mode —
   note Zod .strict() THROWS on unknown keys, it does not drop)
3. Is the model on a cache/LLM/API hot path where field dropping causes user-visible issues?

### Data Flow Tracing
Trace data from input to output through every transformation layer:
1. Input → extraction/validation — where do fields first get filtered?
   Field resolvers that only pass declared fields; schema validators that strip unknown fields.
2. Extraction → context building — what gets injected vs what gets lost?
   Two parallel injection mechanisms? Fields injected by orchestrator but not declared in config?
3. Context → builder/generator — does the builder get all the data it needs?
   Cross-reference context.get("field") calls against what's actually in the context.
4. Builder → serialization — what disappears during model_dump?
   exclude_none=True dropping fields; by_alias=True with wrong aliases.
5. Serialization → cache — cache key completeness (code/prompt version?), deserialization
   wrapped in try/except or crash on schema change?

### Declaration-Execution Integrity
1. Registered handlers/builders without corresponding implementation
2. Enum values without config entries, config entries without code
3. Declared but never-called methods (persist/save/restore that no startup code invokes)

### Registry Coverage Alignment (critical — easy to miss)
Find all module-level dicts/maps/registries keyed by the same type; compare key sets pairwise;
flag any registry with fewer keys than the source-of-truth registry.
For each registry-pair finding, evidence must include: registry A file:line + key count,
registry B file:line + key count, the missing keys, and what happens for a key in A but not B.

For each data-flow finding: evidence must include the full path
(source file:line → transform file:line → destination file:line).
```

---

## Frontend-Only Configuration (3 agents)

### Agent 1: Component Architecture & Rendering

```
Deep audit of {TARGET_DIR} for component architecture.

Tech stack: {STACK_INFO}

1. Type routing completeness — all possible types have renderers?
2. Component registration — dead components, missing registrations?
3. Props consumed but never provided? Props provided but never consumed?
4. State management — inconsistent patterns, prop drilling, stale state?
5. API consumption — error handling for API calls, loading states, empty states?
```

### Agent 2: Error Handling & Code Quality

```
Deep audit of {TARGET_DIR} for error handling and code quality.

Tech stack: {STACK_INFO}

1. Unhandled promise rejections, empty catch blocks
2. Error boundaries coverage
3. God components (>300 lines), code duplication
4. Accessibility issues
5. Dependency audit classification when Phase 0 `npm audit` output is provided:
   critical = RCE-grade CVE on a reachable path; high = known vulnerability on a reachable path; medium = reachability unclear.
```

### Agent 3: Config & Build

```
Deep audit of {TARGET_DIR} for build and configuration issues.

Tech stack: {STACK_INFO}

1. Build config consistency, dead dependencies
2. Environment variable management
3. Bundle size issues (large imports, tree-shaking failures)
```

---

## Quick Mode Configuration (2 agents)

- **Agent Q1: Silent Degradation & Security** — use full-stack Agent 3 verbatim.
- **Agent Q2: Data Integrity & Registry** — use full-stack Agent 2, keeping only the "Data Flow Tracing" (steps 1, 4, 5) and "Registry Coverage Alignment" sections.

Quick mode skips the verify pass; label every finding `unverified` in the report.

---

## Fallback Agent Types (Agent tool path only)

Agent type availability is ENVIRONMENT-SPECIFIC: check the subagent registry visible in the
current session before launching, and only use type names that actually appear there. Never
invent aliases (there is no generic `reviewer` type). If no specialized type matches, use
`general-purpose` (or the environment's default catch-all agent) for every dimension — the
prompts are self-contained and do not rely on a specialized agent's system prompt.

Example mapping when the common Claude Code review agents are installed:

| Dimension | subagent_type |
|-----------|---------------|
| Frontend-Backend Contract / Component Architecture | `general-purpose` |
| Data Integrity & Flow / API Contract | `code-reviewer` |
| Error Handling & Security | `security-reviewer` |
| Architecture & Code Quality | `architect` |
| Config & Persistence | `database-reviewer` |
| Test Quality / Concurrency / Config & Build | `code-reviewer` |

Note: several of these agent types carry Write/Edit/Bash tools — the READ-ONLY preamble is what prevents modification. Never omit it.
