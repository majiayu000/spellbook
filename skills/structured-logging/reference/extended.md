# structured-logging Extended Reference

This file preserves detailed material moved out of `SKILL.md` for progressive disclosure. Load it only when the current task needs the specific examples, commands, templates, or checklists below.

Moved content starts at: `## Sensitive Data Handling`.

## Sensitive Data Handling

### Never Log

- Passwords and password hashes
- API keys, tokens, secrets
- Full credit card numbers
- Social security numbers
- Private keys

### Always Mask

| Data Type | Masking Pattern | Example |
|-----------|-----------------|---------|
| Email | Partial | `j***n@example.com` |
| Phone | Last 4 digits | `****1234` |
| Credit Card | Last 4 digits | `****4242` |
| IP Address | Partial | `192.168.***.***` |

```typescript
// utils/mask.ts
export const mask = {
  email: (email: string) => {
    const [local, domain] = email.split('@');
    return `${local[0]}***${local.slice(-1)}@${domain}`;
  },

  phone: (phone: string) => {
    return `****${phone.slice(-4)}`;
  },

  creditCard: (card: string) => {
    return `****${card.slice(-4)}`;
  },

  ip: (ip: string) => {
    const parts = ip.split('.');
    return `${parts[0]}.${parts[1]}.***.***`;
  }
};

// Usage
log.info('User login', {
  email: mask.email(user.email),  // j***n@example.com
  ip: mask.ip(request.ip)         // 192.168.***.***
});
```

## Log Format Examples

### Success Flow

```json
{"timestamp":"2025-12-16T10:30:00.100Z","level":"INFO","message":"API request received","service":"order-service","trace_id":"abc123","request_id":"req_001","method":"POST","path":"/api/orders"}
{"timestamp":"2025-12-16T10:30:00.150Z","level":"INFO","message":"Order validated","service":"order-service","trace_id":"abc123","order_id":"ord_789","items_count":3}
{"timestamp":"2025-12-16T10:30:00.200Z","level":"INFO","message":"Payment processed","service":"payment-service","trace_id":"abc123","order_id":"ord_789","amount":99.99}
{"timestamp":"2025-12-16T10:30:00.250Z","level":"INFO","message":"Order created","service":"order-service","trace_id":"abc123","order_id":"ord_789","duration_ms":150}
{"timestamp":"2025-12-16T10:30:00.260Z","level":"INFO","message":"API response sent","service":"order-service","trace_id":"abc123","request_id":"req_001","status":201,"duration_ms":160}
```

### Error Flow

```json
{"timestamp":"2025-12-16T10:31:00.100Z","level":"INFO","message":"API request received","service":"order-service","trace_id":"def456","request_id":"req_002","method":"POST","path":"/api/orders"}
{"timestamp":"2025-12-16T10:31:00.150Z","level":"INFO","message":"Order validated","service":"order-service","trace_id":"def456","order_id":"ord_790","items_count":2}
{"timestamp":"2025-12-16T10:31:00.200Z","level":"WARN","message":"Payment retry","service":"payment-service","trace_id":"def456","order_id":"ord_790","attempt":1,"reason":"timeout"}
{"timestamp":"2025-12-16T10:31:00.400Z","level":"ERROR","message":"Payment failed","service":"payment-service","trace_id":"def456","order_id":"ord_790","error_code":"CARD_DECLINED","error_message":"Insufficient funds","attempts":2}
{"timestamp":"2025-12-16T10:31:00.410Z","level":"INFO","message":"API response sent","service":"order-service","trace_id":"def456","request_id":"req_002","status":402,"duration_ms":310,"error_code":"PAYMENT_FAILED"}
```

---

## Centralized Configuration

### Configuration Schema

```typescript
// lib/logging/config.ts
export interface LoggingConfig {
  // Required
  service: string;
  environment: 'development' | 'staging' | 'production';

  // Log control
  level: 'trace' | 'debug' | 'info' | 'warn' | 'error' | 'fatal';

  // Output
  format: 'json' | 'pretty';
  transports: TransportConfig[];

  // Context enrichment
  defaultFields?: Record<string, unknown>;

  // Sensitive data
  redactPaths?: string[];  // Paths to always redact: ['password', 'token', 'secret']

  // Sampling (high-volume systems)
  sampling?: {
    enabled: boolean;
    rate: number;        // 0.0 to 1.0
    alwaysLogLevels: string[];  // ['error', 'fatal'] - never sample these
  };
}

interface TransportConfig {
  type: 'console' | 'file' | 'http' | 'syslog';
  level?: string;  // Minimum level for this transport
  options?: Record<string, unknown>;
}
```

