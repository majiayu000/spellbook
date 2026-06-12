# Agent Prompt Templates

**Model policy: see SKILL.md Core Principles #1** (highest-tier model for every audit agent).

Replace `{TARGET_DIR}` and `{STACK_INFO}` based on detected stack. Adapt technology-specific sections accordingly. Every template MUST be sent self-contained — sub-agents cannot see SKILL.md or this file's other sections, so always append the Unified Output Contract below to every prompt.

---

## Unified Output Contract (append to EVERY agent prompt)

```
Every agent MUST end its report with findings in this exact Markdown table, one row per finding:

| severity | title | files | evidence | evidence_type | confidence | impact | fix |
|---|---|---|---|---|---|---|---|

- severity: Critical / High / Medium / Low — use this rubric:
  - Critical: data loss, rendering failure, security vulnerability, complete feature breakage affecting users NOW
  - High: silent degradation (user sees wrong/incomplete output), type mismatch causing truncation, missing config causing empty output, architectural violations blocking development
  - Medium: code duplication, inconsistent patterns, suboptimal error handling, tech debt that slows development
  - Low: informational / style-level findings
- files: every involved `path:line`, comma-separated (this is the dedup key — mandatory)
- evidence: code snippet ≤3 lines
- Table cells must stay parseable: replace newlines inside cells with `<br>` and escape literal pipe characters as `\|` in every cell, especially `evidence`.
- evidence_type: `observed` (directly visible in code) / `inferred` (cross-file reasoning)
- confidence: high / medium / low (inference chains >2 steps MUST be ≤ medium)
- Max 25 findings. If zero findings, write `NO_FINDINGS` and list the patterns you searched.
- Write all finding descriptions in Chinese; keep code identifiers, paths, and error messages as-is.
- No prose summaries outside the table.
```

---

## Full-Stack Configuration (5 agents)

### Agent 1: Frontend-Backend Contract (senior-code-reviewer)

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
1. Does it silently drop unknown fields? (Pydantic extra="ignore", serde default, Zod strict)
2. Is it on a cache/LLM/API hot path where field dropping causes user-visible issues?

For every finding, `files` must include BOTH sides (frontend AND backend path:line).

[Unified Output Contract]
```

### Agent 2: Data Integrity & Flow (senior-code-reviewer)

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
4. Registered but never-called methods (persist/save/restore that no startup code invokes)

### Registry Coverage Alignment (critical — easy to miss; you are the SOLE owner of this check)
This is the hardest class of bug to find: two dicts/maps/registries that SHOULD have the same key set but DON'T. The system works for the keys that overlap but silently does nothing for the missing ones.

Pattern to search for:
- Find all module-level dicts, frozensets, match/switch statements that use the same key type (e.g., section types, layout names, block types)
- Compare their key sets pairwise
- Flag any dict that has fewer keys than the "source of truth" dict

Examples of what this catches:
- SLOT_CAPACITIES has 24 layouts but LAYOUT_META only has 10 → 14 layouts get no budget info in prompts
- SectionType enum has 25 values but fieldConfig only has 20 → 5 sections get empty data from FieldResolver
- DETERMINISTIC_SECTION_BUILDERS has 18 entries but ROUTABLE_SECTION_BUILDERS has 14 → 4 sections can't route

For each pair of registries that share a key type, the finding must list:
- Registry A: file:line, N keys / Registry B: file:line, M keys
- Missing in B: [list of keys]
- Impact: what happens when a key is in A but not B

### Concurrency & Async Hygiene (only when Phase 0 detected an async runtime)
Only report statically provable items with file:line evidence. NO speculative performance guesses.
1. Lock guards held across .await (std::sync::Mutex/RwLock guard crossing an await point)
2. tokio::spawn with discarded JoinHandle / no panic propagation
3. unbounded_channel and unbounded queues on hot paths
4. Arc<Mutex<HashMap>> hot write contention
5. Go: goroutines with no exit path; concurrent map writes
6. Blocking calls inside async context: std::fs, reqwest::blocking, thread::sleep
7. Per-item DB/HTTP calls inside loops (N+1)
8. Grow-only caches/collections (insert with no eviction)

For data-flow findings, `files` must include the full path (source → transform → destination).

[Unified Output Contract]
```

### Agent 3: Error Handling & Security (security-auditor)

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
- Critical = RCE-grade CVE with PoC on a reachable path
- High = known vuln on a reachable path
- Medium = known vuln, reachability unclear
Mark these findings evidence_type = observed (tool output is evidence).

[Unified Output Contract]
```

### Agent 4: Architecture & Code Quality (code-archaeologist)

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
List the exact files for the most common extension operation.

Note: Registry key-set alignment is owned by the Data Integrity agent — do not re-check it.

### Test Quality
1. Business-logic modules with no matching test file / #[cfg(test)] block — list them
2. Weakened assertions: assertTrue wrapping, containment instead of exact match
3. Skip markers without justification: pytest.mark.skip, test.skip, #[ignore]
4. Test-stale: tests referencing signatures that no longer match the code under test

### DI & Pattern Consistency
1. Multiple dependency injection patterns in use? (global state, factory, constructor mixed)
2. Inconsistent error handling patterns across modules

If useful, include an "Extension Cost" table before the final findings table. The report must still end with the Unified Output Contract findings table; do not place any extra table or prose after it.

[Unified Output Contract]
```

