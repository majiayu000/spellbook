# devops-excellence Extended Reference

This file preserves detailed material moved out of `SKILL.md` for progressive disclosure. Load it only when the current task needs the specific examples, commands, templates, or checklists below.

Moved content starts at: `## Infrastructure as Code (Terraform/Pulumi)`.

## Infrastructure as Code (Terraform/Pulumi)

### Directory Structure

```
terraform/
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   └── terraform.tfvars
│   ├── staging/
│   └── prod/
├── modules/
│   ├── vpc/
│   ├── eks/
│   └── rds/
├── backend.tf        # Remote state config
└── versions.tf       # Provider versions
```

### Best Practices

#### 1. Remote State with Locking

```hcl
# backend.tf
terraform {
  backend "s3" {
    bucket         = "mycompany-terraform-state"
    key            = "prod/vpc/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"  # Prevents concurrent runs
  }
}
```

#### 2. Modularization

```hcl
# modules/vpc/main.tf
variable "cidr_block" {
  type        = string
  description = "VPC CIDR block"
}

resource "aws_vpc" "main" {
  cidr_block           = var.cidr_block
  enable_dns_hostnames = true
  tags = {
    Name = "${var.environment}-vpc"
  }
}

# environments/prod/main.tf
module "vpc" {
  source     = "../../modules/vpc"
  cidr_block = "10.0.0.0/16"
  environment = "prod"
}
```

#### 3. Policy as Code

```hcl
# Use Sentinel (Terraform Cloud) or OPA
policy "enforce-tags" {
  enforcement_level = "hard-mandatory"

  # Require tags on all resources
  rule {
    condition = all resource.tags contains "Owner"
    error_message = "All resources must have Owner tag"
  }
}
```

#### 4. Automated Testing

```go
// Terratest example
func TestVPCCreation(t *testing.T) {
  terraformOptions := &terraform.Options{
    TerraformDir: "../environments/dev",
  }

  defer terraform.Destroy(t, terraformOptions)
  terraform.InitAndApply(t, terraformOptions)

  vpcId := terraform.Output(t, terraformOptions, "vpc_id")
  assert.NotEmpty(t, vpcId)
}
```

### Pulumi Advantages

```typescript
// Pulumi - real programming language benefits
import * as aws from "@pulumi/aws";

const environments = ["dev", "staging", "prod"];

// Use loops, conditionals, functions
environments.forEach(env => {
  new aws.ec2.Vpc(`${env}-vpc`, {
    cidrBlock: env === "prod" ? "10.0.0.0/16" : "10.1.0.0/16",
    tags: { Environment: env },
  });
});

// Built-in testing framework
import * as pulumi from "@pulumi/pulumi";
pulumi.runtime.setMocks(...);
```

---

## Release Strategies

### Blue-Green Deployment

```yaml
# Two identical environments
# Switch traffic instantly via load balancer

# Step 1: Deploy to Green (idle)
# Step 2: Test Green environment
# Step 3: Switch LB from Blue to Green
# Step 4: Keep Blue as rollback option

# Kubernetes example
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  selector:
    app: myapp
    version: blue  # Change to 'green' to switch
  ports:
  - port: 80
```

**When to use:**
- Critical systems requiring instant rollback
- Compliance requirements for zero downtime
- Budget allows 2x infrastructure

### Canary Deployment

```yaml
# Gradual rollout: 5% → 25% → 50% → 100%
# Monitor metrics at each stage

# Argo Rollouts example
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
spec:
  replicas: 10
  strategy:
    canary:
      steps:
      - setWeight: 10      # 1 pod (10%)
      - pause: {duration: 5m}
      - setWeight: 50      # 5 pods
      - pause: {duration: 10m}
      - setWeight: 100     # All pods
  template:
    spec:
      containers:
      - name: myapp
        image: myapp:v2.0
```

**When to use:**
- High-risk deployments (major refactors)
- User-facing features needing validation
- Data-driven rollout decisions

### Rolling Update

```yaml
# Default Kubernetes strategy
# Gradually replace old pods with new

apiVersion: apps/v1
kind: Deployment
spec:
  replicas: 10
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1  # Never < 9 pods available
      maxSurge: 2        # Never > 12 pods total
```

**When to use:**
- Regular incremental updates
- Cost-conscious deployments
- Low-risk changes

---

## Feature Flags and Progressive Delivery

### Best Practices

#### 1. Flag Lifecycle Management

