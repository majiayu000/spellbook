<div align="center">
  <h1>Spellbook</h1>
  <p><strong>102 个跨 Runtime Skills | 7 个 Claude Code Agents | 一键安装</strong></p>

  <p>面向 Claude Code、Codex 与多智能体工作流的跨 Runtime 技能库。</p>

  <p>
    <a href="https://github.com/majiayu000/spellbook/stargazers"><img src="https://img.shields.io/github/stars/majiayu000/spellbook?style=flat-square&logo=github" alt="Stars"></a>
    <a href="https://github.com/majiayu000/spellbook/blob/main/LICENSE"><img src="https://img.shields.io/github/license/majiayu000/spellbook?style=flat-square" alt="License"></a>
    <img src="https://img.shields.io/badge/skills-102-blue?style=flat-square" alt="Skills">
    <img src="https://img.shields.io/badge/agents-7-green?style=flat-square" alt="Agents">
  </p>

  <p>
    <a href="#快速开始">快速开始</a> •
    <a href="#runtime-目标">Runtime 目标</a> •
    <a href="#选择工作流">选择工作流</a> •
    <a href="#技能列表">技能列表</a> •
    <a href="#智能体">智能体</a> •
    <a href="./CHANGELOG.md">更新日志</a> •
    <a href="#发布状态">发布状态</a> •
    <a href="#贡献">贡献</a> •
    <a href="./README.md">English</a>
  </p>
</div>

---

> **改名说明：** Spellbook 原名 **Claude Arsenal**。Claude Code 仍是一等支持目标；新名称是为了覆盖 Claude Code、Codex 与跨 Runtime agent skills 的长期路线。详情见[迁移说明](./docs/migration-from-claude-arsenal.md)。

---

## 快速开始

### 一键安装（所有技能）

```bash
curl -fsSL https://raw.githubusercontent.com/majiayu000/spellbook/main/install.sh | bash -s -- --target all
```

### 手动安装（选择性）

```bash
# 克隆仓库
git clone https://github.com/majiayu000/spellbook.git
cd spellbook

# 为 Claude Code 和 Codex 安装特定技能
./install.sh --target all --skills typescript-project,python-project,devops-excellence

# 或为单个 Runtime 安装全部
./install.sh --target claude --all
./install.sh --target codex --all
```

### 验证安装

- Claude Code：输入 `/` 查看已安装的技能。
- Codex：重启 Codex，让它重新加载 `~/.agents/skills`。

---

## Runtime 目标

Spellbook 将 skill 源文件保存在一个地方，再安装到你实际使用的 runtime。

| 目标 | 安装位置 | 状态 |
|------|----------|------|
| Claude Code | `~/.claude/skills` 和 `~/.claude/agents` | 支持 skills 和 agents |
| Codex | `~/.agents/skills` | 支持 skills；跳过 agents |
| all | 同时安装到 Claude Code 和 Codex 路径 | 推荐给多工具用户 |

Claude Code 仍是一等支持目标，也是用户搜索和认知入口。项目原名 Claude Arsenal；改名为 Spellbook 是为了表达更长期的目标：让可复用 skills 在不同 coding agents 之间流动。
旧版 Spellbook 曾将 Codex skills 安装到 `~/.codex/skills`；请重新运行当前安装器，以使用 Codex 文档中的用户级 skill 路径。

---

## 选择工作流

先安装一个贴近当前任务的小组合，跑通后再扩展更多 skills。

