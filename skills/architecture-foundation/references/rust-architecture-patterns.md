# Rust Architecture Patterns

Use this reference when the target project is Rust or Rust-heavy. The point is
to borrow boundary principles from mature projects, not to copy their folder
names or internal complexity.

## Pattern Selection

| Project shape | Useful references | Primary state model | Boundary lesson |
| --- | --- | --- | --- |
| Native UI/editor runtime | WarpUI, GPUI/Zed | App-owned entities and handles | Keep app state, element lifecycle, platform, and renderer separate. |
| Declarative UI app | Iced | State plus typed message | Make update/view/subscription explicit and testable. |
| Multi-target UI | Dioxus | Virtual DOM plus signals/hooks | Renderer consumes mutation protocol, not business state. |
| App shell/webview desktop | Tauri, Wry, Slint | Core plus runtime plus adapters/plugins | Keep OS/webview/windowing outside core; govern capabilities. |
| Runtime/scheduler | Tokio, Bevy | Runtime drivers or world/resources | Model lifecycle, scheduling, blocking, and resources explicitly. |
| Middleware/service framework | Tower, Axum | Service instance or typed router state | Encode readiness, backpressure, and error-to-response contracts. |
| Developer tool/CLI | rust-analyzer, ripgrep, clap, Cargo | Snapshot DB, input facts, or streaming pipeline | Separate CLI/IO from reusable core and diagnostics. |
| Trait API and diagnostics | serde, tracing, thiserror, anyhow, miette | Protocol traits plus derive or reporting facade | Keep data protocols, observability producers, typed errors, and user-facing reports separate. |
| Protocol/network/security | hyper, reqwest, rustls, quinn, h3 | Protocol state machine plus runtime adapter or client facade | Keep deterministic protocol core, transport, security config, and product API apart. |
| Concurrency primitives | futures-rs, rayon, crossbeam, parking_lot | Async protocol, CPU pool, channels, or locks | Make scheduling ownership, cancellation, backpressure, fairness, and unsafe boundaries explicit. |
| Data/query/storage | Polars, Arrow-rs, SQLx, Diesel, SeaORM | Data model plus query model plus backend adapter | Separate data containers, plans/queries, drivers, schemas, and runtime errors. |

## UI And App Runtime Lessons

### WarpUI / GPUI style

Borrow:
- App/runtime owns long-lived entities or models.
- Views render ephemeral element trees.
- A presenter/runtime owns build, layout, event dispatch, scene construction,
  rendering, invalidation, focus, actions, text, accessibility, and telemetry.
- Platform and renderer are backends with explicit callbacks and resource
  lifetimes.
- Headless app contexts test lifecycle without a real OS window.

Do not copy:
- Custom GPU/native UI stacks unless the product needs editor-grade rendering,
  input, and performance.
- Central app ownership into a small CRUD app where state plus message is enough.

Sources:
- https://github.com/warpdotdev/warp/tree/master/crates/warpui_core
- https://github.com/warpdotdev/warp/tree/master/crates/warpui
- https://github.com/zed-industries/zed/blob/main/crates/gpui/README.md
- https://zed.dev/blog/gpui-ownership

### Iced style

Borrow:
- One application state, typed messages, `update`, `view`, and subscriptions.
- Runtime, widget core, renderer, and window shell remain separate.
- Tests can drive update/view or a headless simulator.

Do not copy:
- Giant message enums and one huge update function for domains that need
  independent long-lived entities.

Sources:
- https://github.com/iced-rs/iced
- https://docs.iced.rs/iced/trait.Program.html
- https://docs.iced.rs/iced/struct.Subscription.html

### Dioxus style

Borrow:
- Keep component model and renderer connected through a mutation protocol.
- Use SSR/headless/native-dom paths as validation surfaces.
- Make signal/read tracking visible enough to reason about invalidation.

Do not copy:
- Web/HTML assumptions into native-only or terminal-only products.
- Hydration/fullstack complexity unless product requirements need it.

Sources:
- https://dioxuslabs.com/learn/0.7/beyond/project_structure/
- https://dioxuslabs.com/learn/0.7/guides/depth/custom_renderer/
- https://github.com/DioxusLabs/dioxus/blob/main/packages/core/src/virtual_dom.rs

