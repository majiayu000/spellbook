<div align="center">
  <h1>Claude Arsenal</h1>
  <p><strong>75 Production-Ready Skills | 7 Specialized Agents | One Command Install | Validated Registry</strong></p>

  <p>An opinionated Claude Code skill pack for real engineering work: debugging, code review, frontend design, DevOps, product specs, deployment, and AI-agent workflows.</p>

  <p>
    <a href="https://github.com/majiayu000/claude-arsenal/stargazers"><img src="https://img.shields.io/github/stars/majiayu000/claude-arsenal?style=flat-square&logo=github" alt="Stars"></a>
    <a href="https://github.com/majiayu000/claude-arsenal/blob/main/LICENSE"><img src="https://img.shields.io/github/license/majiayu000/claude-arsenal?style=flat-square" alt="License"></a>
    <img src="https://img.shields.io/badge/skills-75-blue?style=flat-square" alt="Skills">
    <img src="https://img.shields.io/badge/agents-7-green?style=flat-square" alt="Agents">
    <img src="https://img.shields.io/badge/registry-validated-brightgreen?style=flat-square" alt="Registry validated">
  </p>

  <p>
    <a href="#quick-start">Quick Start</a> •
    <a href="#pick-a-workflow">Pick a Workflow</a> •
    <a href="#skills">Skills</a> •
    <a href="#agents">Agents</a> •
    <a href="#contributing">Contributing</a> •
    <a href="./README_CN.md">中文</a>
  </p>
</div>

---

## Quick Start

### Marketplace Install

```bash
npx skills add majiayu000/claude-arsenal
```

### One-Line Install

```bash
curl -fsSL https://raw.githubusercontent.com/majiayu000/claude-arsenal/main/install.sh | bash
```

### Selective Install

```bash
# Clone the repository
git clone https://github.com/majiayu000/claude-arsenal.git
cd claude-arsenal

# Install specific skills
./install.sh --skills typescript-project,python-project,devops-excellence

# Or install everything
./install.sh --all
```

### Verify Installation

In Claude Code, type `/` to see your installed skills.

---

## Pick a Workflow

Start with a small bundle that matches the job, then add more skills when the workflow sticks.

| Workflow | Install | Good for |
|---|---|---|
| Frontend and UI | `./install.sh --skills frontend-design,app-ui-design,ui-design-system,figma-to-react` | Product UI, landing pages, design systems, Figma handoff |
| Code quality | `./install.sh --skills codebase-audit,fixflow,optflow,systematic-debugging` | Audits, bug fixes, refactors, root-cause debugging |
| Ops and deploy | `./install.sh --skills server-deploy,server-security,clash-doctor,system-doctor` | Shipping apps, hardening servers, diagnosing local and network issues |
| Product and docs | `./install.sh --skills product-discovery,prd-master,technical-spec,product-analytics` | Discovery, PRDs, technical specs, metrics plans |
| Agent workflows | `./install.sh --skills codex-agent,multi-ai-research,strategic-compact,vibeguard` | Cross-review, multi-AI research, context handoff, anti-hallucination checks |

High-signal individual skills to try first: `github-trending`, `harmonyos-app`, `app-ui-design`, `product-discovery`, `xiaohongshu`, `codebase-audit`, and `server-deploy`.

See [Showcase](./docs/showcase.md) for copy-paste prompts and expected outputs.

---

## Why Claude Arsenal

- **Validated registry**: every installable skill is checked by `python3 scripts/validate_skills.py --check`.
- **Progressive disclosure**: larger skills use `references/`, `templates/`, `scripts/`, and support files instead of one giant prompt.
- **Practical coverage**: engineering, operations, product, UI, content, and agent workflows live in one catalog.
- **Bilingual coverage**: English and Chinese workflows are both represented in the registry.

---

## Skills

> The generated full skill inventory lives in [Skill Registry](./docs/skill-registry.md).
> Skill layout rules live in [Skill Format Policy](./docs/skill-format-policy.md).

### Search the Registry

```bash
# Free-text query (AND semantics across name, description, category, tags)
python3 scripts/validate_skills.py search rust testing

# Filter by tag
python3 scripts/validate_skills.py search --tag agent

# Restrict to a description language
python3 scripts/validate_skills.py search --language zh deploy

# Machine-readable output
python3 scripts/validate_skills.py search --tag react --json
```

The tag index lives in [`registry/tags.json`](./registry/tags.json) for tooling and dashboards. Curated overrides for skills the keyword heuristic cannot infer live in [`registry/tag_overrides.yml`](./registry/tag_overrides.yml).

### Development Architecture

Build production-ready projects with language-specific best practices.