### Environment-Based Configuration

```typescript
// lib/logging/config.ts
export function getConfig(): LoggingConfig {
  const env = process.env.NODE_ENV || 'development';

  const baseConfig: LoggingConfig = {
    service: process.env.SERVICE_NAME || 'unknown-service',
    environment: env as LoggingConfig['environment'],
    level: (process.env.LOG_LEVEL || 'info') as LoggingConfig['level'],
    format: env === 'development' ? 'pretty' : 'json',
    transports: [],
    redactPaths: ['password', 'token', 'secret', 'authorization', 'apiKey'],
  };

  // Environment-specific transports
  if (env === 'development') {
    baseConfig.transports = [
      { type: 'console', options: { colorize: true } }
    ];
  } else {
    baseConfig.transports = [
      { type: 'console' },
      { type: 'file', options: { path: '/var/log/app/app.log' } }
    ];
  }

  return baseConfig;
}
```

### Initialization Pattern

```typescript
// lib/logging/index.ts
let initialized = false;
let globalLogger: Logger;

export function initializeLogging(config?: Partial<LoggingConfig>): void {
  if (initialized) {
    console.warn('Logging already initialized. Skipping re-initialization.');
    return;
  }

  const finalConfig = { ...getConfig(), ...config };
  globalLogger = createLogger(finalConfig);
  initialized = true;

  globalLogger.info('Logging initialized', {
    service: finalConfig.service,
    environment: finalConfig.environment,
    level: finalConfig.level,
  });
}

export function getLogger(): Logger {
  if (!initialized) {
    // Auto-initialize with defaults in development
    if (process.env.NODE_ENV === 'development') {
      initializeLogging();
    } else {
      throw new Error('Logging not initialized. Call initializeLogging() at startup.');
    }
  }
  return globalLogger;
}

// Convenience export for simple cases
export const logger = {
  debug: (msg: string, data?: object) => getLogger().debug(msg, data),
  info: (msg: string, data?: object) => getLogger().info(msg, data),
  warn: (msg: string, data?: object) => getLogger().warn(msg, data),
  error: (msg: string, data?: object) => getLogger().error(msg, data),
};
```

---

## Library Selection Guide

### Recommended Libraries by Language

| Language | Library | Why |
|----------|---------|-----|
| **Node.js** | Pino | Fastest, native JSON, low overhead |
| **Node.js** | Winston | Most popular, flexible transports |
| **Python** | structlog | Best structured logging, context binding |
| **Python** | loguru | Simple API, great defaults |
| **Go** | zerolog | Zero allocation, JSON native |
| **Go** | zap | High performance, typed fields |
| **Java** | Logback + SLF4J | Industry standard, MDC support |
| **Rust** | tracing | Async-aware, spans built-in |
| **C#/.NET** | Serilog | Structured logging pioneer |

### Node.js: Pino Setup (Recommended)

```typescript
// lib/logging/logger.ts
import pino from 'pino';
import { getConfig } from './config';

export function createLogger(config = getConfig()) {
  return pino({
    name: config.service,
    level: config.level,

    // Standard field names
    messageKey: 'message',
    timestamp: () => `,"timestamp":"${new Date().toISOString()}"`,

    // Redaction
    redact: {
      paths: config.redactPaths || [],
      censor: '[REDACTED]'
    },

    // Base fields on every log
    base: {
      service: config.service,
      env: config.environment,
      version: process.env.APP_VERSION,
    },

    // Pretty print in development
    transport: config.format === 'pretty'
      ? { target: 'pino-pretty', options: { colorize: true } }
      : undefined,
  });
}
```

### Python: structlog Setup

```python
# lib/logging/logger.py
import structlog
import logging
import sys
from typing import Optional

def initialize_logging(
    service: str,
    level: str = "INFO",
    json_format: bool = True
):
    """Initialize logging once at application startup."""

    # Configure processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Bind service name globally
    structlog.contextvars.bind_contextvars(service=service)

def get_logger(name: Optional[str] = None):
    """Get a logger instance with optional name binding."""
    log = structlog.get_logger()
    if name:
        log = log.bind(module=name)
    return log

# Usage in application code
# from lib.logging import get_logger
# logger = get_logger(__name__)
# logger.info("User created", user_id="123")
```

