# comprehensive-testing Extended Reference

This file preserves detailed material moved out of `SKILL.md` for progressive disclosure. Load it only when the current task needs the specific examples, commands, templates, or checklists below.

Moved content starts at: `## Boundary Testing`.

## Boundary Testing

### Test These Boundaries

```typescript
describe('boundary testing', () => {
  // Null/Undefined
  it('handles null input', () => {
    expect(() => process(null)).toThrow('Input required');
  });

  // Empty values
  it('handles empty string', () => {
    expect(validate('')).toBe(false);
  });

  it('handles empty array', () => {
    expect(sum([])).toBe(0);
  });

  // Zero values
  it('handles zero', () => {
    expect(divide(0, 5)).toBe(0);
  });

  it('handles divide by zero', () => {
    expect(() => divide(5, 0)).toThrow('Division by zero');
  });

  // Boundary values
  it('handles minimum value', () => {
    expect(clamp(Number.MIN_SAFE_INTEGER, 0, 100)).toBe(0);
  });

  it('handles maximum value', () => {
    expect(clamp(Number.MAX_SAFE_INTEGER, 0, 100)).toBe(100);
  });

  // Off-by-one
  it('includes boundary', () => {
    expect(isInRange(10, 0, 10)).toBe(true);  // inclusive
  });

  it('excludes just outside boundary', () => {
    expect(isInRange(11, 0, 10)).toBe(false);
  });

  // Type coercion
  it('handles string numbers', () => {
    expect(parsePositiveInt('42')).toBe(42);
    expect(() => parsePositiveInt('abc')).toThrow();
  });

  // Unicode/Special chars
  it('handles unicode', () => {
    expect(normalize('héllo')).toBe('hello');
  });

  it('handles emoji', () => {
    expect(charCount('👨‍👩‍👧‍👦')).toBe(1); // grapheme cluster
  });
});
```

### Error Scenario Checklist

```markdown
- [ ] Network failure
- [ ] Timeout
- [ ] Invalid input format
- [ ] Missing required fields
- [ ] Unauthorized access
- [ ] Resource not found
- [ ] Concurrent modification
- [ ] Disk full
- [ ] Out of memory
- [ ] Rate limit exceeded
```

---

## Property-Based Testing

### Concept

Instead of specific examples, define **properties that must hold for all inputs**.

```typescript
import fc from 'fast-check';

// Property: reversing twice returns original
test('reverse is involutory', () => {
  fc.assert(
    fc.property(fc.array(fc.integer()), (arr) => {
      const reversed = reverse(reverse(arr));
      return deepEquals(arr, reversed);
    })
  );
});

// Property: sorted array is always ordered
test('sort produces ordered output', () => {
  fc.assert(
    fc.property(fc.array(fc.integer()), (arr) => {
      const sorted = sort(arr);
      for (let i = 1; i < sorted.length; i++) {
        if (sorted[i] < sorted[i - 1]) return false;
      }
      return true;
    })
  );
});

// Property: encoding then decoding returns original
test('JSON roundtrip', () => {
  fc.assert(
    fc.property(fc.jsonValue(), (value) => {
      const encoded = JSON.stringify(value);
      const decoded = JSON.parse(encoded);
      return deepEquals(value, decoded);
    })
  );
});
```

```python
from hypothesis import given, strategies as st

@given(st.lists(st.integers()))
def test_sort_is_idempotent(xs):
    """Sorting twice gives same result as sorting once"""
    assert sorted(sorted(xs)) == sorted(xs)

@given(st.text())
def test_encode_decode_roundtrip(s):
    """Base64 encoding/decoding preserves data"""
    encoded = base64.b64encode(s.encode())
    decoded = base64.b64decode(encoded).decode()
    assert decoded == s
```

---

## Async Testing

### Patterns

```typescript
// Wait for promise
it('resolves with data', async () => {
  const result = await fetchData();
  expect(result).toBeDefined();
});

// Wait for rejection
it('rejects with error', async () => {
  await expect(failingOperation()).rejects.toThrow('Error message');
});

// Timeout handling
it('times out after 5s', async () => {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);

  try {
    await fetch(url, { signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
}, 10000);

// Polling/Retry
it('eventually succeeds', async () => {
  await waitFor(async () => {
    const status = await getStatus();
    expect(status).toBe('ready');
  }, { timeout: 5000, interval: 100 });
});

// ❌ NEVER use fixed sleep
it('bad: uses sleep', async () => {
  await doSomething();
  await sleep(1000);  // NEVER DO THIS
  expect(result).toBe(expected);
});

// ✅ Use proper waiting
it('good: polls for condition', async () => {
  await doSomething();
  await waitFor(() => expect(getResult()).toBe(expected));
});
```