| Skill | Language | Key Features |
|-------|----------|--------------|
| [`typescript-project`](./skills/typescript-project/) | TypeScript | ESM, Zod, Biome, Clean Architecture |
| [`python-project`](./skills/python-project/) | Python | uv, Pydantic, Ruff, FastAPI |
| [`rust-project`](./skills/rust-project/) | Rust | Cargo workspace, error handling, async |
| [`golang-web`](./skills/golang-web/) | Go | Chi/Echo, sqlc, structured logging |
| [`zig-project`](./skills/zig-project/) | Zig | Build system, memory management |

### Product Lifecycle

End-to-end product development from discovery to deployment.

| Skill | Phase | What You Get |
|-------|-------|--------------|
| [`product-discovery`](./skills/product-discovery/) | Discovery | JTBD, user interviews, market research |
| [`prd-master`](./skills/prd-master/) | Definition | PRD writing, user stories, RICE prioritization |
| [`technical-spec`](./skills/technical-spec/) | Design | Design docs, ADR, C4 diagrams |
| [`product-analytics`](./skills/product-analytics/) | Growth | Event tracking, A/B testing, AARRR |
| [`devops-excellence`](./skills/devops-excellence/) | Deployment | CI/CD, Docker, Kubernetes, GitOps |
| [`observability-sre`](./skills/observability-sre/) | Operations | Monitoring, logging, tracing, SLO/SLI |

### API & Backend

| Skill | Description |
|-------|-------------|
| [`api-design`](./skills/api-design/) | REST/GraphQL/gRPC patterns, OpenAPI 3.2 |
| [`auth-security`](./skills/auth-security/) | OAuth 2.1, JWT, security best practices |
| [`database-patterns`](./skills/database-patterns/) | PostgreSQL, Redis, migrations, optimization |
| [`codebase-audit`](./skills/codebase-audit/) | Deep adaptive repository audit with severity-ranked findings and repair roadmap |

### Development Practices

| Skill | Description | Origin |
|-------|-------------|--------|
| [`contributor`](./skills/contributor/) | End-to-end open source contribution workflow from issue discovery to PR submission | Custom |
| [`strategic-compact`](./skills/strategic-compact/) | Compress context at logical boundaries while preserving decisions and constraints | Custom |
| [`skill-creator`](./skills/skill-creator/) | Create, improve, and benchmark reusable skills | Custom |
| [`codex-agent`](./skills/codex-agent/) | Code review, cross-verification, and alternative implementations through Codex CLI | Custom |
| [`humanizer`](./skills/humanizer/) | Remove obvious AI writing patterns from user-facing text | External guide + custom adaptation |

### UI/UX & Design

| Skill | Description |
|-------|-------------|
| [`app-ui-design`](./skills/app-ui-design/) | iOS/Android UI design, Material Design 3, HIG |
| [`product-ux-expert`](./skills/product-ux-expert/) | UX evaluation, heuristics, accessibility |
| [`frontend-design`](./skills/frontend-design/) | Web frontend design patterns |
| [`ui-designer`](./skills/ui-designer.SKILL.md) | Extract design systems from UI screenshots and references |
| [`ui-design-system`](./skills/ui-design-system/) | Design system toolkit and design-dev handoff support |
| [`web-artifacts-builder`](./skills/web-artifacts-builder/) | Claude.ai HTML artifacts |
| [`react-best-practices`](./skills/react-best-practices/) | React and Next.js performance patterns distilled from Vercel guidance |
| [`react-hooks-best-practices`](./skills/react-hooks-best-practices/) | React hooks, effects, refs, and component design patterns |
| [`slides`](./skills/slides/) | Speech-friendly slide deck and background slide generation |
| [`ui-ux-pro-max`](./skills/ui-ux-pro-max/) | 50+ styles, 97 palettes, 57 font pairings, 9 stacks |

### Tooling & Automation

