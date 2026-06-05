# Go Architecture Patterns

Use this reference when the target project is Go or Go-heavy. Go architecture
is usually less about frameworks and more about package boundaries, small
interfaces, explicit effects, context propagation, and tests that exercise the
public API.

## First Principles

1. Start simple. A small Go module does not need `cmd`, `internal`, `pkg`,
   clean architecture layers, or a repository interface.
2. Package names are API design. Client code reads `package.Name`, so names
   should be short, concrete, and not repetitive.
3. Prefer domain or capability packages over mechanical layers. A package
   should explain what it does, not just where it sits.
4. Interfaces usually belong to the consumer, not the producer. Accept small
   interfaces where needed and return concrete types.
5. Keep `context.Context` request-scoped: pass it as an argument, normally
   first, and do not store it on long-lived structs.
6. Goroutines need owners. Every spawned goroutine needs a cancellation,
   shutdown, error, or channel-close story.
7. Errors are values. Return typed or distinguishable errors only when callers
   can act on them; wrap at boundaries where extra context matters.
8. Use tests to protect package contracts. Prefer public API tests and fake
   adapters over large mock hierarchies.

## Pattern Selection

| Project shape | Useful model | Boundary lesson |
| --- | --- | --- |
| Tiny command or package | One module, one package, maybe one `main.go` | Do not scaffold before there is real complexity. |
| Multiple commands | `cmd/<name>` plus supporting packages | Command packages parse config/flags and call core logic. |
| Private app internals | `internal/<capability>` | Hide packages that are not supported public API. |
| Reusable library | Root package plus small subpackages | Design from client import and `pkg.Name` usage. |
| HTTP/RPC service | handlers, application use cases, adapters | HTTP types stop at transport boundary; domain stays transport-free. |
| API gateway or model router | transport, auth/accounting, routing policy, provider adapters | Provider quirks stay behind adapters; public request contracts stay stable. |
| Async workflow or billing service | command/outbox, worker, state table, projection, reconciler | Source of truth, idempotency, and reconciliation are explicit contracts. |
| Domain-heavy app | bounded contexts or feature packages | Organize by domain language, not generic `models/services/utils`. |
| Infrastructure adapters | DB, queue, email, external clients | Concrete adapter structs implement consumer-owned interfaces. |
| Concurrent workflow | context, errgroup, channels, worker pool | Ownership, cancellation, close, and backpressure are contracts. |

## Mature Go Reference Models

Use mature projects as pattern evidence, not directory templates. Always write
both `borrow` and `do_not_copy`.

### Small API Library: chi

Borrow:
- Keep the public API close to standard-library types when the standard
  contract is already good enough. `chi` centers on `net/http` handlers,
  middleware, and route composition.
- Keep internal state private and expose traversal/inspection APIs only when
  they are part of the supported contract.
- Enforce configuration-order invariants at the boundary.

Do not copy:
- `panic`-based configuration errors into operator-facing runtimes.
- Global mutable registries for broad plugin or provider capability systems.
- Router shape for background workers, billing, or workflow engines.

### Lifecycle Framework: fx

Borrow:
- Separate declaration from effects: constructors build dependencies; lifecycle
  hooks own goroutines, listeners, background loops, and shutdown.
- Make startup and shutdown ordered, timeout-bound, rollback-aware, and testable.
- Provide a test harness that can explicitly start and stop the runtime.

Do not copy:
- Reflection DI as a default architecture for normal Go services.
- Unordered value groups for ordered handler/plugin chains.
- Deprecated no-op compatibility APIs without a deletion plan.

### Event Cache Reconcile: client-go

Borrow:
- Use watch/list input, cache/projection, queue/backpressure, and reconciler
  workers as distinct boundaries.
- Keep event handlers cheap; they enqueue keys and do not run business work.
- Define cache consistency, notification order, retry, drain, and shutdown
  semantics.

Do not copy:
- Kubernetes-scale generated informer/lister machinery unless the domain has a
  comparable typed API surface.