---

## Test Data Management

### Fixtures

```typescript
// Shared test data
const fixtures = {
  validUser: {
    id: 'user-1',
    email: 'test@example.com',
    name: 'Test User',
  },
  adminUser: {
    id: 'admin-1',
    email: 'admin@example.com',
    name: 'Admin User',
    role: 'admin',
  },
};
```

### Factories

```typescript
// Factory function
function createUser(overrides: Partial<User> = {}): User {
  return {
    id: `user-${Math.random().toString(36).slice(2)}`,
    email: 'test@example.com',
    name: 'Test User',
    createdAt: new Date(),
    ...overrides,
  };
}

// Usage
const user = createUser({ email: 'custom@example.com' });
```

### Builders

```typescript
class UserBuilder {
  private user: Partial<User> = {};

  withEmail(email: string): this {
    this.user.email = email;
    return this;
  }

  withRole(role: Role): this {
    this.user.role = role;
    return this;
  }

  asAdmin(): this {
    return this.withRole('admin');
  }

  build(): User {
    return {
      id: this.user.id ?? generateId(),
      email: this.user.email ?? 'test@example.com',
      name: this.user.name ?? 'Test User',
      role: this.user.role ?? 'user',
      createdAt: new Date(),
    };
  }
}

// Usage
const admin = new UserBuilder().withEmail('admin@test.com').asAdmin().build();
```

---

## Coverage Strategy

### Targets

| Metric | Minimum | Target | Critical Path |
|--------|---------|--------|---------------|
| Line | 70% | 80% | 100% |
| Branch | 60% | 70% | 100% |
| Function | 70% | 80% | 100% |

### What to Cover First

```markdown
1. Business-critical logic
2. Complex algorithms
3. Error handling paths
4. Edge cases
5. Integration points
```

### What NOT to Cover

```markdown
- Third-party library code
- Generated code
- Configuration files
- Type definitions only
- Trivial getters/setters
```

---

## CI Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci

      - name: Run tests
        run: npm test -- --coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage/lcov.info
          fail_ci_if_error: true

      - name: Check coverage thresholds
        run: |
          npm test -- --coverage --coverageThreshold='{
            "global": {
              "lines": 80,
              "branches": 70
            }
          }'
```

---

## Anti-Patterns to Avoid

```markdown
❌ Testing implementation, not behavior
   - Don't verify internal method calls
   - Test observable outputs only

❌ Over-mocking
   - Mocking everything tests nothing
   - Prefer real implementations or test doubles

❌ Test interdependence
   - Tests must run in any order
   - Each test must be isolated

❌ Hardcoded time
   - Use clock mocking
   - Inject time source

❌ Sleep/delay in tests
   - Use polling or async/await
   - Condition-based waiting

❌ Ignoring flaky tests
   - Fix or delete, never skip
   - Flaky tests erode trust

❌ Too much test setup
   - Indicates code design issues
   - Refactor code, not just tests

❌ Testing private methods
   - Test through public interface
   - If hard to test, refactor
```

---

## Testing Checklist

```markdown
## Before Writing Tests
- [ ] Understood requirements
- [ ] Identified test cases
- [ ] Determined test type (unit/integration/E2E)
- [ ] Planned test data

## Writing Tests
- [ ] Follows AAA or Given-When-Then
- [ ] Descriptive test names
- [ ] One assertion per concept
- [ ] Tests behavior, not implementation
- [ ] Covers happy path
- [ ] Covers error cases
- [ ] Covers boundary conditions

## Test Quality
- [ ] Tests are deterministic
- [ ] Tests are isolated
- [ ] Tests are fast
- [ ] No hardcoded values that will break
- [ ] Proper mocking (not over-mocking)

## Coverage
- [ ] Line coverage ≥ 80%
- [ ] Branch coverage ≥ 70%
- [ ] Critical paths at 100%

## CI/CD
- [ ] Tests run on every push
- [ ] Coverage reported
- [ ] Thresholds enforced
```

---

## Key Principles

1. **Tests are documentation** — They describe expected behavior
2. **Fast feedback** — Tests should run in seconds
3. **Deterministic** — Same input, same result, every time
4. **Independent** — No test depends on another
5. **Focused** — One test, one concept
6. **Maintainable** — Test code is production code

---

## Sources

- [Anthropic Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [TDD with Claude Code](https://thenewstack.io/claude-code-and-the-art-of-test-driven-development/)
- [Property-Based Fuzzing](https://www.mayhem.security/blog/property-based-fuzzing)
- [wshobson/agents Testing Patterns](https://github.com/wshobson/agents)