```typescript
// Avoid "flag debt" - remove after rollout
const featureFlags = {
  // Short-lived (remove after 100% rollout)
  "new-checkout-v4": {
    enabled: true,
    rollout: 100,
    created: "2025-01-15",
    removeBy: "2025-02-15"
  },

  // Long-lived (kill switch)
  "payment-processing": {
    enabled: true,
    permanent: true,  // Document why
    reason: "Emergency shutoff for payment issues"
  }
};
```

#### 2. Progressive Rollout

```typescript
// LaunchDarkly example
const showNewFeature = ldClient.variation(
  "new-dashboard-ui",
  user,
  false  // Default fallback
);

// Configuration
{
  "targeting": {
    "rules": [
      {
        "variation": "on",
        "clauses": [
          {
            "attribute": "email",
            "op": "endsWith",
            "values": ["@mycompany.com"]
          }
        ]
      }
    ],
    "rollout": {
      "percentage": 10  // 10% of remaining users
    }
  }
}
```

#### 3. Segment Meaningfully

- Geographic: Region-specific rollouts
- Behavioral: Power users first, then general
- Technical: Browser/device-based targeting
- Business: Premium tier vs free tier

#### 4. Observability Integration

```typescript
// Tie metrics to feature flags
metrics.increment('checkout.completed', {
  feature_flag: 'new-checkout-v4',
  enabled: showNewCheckout
});

// Automatic rollback on error spike
if (errorRate > threshold) {
  ldClient.updateFeatureFlag('new-checkout-v4', { enabled: false });
  alerts.critical('Auto-rollback triggered for new-checkout-v4');
}
```

---

## GitOps Practices

### Core Principles

1. **Declarative** — Entire system state in Git
2. **Versioned** — Git history = audit trail
3. **Immutable** — Git commits are immutable
4. **Automatic** — Agents auto-sync cluster to Git state
5. **Continuous** — Reconciliation loop detects drift

### ArgoCD Workflow

```yaml
# Application definition
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/k8s-manifests
    targetRevision: main
    path: apps/myapp
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true      # Delete resources not in Git
      selfHeal: true   # Auto-sync on drift detection
    syncOptions:
    - CreateNamespace=true
```

### Repository Structure

```
k8s-manifests/
├── apps/
│   ├── myapp/
│   │   ├── base/
│   │   │   ├── deployment.yaml
│   │   │   ├── service.yaml
│   │   │   └── kustomization.yaml
│   │   └── overlays/
│   │       ├── dev/
│   │       ├── staging/
│   │       └── prod/
│   │           ├── kustomization.yaml
│   │           └── replicas-patch.yaml
├── infrastructure/
│   ├── ingress-nginx/
│   └── cert-manager/
└── argocd/
    ├── projects.yaml
    └── applications.yaml
```

### Policy Enforcement

```yaml
# OPA Gatekeeper - deny images without tags
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-owner-label
spec:
  match:
    kinds:
    - apiGroups: ["apps"]
      kinds: ["Deployment"]
  parameters:
    labels: ["owner", "environment"]
```

---

## Platform Engineering

### Internal Developer Portal (Backstage)

```yaml
# Software catalog
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: order-service
  description: Order processing microservice
  tags:
    - java
    - spring-boot
  annotations:
    github.com/project-slug: myorg/order-service
    pagerduty.com/integration-key: xyz
spec:
  type: service
  lifecycle: production
  owner: team-orders
  system: ecommerce-platform
```

### Golden Paths (Templates)

```yaml
# Self-service project scaffolding
apiVersion: scaffolder.backstage.io/v1beta3
kind: Template
metadata:
  name: nodejs-service
  title: Node.js Microservice
spec:
  steps:
  - id: fetch-template
    action: fetch:template
    input:
      url: ./skeleton
  - id: create-repo
    action: github:repo:create
  - id: setup-pipeline
    action: github:actions:create
  - id: provision-k8s
    action: argocd:create-app
```

### Benefits

- **Setup time** — Days to minutes (40% reduction in tickets)
- **Consistency** — Standardized patterns across teams
- **Security** — Policies enforced at platform level
- **Autonomy** — Self-service without DevOps bottleneck

---

## Security Scanning (SAST/DAST/SCA)

### Testing Types

| Type | What | When | Tools |
|------|------|------|-------|
| **SAST** | Static code analysis | Build time | SonarQube, CodeQL, Semgrep |
| **DAST** | Runtime testing | After deployment | OWASP ZAP, Burp Suite |
| **SCA** | Dependency vulnerabilities | Build + runtime | Trivy, Snyk, Dependabot |
| **Secret Scanning** | Detect leaked credentials | Pre-commit + CI | Gitleaks, TruffleHog |
| **Container Scanning** | Image vulnerabilities | Build + registry | Trivy, Clair, Grype |