| 工作流 | 安装命令 | 适合场景 |
|---|---|---|
| 前端与 UI | `./install.sh --target all --skills frontend-design,app-ui-design,ui-design-system,figma-to-react` | 产品界面、落地页、设计系统、Figma 交付 |
| 代码质量 | `./install.sh --target all --skills codebase-audit,fixflow,optflow,systematic-debugging` | 代码审计、Bug 修复、重构、根因定位 |
| 运维与部署 | `./install.sh --target all --skills server-deploy,server-security,clash-doctor,system-doctor` | 应用上线、服务器加固、本地与网络诊断 |
| 产品与文档 | `./install.sh --target all --skills product-discovery,prd-master,technical-spec,product-analytics` | 用户发现、PRD、技术方案、指标设计 |
| Agent 工作流 | `./install.sh --target all --skills codex-agent,multi-ai-research,strategic-compact,vibeguard` | 交叉审查、多 AI 调研、上下文交接、防幻觉检查 |

优先体验的高信号单项：`github-trending`、`harmonyos-app`、`app-ui-design`、`product-discovery`、`xiaohongshu`、`codebase-audit`、`server-deploy`。

可复制的试用 prompt 见 [Showcase](./docs/showcase.md)。
版本历史见 [Changelog](./CHANGELOG.md)。

---

## 为什么用 Spellbook

- **跨 Runtime 安装**：一份源文件可以安装到 Claude Code 和 Codex。
- **注册表已校验**：所有可安装 skill 都通过 `python3 scripts/validate_skills.py --check`。
- **渐进式披露**：复杂 skill 使用 `references/`、`templates/`、`scripts/` 和 eval 文件，不把所有内容塞进一个超长 prompt。
- **覆盖真实工作流**：工程、运维、产品、UI、内容和 agent 工作流在一个目录里统一管理。

---

## 技能列表

> 完整的自动生成清单位于 [Skill Registry](./docs/skill-registry.md)。
> 技能目录/单文件格式规则见 [Skill Format Policy](./docs/skill-format-policy.md)。
> Skill 编写质量规则见 [Skill Quality Playbook](./docs/skill-quality-playbook.md)。

### 检索技能

```bash
# 关键词检索（在 name / description / category / tags 中按 AND 语义匹配）
python3 scripts/validate_skills.py search rust testing

# 按标签筛选
python3 scripts/validate_skills.py search --tag agent

# 按描述语言筛选（en / zh / mixed）
python3 scripts/validate_skills.py search --language zh deploy

# 机器可读输出
python3 scripts/validate_skills.py search --tag react --json
```

标签索引位于 [`registry/tags.json`](./registry/tags.json)，可供面板/工具直接消费。无法被关键词启发式识别的标签可在 [`registry/tag_overrides.yml`](./registry/tag_overrides.yml) 中手动维护。

审计非阻断的 skill 质量信号：

```bash
python3 scripts/audit_skill_quality.py
python3 scripts/audit_skill_quality.py skill-creator
```

### AI 与 Agent 工作流

编排、守护与维护 AI agent 工作流的 skills —— Spellbook 跨 Runtime 使命的核心。

| 技能 | 描述 |
|------|------|
| [`multi-model-orchestrator`](./skills/multi-model-orchestrator/) | 通过中心化交接文档协调多 agent 任务 |
| [`flowguard`](./skills/flowguard/) | 守护长链路、模糊或有状态的 agent 任务，防止漂移 |
| [`skill-lifeguard`](./skills/skill-lifeguard/) | 为高价值 skill 增加可靠性契约、检查点、烟测钩子与漂移信号 |
| [`review-gate`](./skills/review-gate/) | 在 agent 变更落地前产出 review pack 并要求人工批准 |
| [`skill-audit`](./skills/skill-audit/) | 审计、设计、分类并度量 agent skills |
| [`threads`](./skills/threads/) | Codex 原生子 agent 与并行 GitHub 队列通道 |
| [`codex-fluent`](./skills/codex-fluent/) | Codex session 清理、归档策略与交接纪律 |
| [`codex-retrospective`](./skills/codex-retrospective/) | 让 Codex 复盘近期历史以改进行为 |
| [`brainstorming`](./skills/brainstorming/) | 通过苏格拉底式对话打磨设计与架构 |
| [`personal-arsenal-lifecycle-doctor`](./skills/personal-arsenal-lifecycle-doctor/) | 诊断个人 `~/.claude/skills` 的技能健康状态 |

