<div align="center">
  <h1>Claude Arsenal</h1>
  <p><strong>74 个生产级 Skills | 7 个专业 Agents | 一键安装</strong></p>

  <p>最全面的 Claude Code 技能库</p>

  <p>
    <a href="https://github.com/majiayu000/claude-arsenal/stargazers"><img src="https://img.shields.io/github/stars/majiayu000/claude-arsenal?style=flat-square&logo=github" alt="Stars"></a>
    <a href="https://github.com/majiayu000/claude-arsenal/blob/main/LICENSE"><img src="https://img.shields.io/github/license/majiayu000/claude-arsenal?style=flat-square" alt="License"></a>
    <img src="https://img.shields.io/badge/skills-74-blue?style=flat-square" alt="Skills">
    <img src="https://img.shields.io/badge/agents-7-green?style=flat-square" alt="Agents">
  </p>

  <p>
    <a href="#快速开始">快速开始</a> •
    <a href="#技能列表">技能列表</a> •
    <a href="#智能体">智能体</a> •
    <a href="#贡献">贡献</a> •
    <a href="./README.md">English</a>
  </p>
</div>

---

## 快速开始

### 一键安装（所有技能）

```bash
curl -fsSL https://raw.githubusercontent.com/majiayu000/claude-arsenal/main/install.sh | bash
```

### 手动安装（选择性）

```bash
# 克隆仓库
git clone https://github.com/majiayu000/claude-arsenal.git
cd claude-arsenal

# 安装特定技能
./install.sh --skills typescript-project,python-project,devops-excellence

# 或安装全部
./install.sh --all
```

### 验证安装

在 Claude Code 中输入 `/` 查看已安装的技能。

---

## 技能列表

> 完整的自动生成清单位于 [Skill Registry](./docs/skill-registry.md)。

### 开发架构

使用语言特定的最佳实践构建生产级项目。

| 技能 | 语言 | 核心特性 |
|------|------|----------|
| [`typescript-project`](./skills/typescript-project/) | TypeScript | ESM、Zod、Biome、整洁架构 |
| [`python-project`](./skills/python-project/) | Python | uv、Pydantic、Ruff、FastAPI |
| [`rust-project`](./skills/rust-project/) | Rust | Cargo 工作区、错误处理、异步 |
| [`golang-web`](./skills/golang-web/) | Go | Chi/Echo、sqlc、结构化日志 |
| [`zig-project`](./skills/zig-project/) | Zig | 构建系统、内存管理 |

### 产品全生命周期

从发现到部署的端到端产品开发。

| 技能 | 阶段 | 能力 |
|------|------|------|
| [`product-discovery`](./skills/product-discovery/) | 发现 | JTBD、用户访谈、市场研究 |
| [`prd-master`](./skills/prd-master/) | 定义 | PRD 编写、用户故事、RICE 优先级 |
| [`technical-spec`](./skills/technical-spec/) | 设计 | 设计文档、ADR、C4 图 |
| [`product-analytics`](./skills/product-analytics/) | 增长 | 事件追踪、A/B 测试、AARRR |
| [`devops-excellence`](./skills/devops-excellence/) | 部署 | CI/CD、Docker、Kubernetes、GitOps |
| [`observability-sre`](./skills/observability-sre/) | 运维 | 监控、日志、追踪、SLO/SLI |

### API 与后端

| 技能 | 描述 |
|------|------|
| [`api-design`](./skills/api-design/) | REST/GraphQL/gRPC 模式，OpenAPI 3.2 |
| [`auth-security`](./skills/auth-security/) | OAuth 2.1、JWT、安全最佳实践 |
| [`database-patterns`](./skills/database-patterns/) | PostgreSQL、Redis、迁移、优化 |
| [`codebase-audit`](./skills/codebase-audit/) | 自适应深度代码库审计，输出按严重度排序的问题与修复路线图 |

### 开发实践

| 技能 | 描述 | 来源 |
|------|------|------|
| [`contributor`](./skills/contributor/) | 从 Issue 扫描到 PR 提交的端到端开源贡献工作流 | 自研 |
| [`strategic-compact`](./skills/strategic-compact/) | 在逻辑边界压缩上下文，保留关键决策与约束 | 自研 |
| [`skill-creator`](./skills/skill-creator/) | 创建、优化并评估可复用 skill | 自研 |
| [`codex-agent`](./skills/codex-agent/) | 通过 Codex CLI 做代码审查、交叉验证和替代实现 | 自研 |
| [`humanizer`](./skills/humanizer/) | 消除明显 AI 痕迹，让文本更自然可读 | 外部指南 + 自研整理 |

### UI/UX 与设计

| 技能 | 描述 |
|------|------|
| [`app-ui-design`](./skills/app-ui-design/) | iOS/Android UI 设计，Material Design 3，HIG |
| [`product-ux-expert`](./skills/product-ux-expert/) | UX 评估、启发式、可访问性 |
| [`frontend-design`](./skills/frontend-design/) | Web 前端设计模式 |
| [`ui-designer`](./skills/ui-designer.SKILL.md) | 从 UI 截图和参考图提取设计系统 |
| [`ui-design-system`](./skills/ui-design-system/) | 设计系统工具包与设计交付支持 |
| [`web-artifacts-builder`](./skills/web-artifacts-builder/) | Claude.ai HTML 组件 |
| [`react-best-practices`](./skills/react-best-practices/) | 基于 Vercel 指南整理的 React / Next.js 性能实践 |
| [`react-hooks-best-practices`](./skills/react-hooks-best-practices/) | React hooks、effects、refs 与组件设计模式 |
| [`slides`](./skills/slides/) | 口播视频背景和演示用幻灯片生成 |
| [`ui-ux-pro-max`](./skills/ui-ux-pro-max/) | 50+ 风格、97 配色、57 字体配对、9 技术栈 |

