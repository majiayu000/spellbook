<div align="center">
  <h1>Spellbook</h1>
  <p><strong>86 Cross-Runtime Skills | 7 Claude Code Agents | One Command Install</strong></p>

  <p>A cross-runtime skill library for Claude Code, Codex, and multi-agent workflows.</p>

  <p>
    <a href="https://github.com/majiayu000/spellbook/stargazers"><img src="https://img.shields.io/github/stars/majiayu000/spellbook?style=flat-square&logo=github" alt="Stars"></a>
    <a href="https://github.com/majiayu000/spellbook/blob/main/LICENSE"><img src="https://img.shields.io/github/license/majiayu000/spellbook?style=flat-square" alt="License"></a>
    <img src="https://img.shields.io/badge/skills-86-blue?style=flat-square" alt="Skills">
    <img src="https://img.shields.io/badge/agents-7-green?style=flat-square" alt="Agents">
  </p>

  <p>
    <a href="#quick-start">Quick Start</a> •
    <a href="#runtime-targets">Runtime Targets</a> •
    <a href="#pick-a-workflow">Pick a Workflow</a> •
    <a href="#skills">Skills</a> •
    <a href="#agents">Agents</a> •
    <a href="./CHANGELOG.md">Changelog</a> •
    <a href="#release-status">Release Status</a> •
    <a href="#contributing">Contributing</a> •
    <a href="./README_CN.md">中文</a>
  </p>
</div>

---

> **Rename notice:** Spellbook was formerly **Claude Arsenal**. Claude Code remains a first-class target; the new name reflects the broader roadmap for Claude Code, Codex, and cross-runtime agent skills. See the [migration note](./docs/migration-from-claude-arsenal.md) for details.

---

## Quick Start

### One-Line Install (All Skills)

```bash
curl -fsSL https://raw.githubusercontent.com/majiayu000/spellbook/main/install.sh | bash -s -- --target all
```

### Manual Install (Selective)

```bash
# Clone the repository
git clone https://github.com/majiayu000/spellbook.git
cd spellbook

# Install specific skills for Claude Code and Codex
./install.sh --target all --skills typescript-project,python-project,devops-excellence

# Or install everything for one runtime
./install.sh --target claude --all
./install.sh --target codex --all
```

### Verify Installation

- Claude Code: type `/` to see your installed skills.
- Codex: restart Codex so it reloads `~/.agents/skills`.

---

## Runtime Targets

Spellbook keeps the skill source in one place and installs it into the runtime you use.

| Target | Installed To | Status |
|--------|--------------|--------|
| Claude Code | `~/.claude/skills` plus `~/.claude/agents` | Skills and agents supported |
| Codex | `~/.agents/skills` | Skills supported; agents skipped |
| All | Both Claude Code and Codex paths | Recommended for multi-tool users |

Claude Code remains a first-class target and search entry. The project was formerly known as Claude Arsenal; the new Spellbook name reflects the broader goal: reusable skills that can travel across coding agents.
Older Spellbook versions installed Codex skills under `~/.codex/skills`; reinstall with the current installer to use the documented Codex user-level skill path.

---

## Pick a Workflow

Start with a small bundle that matches the job, then add more skills when the workflow sticks.

| Workflow | Install | Good for |
|---|---|---|
| Frontend and UI | `./install.sh --target all --skills frontend-design,app-ui-design,ui-design-system,figma-to-react` | Product UI, landing pages, design systems, Figma handoff |
| Code quality | `./install.sh --target all --skills codebase-audit,fixflow,optflow,systematic-debugging` | Audits, bug fixes, refactors, root-cause debugging |
| Ops and deploy | `./install.sh --target all --skills server-deploy,server-security,clash-doctor,system-doctor` | Shipping apps, hardening servers, diagnosing local and network issues |
| Product and docs | `./install.sh --target all --skills product-discovery,prd-master,technical-spec,product-analytics` | Discovery, PRDs, technical specs, metrics plans |
| Agent workflows | `./install.sh --target all --skills codex-agent,multi-ai-research,strategic-compact,vibeguard` | Cross-review, multi-AI research, context handoff, anti-hallucination checks |

High-signal individual skills to try first: `github-trending`, `harmonyos-app`, `app-ui-design`, `product-discovery`, `xiaohongshu`, `codebase-audit`, and `server-deploy`.

