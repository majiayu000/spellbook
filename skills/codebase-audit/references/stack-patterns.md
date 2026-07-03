# Stack-Specific Search Patterns

Quick reference for each agent to adapt its searches based on the detected tech stack.

## Python + Pydantic + FastAPI

| Agent | Key Search Patterns |
|-------|-------------------|
| Type Consistency | `Field(alias=...)` values, `model_dump(by_alias=True)` output keys |
| Declaration-Execution | `@app.get/post`, dependency injection `Depends()`, `include_router()` |
| Data Flow | `model_validate()`, `model_dump(exclude_none=True)`, `extra="ignore"` |
| Serialization | `class X(BaseModel)`, check `model_config` for `extra` setting |
| Exception | `except Exception: pass`, `logger.debug` for errors, `logger.warning + return` |
| Cache | `hashlib`, cache key construction, `pickle.dumps/loads` |
| Config | `os.getenv()`, `.env` files, `Settings(BaseSettings)` |

## TypeScript + React

| Agent | Key Search Patterns |
|-------|-------------------|
| Type Consistency | `interface X`, `type X =`, compare with backend model fields |
| Declaration-Execution | Component registry, route definitions, `switch(type)` exhaustiveness |
| Rendering | `props?.fieldName`, component `switch/if-else` chains for type routing |
| Serialization | Zod schemas (`.strict()` vs `.passthrough()`), `as` type assertions |
| Exception | `catch(e) {}`, `.catch(() => {})`, unhandled promise rejections |

## Rust + serde + axum/actix

| Agent | Key Search Patterns |
|-------|-------------------|
| Type Consistency | `#[serde(rename=...)]`, `#[serde(rename_all=...)]` |
| Declaration-Execution | `impl Trait for X`, `Router::new().route()`, `mod` declarations |
| Data Flow | `#[serde(skip_serializing_if)]`, `#[serde(default)]` |
| Serialization | `#[serde(deny_unknown_fields)]` absence, `serde_json::from_str` |
| Exception | `let _ = expr`, `unwrap()`, `.ok()` discarding errors |
| God Objects | `impl X { }` with >15 methods, files >800 lines |

## Go + gin/echo

| Agent | Key Search Patterns |
|-------|-------------------|
| Type Consistency | `json:"field_name"` struct tags, compare with frontend types |
| Declaration-Execution | `r.GET/POST()` route registrations, interface implementations |
| Data Flow | `json.Marshal/Unmarshal`, `omitempty` tags, struct embedding |
| Serialization | Missing `json` tags (Go exports uppercase but JSON uses lowercase) |
| Exception | `if err != nil { return }` without logging, `_ = expr` |

## Full-Stack Projects

When both frontend and backend are detected (dimension names per SKILL.md Phase 1):
- **Frontend-Backend Contract** becomes the most critical dimension — compare BOTH sides, including the rendering pipeline (backend-producible types vs frontend renderers)
- **Data Integrity & Flow** should trace data across the API boundary, not stop at the serialization edge
- **Architecture & Code Quality** should specifically check cross-stack duplication (same constants, enums, validation rules defined in both stacks)
