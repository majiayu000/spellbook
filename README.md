<div align="center">
  <h1>Claude Arsenal</h1>
  <p><strong>74 Production-Ready Skills | 7 Specialized Agents | One Command Install</strong></p>

  <p>The most comprehensive skill library for Claude Code</p>

  <p>
    <a href="https://github.com/majiayu000/claude-arsenal/stargazers"><img src="https://img.shields.io/github/stars/majiayu000/claude-arsenal?style=flat-square&logo=github" alt="Stars"></a>
    <a href="https://github.com/majiayu000/claude-arsenal/blob/main/LICENSE"><img src="https://img.shields.io/github/license/majiayu000/claude-arsenal?style=flat-square" alt="License"></a>
    <img src="https://img.shields.io/badge/skills-74-blue?style=flat-square" alt="Skills">
    <img src="https://img.shields.io/badge/agents-7-green?style=flat-square" alt="Agents">
  </p>

  <p>
    <a href="#quick-start">Quick Start</a> •
    <a href="#skills">Skills</a> •
    <a href="#agents">Agents</a> •
    <a href="#contributing">Contributing</a> •
    <a href="./README_CN.md">中文</a>
  </p>
</div>

---

## Quick Start

### One-Line Install (All Skills)

```bash
curl -fsSL https://raw.githubusercontent.com/majiayu000/claude-arsenal/main/install.sh | bash
```

### Manual Install (Selective)

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

## Skills

> The generated full skill inventory lives in [Skill Registry](./docs/skill-registry.md).

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