See [Showcase](./docs/showcase.md) for copy-paste prompts and expected outputs.
Release history lives in [Changelog](./CHANGELOG.md).

---

## Why Spellbook

- **Cross-runtime install**: one source tree can install into Claude Code and Codex.
- **Validated registry**: every installable skill is checked by `python3 scripts/validate_skills.py --check`.
- **Progressive disclosure**: larger skills use `references/`, `templates/`, `scripts/`, and eval files instead of one giant prompt.
- **Practical coverage**: engineering, operations, product, UI, content, and agent workflows live in one catalog.

---

## Skills

> The generated full skill inventory lives in [Skill Registry](./docs/skill-registry.md).
> Skill layout rules live in [Skill Format Policy](./docs/skill-format-policy.md).
> Skill authoring quality rules live in [Skill Quality Playbook](./docs/skill-quality-playbook.md).

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

Audit non-blocking skill quality signals:

```bash
python3 scripts/audit_skill_quality.py
python3 scripts/audit_skill_quality.py skill-creator
```

### AI & Agent Workflow

Skills for orchestrating, guarding, and maintaining AI agent workflows — the core of Spellbook's cross-runtime mission.

| Skill | Description |
|-------|-------------|
| [`multi-model-orchestrator`](./skills/multi-model-orchestrator/) | Coordinate multi-agent tasks via a centralized handoff document |
| [`flowguard`](./skills/flowguard/) | Guard long, ambiguous, or stateful agent tasks from drift |
| [`skill-audit`](./skills/skill-audit/) | Audit, design, categorize, and measure agent skills |
| [`threads`](./skills/threads/) | Codex-native subagents and parallel GitHub queue lanes |
| [`codex-fluent`](./skills/codex-fluent/) | Codex session hygiene, archive strategy, and handoff discipline |
| [`codex-retrospective`](./skills/codex-retrospective/) | Codex self-review of recent history to improve behavior |
| [`brainstorming`](./skills/brainstorming/) | Socratic dialogue for design refinement and architecture exploration |
| [`personal-arsenal-lifecycle-doctor`](./skills/personal-arsenal-lifecycle-doctor/) | Diagnose the health of personal `~/.claude/skills` |

### Development Architecture

Build production-ready projects with language-specific best practices.

| Skill | Language | Key Features |
|-------|----------|--------------|
| [`typescript-project`](./skills/typescript-project/) | TypeScript | ESM, Zod, Biome, Clean Architecture |
| [`python-project`](./skills/python-project/) | Python | uv, Pydantic, Ruff, FastAPI |
| [`rust-project`](./skills/rust-project/) | Rust | Cargo workspace, error handling, async |
| [`golang-web`](./skills/golang-web/) | Go | Chi/Echo, sqlc, structured logging |
| [`zig-project`](./skills/zig-project/) | Zig | Build system, memory management |
| [`architecture-foundation`](./skills/architecture-foundation/) | Cross-language | Runtime, state ownership, adapters, and convergence specs |
| [`elegant-architecture`](./skills/elegant-architecture/) | Cross-language | Clean architecture with strict 200-line file limits |

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
| [`product-manager-toolkit`](./skills/product-manager-toolkit/) | Definition | RICE, customer interviews, PRD templates, discovery frameworks |

### API & Backend

| Skill | Description |
|-------|-------------|
| [`api-design`](./skills/api-design/) | REST/GraphQL/gRPC patterns, OpenAPI 3.2 |
| [`auth-security`](./skills/auth-security/) | OAuth 2.1, JWT, security best practices |
| [`database-patterns`](./skills/database-patterns/) | PostgreSQL, Redis, migrations, optimization |
| [`codebase-audit`](./skills/codebase-audit/) | Deep adaptive repository audit with severity-ranked findings and repair roadmap |
| [`structured-logging`](./skills/structured-logging/) | Log architecture, standards, observability, and tracing |
| [`structured-logging-lite`](./skills/structured-logging-lite/) | Centralized logging, field standards, and distributed tracing |

### Development Practices