参见 [`docs/agent-reliability-trio.md`](./docs/agent-reliability-trio.md) 了解 Reliable Skill + Context Engineering + Review Gate 组合流程。

### 开发架构

使用语言特定的最佳实践构建生产级项目。

| 技能 | 语言 | 核心特性 |
|------|------|----------|
| [`typescript-project`](./skills/typescript-project/) | TypeScript | ESM、Zod、Biome、整洁架构 |
| [`python-project`](./skills/python-project/) | Python | uv、Pydantic、Ruff、FastAPI |
| [`rust-project`](./skills/rust-project/) | Rust | Cargo 工作区、错误处理、异步 |
| [`golang-web`](./skills/golang-web/) | Go | Chi/Echo、sqlc、结构化日志 |
| [`zig-project`](./skills/zig-project/) | Zig | 构建系统、内存管理 |
| [`architecture-foundation`](./skills/architecture-foundation/) | 跨语言 | Runtime、状态所有权、适配器与收敛 spec |
| [`elegant-architecture`](./skills/elegant-architecture/) | 跨语言 | 整洁架构，严格的 200 行文件上限 |

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
| [`product-manager-toolkit`](./skills/product-manager-toolkit/) | 定义 | RICE、用户访谈、PRD 模板、发现框架 |

### API 与后端

| 技能 | 描述 |
|------|------|
| [`api-design`](./skills/api-design/) | REST/GraphQL/gRPC 模式，OpenAPI 3.2 |
| [`auth-security`](./skills/auth-security/) | OAuth 2.1、JWT、安全最佳实践 |
| [`database-patterns`](./skills/database-patterns/) | PostgreSQL、Redis、迁移、优化 |
| [`codebase-audit`](./skills/codebase-audit/) | 自适应深度代码库审计，输出按严重度排序的问题与修复路线图 |
| [`structured-logging`](./skills/structured-logging/) | 日志架构、标准、可观测性与链路追踪 |
| [`structured-logging-lite`](./skills/structured-logging-lite/) | 集中式日志、字段标准与分布式追踪 |

### 开发实践

| 技能 | 描述 | 来源 |
|------|------|------|
| [`contributor`](./skills/contributor/) | 从 Issue 扫描到 PR 提交的端到端开源贡献工作流 | 自研 |
| [`repo-agent-context-audit`](./skills/repo-agent-context-audit/) | 审计并搭建仓库级 agent 上下文，覆盖 AGENTS、skills 与 specs | 自研 |
| [`strategic-compact`](./skills/strategic-compact/) | 在逻辑边界压缩上下文，保留关键决策与约束 | 自研 |
| [`skill-creator`](./skills/skill-creator/) | 创建、优化并评估可复用 skill | 自研 |
| [`humanizer`](./skills/humanizer/) | 消除明显 AI 痕迹，让文本更自然可读 | 外部指南 + 自研整理 |

### 交付工作流

端到端交付纪律：测试、提交、健康检查与贡献流程。

| 技能 | 描述 |
|------|------|
| [`app-user-story-qa`](./skills/app-user-story-qa/) | 端到端应用功能盘点、单一 tracker、用户故事测试、修复与复测闭环 |
| [`test-driven-development`](./skills/test-driven-development/) | 强制 RED-GREEN-REFACTOR 的 TDD 纪律 |
| [`comprehensive-testing`](./skills/comprehensive-testing/) | 测试金字塔、单元/集成/E2E/属性测试与框架最佳实践 |
| [`git-commit-smart`](./skills/git-commit-smart/) | 基于 diff 自动生成规范的 conventional commit |
| [`push-all`](./skills/push-all/) | 安全检查后暂存、提交并推送全部改动 |
| [`project-health-auditor`](./skills/project-health-auditor/) | 代码库健康、技术债、依赖与项目风险分析 |
| [`contribution-architect`](./skills/contribution-architect/) | 从修 bug 进阶到架构改进与技术债挖掘 |