## App Shell And Platform Lessons

### Tauri / Wry / Winit

Borrow:
- Separate application core from runtime glue and concrete platform backend.
- Treat OS windows, webviews, trays, notifications, IPC, and permissions as
  runtime or plugin capabilities, not core business logic.
- Make config stage explicit: compile-time, startup-time, or runtime.

Do not copy:
- Macro/codegen/capability machinery for small shells unless the security and
  plugin model justify it.
- Direct event loop/window handles in business logic.

Sources:
- https://v2.tauri.app/concept/architecture/
- https://docs.rs/tauri-runtime-wry/latest/tauri_runtime_wry/
- https://docs.rs/winit/latest/winit/application/trait.ApplicationHandler.html
- https://github.com/tauri-apps/wry

### Slint style

Borrow:
- Compiler/runtime/backend/renderer separation.
- `Platform`, `WindowAdapter`, and `Renderer` traits as platform/rendering
  seams.
- Screenshot and interpreter drivers as first-class tests.

Do not copy:
- A DSL or compiler pipeline unless product requirements need design-time
  language tooling, embedded support, or multi-language bindings.

Sources:
- https://docs.slint.dev/latest/docs/slint/
- https://github.com/slint-ui/slint/tree/master/internal
- https://snapshots.slint.dev/master/docs/slint/guide/backends-and-renderers/backend_winit/

## Runtime, Scheduler, And Service Lessons

### Bevy style

Borrow:
- World/resource/system model when data-parallel ECS is a natural fit.
- Explicit schedules, startup/update stages, plugins, diagnostics, and single
  tick tests.

Do not copy:
- ECS service-locator patterns into ordinary apps.
- Frame-based scheduling into request/response systems without a real frame
  model.

Sources:
- https://bevy.org/learn/quick-start/getting-started/ecs/
- https://docs.rs/bevy/latest/bevy/ecs/resource/trait.Resource.html
- https://docs.rs/bevy/latest/bevy/app/prelude/trait.Plugin.html

### Tokio style

Borrow:
- Runtime owns scheduler, IO driver, timer driver, and blocking pool.
- Fairness and blocking rules are part of the architecture contract.
- Metrics and paused-time tests make runtime behavior observable.

Do not copy:
- Nested runtimes or long CPU work on async workers.
- An arbitrary replaceable scheduler trait when builder configuration is enough.

Sources:
- https://docs.rs/tokio/latest/tokio/runtime/index.html
- https://docs.rs/tokio/latest/tokio/runtime/struct.Builder.html
- https://tokio.rs/tokio/topics/testing

### Tower / Axum style

Borrow:
- Tiny `Service` boundary with readiness, call, response, error, and future.
- Layers wrap capabilities without protocol-specific core coupling.
- HTTP errors must become responses at the boundary.

Do not copy:
- `poll_ready` complexity unless backpressure is an actual requirement.
- HTTP response types inside pure domain logic.

Sources:
- https://docs.rs/tower/latest/tower/trait.Service.html
- https://docs.rs/axum/latest/axum/error_handling/index.html
- https://docs.rs/axum/latest/axum/extract/struct.State.html

## Developer Tool And CLI Lessons

### rust-analyzer style

Borrow:
- Syntax, semantic model, IDE facade, VFS, project model, and LSP binary are
  distinct layers.
- Input facts and immutable snapshots make long-running incremental analysis
  testable.
- Public facade crates should use client terminology, not internal compiler
  implementation types.

Do not copy:
- Salsa/VFS/cancellation machinery into one-shot CLIs.
- Internal crates as if they were public API boundaries.

Sources:
- https://rust-analyzer.github.io/book/contributing/architecture.html
- https://rust-lang.github.io/rust-analyzer/hir/index.html
- https://rust-lang.github.io/rust-analyzer/project_model/index.html

### ripgrep style

Borrow:
- CLI glue is thin; reusable work sits in matcher, searcher, printer, ignore,
  and facade crates.
- Streaming pipeline beats global state for one-shot file processing.
- Library errors stay typed; binary decides display and exit behavior.

Do not copy:
- Many crates before there is clear reuse, API stability, or side-effect
  isolation.
