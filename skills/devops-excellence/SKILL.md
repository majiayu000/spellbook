---
name: devops-excellence
description: DevOps and CI/CD expert. Use when setting up pipelines, containerizing applications, deploying to Kubernetes, or implementing release strategies. Covers GitHub Actions, Docker, K8s, Terraform, and GitOps.
---
# DevOps Excellence

## Core Principles

- **Shift Left** — Address security and quality early in SDLC
- **GitOps** — Git as single source of truth for infrastructure and deployments
- **Infrastructure as Code** — All infrastructure versioned and reproducible
- **Progressive Delivery** — Gradual rollouts with feature flags and canary releases
- **Immutable Infrastructure** — Replace, don't modify running systems
- **Observability-First** — Monitor metrics tied to deployments and features
- **Policy as Code** — Enforce compliance and security automatically
- **Platform Engineering** — Build golden paths and self-service portals

---

## Hard Rules (Must Follow)

> These rules are mandatory. Violating them means the skill is not working correctly.

### No Static Credentials

**Never use long-lived static credentials. Always use OIDC or short-lived tokens.**

```yaml
# ❌ FORBIDDEN: Static AWS credentials
env:
  AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
  AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

# ✅ REQUIRED: OIDC-based authentication
- name: Configure AWS Credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789012:role/GitHubActions
    aws-region: us-east-1
    # No long-lived secrets - uses GitHub OIDC provider
```

### No Root Containers

**Containers must NEVER run as root. Always specify a non-root user.**

```dockerfile
# ❌ FORBIDDEN: Running as root (default)
FROM node:20
WORKDIR /app
CMD ["node", "server.js"]

# ❌ FORBIDDEN: Explicit root user
USER root

# ✅ REQUIRED: Non-root user with UID > 1000
FROM node:20-alpine
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001
USER nodejs
WORKDIR /app
CMD ["node", "server.js"]
```

### No Secrets in Images

**Never bake secrets into Docker images. Use runtime injection or secrets managers.**

```dockerfile
# ❌ FORBIDDEN: Secrets in build args or ENV
ARG DATABASE_PASSWORD
ENV API_KEY=sk-xxx

# ❌ FORBIDDEN: Copying secret files
COPY .env /app/.env
COPY credentials.json /app/

# ✅ REQUIRED: Mount secrets at runtime
# docker run -v /secrets:/app/secrets:ro myapp
# Or use Kubernetes secrets/configmaps
```

### Protected Production Deployments

**Production deployments must require approval and be restricted to main branch.**

```yaml
# ❌ FORBIDDEN: Direct production deploy without protection
deploy:
  runs-on: ubuntu-latest
  steps:
    - run: deploy-to-prod.sh

# ✅ REQUIRED: Environment protection
deploy:
  runs-on: ubuntu-latest
  environment:
    name: production
    url: https://myapp.com
  # Requires: approval + main branch only
```

---

## Quick Reference

### When to Use What

| Scenario | Tool/Pattern | Reason |
|----------|--------------|--------|
| Public GitHub project | GitHub Actions | Native integration, free for public repos |
| Enterprise GitLab | GitLab CI | Unified platform, advanced security scanning |
| Multi-cloud IaC | Terraform | Mature ecosystem, wide provider support |
| Developer-centric IaC | Pulumi | Real programming languages, better testing |
| Kubernetes deployments | ArgoCD + Kustomize | GitOps standard, declarative config |
| Zero-downtime releases | Blue-Green or Canary | Instant rollback capability |
| Gradual feature rollout | Feature flags (LaunchDarkly) | Progressive delivery with targeting |

### Deployment Strategy Selection

| Strategy | Downtime | Cost | Rollback Speed | Complexity | Best For |
|----------|----------|------|----------------|------------|----------|
| **Rolling** | Minimal | Low | Medium | Low | Regular updates, cost-conscious |
| **Blue-Green** | Zero | High (2x) | Instant | Medium | Critical systems, easy rollback |
| **Canary** | Zero | Medium | Fast | High | Risk mitigation, data-driven |
| **Recreate** | High | Low | N/A | Very Low | Non-critical, dev/test only |

---

## CI/CD Pipeline Best Practices

### Pipeline Security

```yaml
# Short-lived credentials (not static keys)
- name: Configure AWS Credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789012:role/GitHubActions
    aws-region: us-east-1
    # OIDC provider - no long-lived secrets!

# Protected environments for production
environment:
  name: production
  # Requires approval + restricts to main branch
```