- Controller complexity when there is no watch stream, projection cache, or
  reconcile need.

### API SDK Exporter: opentelemetry-go

Borrow:
- Separate public API contracts from SDK/runtime implementation and exporters.
- Put external protocol translation, retry, timeout, queue/drop/block behavior,
  and shutdown in exporters or processors.
- Keep host-application safety and API stability explicit.

Do not copy:
- Global delegating providers or global error handlers into business cores;
  those are observability ecosystem compatibility mechanisms.
- Provider implementation fields in public request schemas.

### Deterministic State Machine: etcd/raft

Borrow:
- Keep core transition logic pure when ordering, replay, idempotency, or
  convergence is the problem.
- Emit effect batches such as `Ready` and let the runtime shell own durable
  writes, network sends, apply, ticks, cancellation, and recovery.
- Specify effect order, especially durable-before-send rules.

Do not copy:
- Consensus-specific complexity such as terms, quorum, async storage writes, or
  panic-level invariants unless the product is actually a consensus system.
- State-machine shells for ordinary CRUD or simple request/response services.

### Config Module Platform: Caddy

Borrow:
- Name the canonical runtime config. Treat human config formats as adapters
  that produce canonical config.
- Give modules explicit IDs, host interfaces, provisioning, validation,
  cleanup, and context-owned lifecycle.
- For reloadable systems, provision new state before replacing old state, then
  clean up the old context.

Do not copy:
- Init-time global module registration, reflect-heavy loading, or Admin API
  hot config mutation into ordinary services by default.
- A module platform unless real extension or many same-lifecycle capabilities
  justify it.

### Operational Service Managers: Prometheus

Borrow:
- Use one composition root to validate config and wire subsystem managers.
- Give each manager explicit dependencies, `Run`, `Stop`, `ApplyConfig` when
  needed, metrics, and shutdown order.
- Make reload order explicit and keep config source-of-truth read-only to
  consumers.
- Distinguish primary storage from secondary or best-effort sinks.

Do not copy:
- A giant entrypoint unless it is truly only the composition root.
- Server/agent dual-mode complexity, broad feature flags, or migration
  interfaces unless the product has that scale and history.

## Module And Package Layout

Borrow:
- Use the official module-layout guidance first: basic package, basic command,
  supporting packages, multiple commands, and server projects scale differently.
- Use `cmd/<binary>` when a repo has multiple commands or a command plus
  reusable packages.
- Use `internal/` when a package must not become importable public API.
- Use `pkg/` only when the package is intentionally reusable by external code.
- Let package names and exported identifiers read naturally from the caller's
  point of view.

Do not copy:
- A "standard project layout" repo as if it were official or mandatory.
- Empty `models`, `types`, `utils`, `common`, `interfaces`, or `api` packages.
- Layer folders that force every feature through handler/service/repository
  even when the feature is small.

Sources:
- https://go.dev/doc/modules/layout
- https://go.dev/blog/package-names
- https://go.dev/wiki/CodeReviewComments
- https://github.com/golang-standards/project-layout

## Interfaces And API Boundaries

Borrow:
- Define the interface at the package that consumes the dependency.
- Keep interfaces small and named by behavior: `Reader`, `Clock`, `Store`,
  `Publisher`, `Authorizer`, `TxRunner`.
- Return concrete types from constructors unless callers need an abstraction.
- Accept concrete types when no substitution point is needed.
- Put fakes in tests or test packages when a real adapter is too expensive.

Do not copy:
- Producer-owned interfaces such as `UserRepositoryInterface` next to the
  concrete implementation just to make tests easy.
- Interfaces with many methods that mirror a whole concrete type.
- Generic "service" interfaces without a caller-owned reason.

Sources:
- https://go.dev/wiki/CodeReviewComments
- https://go.dev/blog/package-names

## Domain-First And Clean Architecture, Go-Style