- Push/internal iteration if the target library needs a pull-based API.

Sources:
- https://github.com/BurntSushi/ripgrep
- https://github.com/BurntSushi/ripgrep/tree/master/crates
- https://github.com/BurntSushi/ripgrep/blob/master/crates/grep/README.md

### clap / Cargo style

Borrow:
- CLI schema, parse, error formatting, and business operation should be
  separate.
- Commands should parse flags, load config, call `ops` or core, then report.
- Integration tests should exercise the real binary when CLI behavior matters.

Do not copy:
- Heavy derive/codegen or historical global context without a product reason.
- Cargo's internal library shape as a stable public API template.

Sources:
- https://docs.rs/clap/latest/clap/trait.Parser.html
- https://docs.rs/clap/latest/clap/error/index.html
- https://doc.rust-lang.org/nightly/nightly-rustc/cargo/index.html

## Trait API, Derive, Diagnostics, And Observability

### serde style

Borrow:
- Put a small trait protocol between user data structures and external formats.
- Keep derive as an adoption layer; handwritten implementations must remain
  possible for precise control.
- Test protocol behavior through format-independent tokens or fake adapters.

Do not copy:
- Visitor/lifetime/attribute complexity for small internal DTO or config types.
- Format-specific behavior in the core trait layer.

Sources:
- https://docs.rs/serde/latest/
- https://docs.rs/serde/latest/src/serde/core/ser/mod.rs.html
- https://serde.rs/impl-deserialize.html
- https://docs.rs/serde_test/latest/serde_test/

### tracing style

Borrow:
- Libraries emit spans/events; applications install subscribers/layers.
- Keep instrumentation producers separate from formatting, filtering, storage,
  and export backends.
- Use scoped or fake subscribers in tests.

Do not copy:
- Global subscriber installation from a library.
- Dynamic filtering, callsite caching, and layer stacks unless cross-crate
  observability is a real product need.

Sources:
- https://github.com/tokio-rs/tracing
- https://docs.rs/tracing-core/latest/tracing_core/subscriber/trait.Subscriber.html
- https://docs.rs/tracing-subscriber/latest/tracing_subscriber/layer/trait.Layer.html
- https://docs.rs/tracing-attributes/latest/tracing_attributes/attr.instrument.html

### thiserror / anyhow / miette style

Borrow:
- Library boundaries expose typed errors or diagnostic-capable types.
- Application boundaries may aggregate with `anyhow::Error` or render reports
  with `miette::Report`.
- Derive is useful for `Display`, `source`, `From`, and diagnostic metadata,
  but the error taxonomy is still an architecture decision.

Do not copy:
- `anyhow::Error` as the default public library API.
- A giant catch-all error enum with `#[from]` on every dependency error.
- Fancy terminal diagnostics in background services or library internals.

Sources:
- https://docs.rs/thiserror/latest/thiserror/
- https://docs.rs/anyhow/latest/anyhow/
- https://docs.rs/miette/latest/miette/
- https://docs.rs/miette/latest/miette/trait.Diagnostic.html

### Configuration protocol style

Borrow:
- Separate source format, partial config layer, merge, final config,
  validation, and schema generation.
- Treat configuration diagnostics as first-class user-facing errors.

Do not copy:
- A full config framework for one small static config file.

Sources:
- https://docs.rs/schematic/latest/schematic/

## Protocol, Network, And Security Lessons

### hyper style

Borrow:
- Low-level protocol libraries should hide HTTP parser/state-machine internals
  behind connection, body, client/server, service, runtime, and upgrade APIs.
- Feature flags may select protocol sides and versions when dependencies are
  large or optional.

Do not copy:
- HTTP internal state machines into business logic.
- A low-level library facade when the product needs a high-level client.

Sources:
- https://docs.rs/hyper/latest/hyper/
- https://docs.rs/hyper/latest/hyper/client/conn/http1/
- https://docs.rs/hyper/latest/hyper/server/conn/http1/
- https://docs.rs/hyper/latest/hyper/rt/

### reqwest style

Borrow:
- A product-grade client facade can hide transport, TLS, redirect, cookie,
  proxy, compression, and platform-specific adapters behind `ClientBuilder`,
  `RequestBuilder`, and `Response`.