### Speed Optimization

- **10-minute build rule** — Most projects should build in <10 minutes
- **Parallel jobs** — Run tests, linting, security scans concurrently
- **Cache dependencies** — Cache node_modules, .m2, pip packages
- **Conditional execution** — Skip jobs when files haven't changed

```yaml
# Example: conditional job execution
jobs:
  backend-tests:
    if: contains(github.event.head_commit.modified, 'backend/')
    runs-on: ubuntu-latest
```

### Testing Pyramid

```
              /\
             /E2E\        <- Few (slow, expensive)
            /------\
           /Integration\ <- Some (medium speed)
          /------------\
         /  Unit Tests  \ <- Many (fast, cheap)
        /----------------\
```

- 70% Unit tests (fast, isolated)
- 20% Integration tests (service interactions)
- 10% E2E tests (full user workflows)

### Security Scanning Integration

```yaml
# Multi-layer security scanning
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      # SAST - Static code analysis
      - uses: github/codeql-action/init@v3

      # SCA - Dependency vulnerabilities
      - name: Run Trivy
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          format: 'sarif'

      # Secret scanning
      - name: Gitleaks
        uses: gitleaks/gitleaks-action@v2

      # Container scanning
      - name: Scan Docker image
        run: trivy image myapp:${{ github.sha }}
```

---

## Docker Best Practices

### Multi-Stage Builds

```dockerfile
# Build stage - includes build tools (900MB+)
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# Runtime stage - minimal image (<100MB)
FROM node:20-alpine AS runtime
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001
WORKDIR /app
COPY --from=builder --chown=nodejs:nodejs /app/node_modules ./node_modules
COPY --chown=nodejs:nodejs . .
USER nodejs
EXPOSE 3000
CMD ["node", "server.js"]
```

### Security Hardening

- **Non-root user** — ALWAYS run as non-root (UID 1001)
- **Minimal base images** — Use `alpine`, `distroless`, or `scratch`
- **Read-only filesystem** — `docker run --read-only`
- **No secrets in layers** — Use build secrets or external vaults
- **Resource limits** — Set CPU/memory limits to prevent DoS
- **Signed images** — Enable Docker Content Trust

```dockerfile
# Security best practices example
FROM gcr.io/distroless/nodejs20-debian12
COPY --chown=65532:65532 /app /app
USER 65532
EXPOSE 8080
```

### .dockerignore

```
# Version control
.git
.gitignore

# Dependencies (install fresh in container)
node_modules
vendor/
*.pyc
__pycache__

# Secrets and configs
.env
.env.local
secrets/
*.key
*.pem

# Development files
README.md
Dockerfile
docker-compose.yml
.vscode/
.idea/

# Testing and CI
tests/
*.test.js
.github/
```

---

## Kubernetes Deployment Patterns

### Resource Management (Right-Sizing)

```yaml
# 99.94% of clusters are over-provisioned!
# Average CPU usage: 10%, Memory: 23%
resources:
  requests:
    memory: "128Mi"  # Guaranteed allocation
    cpu: "100m"      # 0.1 CPU cores
  limits:
    memory: "256Mi"  # Maximum allowed
    cpu: "200m"      # Hard cap

# Use tools: Kubecost, Goldilocks, VPA
```

### Health Checks

```yaml
# Liveness: Is container alive?
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

# Readiness: Can it receive traffic?
readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  successThreshold: 1

# Startup: Has initialization completed?
startupProbe:
  httpGet:
    path: /startup
    port: 8080
  failureThreshold: 30  # 30*10s = 5min for slow starts
  periodSeconds: 10
```

### ConfigMaps and Secrets

```yaml
# Group related resources in single manifest
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_ENV: production
  LOG_LEVEL: info
---
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
stringData:
  DATABASE_URL: postgresql://user:pass@db:5432/mydb
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      containers:
      - name: app
        envFrom:
        - configMapRef:
            name: app-config
        - secretRef:
            name: app-secrets
```

### Security Best Practices

```yaml
# Pod Security Standards
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault
  capabilities:
    drop:
    - ALL

# Network Policies (deny-by-default)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-ingress
spec:
  podSelector: {}
  policyTypes:
  - Ingress
```

---


## Extended Reference

Detailed material starting at `## Infrastructure as Code (Terraform/Pulumi)` has been moved to [`reference/extended.md`](reference/extended.md) to keep this skill concise. Load that reference when the task requires the moved examples, command catalogs, checklists, platform details, or implementation templates.
