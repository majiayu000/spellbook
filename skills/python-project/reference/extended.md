# python-project Extended Reference

This file preserves detailed material moved out of `SKILL.md` for progressive disclosure. Load it only when the current task needs the specific examples, commands, templates, or checklists below.

Moved content starts at: `## Testing`.

## Testing

```python
# tests/conftest.py
import pytest
from httpx import ASGITransport, AsyncClient

from myapp.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# tests/test_user.py
import pytest


@pytest.mark.asyncio
async def test_create_user(client):
    response = await client.post(
        "/api/v1/users",
        json={"email": "test@example.com", "name": "Test User"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_get_user_not_found(client):
    response = await client.get("/api/v1/users/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
```

---

## Makefile

```makefile
.PHONY: dev test lint fmt check clean

# Run development server
dev:
	uv run uvicorn myapp.main:app --reload

# Run tests
test:
	uv run pytest

# Run tests with coverage
test-cov:
	uv run pytest --cov=myapp --cov-report=html

# Lint code
lint:
	uv run ruff check src tests

# Format code
fmt:
	uv run ruff format src tests
	uv run ruff check --fix src tests

# Type check
typecheck:
	uv run mypy src

# Run all checks
check: fmt lint typecheck test
	@echo "All checks passed!"

# Clean
clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +

# Sync dependencies
sync:
	uv sync

# Upgrade dependencies
upgrade:
	uv lock --upgrade
	uv sync
```

---

## Checklist

```markdown
## Project Setup
- [ ] uv initialized with pyproject.toml
- [ ] .python-version set (3.12+)
- [ ] src/ layout structure
- [ ] Ruff configured
- [ ] mypy strict mode

## Architecture
- [ ] Pydantic models for validation
- [ ] Services for business logic
- [ ] Repositories for data access
- [ ] Custom exceptions
- [ ] Dependency injection

## Quality
- [ ] pytest with pytest-asyncio
- [ ] Type hints everywhere
- [ ] Structured logging
- [ ] Error handling middleware

## CI
- [ ] ruff check
- [ ] ruff format --check
- [ ] mypy
- [ ] pytest
```

---

## See Also

- [reference/architecture.md](reference/architecture.md) — Project structure patterns
- [reference/tech-stack.md](reference/tech-stack.md) — Tool comparisons
- [reference/patterns.md](reference/patterns.md) — Python design patterns