---

## Framework Integration

### Express.js Middleware

```typescript
// lib/logging/middleware/express.ts
import { Request, Response, NextFunction } from 'express';
import { AsyncLocalStorage } from 'async_hooks';
import { randomUUID } from 'crypto';
import { logger } from '../index';

interface RequestContext {
  trace_id: string;
  span_id: string;
  request_id: string;
  user_id?: string;
}

export const requestContext = new AsyncLocalStorage<RequestContext>();

export function loggingMiddleware() {
  return (req: Request, res: Response, next: NextFunction) => {
    const startTime = process.hrtime.bigint();

    // Extract or generate correlation IDs
    const context: RequestContext = {
      trace_id: (req.headers['x-trace-id'] as string) || randomUUID().replace(/-/g, ''),
      span_id: randomUUID().substring(0, 16),
      request_id: (req.headers['x-request-id'] as string) || `req_${randomUUID().substring(0, 8)}`,
      user_id: (req as any).user?.id,
    };

    // Set response headers for downstream tracing
    res.setHeader('x-trace-id', context.trace_id);
    res.setHeader('x-request-id', context.request_id);

    // Log request
    logger.info('HTTP request received', {
      ...context,
      http_method: req.method,
      http_path: req.path,
      http_query: req.query,
      http_user_agent: req.headers['user-agent'],
    });

    // Log response on finish
    res.on('finish', () => {
      const duration_ms = Number(process.hrtime.bigint() - startTime) / 1_000_000;

      const logLevel = res.statusCode >= 500 ? 'error'
                     : res.statusCode >= 400 ? 'warn'
                     : 'info';

      logger[logLevel]('HTTP response sent', {
        ...context,
        http_method: req.method,
        http_path: req.path,
        http_status: res.statusCode,
        duration_ms: Math.round(duration_ms),
      });
    });

    // Run with context
    requestContext.run(context, () => next());
  };
}

// Context-aware logger getter
export function getContextLogger() {
  const ctx = requestContext.getStore();
  // Return logger with context bound
  return {
    debug: (msg: string, data?: object) => logger.debug(msg, { ...ctx, ...data }),
    info: (msg: string, data?: object) => logger.info(msg, { ...ctx, ...data }),
    warn: (msg: string, data?: object) => logger.warn(msg, { ...ctx, ...data }),
    error: (msg: string, data?: object) => logger.error(msg, { ...ctx, ...data }),
  };
}
```

### NestJS Integration

```typescript
// lib/logging/nest/logging.module.ts
import { Module, Global, DynamicModule } from '@nestjs/common';
import { LoggingService } from './logging.service';
import { LoggingConfig } from '../config';

@Global()
@Module({})
export class LoggingModule {
  static forRoot(config: Partial<LoggingConfig>): DynamicModule {
    return {
      module: LoggingModule,
      providers: [
        {
          provide: 'LOGGING_CONFIG',
          useValue: config,
        },
        LoggingService,
      ],
      exports: [LoggingService],
    };
  }
}

// lib/logging/nest/logging.service.ts
import { Injectable, Inject, Scope } from '@nestjs/common';
import { REQUEST } from '@nestjs/core';
import { Request } from 'express';
import { createLogger } from '../logger';
import { LoggingConfig } from '../config';

@Injectable({ scope: Scope.REQUEST })
export class LoggingService {
  private logger;
  private context: Record<string, unknown> = {};

  constructor(
    @Inject('LOGGING_CONFIG') config: LoggingConfig,
    @Inject(REQUEST) private request: Request,
  ) {
    this.logger = createLogger(config);
    this.context = {
      trace_id: this.request.headers['x-trace-id'],
      request_id: this.request.headers['x-request-id'],
      user_id: (this.request as any).user?.id,
    };
  }

  info(message: string, data?: object) {
    this.logger.info({ ...this.context, ...data }, message);
  }

  error(message: string, data?: object) {
    this.logger.error({ ...this.context, ...data }, message);
  }

  // ... other methods
}

// Usage in controllers/services
@Injectable()
export class OrderService {
  constructor(private readonly log: LoggingService) {}

  async createOrder(data: CreateOrderDto) {
    this.log.info('Creating order', { order_data: data });
    // ... business logic
    this.log.info('Order created', { order_id: order.id });
  }
}
```