### Agent 5: Config & Persistence (code-archaeologist)

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

[Unified Output Contract]
```

---

## Backend-Only Configuration (4 agents)

Use Agent 3, 4, 5 from the full-stack config unchanged. Agent 1 below replaces both full-stack Agent 1 and Agent 2 — its content is fully inlined so the prompt works with zero external context:

### Agent 1: API Contract & Data Integrity (senior-code-reviewer)

```
Deep audit of {TARGET_DIR} for API contract and data integrity.

Tech stack: {STACK_INFO}

### API Contract
1. API response models vs internal domain models — field mismatches?
2. Serialization models (Pydantic/serde/Zod) — do they silently drop fields?
   (Pydantic extra="ignore", serde missing deny_unknown_fields, struct tags missing)
3. Enum/union values — all variants handled at every consumption site?

### Data Flow Tracing
Trace data from input to output through every transformation layer:
1. Input → extraction/validation — where do fields first get filtered?
   Field resolvers that only pass declared fields; schema validators that strip unknown fields.
2. Extraction → context building — fields injected by orchestrator but not declared in
   config get silently dropped by resolvers; watch for TWO parallel injection mechanisms.
3. Context → builder/generator — search for context.get("field_name") calls and
   cross-reference with what's actually in the context at that point.
4. Builder → serialization — model_dump(exclude_none=True) drops None fields;
   are all by_alias names correct?
5. Serialization → cache — cache key completeness (code version? prompt version?);
   cache deserialization wrapped in try/except or crashes on schema change?

### Declaration-Execution Integrity
1. Registered handlers/builders without corresponding implementation
2. Enum values without config entries, config entries without code
3. Generation mode declarations contradicting code behavior
4. Registered but never-called methods (persist/save/restore that no startup code invokes)

### Registry Coverage Alignment (you are the SOLE owner of this check)
Find all module-level dicts/maps/match statements sharing a key type; compare key sets
pairwise; flag any registry with fewer keys than the source-of-truth registry. For each
pair, list both file:line locations, the missing keys, and the runtime impact.

### Concurrency & Async Hygiene (only when Phase 0 detected an async runtime)
Only report statically provable items. NO speculative performance guesses.
1. Lock guards held across .await
2. tokio::spawn with discarded JoinHandle
3. unbounded channels/queues on hot paths
4. Go: goroutines with no exit path; concurrent map writes
5. Blocking calls inside async context (std::fs, reqwest::blocking, thread::sleep)
6. Per-item DB/HTTP calls inside loops (N+1)
7. Grow-only caches/collections

For data-flow findings, `files` must include the full path (source → transform → destination).

[Unified Output Contract]
```

---

## Frontend-Only Configuration (3 agents)

### Agent 1: Component Architecture & Rendering (senior-code-reviewer)

```
Deep audit of {TARGET_DIR} for component architecture and rendering integrity.

Tech stack: {STACK_INFO}

1. Type routing completeness — all possible types have renderers? What happens with
   unknown types: crash, blank, or graceful fallback?
2. Component registration — dead components, missing registrations?
   Check switch(type)/if-else routing chains for exhaustiveness.
3. Props consumed but never provided? Props provided but never consumed?
4. State management — inconsistent patterns, prop drilling, stale state?
5. API consumption — error handling for API calls, loading states, empty states?
6. Minimal accessibility pass: images without alt, form controls without labels,
   interactive elements unreachable by keyboard.

[Unified Output Contract]
```

### Agent 2: Error Handling & Code Quality (senior-code-reviewer)

```
Deep audit of {TARGET_DIR} for error handling and code quality.

Tech stack: {STACK_INFO}

1. Unhandled promise rejections — search: .then( without .catch, async functions
   without try/catch at call sites
2. Empty catch blocks — search: catch(e) {}, .catch(() => {}), catch (_)
3. Error boundaries — list route-level components without an ErrorBoundary wrapper
4. God components (>300 lines) — list each with line count
5. Code duplication — parallel components doing the same job
6. Test quality — components with logic but no test file; weakened assertions;
   test.skip without justification
7. Dependency audit classification (when Phase 0 npm audit output is provided):
   Critical = RCE-grade CVE on a reachable path; High = known vuln on a reachable path

[Unified Output Contract]
```

### Agent 3: Config & Build (code-archaeologist)

```
Deep audit of {TARGET_DIR} for build configuration and dependency hygiene.

Tech stack: {STACK_INFO}

1. Build config consistency — conflicting settings across tsconfig/vite/webpack configs
2. Dead dependencies — packages in package.json never imported
3. Environment variable management — env vars referenced in code but missing from
   .env.example; secrets committed in env files
4. Bundle size issues — large imports (full lodash/moment), tree-shaking failures,
   missing code splitting on routes

[Unified Output Contract]
```