### 跨工具互操作

用于组合多个 coding agents 与 CLI 工具的 skills。

| 技能 | 描述 |
|------|------|
| [`codex`](./skills/codex/) | 在其他 agent 工作流中调用 Codex CLI session |
| [`codex-agent`](./skills/codex-agent/) | 通过 Codex CLI 做可选的二次审查、交叉验证和替代实现 |
| [`ask-opencli`](./skills/ask-opencli/) | 通过 opencli 和已有浏览器登录态询问 Grok 或 Gemini |
| [`multi-ai-research`](./skills/multi-ai-research/) | 跨多个 AI 工具和内部 agents 并行研究 |

### UI/UX 与设计

| 技能 | 描述 |
|------|------|
| [`app-ui-design`](./skills/app-ui-design/) | iOS/Android UI 设计，Material Design 3，HIG |
| [`product-ux-expert`](./skills/product-ux-expert/) | UX 评估、启发式、可访问性 |
| [`frontend-design`](./skills/frontend-design/) | Web 前端设计模式 |
| [`ui-designer`](./skills/ui-designer/) | 从 UI 截图和参考图提取设计系统 |
| [`ui-design-system`](./skills/ui-design-system/) | 设计系统工具包与设计交付支持 |
| [`web-artifacts-builder`](./skills/web-artifacts-builder/) | Claude.ai HTML 组件 |
| [`react-best-practices`](./skills/react-best-practices/) | 基于 Vercel 指南整理的 React / Next.js 性能实践 |
| [`react-hooks-best-practices`](./skills/react-hooks-best-practices/) | React hooks、effects、refs 与组件设计模式 |
| [`slides`](./skills/slides/) | 口播视频背景和演示用幻灯片生成 |
| [`ui-ux-pro-max`](./skills/ui-ux-pro-max/) | 产品模式、落地页、图表与 9 个技术栈的紧凑 UI/UX 表 |
| [`figma-to-code`](./skills/figma-to-code/) | 把 Figma 设计转成生产级 React/Next.js + TypeScript + Tailwind |
| [`css-debug`](./skills/css-debug/) | 诊断 CSS/布局问题、Tailwind 冲突、z-index 层叠 |
| [`playwright-automation`](./skills/playwright-automation/) | 用 Playwright 做浏览器自动化与测试 |

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
| [`codex-log-guard`](./skills/codex-log-guard/) | 诊断并缓解 Codex 本地 SQLite 诊断日志过量写入 |
| [`server-deploy`](./skills/server-deploy/) | 将 Node、Python、Rust、Go 或静态站部署到远程服务器 |
| [`server-security`](./skills/server-security/) | 审计并加固 Linux 服务器的 SSH、防火墙与暴露服务 |
| [`cliproxy-deploy`](./skills/cliproxy-deploy/) | 在 Linux VPS 上部署 router-for-me/CLIProxyAPI，把 Codex/Claude/Gemini OAuth 订阅账号暴露为 OpenAI 兼容 API |
| [`cliproxy-newapi-stack`](./skills/cliproxy-newapi-stack/) | 在 CLIProxyAPI 之上叠加 NewAPI 计量：Docker 部署、按比例计费、配额充值、双路径验证与 OAuth 账号热切换 |

### 运维与部署

部署模型并诊断本地与远程环境。

| 技能 | 描述 |
|------|------|
| [`gemma4-local-deploy`](./skills/gemma4-local-deploy/) | 在 Mac/Apple Silicon 上用 llama.cpp 或 Ollama 本地部署 Gemma 4 12B |
| [`gpu-use`](./skills/gpu-use/) | 查看远程服务器 GPU 用量（每张卡显存、进程、容器） |
| [`openclaw-deploy`](./skills/openclaw-deploy/) | 在远程服务器上一键部署 OpenClaw |
| [`rustdesk-doctor`](./skills/rustdesk-doctor/) | 诊断 RustDesk 连接问题 |
| [`vscode-doctor`](./skills/vscode-doctor/) | 诊断 VS Code 兼容编辑器卡顿与冻结 |

