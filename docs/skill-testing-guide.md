# Skill 测试指南

本文档用于测试 Claude Code skill 是否有效。以 `typescript-project` skill 为例。

---

## 安装说明

### 方式一：复制到 Claude Code 配置目录

```bash
# macOS/Linux
cp -r skills/typescript-project ~/.claude/skills/

# 或使用符号链接
ln -s $(pwd)/skills/typescript-project ~/.claude/skills/typescript-project
```

### 方式二：在项目中使用

```bash
# 在你的项目根目录创建 .claude/skills 目录
mkdir -p .claude/skills
cp -r /path/to/spellbook/skills/typescript-project .claude/skills/
```

---

## 测试场景

### 测试 1: 项目初始化

**Prompt:**
```
创建一个新的 TypeScript 项目，用于用户管理 API
```

**预期行为 (带 skill):**
- [ ] 使用 Bun 或 Node 22+ 初始化
- [ ] 配置 ESM modules (`"type": "module"`)
- [ ] 安装 Zod 用于验证
- [ ] 使用 Biome 作为 linter
- [ ] 创建 lib/services/adapters 三层结构
- [ ] tsconfig.json 启用 strict mode
- [ ] 依赖版本使用 "latest"

**未使用 skill 可能的行为:**
- 使用 CommonJS 模块
- 使用 ESLint + Prettier (而非 Biome)
- 固定版本号
- 没有分层架构

**验证命令:**
```bash
# 检查 package.json
cat package.json | grep '"type": "module"'
cat package.json | grep '"zod"'
cat package.json | grep '"@biomejs/biome"'

# 检查目录结构
ls -la src/lib src/services src/adapters

# 检查 tsconfig.json
cat tsconfig.json | grep '"strict": true'
```

---

### 测试 2: 代码风格 - No Backwards Compatibility

**Prompt:**
```
我有一个函数 getUserName，现在想改名为 getUsername，帮我重构
```

**预期行为 (带 skill):**
- [ ] 直接重命名，不保留旧名称
- [ ] 不添加 `@deprecated` 注释
- [ ] 不创建别名 `export { getUsername as getUserName }`
- [ ] 一次性更新所有引用

**错误行为 (违反 skill 原则):**
```typescript
// ❌ 保留旧导出 "为了兼容"
export { getUsername as getUserName };

// ❌ 添加废弃警告
/** @deprecated Use getUsername instead */
export function getUserName() { ... }
```

---

### 测试 3: LLM 集成

**Prompt:**
```
添加一个调用 OpenAI API 的功能，实现文本摘要
```

**预期行为 (带 skill):**
- [ ] 使用 LiteLLM proxy 而非直接调用 OpenAI
- [ ] 配置使用 `LITELLM_URL` 环境变量
- [ ] 使用 OpenAI SDK 连接到 LiteLLM proxy
- [ ] 模型名称可配置

**正确代码示例:**
```typescript
import { OpenAI } from 'openai';

const llm = new OpenAI({
  baseURL: process.env.LITELLM_URL || 'http://localhost:4000',
  apiKey: process.env.LITELLM_API_KEY || 'sk-1234',
});
```

**错误行为:**
```typescript
// ❌ 直接使用 OpenAI
import OpenAI from 'openai';
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

// ❌ 或者直接使用 Anthropic SDK
import Anthropic from '@anthropic-ai/sdk';
```

---

### 测试 4: 验证和错误处理

**Prompt:**
```
创建一个用户注册的 API endpoint，包含输入验证
```

**预期行为 (带 skill):**
- [ ] 使用 Zod schema 定义输入
- [ ] 从 schema 推断 TypeScript 类型 (`z.infer`)
- [ ] 创建自定义 AppError 类
- [ ] 使用 Result 类型或抛出错误

**正确代码示例:**
```typescript
import { z } from 'zod';

const CreateUserSchema = z.object({
  email: z.string().email(),
  name: z.string().min(2),
});

type CreateUserInput = z.infer<typeof CreateUserSchema>;
```

---

### 测试 5: 架构分层

**Prompt:**
```
实现一个订单服务，包含创建订单、查询订单功能
```

