# rust-project Extended Reference

This file preserves detailed material moved out of `SKILL.md` for progressive disclosure. Load it only when the current task needs the specific examples, commands, templates, or checklists below.

Moved content starts at: `## Makefile`.

## Makefile

```makefile
.PHONY: build run test lint check clean

build:
	cargo build --release

run:
	cargo run

dev:
	cargo watch -x run

test:
	cargo test

test-coverage:
	cargo tarpaulin --out Html

lint:
	cargo clippy -- -D warnings

fmt:
	cargo fmt

check: fmt lint test
	@echo "All checks passed!"

clean:
	cargo clean

# Database (SeaORM)
db-migrate:
	sea-orm-cli migrate up

db-generate:
	sea-orm-cli generate entity -o src/models

db-fresh:
	sea-orm-cli migrate fresh
```

---

## Checklist

```markdown
## Project Setup
- [ ] Cargo.toml configured
- [ ] Workspace structure (if multi-crate)
- [ ] Edition 2024 / resolver = "3"

## Architecture
- [ ] main.rs: only wiring + startup
- [ ] lib.rs: re-exports + AppState
- [ ] error.rs: thiserror types
- [ ] handlers/ services/ models/ separation

## Quality
- [ ] tracing for logging
- [ ] clippy warnings as errors
- [ ] cargo fmt enforced
- [ ] Tests for critical paths

## CI
- [ ] cargo check
- [ ] cargo clippy
- [ ] cargo test
- [ ] cargo fmt --check
```

---

## See Also

- [reference/architecture.md](reference/architecture.md) — Workspace and module patterns
- [reference/tech-stack.md](reference/tech-stack.md) — Crate comparisons
- [reference/patterns.md](reference/patterns.md) — Builder, Newtype, Error patterns