### 内容与社交媒体

| 技能 | 描述 |
|------|------|
| [`xiaohongshu`](./skills/xiaohongshu/) | 小红书内容创作与发布 |
| [`trip-planner`](./skills/trip-planner/) | 旅行行程规划 |
| [`weekly`](./skills/weekly/) | 整合 Git、Claude Code、Codex session 生成周报 |
| [`xiaohongshu-netfeel-guardian`](./skills/xiaohongshu-netfeel-guardian/) | 去除 Claude 中文内容的翻译腔，恢复母语网感 |

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

Spellbook 中的每个技能都遵循以下原则：

1. **硬性规则** - 使用 `FORBIDDEN` / `REQUIRED` 标记的强制约束
2. **实用示例** - 真实代码，而非纯理论
3. **验证清单** - 可操作的验证步骤
4. **实战检验** - 在生产环境中使用过

---

## 文档

| 文档 | 描述 |
|------|------|
| [更新日志](./CHANGELOG.md) | 发布历史与当前发布状态 |
| [安装指南](./docs/installation.md) | 详细的安装说明 |
| [Runtime 目标](./docs/runtime-targets.md) | Claude Code 与 Codex 安装目标 |
| [Showcase](./docs/showcase.md) | 可直接复制的工作流演示 |
| [Spellbook Operating Contract](./docs/spellbook-operating-contract.md) | 直接执行、升级确认、证据化反驳、反馈闭环与完成检查的 agent 行为规则 |
| [技能格式策略](./docs/skill-format-policy.md) | 目录型与单文件 skill 的格式规则 |
| [Skill Quality Playbook](./docs/skill-quality-playbook.md) | 触发描述、gotchas、渐进式披露与验证标准 |
| [技能测试指南](./docs/skill-testing-guide.md) | 如何验证技能是否生效 |
| [创建插件](./docs/creating-plugins.md) | 构建你自己的技能 |
| [产品生命周期（英文）](./docs/product-lifecycle-skills-en.md) | 完整生命周期覆盖 |
| [产品生命周期（中文）](./docs/product-lifecycle-skills-zh.md) | 产品生命周期覆盖 |

---

## 发布状态

Spellbook 目前处于 pre-1.0 发布准备阶段。尚未切出编号 GitHub release
tag；当前安装路径使用仓库 `main` 分支。发布历史见 [更新日志](./CHANGELOG.md)。

当前限制：

- Codex 目标只安装 skills；Claude Code agents 会在 Codex 目标下跳过。
- 部分 skills 依赖外部 CLI、账号、凭据或平台权限，这些不会由安装器打包提供。
- 注册表校验覆盖可安装 skill 结构，不等于每个外部工作流都已端到端验证。

支持入口：

- Bug：[提交 Issue](https://github.com/majiayu000/spellbook/issues/new/choose)
- Skill 想法：[提交功能请求](https://github.com/majiayu000/spellbook/issues/new/choose)
- 安全漏洞：遵循 [安全策略](./SECURITY.md)

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

- 发现 Bug？[提交 Issue](https://github.com/majiayu000/spellbook/issues)
- 有技能想法？[提交功能请求](https://github.com/majiayu000/spellbook/issues/new/choose)
- 想要贡献？[提交 PR](https://github.com/majiayu000/spellbook/pulls)

---

## 许可证

[MIT 许可证](./LICENSE) - 可在你的项目中自由使用。

---

<div align="center">
  <p>如果对你有帮助，考虑给个 ⭐</p>
  <p>为使用 Claude Code、Codex 与多智能体工作流的构建者打造</p>
</div>