| Skill | Description |
|-------|-------------|
| [`web-asset-generator`](./skills/web-asset-generator/) | Favicons, app icons, OG images |
| [`github-trending`](./skills/github-trending/) | GitHub trending analysis |
| [`auto-optimize`](./skills/auto-optimize/) | Autonomous codebase optimization with dimension rotation |
| [`fixflow`](./skills/fixflow/) | Strict plan-implement-test-commit workflow for delivery tasks |
| [`optflow`](./skills/optflow/) | Optimization discovery and execution workflow with continuous validation |
| [`plan-flow`](./skills/plan-flow/) | Repository-level redundancy analysis with step-test-update planning |
| [`vibeguard`](./skills/vibeguard/) | Task contracts, finding scoring, and lightweight anti-hallucination reviews |
| [`clash-doctor`](./skills/clash-doctor/) | Clash proxy & network diagnostics |
| [`clash-routes`](./skills/clash-routes/) | Inspect active proxy routes for specific processes via Mihomo API |
| [`optimize-network`](./skills/optimize-network/) | Safe local network speed, latency, DNS, Wi-Fi, and bufferbloat diagnostics with VPN/proxy guardrails |
| [`disk-cleaner`](./skills/disk-cleaner/) | Scan and reclaim disk space with interactive cleanup guidance |
| [`system-doctor`](./skills/system-doctor/) | Diagnose CPU, memory, and process-level system slowdowns |
| [`server-deploy`](./skills/server-deploy/) | Deploy Node, Python, Rust, Go, or static projects to remote servers |
| [`server-security`](./skills/server-security/) | Audit and harden Linux server SSH, firewall, and exposed services |
| [`cliproxy-deploy`](./skills/cliproxy-deploy/) | Deploy router-for-me/CLIProxyAPI on a Linux VPS, exposing Codex/Claude/Gemini OAuth subscription accounts as an OpenAI-compatible API |
| [`cliproxy-newapi-stack`](./skills/cliproxy-newapi-stack/) | Layer NewAPI metering on top of CLIProxyAPI: Docker deploy, ratio-based pricing, quota top-up, dual-path verification, and OAuth account hot-swap |
| [`claude-mem`](./skills/claude-mem/) | Orchestrator-driven planning & execution |

### Content & Social Media

| Skill | Description |
|-------|-------------|
| [`xiaohongshu`](./skills/xiaohongshu/) | Xiaohongshu content creation & publishing |
| [`trip-planner`](./skills/trip-planner/) | Travel itinerary planning |

### Mobile & Cross-Platform

| Skill | Description |
|-------|-------------|
| [`harmonyos-app`](./skills/harmonyos-app/) | HarmonyOS with ArkTS, ArkUI, Stage Model |

### Rust Specific

| Skill | Description |
|-------|-------------|
| [`rust-best-practices`](./skills/rust-best-practices/) | Microsoft Rust guidelines, error handling |

---

## Agents

Specialized agents for complex tasks.

| Agent | Expertise | Use Case |
|-------|-----------|----------|
| [`tech-lead-orchestrator`](./agents/tech-lead-orchestrator.md) | Coordination | Multi-step tasks, delegation |
| [`code-archaeologist`](./agents/code-archaeologist.md) | Exploration | Legacy codebase documentation |
| [`backend-typescript-architect`](./agents/backend-typescript-architect.md) | Architecture | Bun/Node.js, API design |
| [`senior-code-reviewer`](./agents/senior-code-reviewer.md) | Review | Security, performance, architecture |
| [`kubernetes-specialist`](./agents/kubernetes-specialist.md) | Infrastructure | K8s, Helm, GitOps |
| [`security-auditor`](./agents/security-auditor.md) | Security | OWASP Top 10, SAST |
| [`opensource-contributor`](./agents/opensource-contributor.md) | Contribution | Open source workflow |

---

## Skill Design Philosophy

Every skill in Claude Arsenal follows these principles:

1. **Hard Rules** - Mandatory constraints with `FORBIDDEN` / `REQUIRED` markers
2. **Practical Examples** - Real code, not just theory
3. **Verification Checklists** - Actionable validation steps
4. **Battle-Tested** - Used in production environments

---

## Documentation

| Document | Description |
|----------|-------------|
| [Installation Guide](./docs/installation.md) | Detailed setup instructions |
| [Showcase](./docs/showcase.md) | Copy-paste workflow demos |
| [Skill Format Policy](./docs/skill-format-policy.md) | Directory vs file skill layout rules |
| [Skill Testing Guide](./docs/skill-testing-guide.md) | How to validate skills work |
| [Creating Plugins](./docs/creating-plugins.md) | Build your own skills |
| [Product Lifecycle (EN)](./docs/product-lifecycle-skills-en.md) | Full lifecycle coverage |
| [Product Lifecycle (中文)](./docs/product-lifecycle-skills-zh.md) | 产品生命周期覆盖 |

---

## Credits

Built on the shoulders of giants:

- [anthropics/skills](https://github.com/anthropics/skills) - Official Anthropic skills
- [obra/superpowers](https://github.com/obra/superpowers) - Development methodology
- [claude-code-plugins-plus](https://github.com/jeremylongshore/claude-code-plugins-plus) - Plugin hub
- [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) - Agent collection

---

## Contributing

Contributions welcome! Please read our [Contributing Guide](./CONTRIBUTING.md) first.

- Found a bug? [Open an issue](https://github.com/majiayu000/claude-arsenal/issues)
- Have a skill idea? [Start a discussion](https://github.com/majiayu000/claude-arsenal/discussions)
- Want to contribute? [Submit a PR](https://github.com/majiayu000/claude-arsenal/pulls)

---

## License

[MIT License](./LICENSE) - Use freely in your projects.

---

<div align="center">
  <p>If this helps you, consider giving it a ⭐</p>
  <p>Made with ❤️ for the Claude Code community</p>
</div>
