# Stack-Specific Search Patterns

Quick reference for each agent to adapt its searches based on the detected tech stack. The "Agent" column uses the current dimension names from SKILL.md (Frontend-Backend Contract / Data Integrity & Flow / Error Handling & Security / Architecture & Code Quality / Config & Persistence).

## Python + Pydantic + FastAPI

| Agent | Key Search Patterns |
|-------|-------------------|
| Frontend-Backend Contract | `Field(alias=...)` values, `model_dump(by_alias=True)` output keys |
| Data Integrity & Flow | `model_validate()`, `model_dump(exclude_none=True)`, `extra="ignore"`, `@app.get/post`, `Depends()`, `include_router()` |
| Error Handling & Security | `except Exception: pass`, `logger.debug` for errors, `logger.warning + return` |
| Architecture & Code Quality | files >800 lines, classes >15 methods; tests: `pytest.mark.skip`, bare `assertTrue`, missing `test_*.py` for logic modules |
| Config & Persistence | `os.getenv()`, `.env` files, `Settings(BaseSettings)`, `hashlib` cache keys, `pickle.dumps/loads` |

## TypeScript + React

| Agent | Key Search Patterns |
|-------|-------------------|
| Frontend-Backend Contract | `interface X`, `type X =`, compare with backend model fields; Zod `.strict()` vs `.passthrough()`, `as` type assertions |
| Data Integrity & Flow | Component registry, route definitions, `switch(type)` exhaustiveness, `props?.fieldName` routing chains |
| Error Handling & Security | `catch(e) {}`, `.catch(() => {})`, unhandled promise rejections |
| Architecture & Code Quality | God components >300 lines; tests: `test.skip`/`it.skip`, `toBeTruthy()` wrapping, missing `*.test.tsx` |
| Config & Persistence | env vars not in `.env.example`, conflicting tsconfig/bundler settings |

## Rust + serde + axum/actix

| Agent | Key Search Patterns |
|-------|-------------------|
| Frontend-Backend Contract | `#[serde(rename=...)]`, `#[serde(rename_all=...)]` |
| Data Integrity & Flow | `#[serde(skip_serializing_if)]`, `#[serde(default)]`, `#[serde(deny_unknown_fields)]` absence, `serde_json::from_str`, `impl Trait for X`, `Router::new().route()`; concurrency: `std::sync::Mutex` guard across `.await`, `tokio::spawn(` with discarded handle, `unbounded_channel`, `reqwest::blocking`/`std::fs` in async fn |
| Error Handling & Security | `let _ = expr`, `unwrap()`, `.ok()` discarding errors |
| Architecture & Code Quality | `impl X { }` with >15 methods, files >800 lines; tests: `#[ignore]`, `assert!(true)`, modules without `#[cfg(test)]` |
| Config & Persistence | config structs never `load()`ed (only `Default::default()`), cache key construction |

## Go + gin/echo

| Agent | Key Search Patterns |
|-------|-------------------|
| Frontend-Backend Contract | `json:"field_name"` struct tags, compare with frontend types; missing `json` tags (Go exports uppercase but JSON uses lowercase) |
| Data Integrity & Flow | `json.Marshal/Unmarshal`, `omitempty` tags, struct embedding, `r.GET/POST()` route registrations, interface implementations; concurrency: `go func(` without exit path, concurrent map writes, channels without close |
| Error Handling & Security | `if err != nil { return }` without logging, `_ = expr` |
| Architecture & Code Quality | files >800 lines; tests: `t.Skip(` without reason, missing `_test.go` for logic packages |
| Config & Persistence | `os.Getenv` outside config package, hardcoded defaults |

## Full-Stack Projects

When both frontend and backend are detected:

- The **Frontend-Backend Contract agent** is the most critical — it must compare BOTH sides of every shared type and owns the full rendering-pipeline check.
- The **Data Integrity & Flow agent** should trace data across the API boundary, not stop at the serialization layer.
- The **Architecture & Code Quality agent** should specifically check for cross-stack duplication (same constants, enums, validation rules defined in both Python/Go and TypeScript).