| Skill | Description | Origin |
|-------|-------------|--------|
| [`contributor`](./skills/contributor/) | End-to-end open source contribution workflow from issue discovery to PR submission | Custom |
| [`repo-agent-context-audit`](./skills/repo-agent-context-audit/) | Audit and scaffold repo agent context across AGENTS, skills, and specs | Custom |
| [`strategic-compact`](./skills/strategic-compact/) | Compress context at logical boundaries while preserving decisions and constraints | Custom |
| [`skill-creator`](./skills/skill-creator/) | Create, improve, and benchmark reusable skills | Custom |
| [`humanizer`](./skills/humanizer/) | Remove obvious AI writing patterns from user-facing text | External guide + custom adaptation |

### Delivery Workflow

Disciplined end-to-end delivery: testing, commits, health checks, and contribution flow.

| Skill | Description |
|-------|-------------|
| [`test-driven-development`](./skills/test-driven-development/) | Enforce RED-GREEN-REFACTOR TDD discipline |
| [`comprehensive-testing`](./skills/comprehensive-testing/) | Test pyramid, unit/integration/E2E/property testing, framework best practices |
| [`git-commit-smart`](./skills/git-commit-smart/) | Generate meaningful conventional commit messages from diff |
| [`push-all`](./skills/push-all/) | Stage, commit, and push all changes after safety checks |
| [`project-health-auditor`](./skills/project-health-auditor/) | Codebase health, tech debt, dependency, and project risk analysis |
| [`contribution-architect`](./skills/contribution-architect/) | Move from bug fixes to architectural improvements and debt discovery |

### Cross-Tool Interop

Skills for using multiple coding agents and CLI tools together.

| Skill | Description |
|-------|-------------|
| [`codex`](./skills/codex/) | Invoke Codex CLI sessions from another agent workflow |
| [`codex-agent`](./skills/codex-agent/) | Optional second-opinion review, cross-verification, and alternatives through Codex CLI |
| [`ask-opencli`](./skills/ask-opencli/) | Ask Grok or Gemini through opencli and an existing browser session |
| [`multi-ai-research`](./skills/multi-ai-research/) | Parallel research across multiple AI tools and internal agents |

### UI/UX & Design

| Skill | Description |
|-------|-------------|
| [`app-ui-design`](./skills/app-ui-design/) | iOS/Android UI design, Material Design 3, HIG |
| [`product-ux-expert`](./skills/product-ux-expert/) | UX evaluation, heuristics, accessibility |
| [`frontend-design`](./skills/frontend-design/) | Web frontend design patterns |
| [`ui-designer`](./skills/ui-designer/) | Extract design systems from UI screenshots and references |
| [`ui-design-system`](./skills/ui-design-system/) | Design system toolkit and design-dev handoff support |
| [`web-artifacts-builder`](./skills/web-artifacts-builder/) | Claude.ai HTML artifacts |
| [`react-best-practices`](./skills/react-best-practices/) | React and Next.js performance patterns distilled from Vercel guidance |
| [`react-hooks-best-practices`](./skills/react-hooks-best-practices/) | React hooks, effects, refs, and component design patterns |
| [`slides`](./skills/slides/) | Speech-friendly slide deck and background slide generation |
| [`ui-ux-pro-max`](./skills/ui-ux-pro-max/) | Compact UI/UX tables for product patterns, landing pages, charts, and 9 stacks |
| [`figma-to-code`](./skills/figma-to-code/) | Figma designs to production React/Next.js with TypeScript and Tailwind |
| [`css-debug`](./skills/css-debug/) | Diagnose CSS/layout issues, Tailwind conflicts, z-index stacking |
| [`playwright-automation`](./skills/playwright-automation/) | Browser automation and testing with Playwright |

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
| [`codex-log-guard`](./skills/codex-log-guard/) | Diagnose and mitigate excessive Codex local SQLite diagnostic log writes |
| [`server-deploy`](./skills/server-deploy/) | Deploy Node, Python, Rust, Go, or static projects to remote servers |
| [`server-security`](./skills/server-security/) | Audit and harden Linux server SSH, firewall, and exposed services |
| [`cliproxy-deploy`](./skills/cliproxy-deploy/) | Deploy router-for-me/CLIProxyAPI on a Linux VPS, exposing Codex/Claude/Gemini OAuth subscription accounts as an OpenAI-compatible API |
| [`cliproxy-newapi-stack`](./skills/cliproxy-newapi-stack/) | Layer NewAPI metering on top of CLIProxyAPI: Docker deploy, ratio-based pricing, quota top-up, dual-path verification, and OAuth account hot-swap |

