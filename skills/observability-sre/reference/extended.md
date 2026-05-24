# observability-sre Extended Reference

This file preserves detailed material moved out of `SKILL.md` for progressive disclosure. Load it only when the current task needs the specific examples, commands, templates, or checklists below.

Moved content starts at: `## SLO/SLI/SLA Management`.

## SLO/SLI/SLA Management

### Definitions

- **SLI (Service Level Indicator)** — Quantifiable measurement of service behavior
  - Examples: Request latency, error rate, availability, throughput

- **SLO (Service Level Objective)** — Target value/range for an SLI
  - Examples: 99.9% availability, P95 latency < 200ms

- **SLA (Service Level Agreement)** — Formal commitment with consequences
  - Examples: "99.9% uptime or 10% credit"

### The Four Golden Signals

```yaml
# Google SRE's key metrics for any service

1. Latency
   SLI: P95 request latency
   SLO: 95% of requests complete in < 200ms

2. Traffic
   SLI: Requests per second
   SLO: Handle 10,000 req/s peak load

3. Errors
   SLI: Error rate (5xx / total)
   SLO: < 0.1% error rate

4. Saturation
   SLI: Resource utilization (CPU, memory, disk)
   SLO: CPU < 70%, Memory < 80%
```

### Error Budget

```python
# Error budget = 1 - SLO
SLO = 99.9%  # "three nines"
Error_Budget = 100% - 99.9% = 0.1%

# Monthly calculation (30 days)
Total_Minutes = 30 * 24 * 60 = 43,200 minutes
Allowed_Downtime = 43,200 * 0.001 = 43.2 minutes

# If you've had 20 minutes downtime this month:
Budget_Remaining = 43.2 - 20 = 23.2 minutes
Budget_Consumed = 20 / 43.2 = 46.3%

# Policy: If budget > 90% consumed, freeze deployments
```

### SLO Implementation with Prometheus

```yaml
# Recording rules for SLI calculation
groups:
  - name: slo_availability
    interval: 30s
    rules:
      # Total requests
      - record: slo:api_requests:total
        expr: sum(rate(http_requests_total[5m]))

      # Successful requests (non-5xx)
      - record: slo:api_requests:success
        expr: sum(rate(http_requests_total{status!~"5.."}[5m]))

      # Availability SLI
      - record: slo:api_availability:ratio
        expr: slo:api_requests:success / slo:api_requests:total

      # 30-day availability
      - record: slo:api_availability:30d
        expr: avg_over_time(slo:api_availability:ratio[30d])

  - name: slo_latency
    interval: 30s
    rules:
      # P95 latency SLI
      - record: slo:api_latency:p95
        expr: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

# Alerting on SLO burn rate
- alert: HighErrorBudgetBurnRate
  expr: |
    (
      slo:api_availability:ratio < 0.999  # Below 99.9% SLO
      and
      slo:api_availability:30d > 0.999    # But 30-day average still OK
    )
  for: 5m
  annotations:
    summary: "Burning error budget too fast"
    description: "Current availability {{ $value }} is below SLO. {{ $labels.service }}"
```

---

## Incident Response

### Incident Severity Levels

| Level | Impact | Response Time | Examples |
|-------|--------|---------------|----------|
| **SEV-1** | Service down or major degradation | < 15 min | Complete outage, data loss, security breach |
| **SEV-2** | Significant impact, partial outage | < 1 hour | Feature unavailable, high error rates |
| **SEV-3** | Minor impact, workaround exists | < 4 hours | Single component degraded, slow performance |
| **SEV-4** | Cosmetic, no user impact | Next business day | UI glitches, logging errors |

### Incident Response Roles (IMAG Framework)

```yaml
Incident Commander (IC):
  - Overall coordination and decision-making
  - Declares incident start/end
  - Decides on escalations
  - Owns communication to leadership

Operations Lead (OL):
  - Technical investigation and mitigation
  - Coordinates engineers
  - Implements fixes
  - Reports status to IC

Communications Lead (CL):
  - Internal/external status updates
  - Customer communication
  - Stakeholder notifications
  - Status page updates
```

### Incident Workflow

```
1. Detection (Alert fires or user reports)
   ↓
2. Triage (Assess severity, assign IC)
   ↓
3. Response (Assemble team, create war room)
   ↓
4. Mitigation (Stop the bleeding, restore service)
   ↓
5. Resolution (Fix root cause)
   ↓
6. Postmortem (Blameless review, action items)
   ↓
7. Follow-up (Implement improvements)
```

### On-Call Best Practices

- **Rotation** — 1-week shifts, balanced across timezones
- **Escalation** — Primary → Secondary → Manager (15 min each)
- **Playbooks** — Step-by-step debugging guides for common issues
- **Runbooks** — Automated remediation scripts
- **Handoff** — 15-min sync at rotation change
- **Compensation** — On-call pay or comp time
- **Health** — No more than 2 incidents/night target

### Alert Fatigue Prevention