### 工具与自动化

| 技能 | 描述 |
|------|------|
| [`web-asset-generator`](./skills/web-asset-generator/) | Favicon、应用图标、OG 图片 |
| [`github-trending`](./skills/github-trending/) | GitHub 趋势分析 |
| [`auto-optimize`](./skills/auto-optimize/) | 自主代码库优化，维度轮换扫描 |
| [`fixflow`](./skills/fixflow/) | 严格的规划-实现-测试-提交交付工作流 |
| [`optflow`](./skills/optflow/) | 优化机会发现与逐步交付工作流，强调持续验证 |
| [`plan-flow`](./skills/plan-flow/) | 仓库级冗余分析与 step-test-update 执行计划 |
| [`vibeguard`](./skills/vibeguard/) | 任务契约、问题评分与轻量防幻觉复盘 |
| [`clash-doctor`](./skills/clash-doctor/) | Clash 代理与网络诊断 |
| [`clash-routes`](./skills/clash-routes/) | 通过 Mihomo API 查看指定进程的代理线路 |
| [`optimize-network`](./skills/optimize-network/) | 带 VPN/代理保护的本地网络速度、延迟、DNS、Wi-Fi 与 bufferbloat 安全诊断 |
| [`disk-cleaner`](./skills/disk-cleaner/) | 扫描磁盘占用并交互式清理可安全删除的内容 |
| [`system-doctor`](./skills/system-doctor/) | 诊断 CPU、内存和进程级系统卡顿问题 |
| [`server-deploy`](./skills/server-deploy/) | 将 Node、Python、Rust、Go 或静态站部署到远程服务器 |
| [`server-security`](./skills/server-security/) | 审计并加固 Linux 服务器的 SSH、防火墙与暴露服务 |
| [`claude-mem`](./skills/claude-mem/) | 编排器驱动的计划与执行 |

### 内容与社交媒体

| 技能 | 描述 |
|------|------|
| [`xiaohongshu`](./skills/xiaohongshu/) | 小红书内容创作与发布 |
| [`trip-planner`](./skills/trip-planner/) | 旅行行程规划 |

### 移动端与跨平台

| 技能 | 描述 |
|------|------|
| [`harmonyos-app`](./skills/harmonyos-app/) | 鸿蒙应用开发：ArkTS、ArkUI、Stage 模型 |

### Rust 专项

| 技能 | 描述 |
|------|------|
| [`rust-best-practices`](./skills/rust-best-practices/) | 微软 Rust 指南、错误处理 |

---

## 智能体

专业智能体处理复杂任务。

| 智能体 | 专长 | 使用场景 |
|--------|------|----------|
| [`tech-lead-orchestrator`](./agents/tech-lead-orchestrator.md) | 协调 | 多步骤任务、任务委派 |
| [`code-archaeologist`](./agents/code-archaeologist.md) | 探索 | 遗留代码库文档化 |
| [`backend-typescript-architect`](./agents/backend-typescript-architect.md) | 架构 | Bun/Node.js、API 设计 |
| [`senior-code-reviewer`](./agents/senior-code-reviewer.md) | 审查 | 安全、性能、架构 |
| [`kubernetes-specialist`](./agents/kubernetes-specialist.md) | 基础设施 | K8s、Helm、GitOps |
| [`security-auditor`](./agents/security-auditor.md) | 安全 | OWASP Top 10、SAST |
| [`opensource-contributor`](./agents/opensource-contributor.md) | 贡献 | 开源工作流 |

---

## 技能设计理念

Claude Arsenal 中的每个技能都遵循以下原则：

1. **硬性规则** - 使用 `FORBIDDEN` / `REQUIRED` 标记的强制约束
2. **实用示例** - 真实代码，而非纯理论
3. **验证清单** - 可操作的验证步骤
4. **实战检验** - 在生产环境中使用过

---

## 文档

| 文档 | 描述 |
|------|------|
| [安装指南](./docs/installation.md) | 详细的安装说明 |
| [技能测试指南](./docs/skill-testing-guide.md) | 如何验证技能是否生效 |
| [创建插件](./docs/creating-plugins.md) | 构建你自己的技能 |
| [产品生命周期（英文）](./docs/product-lifecycle-skills-en.md) | 完整生命周期覆盖 |
| [产品生命周期（中文）](./docs/product-lifecycle-skills-zh.md) | 产品生命周期覆盖 |

---

## 致谢

站在巨人的肩膀上：

- [anthropics/skills](https://github.com/anthropics/skills) - Anthropic 官方技能
- [obra/superpowers](https://github.com/obra/superpowers) - 开发方法论
- [claude-code-plugins-plus](https://github.com/jeremylongshore/claude-code-plugins-plus) - 插件中心
- [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) - 智能体集合

---

## 贡献

欢迎贡献！请先阅读我们的[贡献指南](./CONTRIBUTING.md)。

- 发现 Bug？[提交 Issue](https://github.com/majiayu000/claude-arsenal/issues)
- 有技能想法？[发起讨论](https://github.com/majiayu000/claude-arsenal/discussions)
- 想要贡献？[提交 PR](https://github.com/majiayu000/claude-arsenal/pulls)

---

## 许可证

[MIT 许可证](./LICENSE) - 可在你的项目中自由使用。

---

<div align="center">
  <p>如果对你有帮助，考虑给个 ⭐</p>
  <p>为 Claude Code 社区用心打造 ❤️</p>
</div>