### Operations & Deploy

Deploy models and diagnose local and remote environments.

| Skill | Description |
|-------|-------------|
| [`gemma4-local-deploy`](./skills/gemma4-local-deploy/) | Deploy Gemma 4 12B locally on Mac/Apple Silicon via llama.cpp or Ollama |
| [`gpu-use`](./skills/gpu-use/) | Inspect remote server GPU usage (per-card VRAM, processes, containers) |
| [`openclaw-deploy`](./skills/openclaw-deploy/) | One-click OpenClaw deployment on a remote server |
| [`rustdesk-doctor`](./skills/rustdesk-doctor/) | Diagnose RustDesk connection issues |
| [`vscode-doctor`](./skills/vscode-doctor/) | Diagnose slow or freezing VS Code-compatible editors |

### Content & Social Media

| Skill | Description |
|-------|-------------|
| [`xiaohongshu`](./skills/xiaohongshu/) | Xiaohongshu content creation & publishing |
| [`trip-planner`](./skills/trip-planner/) | Travel itinerary planning |
| [`weekly`](./skills/weekly/) | Weekly report from Git, Claude Code, and Codex sessions |
| [`xiaohongshu-netfeel-guardian`](./skills/xiaohongshu-netfeel-guardian/) | Remove translation-tone from Claude's Chinese content for native readability |

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

Every skill in Spellbook follows these principles:

1. **Hard Rules** - Mandatory constraints with `FORBIDDEN` / `REQUIRED` markers
2. **Practical Examples** - Real code, not just theory
3. **Verification Checklists** - Actionable validation steps
4. **Battle-Tested** - Used in production environments

---

## Documentation

| Document | Description |
|----------|-------------|
| [Changelog](./CHANGELOG.md) | Release history and current release status |
| [Installation Guide](./docs/installation.md) | Detailed setup instructions |
| [Runtime Targets](./docs/runtime-targets.md) | Claude Code and Codex installation targets |
| [Showcase](./docs/showcase.md) | Copy-paste workflow demos |
| [Spellbook Operating Contract](./docs/spellbook-operating-contract.md) | Agent behavior rules for autonomy, escalation, pushback, feedback loops, and done-when checks |
| [Skill Format Policy](./docs/skill-format-policy.md) | Directory vs file skill layout rules |
| [Skill Quality Playbook](./docs/skill-quality-playbook.md) | Trigger descriptions, gotchas, progressive disclosure, and verification |
| [Skill Testing Guide](./docs/skill-testing-guide.md) | How to validate skills work |
| [Creating Plugins](./docs/creating-plugins.md) | Build your own skills |
| [Product Lifecycle (EN)](./docs/product-lifecycle-skills-en.md) | Full lifecycle coverage |
| [Product Lifecycle (中文)](./docs/product-lifecycle-skills-zh.md) | 产品生命周期覆盖 |

---

## Release Status

Spellbook is in pre-1.0 release-readiness mode. No numbered GitHub release tag
has been cut yet; the current install path uses the repository `main` branch.
See [Changelog](./CHANGELOG.md) for release history.

Current limitations:

- Codex installs skills only; Claude Code agents are skipped for Codex targets.
- Some skills depend on external CLIs, accounts, credentials, or platform access
  that are not bundled by the installer.
- The registry validator checks installable skill structure, not every external
  workflow end to end.

Support paths:

- Bugs: [open an issue](https://github.com/majiayu000/spellbook/issues/new/choose)
- Feature ideas: [open a feature request](https://github.com/majiayu000/spellbook/issues/new/choose)
- Security vulnerabilities: follow [Security Policy](./SECURITY.md)

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

- Found a bug? [Open an issue](https://github.com/majiayu000/spellbook/issues)
- Have a skill idea? [Open a feature request](https://github.com/majiayu000/spellbook/issues/new/choose)
- Want to contribute? [Submit a PR](https://github.com/majiayu000/spellbook/pulls)

---

## License

[MIT License](./LICENSE) - Use freely in your projects.

---

<div align="center">
  <p>If this helps you, consider giving it a ⭐</p>
  <p>Made for builders using Claude Code, Codex, and multi-agent workflows</p>
</div>