- Request construction should be distinct from transport execution.
- Error values should preserve relevant context while allowing sensitive data
  to be stripped.

Do not copy:
- Dozens of builder options into a small internal client.
- Transport internals in the user-facing client API.

Sources:
- https://docs.rs/reqwest/latest/reqwest/
- https://docs.rs/reqwest/latest/reqwest/struct.ClientBuilder.html
- https://docs.rs/reqwest/latest/reqwest/struct.RequestBuilder.html
- https://docs.rs/reqwest/latest/reqwest/struct.Error.html

### rustls style

Borrow:
- Security-critical configuration can use type-state builders when ordering
  and completeness matter.
- Dangerous or verification-bypassing APIs must be explicitly named and
  isolated.
- Protocol errors should be typed and non-exhaustive so new failure modes can
  be added without breaking users.

Do not copy:
- Dense TLS-style state machines and type-state config for ordinary business
  settings.
- Any API that silently disables verification or downgrades security.

Sources:
- https://docs.rs/rustls/latest/rustls/
- https://docs.rs/rustls/latest/rustls/struct.ConfigBuilder.html
- https://docs.rs/rustls/latest/rustls/enum.Error.html
- https://github.com/rustls/rustls/tree/main/rustls/tests

### quinn / h3 style

Borrow:
- Keep deterministic sans-IO protocol core separate from socket, runtime,
  timer, and task adapters.
- Split endpoint/global, connection, transport, crypto, and HTTP layer config.
- Expose protocol traits so higher layers can adapt to multiple transports.

Do not copy:
- Experimental 0.x protocol APIs as stable public API templates.
- QUIC token, congestion, MTU, and anti-replay machinery into ordinary
  request/response services.

Sources:
- https://docs.rs/quinn/latest/quinn/
- https://docs.rs/quinn-proto/latest/quinn_proto/
- https://docs.rs/h3/latest/h3/
- https://docs.rs/h3-quinn/latest/h3_quinn/

## Concurrency And Async Primitive Lessons

### futures-rs style

Borrow:
- Separate async protocol traits (`Future`, `Stream`, `Sink`) from executors,
  channels, IO adapters, test utilities, and macros.
- Backpressure, flush/close, termination, waker, abort, and drop behavior are
  protocol semantics, not implementation details.

Do not copy:
- A custom executor or poll/waker implementation unless the product owns the
  runtime problem.
- `Abortable` as a promise to cancel arbitrary OS or IO work.

Sources:
- https://github.com/rust-lang/futures-rs
- https://docs.rs/futures-core/latest/futures_core/
- https://docs.rs/futures-sink/latest/futures_sink/
- https://docs.rs/futures-test/latest/futures_test/

### rayon style

Borrow:
- User-facing parallel iterator APIs can sit above a concentrated scheduler
  core.
- Type-system and compile-fail tests should enforce `Send`, `Sync`, lifetime,
  and scoped-task invariants.
- Panic policy should be explicit at the spawn/scope boundary.

Do not copy:
- CPU work-stealing pools for IO-heavy or async workloads.
- A one-time global thread-pool model without documenting configuration limits.

Sources:
- https://docs.rs/rayon/latest/rayon/
- https://docs.rs/rayon-core/latest/rayon_core/
- https://github.com/rayon-rs/rayon/tree/main/rayon-core/src/compile_fail

### crossbeam / parking_lot style

Borrow:
- Concurrency primitives should be small, composable, and not pretend to own an
  application runtime.
- Unsafe memory reclamation, raw locks, park/unpark queues, scoped threads, and
  channel select behavior belong behind narrow APIs with explicit contracts.
- Fairness, blocking, retry, timeout, disconnect, poisoning, and wakeup policy
  must be documented as API behavior.

Do not copy:
- Lock-free epoch or raw-lock internals into business modules.
- Non-deterministic select/steal behavior without making it part of the
  contract and test strategy.

Sources:
- https://docs.rs/crossbeam/latest/crossbeam/
- https://docs.rs/crossbeam-channel/latest/crossbeam_channel/
- https://docs.rs/crossbeam-epoch/latest/crossbeam_epoch/
- https://docs.rs/parking_lot/latest/parking_lot/
- https://docs.rs/lock_api/latest/lock_api/