### FastAPI (Python) Integration

```python
# lib/logging/middleware/fastapi.py
import time
import uuid
from contextvars import ContextVar
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

# Context variables for request-scoped data
request_id_var: ContextVar[str] = ContextVar('request_id', default='')
trace_id_var: ContextVar[str] = ContextVar('trace_id', default='')

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()

        # Extract or generate IDs
        trace_id = request.headers.get('x-trace-id', uuid.uuid4().hex)
        request_id = request.headers.get('x-request-id', f'req_{uuid.uuid4().hex[:8]}')

        # Set context variables
        request_id_var.set(request_id)
        trace_id_var.set(trace_id)

        # Bind to structlog context
        structlog.contextvars.bind_contextvars(
            trace_id=trace_id,
            request_id=request_id,
        )

        logger = structlog.get_logger()
        logger.info(
            "HTTP request received",
            http_method=request.method,
            http_path=request.url.path,
        )

        response: Response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000

        log_method = logger.error if response.status_code >= 500 else \
                     logger.warning if response.status_code >= 400 else \
                     logger.info

        log_method(
            "HTTP response sent",
            http_method=request.method,
            http_path=request.url.path,
            http_status=response.status_code,
            duration_ms=round(duration_ms),
        )

        # Add headers to response
        response.headers['x-trace-id'] = trace_id
        response.headers['x-request-id'] = request_id

        # Clear context
        structlog.contextvars.unbind_contextvars('trace_id', 'request_id')

        return response
```

---

## Logging Checklist

```markdown
## Architecture
- [ ] Centralized logging module created (lib/logging/)
- [ ] Single configuration source
- [ ] No direct logger instantiation in business code
- [ ] Framework middleware integrated

## Schema Design
- [ ] Tier 1 fields defined (timestamp, level, message, service)
- [ ] Tier 2 fields for tracing (trace_id, span_id, request_id)
- [ ] Field naming convention documented
- [ ] Sensitive data masking rules defined

## Implementation
- [ ] Logger configured with service name
- [ ] Request context propagation middleware
- [ ] Correlation IDs generated and propagated
- [ ] Duration tracking for operations
- [ ] Error normalization and logging

## Standards
- [ ] Log levels used correctly
- [ ] All logs are structured JSON
- [ ] No sensitive data in logs
- [ ] Consistent field names across services
- [ ] No console.log in production code

## Operations
- [ ] Log aggregation configured
- [ ] Alerts set for ERROR/FATAL levels
- [ ] Log retention policy defined
- [ ] Query patterns documented
```

## Field Naming Conventions

### Standard Field Names

Use these exact names for consistency:

```yaml
# Identifiers
user_id, order_id, product_id, session_id, request_id

# Tracing
trace_id, span_id, parent_span_id

# Time
timestamp, duration_ms, started_at, ended_at

# Status
status, outcome, error_code, error_message

# HTTP
http_method, http_path, http_status, http_user_agent

# Database
db_system, db_name, db_operation, db_statement

# Environment
env, version, host, region, instance_id
```

## Quick Reference

```
┌─────────────────────────────────────────────────────────────┐
│                    STRUCTURED LOG ENTRY                      │
├─────────────────────────────────────────────────────────────┤
│  Tier 1 (Required)                                          │
│  ├── timestamp    → ISO 8601 format                         │
│  ├── level        → DEBUG|INFO|WARN|ERROR|FATAL             │
│  ├── message      → Human readable description              │
│  └── service      → Service name                            │
├─────────────────────────────────────────────────────────────┤
│  Tier 2 (Tracing)                                           │
│  ├── trace_id     → Request chain ID                        │
│  ├── span_id      → Current operation ID                    │
│  └── request_id   → HTTP request ID                         │
├─────────────────────────────────────────────────────────────┤
│  Tier 3 (Context)                                           │
│  ├── user_id      → Who triggered this                      │
│  ├── method       → Function/method name                    │
│  ├── duration_ms  → How long it took                        │
│  └── error_*      → Error details (if applicable)           │
├─────────────────────────────────────────────────────────────┤
│  Tier 4 (Environment)                                       │
│  ├── env          → production|staging|dev                  │
│  ├── version      → Service version                         │
│  └── host/region  → Where it's running                      │
└─────────────────────────────────────────────────────────────┘
```
