# Go Structured Logging Reference

Use this reference for Go applications after inspecting the module version, existing logger, HTTP stack, adapters, and tests.

## Selection Default

For Go 1.21+ services already using `log/slog`, keep `slog` unless repository evidence proves a missing capability or measured performance problem. Do not migrate to Zap, Zerolog, Logrus, or another frontend solely because a generic benchmark reports fewer allocations.

For older modules or established repositories, preserve the existing logger when it satisfies the logging contract and integrates with the surrounding stack. A logging migration is an API and operational change, not cleanup.

Primary references:

- [`log/slog` package](https://pkg.go.dev/log/slog)
- [Go structured logging overview](https://go.dev/blog/slog)
- [`testing/slogtest`](https://pkg.go.dev/testing/slogtest)

## Composition Root

Construct the process logger once at startup. Inject it only into runtime owners that emit logs; do not let packages construct competing handlers.

```go
level := new(slog.LevelVar)
level.Set(slog.LevelInfo)

logHandler := slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
	Level: level,
})
logger := slog.New(logHandler).With(
	"service", "assetd",
	"environment", environment,
	"version", version,
)
slog.SetDefault(logger)

server := &http.Server{
	Handler:  appHandler,
	ErrorLog: slog.NewLogLogger(logger.Handler(), slog.LevelError),
}
```

Validate log level and format configuration. An invalid production value should fail startup rather than silently fall back.

Prefer JSON for containers and a text handler only for an explicitly configured local-development mode. Keep collection and retention outside the process.

## Context And Boundaries

Pass `context.Context` as the first argument through requests, adapters, and workers. Store typed correlation values such as request ID in context when necessary; do not make context a generic service locator for loggers.

Use `InfoContext`, `WarnContext`, `ErrorContext`, or `LogAttrs` when the handler needs active trace context. Create request-scoped child loggers at the transport/runtime boundary when repeated attributes justify it, but do not inject a logger into pure domain functions.

Errors should be returned and wrapped with operation context. Log once where the caller has enough information to classify outcome and ownership. Avoid logging the same error in repository, service, handler, and middleware layers.

## HTTP Observation

Recommended middleware order:

```text
request_id -> completion capture -> recovery -> auth -> route handler
```

Capture normalized route/operation, method, status, duration, response bytes, request ID, fixed error code, and authenticated mode/source when safe. Exclude the raw query and do not use resource-bearing paths as metric labels.

A custom `http.ResponseWriter` wrapper must preserve the optional interfaces implemented by the underlying writer. For services with streaming, WebSockets, flushing, or `io.ReaderFrom`, use a tested wrapper such as [`felixge/httpsnoop`](https://pkg.go.dev/github.com/felixge/httpsnoop) or prove equivalent interface-preservation tests. Do not add the dependency when the existing framework already exposes reliable request metrics.

Recovery should emit the standard internal-error response when possible and one structured error event. Log a safe panic type and stack; avoid arbitrary panic values that may contain request data.

## `slog` Field Discipline

Use stable keys and explicit `slog.Attr` values on hot paths:

```go
logger.LogAttrs(ctx, slog.LevelInfo, "http request completed",
	slog.String("event", "http_request_completed"),
	slog.String("request_id", requestID),
	slog.String("method", r.Method),
	slog.String("route", route),
	slog.Int("status_code", status),
	slog.Int64("duration_ms", duration.Milliseconds()),
)
```

Use `Logger.With` for stable common attributes. Use `WithGroup` for a real ingestion schema, not merely to make output look nested. Implement `LogValuer` only for types with a deliberate safe representation; never use it to expose arbitrary request, config, principal, or SDK structs.

A `ReplaceAttr` redactor can block known sensitive keys, but it is defense in depth. The primary control is an allowlist of fields at each event site.

## GORM And Database Logging

GORM's default logger may print slow SQL and errors. Configure it explicitly rather than inheriting environment-dependent output:

- enable parameterized-query output so values are not interpolated;
- ignore expected record-not-found logging when the application classifies it normally;
- choose a measured slow-query threshold;
- keep production level at warn/error unless query diagnostics are temporarily authorized;
- propagate request context so safe correlation fields remain available.

See [GORM Logger](https://gorm.io/docs/logger.html). Do not log DSNs, SQL arguments, full model values, or raw database errors as metric labels.

## Testing

Capture JSON records with a `bytes.Buffer` or a test handler, decode each line, and assert semantic fields. Avoid brittle comparisons of timestamps or source line numbers.

At minimum, test:

- logger initialization and invalid level handling;
- one request-completion record for success, client rejection, auth failure, and server failure;
- request ID generation, validation, and propagation;
- normalized routes across different resource IDs;
- panic recovery and HTTP server error logging;
- streaming and optional writer interfaces when wrapped;
- secret canaries across headers, query, body, configuration, and upstream errors;
- GORM expected-not-found suppression and parameter redaction;
- cancellation/shutdown paths not reported as operational failures.

Run repository-native checks plus `go test -race ./...` when middleware, shared handlers, counters, or worker logging changed. Use `go vet ./...` to catch malformed alternating `slog` key/value calls.