```yaml
# Symptoms vs Causes alerting
# Alert on WHAT users experience, not WHY it's broken

# GOOD: Symptom-based alert
- alert: APILatencyHigh
  expr: slo:api_latency:p95 > 0.200  # User-facing metric
  annotations:
    summary: "API is slow for users"

# BAD: Cause-based alert
- alert: CPUHigh
  expr: cpu_usage > 70%  # Internal metric, might not impact users
  # Don't alert unless this affects SLOs

# Use SLO-based alerting
# Alert when error budget burn rate is too high
```

---

## Blameless Postmortems

### Core Principles

- **Assume Good Intentions** — Everyone did their best with available information
- **Focus on Systems** — Identify gaps in process/tooling, not people
- **Psychological Safety** — No punishment for honest mistakes
- **Learning Culture** — Incidents are opportunities to improve
- **Separate from Performance Reviews** — Postmortem participation never affects evaluations

### Postmortem Template

```markdown
# Incident Postmortem: [Title]

**Date:** 2025-01-15
**Duration:** 10:30 - 12:15 UTC (1h 45m)
**Severity:** SEV-2
**Incident Commander:** Jane Doe
**Responders:** John Smith, Alice Johnson

## Impact
- 15,000 users affected
- 12% error rate on payment processing
- $5,000 estimated revenue impact
- No data loss

## Timeline (UTC)
- 10:30 - Alert: Payment error rate > 5%
- 10:32 - IC assigned, war room created
- 10:45 - Identified: Database connection pool exhausted
- 11:00 - Mitigation: Increased pool size from 50 → 100
- 11:15 - Error rate back to normal
- 12:15 - Incident closed after monitoring

## Root Cause
Database connection pool configured for average load, not peak traffic.
Black Friday traffic spike (3x normal) exhausted connections.

## What Went Well
- Alert fired within 2 minutes of issue
- Clear escalation path, IC available immediately
- Mitigation applied quickly (30 minutes to fix)
- No data corruption or loss

## What Went Wrong
- No load testing at 3x scale
- No auto-scaling for connection pool
- No alert on connection pool saturation
- Insufficient monitoring of database metrics

## Action Items
- [ ] (@john) Add connection pool metrics to Grafana (Due: Jan 20)
- [ ] (@alice) Implement auto-scaling based on request rate (Due: Jan 25)
- [ ] (@jane) Add load testing to CI for 5x scale (Due: Feb 1)
- [ ] (@jane) Add alert: connection pool > 80% (Due: Jan 18)
- [ ] (@john) Document connection pool tuning runbook (Due: Jan 22)

## Lessons Learned
1. Black Friday load patterns need dedicated testing
2. Database metrics were missing from standard dashboards
3. Auto-scaling should cover ALL resources, not just pods
```

### Follow-up

- Review postmortem in team meeting within 1 week
- Track action items to completion (not optional!)
- Share learnings across teams
- Update runbooks and playbooks
- Celebrate successful incident response

---

## Chaos Engineering

### Principles

1. **Define Steady State** — Normal system behavior (e.g., 99.9% success rate)
2. **Hypothesize** — Predict system will remain stable under failure
3. **Inject Failures** — Simulate real-world events
4. **Disprove Hypothesis** — Look for deviations from steady state
5. **Learn and Improve** — Fix weaknesses, increase resilience

### Failure Types

```yaml
Infrastructure:
  - Pod/node termination
  - Network latency/packet loss
  - DNS failures
  - Cloud region outage

Resources:
  - CPU stress
  - Memory exhaustion
  - Disk I/O saturation
  - File descriptor limits

Dependencies:
  - Database connection failures
  - API timeout/errors
  - Cache unavailability
  - Message queue backlog

Security:
  - DDoS simulation
  - Certificate expiration
  - Unauthorized access attempts
```

### Chaos Mesh Example

```yaml
# Network latency injection
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: network-delay
spec:
  action: delay
  mode: one
  selector:
    namespaces:
      - production
    labelSelectors:
      app: payment-service
  delay:
    latency: "100ms"
    correlation: "50"
    jitter: "50ms"
  duration: "5m"
  scheduler:
    cron: "@every 2h"  # Run every 2 hours

---
# Pod kill experiment
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: pod-kill
spec:
  action: pod-kill
  mode: fixed-percent
  value: "10"  # Kill 10% of pods
  selector:
    namespaces:
      - production
    labelSelectors:
      app: api-server
  duration: "30s"
```

### Best Practices

- **Start Small** — Non-production first, then canary production
- **Collect Baselines** — Know normal metrics before experiments
- **Define Success** — Clear criteria for what "stable" means
- **Monitor Everything** — Watch metrics, logs, traces during tests
- **Automate Rollback** — Stop experiment if SLOs violated
- **Game Days** — Scheduled chaos exercises with full team
- **Blameless Reviews** — Treat chaos failures like production incidents

---

## AIOps and AI in Observability

### 2025 Trends

- **Anomaly Detection** — AI spots unusual patterns in metrics/logs
- **Root Cause Analysis** — Correlate failures across services automatically
- **Predictive Alerting** — Predict failures before they happen
- **Auto-Remediation** — AI suggests or applies fixes autonomously
- **Natural Language Queries** — Ask "Why is checkout slow?" instead of writing PromQL
- **AI Observability** — Monitor AI model drift, hallucinations, token usage

