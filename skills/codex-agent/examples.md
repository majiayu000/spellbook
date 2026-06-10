# Examples

Practical examples of Claude-Codex collaboration patterns.

## Code Analysis & Review

### Analyze Code Structure

```bash
codex exec -C /project -s read-only \
  "Analyze the architecture of src/services/ directory. Identify patterns, dependencies, and potential improvements."
```

### Security Review

```bash
codex exec -C /project -s read-only --json \
  "Review src/api/ for OWASP Top 10 vulnerabilities. Focus on injection, auth, and data exposure." \
  | jq -r '.content.text // .message'
```

### Performance Analysis

```bash
codex exec -C /project -s read-only \
  "Identify performance bottlenecks in src/database/queries.ts. Check for N+1 queries and missing indexes."
```

## Cross-Verification

### Verify Implementation

Claude implements a feature, then:

```bash
codex exec -C /project -s read-only \
  "Review the implementation in src/auth/oauth.ts. Verify correctness, check edge cases, and suggest improvements."
```

### Compare Approaches

```bash
REPORT="$(mktemp -t codex-approach.XXXXXX.md)"
codex exec -C /project -s read-only -o "$REPORT" \
  "Propose an alternative implementation for the caching logic in src/cache/manager.ts"
cat "$REPORT"
```

## Implementation Tasks

### Implement Feature (with review)

```bash
codex exec -C /project -s workspace-write \
  "Add rate limiting middleware to src/api/middleware/. Use sliding window algorithm, 100 req/min per IP."
```

### Fix Bug

```bash
codex exec -C /project -s workspace-write \
  "Fix the race condition in src/queue/worker.ts line 45-60. Ensure thread-safe access to shared state."
```

### Refactor Code

```bash
codex exec -C /project -s workspace-write \
  "Refactor src/utils/helpers.ts: split into separate modules, add TypeScript types, improve naming."
```

## Multi-Turn Sessions

### Start a Session

```bash
# First interaction - note the session ID in response
codex exec -C /project --json \
  "Analyze the test coverage in tests/. What areas need more testing?" \
  | tee "$(mktemp -t codex-session.XXXXXX.json)" | jq -r '.session // empty'
```

### Continue Session

```bash
# Use session ID from previous response
codex exec resume <session_id> \
  "Generate test cases for the auth module you identified"
```

### Resume Last Session

```bash
codex exec resume --last "What was the priority order again?"
```

## Output Handling

### Save to File

```bash
REPORT="$(mktemp -t codex-analysis.XXXXXX.md)"
codex exec -C /project -o "$REPORT" \
  "Document the API endpoints in src/api/routes/"

cat "$REPORT"
```

### JSON Processing

```bash
# Extract just the message content
codex exec -C /project --json "Explain main.ts" \
  | jq -s 'map(select(.type == "turn.completed")) | .[0].content'
```

### Stream Events

```bash
# Watch events in real-time
codex exec -C /project --json "Implement logging" \
  | while read -r line; do
      echo "$line" | jq -r '.type // "event"'
    done
```

## Integration Patterns

### Claude + Codex Code Review Pipeline

1. Claude writes code
2. Run Codex review:
```bash
REPORT="$(mktemp -t codex-review.XXXXXX.md)"
codex exec -C /project -s read-only -o "$REPORT" \
  "Review the uncommitted changes. Check for bugs, security issues, and code style."
cat "$REPORT"
```
3. Primary agent reads review and addresses issues

### Parallel Analysis

Run multiple Codex analyses in background:

```bash
SECURITY_REPORT="$(mktemp -t codex-security.XXXXXX.md)"
PERF_REPORT="$(mktemp -t codex-perf.XXXXXX.md)"

codex exec -C /project -s read-only -o "$SECURITY_REPORT" \
  "Security audit of src/" &

codex exec -C /project -s read-only -o "$PERF_REPORT" \
  "Performance analysis of src/" &

wait
cat "$SECURITY_REPORT" "$PERF_REPORT"
```

### Structured Output

```bash
codex exec -C /project --json --output-schema /path/to/schema.json \
  "List all TODO comments in the codebase with file, line, and content"
```

## Debugging Collaboration

### Analyze Test Failures

```bash
codex exec -C /project -s read-only \
  "Tests in tests/auth.test.ts are failing. Analyze the test setup, mocks, and async handling."
```

### Debug Runtime Error

```bash
codex exec -C /project -s read-only \
  "Getting 'undefined is not a function' at src/app.ts:123. Trace the call stack and identify root cause."
```

### Memory Leak Investigation

```bash
codex exec -C /project -s read-only \
  "Investigate potential memory leaks in src/cache/. Check for event listener cleanup and cache eviction."
```