**预期行为 (带 skill):**
- [ ] 业务逻辑放在 `services/order.service.ts`
- [ ] 数据库操作放在 `adapters/order.repository.ts`
- [ ] Service 通过构造函数注入 Repository
- [ ] 定义 Repository 接口，方便测试

**正确结构:**
```
src/
├── services/
│   └── order.service.ts    # 业务逻辑
├── adapters/
│   ├── postgres.order.repository.ts  # 生产实现
│   └── in-memory.order.repository.ts # 测试实现
└── lib/
    └── types.ts            # Order 接口定义
```

---

### 测试 6: 测试代码

**Prompt:**
```
为 UserService 编写单元测试
```

**预期行为 (带 skill):**
- [ ] 使用 Bun test 或 Vitest
- [ ] 使用 in-memory repository 而非 mock
- [ ] 测试真实行为，不过度 mock
- [ ] 使用 beforeEach 重置状态

**正确示例:**
```typescript
import { describe, it, expect, beforeEach } from 'bun:test';

describe('UserService', () => {
  let service: UserService;
  let repo: InMemoryUserRepository;

  beforeEach(() => {
    repo = new InMemoryUserRepository();
    service = new UserService(repo);
  });

  it('creates user', async () => {
    const user = await service.create({ email: 'test@test.com', name: 'Test' });
    expect(user.email).toBe('test@test.com');
  });
});
```

---

## 评分标准

| 测试场景 | 权重 | 通过标准 |
|---------|------|---------|
| 项目初始化 | 20% | 5/7 项符合 |
| No Backwards Compatibility | 20% | 不创建任何兼容层 |
| LiteLLM 集成 | 15% | 使用 LiteLLM proxy |
| Zod 验证 | 15% | 使用 Zod + 类型推断 |
| 架构分层 | 15% | 正确分离 services/adapters |
| 测试代码 | 15% | 使用真实实现而非 mock |

**总分解读:**
- 90-100%: Skill 完全生效
- 70-89%: Skill 部分生效，需检查配置
- 50-69%: Skill 可能未正确加载
- <50%: Skill 未生效

---

## 对比测试方法

### A/B 测试流程

1. **准备两个 Claude Code 环境:**
   - 环境 A: 不安装 skill
   - 环境 B: 安装 typescript-project skill

2. **使用相同 prompt 测试:**
   ```
   创建一个 TypeScript 项目，实现一个简单的 TODO API，
   包含添加、删除、列表功能，需要数据验证和错误处理
   ```

3. **对比生成的代码:**
   - 项目结构差异
   - 依赖选择差异
   - 代码风格差异
   - 测试方法差异

---

## 快速验证 Checklist

```markdown
## Skill 生效检查表

### 项目结构
- [ ] 存在 src/lib/ 目录
- [ ] 存在 src/services/ 目录
- [ ] 存在 src/adapters/ 目录
- [ ] package.json 有 "type": "module"

### 依赖
- [ ] 使用 zod 进行验证
- [ ] 使用 @biomejs/biome 作为 linter
- [ ] 依赖版本为 "latest" 而非固定版本

### 代码风格
- [ ] tsconfig.json 启用 strict mode
- [ ] 没有使用 any 类型
- [ ] 没有 @deprecated 注释
- [ ] 没有 backwards compatibility 别名导出

### LLM 集成 (如果有)
- [ ] 使用 LiteLLM proxy
- [ ] 配置通过环境变量

### 测试
- [ ] 使用 bun:test 或 vitest
- [ ] 使用 in-memory 实现而非 mock
```

---

## 常见问题

### Q: Skill 文件放在哪里？

```bash
# 全局 (所有项目生效)
~/.claude/skills/typescript-project/

# 项目级 (仅当前项目)
./.claude/skills/typescript-project/
```

### Q: 如何确认 Skill 已加载？

在 Claude Code 中输入:
```
/skills
```
应该看到 `typescript-project` 在列表中。

### Q: Skill 没有生效怎么办？

1. 确认 SKILL.md 存在且有正确的 frontmatter
2. 重启 Claude Code
3. 检查文件权限
4. 查看 Claude Code 日志