## Data, Query, And Storage Lessons

### Polars style

Borrow:
- Separate dataframe/series core, lazy logical plan, optimizer/execution, IO
  adapters, SQL adapter, and error taxonomy.
- Lazy execution needs a real intermediate representation and an explicit
  `collect` or execution boundary.

Do not copy:
- Huge feature matrices, unchecked constructors, and engine-scale complexity
  into ordinary data apps.

Sources:
- https://docs.pola.rs/
- https://github.com/pola-rs/polars/tree/main/crates
- https://docs.rs/polars/latest/polars/

### Arrow-rs style

Borrow:
- Low-level data foundations should separate arrays, schemas, buffers, compute,
  IPC, parquet, and top-level re-exports.
- Data invariants such as same-length arrays and schema/data alignment should
  be encoded in core types and integration tests.

Do not copy:
- `dyn Array` downcasting and unsafe data-layer complexity into business code.
- A data container layer as if it were a query engine.

Sources:
- https://docs.rs/arrow/latest/arrow/
- https://docs.rs/arrow/latest/arrow/array/trait.Array.html
- https://docs.rs/arrow/latest/arrow/array/struct.RecordBatch.html
- https://arrow.apache.org/rust/arrow_integration_testing/

### SQLx style

Borrow:
- Keep SQL text as a source of truth when the product team wants SQL-first
  control, then add compile-time or offline validation at the boundary.
- Separate facade, core database traits, driver crates, macros, CLI, and tests.
- Runtime errors still need typed public variants even when compile-time query
  checking exists.

Do not copy:
- Build-time database requirements or offline metadata unless CI and developer
  workflow can support them.
- Macro-only query APIs when dynamic query building is required.

Sources:
- https://docs.rs/sqlx/latest/sqlx/
- https://docs.rs/sqlx/latest/sqlx/trait.Database.html
- https://docs.rs/sqlx/latest/sqlx/trait.Executor.html
- https://docs.rs/sqlx/latest/sqlx/macro.query.html

### Diesel / SeaORM style

Borrow:
- Type-level query DSLs can make schema, backend support, selectable fields,
  and row mapping compile-time concerns.
- Service-layer ORMs can be useful adapters around SQLx/SeaQuery-style dynamic
  query construction when application productivity matters.
- Tests should match the boundary: compile diagnostics for type DSLs, real DB
  roundtrips for drivers, and mock query logs for ORMs.

Do not copy:
- Complex type errors, heavy derive ecosystems, native linking constraints, or
  ORM relation machinery unless the application explicitly needs them.

Sources:
- https://docs.diesel.rs/main/diesel/
- https://docs.diesel.rs/main/diesel/query_dsl/
- https://docs.diesel.rs/main/diesel/query_builder/trait.QueryFragment.html
- https://docs.rs/sea-orm/latest/sea_orm/

## Universal Rust Design Rules

1. Pick one state ownership model before naming modules.
2. Keep core free of IO, OS handles, renderer handles, provider clients, and
   environment reads.
3. Make lifecycle, scheduling, backpressure, cancellation, and shutdown visible.
4. Use small traits or typed protocols for extension points.
5. Convert errors only at explicit boundaries; do not warn and silently fall
   back for user-visible missing behavior.
6. Observability is part of architecture: metrics, logs, queue depth, frame
   telemetry, cache state, or diagnostics should be externally readable.
7. Tests must be able to step the system through core behavior without the
   full platform stack.
8. Split crates only when the boundary is stable, reusable, independently
   testable, or isolates expensive dependencies and side effects.
9. Define trait protocols before adding derive macros; macros are adoption
   tooling, not the architecture.
10. Keep observability producer APIs separate from subscribers/exporters, and
    keep diagnostics facts separate from report rendering.
11. For protocols and security-sensitive systems, separate deterministic core,
    runtime/socket adapters, configuration scope, and dangerous APIs.
12. For concurrency, state who owns scheduling and what cancellation, close,
    fairness, blocking, wakeup, and panic behavior mean.
13. For data systems, separate data containers, query/planning IR, IO/backend
    drivers, schema validation, and runtime errors.
