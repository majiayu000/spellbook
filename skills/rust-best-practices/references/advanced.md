# Advanced Rust Practices

Use this reference after the core error-handling and API-design guidance in
`../SKILL.md`. Keep the main skill compact; load this file when the task touches
performance, async runtime behavior, test strategy, or common Rust footguns.

## Performance

### Avoid Unnecessary Clones
```rust
// ❌ BAD
fn process(data: &String) {
    let owned = data.clone();  // Unnecessary allocation
    do_something(owned);
}

// ✅ GOOD
fn process(data: &str) {
    do_something(data);
}
```

### Use `Cow` for Conditional Ownership
```rust
use std::borrow::Cow;

fn normalize(input: &str) -> Cow<'_, str> {
    if input.contains(' ') {
        Cow::Owned(input.replace(' ', "_"))
    } else {
        Cow::Borrowed(input)
    }
}
```

### Prefer Iterators Over Loops
```rust
// ❌ BAD
let mut result = Vec::new();
for item in items {
    if item.is_valid() {
        result.push(item.transform());
    }
}

// ✅ GOOD
let result: Vec<_> = items
    .into_iter()
    .filter(|item| item.is_valid())
    .map(|item| item.transform())
    .collect();
```

## Async Patterns

### Use `tokio` Runtime
```rust
#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::init();
    run().await
}
```

### Structured Concurrency with `JoinSet`
```rust
use tokio::task::JoinSet;

async fn process_all(urls: Vec<String>) -> Vec<Result<Response, Error>> {
    let mut set = JoinSet::new();

    for url in urls {
        set.spawn(async move {
            fetch(&url).await
        });
    }

    let mut results = Vec::new();
    while let Some(res) = set.join_next().await {
        results.push(res.unwrap());
    }
    results
}
```

### Use `#[instrument]` for Tracing
```rust
use tracing::instrument;

#[instrument(skip(password))]
async fn login(username: &str, password: &str) -> Result<Token> {
    tracing::info!("Attempting login");
    // ...
}
```

## Testing

### Use `#[test]` and `proptest`
```rust
#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    #[test]
    fn test_basic() {
        assert_eq!(add(2, 2), 4);
    }

    proptest! {
        #[test]
        fn test_add_commutative(a: i32, b: i32) {
            prop_assert_eq!(add(a, b), add(b, a));
        }
    }
}
```

### Use `mockall` for Mocking
```rust
#[cfg_attr(test, mockall::automock)]
trait Database {
    async fn get(&self, id: u64) -> Result<Record>;
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_with_mock() {
        let mut mock = MockDatabase::new();
        mock.expect_get()
            .returning(|_| Ok(Record::default()));

        let service = Service::new(mock);
        assert!(service.process(1).await.is_ok());
    }
}
```

## Common Anti-Patterns to Avoid

| Anti-Pattern | Better Alternative |
|-------------|-------------------|
| `unwrap()` everywhere | `?` operator with proper error types |
| `clone()` to satisfy borrow checker | Restructure code, use references |
| `Box<dyn Error>` | Concrete error types with `thiserror` |
| `String` for all text | `&str`, `Cow<str>`, or domain types |
| Manual `Drop` for cleanup | RAII with struct destructors |
| `unsafe` without justification | Safe abstractions first |
| `Arc<Mutex<_>>` overuse | Message passing, channels |
| Blocking in async context | `spawn_blocking` for CPU work |