Borrow:
- Use Clean Architecture, Hexagonal Architecture, or DDD as dependency
  direction rules, not as mandatory folder names.
- Keep domain language in the domain package. If a term has different meaning
  in different contexts, split the bounded context.
- Use in-memory adapters early when they help validate domain behavior before
  choosing a database.
- Keep transport DTOs and persistence records out of rich domain entities when
  tags or external formats would weaken invariants.

Do not copy:
- Java-style layer hierarchies, abstract factories, and interface stacks.
- A repository per table when the use case needs transaction or aggregate
  behavior.
- DDD tactical patterns in CRUD-only systems where simple structs and SQL are
  clearer.

Sources:
- https://threedots.tech/go-with-the-domain/
- https://academy.threedots.tech/knowledge/domain-first-approach
- https://academy.threedots.tech/knowledge/bounded-context
- https://academy.threedots.tech/knowledge/dto
- https://www.packtpub.com/en-us/product/domain-driven-design-with-golang-9781804619261

## HTTP, Service, Repository, And Transactions

Borrow:
- Handlers translate transport input to application commands and responses.
- Application/use-case code owns transaction boundaries when multiple adapter
  operations must commit or roll back together.
- Repositories should express domain operations or aggregate persistence, not
  just table CRUD by default.
- External clients and stores are concrete adapters behind consumer-owned
  interfaces only when tests or alternate implementations require it.
- Map domain/application errors to HTTP/RPC responses at the transport layer.

Do not copy:
- HTTP request, response, JSON, SQL row, or ORM model types into domain logic.
- A service layer that only forwards calls and adds no policy.
- Transaction APIs that leak through every domain function just because the DB
  adapter needs them.

Sources:
- https://go.dev/blog/error-handling-and-go
- https://go.dev/wiki/Errors
- https://threedots.tech/go-with-the-domain/

## API Gateways, Model Routers, And Provider Adapters

Borrow:
- Keep the public API contract separate from provider-specific request shapes.
- Route selection, account selection, pricing, and capability policy belong in
  application packages, not inside transport handlers or provider clients.
- Provider adapters should own authentication, request/response translation,
  retry semantics, provider error classification, and provider telemetry.
- Generated docs, model schemas, workflow configs, and SQL seeds need an
  explicit source-of-truth order.

Do not copy:
- Letting downstream provider fields leak into the public request schema.
- Making every provider adapter a special case in controller code.
- Treating generated examples or docs as authoritative when SQL/config/code is
  what production actually loads.
- Adding a generic adapter framework before at least two real providers share
  the same contract.

## Context, Cancellation, And Concurrency

Borrow:
- Pass `context.Context` into operations that may block, perform IO, or spawn
  request-scoped work.
- Use context for deadlines, cancellation, and request-scoped values; not for
  optional parameters or long-lived dependencies.
- Pipeline stages need rules for input close, output close, fan-out, fan-in,
  cancellation, and error propagation.
- Worker pools and background loops need explicit owner, lifecycle, shutdown,
  and observability.

Do not copy:
- Storing request context in service structs.
- Starting goroutines without a cancellation or join path.
- Unbounded channel queues without backpressure and shutdown semantics.
- Pipelines for simple sequential code.

Sources:
- https://go.dev/blog/context-and-structs
- https://go.dev/blog/context
- https://go.dev/blog/pipelines
- https://go.dev/blog/advanced-go-concurrency-patterns

## Workflow, Billing, And Reconciliation

Borrow:
- Model async work as explicit state transitions with idempotency keys, owner,
  deadline/TTL, retry policy, and terminal states.
- Use an outbox or durable command table when billing, provider calls, or MQ
  publishing must survive process crashes.
- Keep projection status separate from the execution log, but define which one
  is authoritative for each user/operator question.
- Reconciliation loops need bounded scans, lock ownership, metrics, and tests
  for stuck/running/partial-failure states.

Do not copy:
- A worker that silently fixes state without recording why the state changed.
- Billing or settlement logic hidden in controllers because the HTTP path was
  the first implementation.
