---
name: rust-best-practices
description: Use when writing, modifying, or reviewing Rust code. ALWAYS invoke before Rust edits; covers Microsoft Pragmatic Rust guidance for error handling, API design, performance, and idiomatic patterns.
---
# Rust Best Practices

Based on Microsoft Pragmatic Rust Guidelines and Rust community standards.

## Core Principles

1. **Leverage the type system** — Use types to make invalid states unrepresentable
2. **Embrace ownership** — Work with the borrow checker, not against it
3. **Explicit over implicit** — Be clear about fallibility, mutability, and lifetimes
4. **Zero-cost abstractions** — Use iterators, generics, and traits without runtime cost
5. **Fail fast, recover gracefully** — Validate early, handle errors explicitly

---

## Error Handling

### Use `thiserror` for Libraries
```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum MyError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Parse error at line {line}: {message}")]
    Parse { line: usize, message: String },
    #[error("Not found: {0}")]
    NotFound(String),
}
```

### Use `anyhow` for Applications
```rust
use anyhow::{Context, Result};

fn main() -> Result<()> {
    let config = load_config()
        .context("Failed to load configuration")?;
    run_app(config)?;
    Ok(())
}
```

### Never Panic in Libraries
```rust
// ❌ BAD
pub fn get_item(index: usize) -> &Item {
    &self.items[index]  // Panics on out-of-bounds
}

// ✅ GOOD
pub fn get_item(&self, index: usize) -> Option<&Item> {
    self.items.get(index)
}

// ✅ GOOD - when you need Result
pub fn get_item(&self, index: usize) -> Result<&Item, Error> {
    self.items.get(index).ok_or(Error::NotFound(index))
}
```

---

## API Design

### Use Builder Pattern for Complex Configs
```rust
pub struct Client {
    url: String,
    timeout: Duration,
    retries: u32,
}

impl Client {
    pub fn builder(url: impl Into<String>) -> ClientBuilder {
        ClientBuilder {
            url: url.into(),
            timeout: Duration::from_secs(30),
            retries: 3,
        }
    }
}

pub struct ClientBuilder {
    url: String,
    timeout: Duration,
    retries: u32,
}

impl ClientBuilder {
    pub fn timeout(mut self, timeout: Duration) -> Self {
        self.timeout = timeout;
        self
    }

    pub fn retries(mut self, retries: u32) -> Self {
        self.retries = retries;
        self
    }

    pub fn build(self) -> Client {
        Client {
            url: self.url,
            timeout: self.timeout,
            retries: self.retries,
        }
    }
}
```

### Use Newtype Pattern
```rust
// ❌ BAD - primitive obsession
fn create_user(name: String, email: String, age: u32) -> User { ... }

// ✅ GOOD - newtype wrappers
pub struct Username(String);
pub struct Email(String);
pub struct Age(u32);

impl Email {
    pub fn new(email: impl Into<String>) -> Result<Self, ValidationError> {
        let email = email.into();
        if email.contains('@') {
            Ok(Self(email))
        } else {
            Err(ValidationError::InvalidEmail)
        }
    }
}

fn create_user(name: Username, email: Email, age: Age) -> User { ... }
```

### Accept `impl Trait` for Flexibility
```rust
// ❌ BAD - overly specific
pub fn process(items: Vec<String>) { ... }

// ✅ GOOD - accept any iterable
pub fn process(items: impl IntoIterator<Item = impl AsRef<str>>) {
    for item in items {
        println!("{}", item.as_ref());
    }
}
```

---

## References

- [Microsoft Pragmatic Rust Guidelines](https://microsoft.github.io/rust-guidelines/)
- [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/)
- [The Rust Book](https://doc.rust-lang.org/book/)
- [references/advanced.md](references/advanced.md) — performance, async, testing, and anti-pattern examples