### Complete Pipeline Integration

```yaml
# GitHub Actions security workflow
name: Security Scan
on: [push, pull_request]

jobs:
  sast:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: github/codeql-action/init@v3
      with:
        languages: javascript, python
    - uses: github/codeql-action/analyze@v3

  sca:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Run Trivy SCA
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        severity: 'CRITICAL,HIGH'

  secrets:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0  # Full history
    - uses: gitleaks/gitleaks-action@v2

  container:
    runs-on: ubuntu-latest
    steps:
    - name: Build image
      run: docker build -t myapp:${{ github.sha }} .
    - name: Scan image
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: myapp:${{ github.sha }}
        severity: 'CRITICAL,HIGH'
        exit-code: 1  # Fail on vulnerabilities
```

### Runtime Security (Falco)

```yaml
# Detect suspicious container activity
- rule: Shell in Container
  desc: Unexpected shell execution in container
  condition: >
    spawned_process and
    container and
    proc.name in (bash, sh, zsh)
  output: >
    Shell spawned in container
    (user=%user.name container=%container.name
    command=%proc.cmdline)
  priority: WARNING
```

---

## Metrics and Observability

### DORA Metrics (2025 Benchmarks)

| Metric | Elite | High | Medium | Low |
|--------|-------|------|--------|-----|
| **Deployment Frequency** | Multiple/day | Weekly | Monthly | Less than monthly |
| **Lead Time for Changes** | < 1 hour | < 1 day | 1 week | > 6 months |
| **Mean Time to Recovery** | < 1 hour | < 1 day | < 1 week | > 6 months |
| **Change Failure Rate** | 0-15% | 16-30% | 31-45% | > 45% |

### Key Metrics to Track

```yaml
# Deployment metrics
deployment.frequency: counter
deployment.duration: histogram
deployment.rollback: counter

# Pipeline metrics
pipeline.success_rate: gauge
pipeline.duration: histogram
pipeline.queue_time: histogram

# Feature flag metrics
feature_flag.evaluation: counter
feature_flag.enabled_users: gauge
feature_flag.error_rate: gauge (by flag)

# Resource metrics
pod.cpu_usage: gauge
pod.memory_usage: gauge
pod.restart_count: counter
```

---

## Checklist

```markdown
## CI/CD Pipeline
- [ ] Short-lived credentials (OIDC, not static keys)
- [ ] Protected branches for production
- [ ] Parallel jobs for speed
- [ ] Dependency caching configured
- [ ] Build completes in < 10 minutes
- [ ] Security scanning (SAST, SCA, secrets)

## Containers
- [ ] Multi-stage Dockerfile
- [ ] Non-root user (UID > 1000)
- [ ] Minimal base image (alpine/distroless)
- [ ] .dockerignore configured
- [ ] Image scanning in CI
- [ ] Resource limits defined

## Kubernetes
- [ ] Resource requests/limits set
- [ ] Liveness and readiness probes
- [ ] Security context (runAsNonRoot)
- [ ] Network policies defined
- [ ] ConfigMaps/Secrets for config
- [ ] Deployment strategy chosen
- [ ] Image pull policy configured

## Infrastructure as Code
- [ ] Remote state with locking
- [ ] Modular architecture
- [ ] Policy as Code enforcement
- [ ] Automated tests (Terratest/Pulumi tests)
- [ ] Version pinning for providers
- [ ] Environment parity

## Deployments
- [ ] Deployment strategy selected
- [ ] Rollback plan documented
- [ ] Feature flags for large changes
- [ ] Gradual rollout configured
- [ ] Metrics tied to deployments
- [ ] Automated rollback on errors

## Security
- [ ] SAST in pipeline
- [ ] SCA for dependencies
- [ ] Secret scanning enabled
- [ ] Container vulnerability scanning
- [ ] Runtime security monitoring
- [ ] Supply chain security (signed images)

## Observability
- [ ] Deployment frequency tracked
- [ ] Lead time measured
- [ ] MTTR tracked
- [ ] Change failure rate monitored
- [ ] Feature flag metrics
- [ ] Resource utilization dashboards
```

---

## See Also

- [reference/cicd.md](reference/cicd.md) — CI/CD pipeline patterns and examples
- [reference/containers.md](reference/containers.md) — Docker and Kubernetes deep dive
- [reference/release-strategies.md](reference/release-strategies.md) — Deployment patterns comparison
- [templates/github-actions.yaml](templates/github-actions.yaml) — Production-ready workflow
- [templates/Dockerfile](templates/Dockerfile) — Secure multi-stage Dockerfile