- Multiple cron/worker paths that update the same state without one transition
  API or transaction owner.
- Retrying provider calls without an idempotency and billing policy.

## Errors, Diagnostics, And Observability

Borrow:
- Return `error` values and handle them at the boundary that knows what to do.
- Wrap errors when the current layer adds useful operation context.
- Use sentinel or typed errors only when callers need programmatic handling.
- Keep user response messages, logs, metrics, and traces separate from the
  low-level error value.
- Panic only for impossible programmer errors or narrow internal unwind paths
  that recover to an error at a documented boundary.

Do not copy:
- Parsing error strings to make decisions.
- Logging and returning the same error at every layer.
- Returning bare dependency errors across public package boundaries when they
  become accidental API commitments.
- Recovering panics silently.

Sources:
- https://go.dev/wiki/Errors
- https://go.dev/blog/error-handling-and-go
- https://go.dev/blog/defer-panic-and-recover
- https://go.dev/pkg/errors/

## Testing And Verification

Borrow:
- Test package contracts through the public API when possible.
- Use table tests for behavior matrixes and golden tests for stable output.
- Use fake adapters for DB, queue, clock, email, and external services when the
  contract matters more than the implementation.
- Use integration tests for real DB/network behavior at adapter boundaries.
- Add goroutine-leak, cancellation, race, and shutdown tests for concurrent
  services.

Do not copy:
- Deep mock stacks that encode implementation details.
- Tests that require every layer to expose interfaces only for mocking.
- Concurrency tests that assert deterministic ordering unless ordering is part
  of the contract.

Sources:
- https://go.dev/wiki/CodeReviewComments
- https://go.dev/doc/modules/layout

## Book And Long-Form References

Use books as pattern sources, not rules to copy directly.

Go-specific:
- `Learning Go` by Jon Bodner: idiomatic Go, project design, generics, tooling,
  and when to avoid non-Go patterns.
- `100 Go Mistakes and How to Avoid Them` by Teiva Harsanyi: practical failure
  modes around concurrency, errors, testing, memory, and performance.
- `Domain-Driven Design with Golang` by Matthew Boyle: applying DDD concepts
  to Go business systems.
- `Go With The Domain` by Three Dots Labs: pragmatic domain-first Go examples.

General architecture books that can inform Go but should be adapted:
- `Domain-Driven Design` by Eric Evans.
- `Implementing Domain-Driven Design` by Vaughn Vernon.
- `Clean Architecture` by Robert C. Martin.
- `Patterns of Enterprise Application Architecture` by Martin Fowler.
- `Release It!` by Michael Nygard.

Sources:
- https://www.ingramacademic.com/9781098139292/learning-go/
- https://www.pearson.com/en-gb/subject-catalog/p/100-go-mistakes/P200000007212/9781617299599
- https://www.packtpub.com/en-us/product/domain-driven-design-with-golang-9781804619261
- https://threedots.tech/go-with-the-domain/

## Go Design Rules For Architecture Specs

1. State the package import graph before drawing layers.
2. Name packages by domain or capability, not generic technical categories.
3. Put interfaces at the consumer boundary and keep them tiny.
4. Return concrete types until an abstraction is needed.
5. Keep HTTP/RPC/DB/queue types out of the domain unless the app is purely
   infrastructural.
6. Put context, cancellation, timeout, and shutdown in every blocking or
   goroutine-spawning contract.
7. Make transaction ownership explicit at the use-case/application boundary.
8. Errors should say who can act on them: caller, transport mapper, operator,
   or developer.
9. For existing services, name the source of truth for public contracts,
   workflow state, billing state, generated docs, and SQL/config seeds.
10. Mark compatibility paths as bridge, legacy, or accidental fork; require a
    deletion or convergence condition before adding another path.
11. Avoid new packages until there is a stable concept, separate owner,
   side-effect boundary, or test boundary.
12. Prefer boring, readable Go over framework-shaped architecture.