### AI-Driven Platforms (2025)

```yaml
Dynatrace Davis AI:
  - Auto-detected 73% of incidents before customer impact
  - Reduced alert noise by 90%
  - Causal AI for root cause analysis

Datadog Watchdog:
  - Anomaly detection across metrics, logs, traces
  - Automated correlation of related issues
  - LLM-powered investigation assistant

Elastic AIOps:
  - Machine learning for log anomaly detection
  - Automated baseline learning
  - Predictive alerting

New Relic AI:
  - Natural language query interface
  - Automated incident summarization
  - Proactive capacity recommendations
```

### Implementing AI Observability

```python
# Monitor AI model performance
from opentelemetry import trace, metrics

tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Create metrics for AI model
model_latency = meter.create_histogram(
    "ai.model.latency",
    description="AI model inference latency",
    unit="ms"
)
model_tokens = meter.create_counter(
    "ai.model.tokens",
    description="Token usage"
)

async def run_ai_model(prompt: str):
    with tracer.start_as_current_span("ai.inference") as span:
        start = time.time()

        span.set_attribute("ai.model", "gpt-4")
        span.set_attribute("ai.prompt_length", len(prompt))

        response = await openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        latency = (time.time() - start) * 1000
        tokens = response.usage.total_tokens

        # Record metrics
        model_latency.record(latency, {"model": "gpt-4"})
        model_tokens.add(tokens, {"model": "gpt-4", "type": "total"})

        # Add to span
        span.set_attribute("ai.response_length", len(response.choices[0].message.content))
        span.set_attribute("ai.tokens_used", tokens)

        return response
```

---

## Grafana Dashboards

### 3-3-3 Rule

- **3 rows** of panels per dashboard
- **3 panels** per row
- **3 key metrics** per panel

Avoid "dashboard sprawl" — Each dashboard should answer ONE question.

### Dashboard Categories

```yaml
RED Dashboard (for services):
  - Rate: Requests per second
  - Errors: Error rate
  - Duration: Latency (P50, P95, P99)

USE Dashboard (for resources):
  - Utilization: % of capacity used
  - Saturation: Queue depth, wait time
  - Errors: Error count

Four Golden Signals Dashboard:
  - Latency
  - Traffic
  - Errors
  - Saturation

SLO Dashboard:
  - Current SLI value
  - Error budget remaining
  - Burn rate
  - Trend (30-day)
```

### Panel Best Practices

```json
{
  "title": "API Request Rate",
  "type": "graph",
  "targets": [
    {
      "expr": "sum(rate(http_requests_total[5m])) by (method)",
      "legendFormat": "{{ method }}"
    }
  ],
  "options": {
    "tooltip": { "mode": "multi" },
    "legend": { "displayMode": "table", "calcs": ["mean", "last"] }
  },
  "fieldConfig": {
    "defaults": {
      "unit": "reqps",  // Requests per second
      "color": { "mode": "palette-classic" },
      "custom": {
        "lineWidth": 2,
        "fillOpacity": 10
      }
    }
  }
}
```

---

## Checklist

```markdown
## Metrics (Prometheus + Grafana)
- [ ] Layered architecture (app/cluster/global)
- [ ] Recording rules for expensive queries
- [ ] Resource limits and retention configured
- [ ] Dashboards follow 3-3-3 rule
- [ ] Alerts based on SLOs, not internal metrics

## Tracing (OpenTelemetry)
- [ ] Auto-instrumentation enabled
- [ ] Custom spans for business operations
- [ ] Sampling strategy configured
- [ ] Trace context in logs (correlation)
- [ ] Backend connected (Tempo/Jaeger)

## Logging (Loki/ELK)
- [ ] Structured JSON logging
- [ ] Low cardinality labels (<10)
- [ ] Trace IDs in logs
- [ ] Appropriate log levels
- [ ] Retention policy defined

## SLOs
- [ ] SLIs defined for key user journeys
- [ ] SLOs documented and tracked
- [ ] Error budget calculated
- [ ] Burn rate alerting configured
- [ ] Monthly SLO review process

## Incident Response
- [ ] Severity levels defined
- [ ] On-call rotation scheduled
- [ ] Escalation policy documented
- [ ] Runbooks for common issues
- [ ] Postmortem template ready

## Culture
- [ ] Blameless postmortem process
- [ ] Action items tracked to completion
- [ ] Incident learnings shared
- [ ] On-call compensation policy
- [ ] Regular chaos engineering exercises
```

---

## See Also

- [reference/monitoring.md](reference/monitoring.md) — Prometheus and Grafana deep dive
- [reference/logging.md](reference/logging.md) — Structured logging best practices
- [reference/tracing.md](reference/tracing.md) — OpenTelemetry and distributed tracing
- [reference/incident-response.md](reference/incident-response.md) — Incident management and postmortems
- [templates/slo-template.md](templates/slo-template.md) — SLO definition template
