# 个人痛点 Skill 完整测试协议（Sandbox 风格）

本协议基于仓库现有的 `skill-creator` 成熟流程 + 三个子代理研究成果制定，目标是对以下两个 Skill 进行**科学、完整、可复现**的验证：

- `skill-ecosystem-doctor`（应对 PAIN-1001，并覆盖跨 Runtime Skill 治理）
- `xiaohongshu-netfeel-guardian`（应对 PAIN-301）

---

## 一、测试环境准备（推荐 Sandbox 方式）

1. 创建一个干净的测试 workspace（避免污染主环境）：
   ```bash
   mkdir -p ~/claude-skill-test-workspace
   cd ~/claude-skill-test-workspace
   ```

2. 把要测试的 Skill 复制进去（或用符号链接，推荐符号链接便于迭代）：
   ```bash
   mkdir -p .claude/skills
   ln -s /path/to/spellbook/skills/skill-ecosystem-doctor .claude/skills/
   ln -s /path/to/spellbook/skills/xiaohongshu-netfeel-guardian .claude/skills/
   ```

3. 准备 baseline（不加载新 Skill 的对比环境）：
   - 可以用另一个目录，或者在测试时通过 prompt 明确“不要使用 xxx skill”。

---

## 二、测试流程（严格遵循 skill-creator 闭环）

### 阶段 1：准备真实测试用例（已为你准备好）

两个 Skill 的 `evals/evals.json` 已经基于 PAIN 原文真实用户语言撰写，包含：
- 客观可验证类（lifecycle-doctor）
- 主观网感类（netfeel-guardian，使用人工盲测为主）

### 阶段 2：运行带 Skill vs 不带 Skill 的对比测试（Sandbox 推荐命令）

**推荐做法**：为每个 Skill 开一个干净的测试 workspace（真正 sandbox）。

**以 netfeel-guardian（优先测试它）为例**：

```bash
# 1. 新建干净 sandbox
mkdir -p ~/claude-skill-sandbox/netfeel-test-1
cd ~/claude-skill-sandbox/netfeel-test-1

# 2. 只链接要测试的这个 Skill（隔离）
mkdir -p .claude/skills
ln -s /absolute/path/to/your/spellbook/skills/xiaohongshu-netfeel-guardian .claude/skills/

# 3. 运行 evals（会同时生成 with-skill 和 baseline 对比）
python /absolute/path/to/your/spellbook/skills/skill-creator/scripts/run_eval.py \
  --skill-name xiaohongshu-netfeel-guardian \
  --eval-file /absolute/path/to/your/spellbook/skills/xiaohongshu-netfeel-guardian/evals/evals.json \
  --workspace ./evals-iteration-1
```

lifecycle-doctor 同理更换路径和名称。

**关键**：baseline 版本不要链接该 Skill 即可实现干净对比。

### 阶段 3：人类 Review（最重要）

使用官方推荐的 viewer：

```bash
python /path/to/spellbook/skills/skill-creator/eval-viewer/generate_review.py \
  ~/claude-skill-test-workspace/iteration-1 \
  --skill-name skill-ecosystem-doctor \
  --benchmark ~/claude-skill-test-workspace/iteration-1/benchmark.json
```

对于主观网感类 Skill（xiaohongshu-netfeel-guardian），**强烈建议**：
- 使用 blind comparator（两个子代理分别生成带/不带守护的版本）
- 找 3-5 个真实内容创作者做盲测打分（网感、真实度、可直接发帖率）
- 记录 feedback.json

### 阶段 4：迭代优化

根据人类反馈 + 客观指标进行迭代：
- 调整 description（用 run_loop 做 description optimization）
- 强化中文网感守护协议模块
- 增加更多真实高赞语料到 references/
- 优化健康报告格式和行动建议

### 阶段 5：真实世界验证（最终验证）

- 找 3-5 个真实长期个人用户（或内容创作者）在他们自己的环境中试用 1-2 周
- 收集真实反馈（“这个技能救了我”“还是有问题”“太好用了”）
- 记录前后对比（尤其是内容创作者的实际发帖数据变化）

---

## 三、推荐的测试重点（来自 3 个子代理研究）

### 对 `skill-ecosystem-doctor` 的测试重点
- 能否准确发现“1-2 年前的技能”类问题（召回率）
- 报告是否 actionable（用户看完能不能马上知道怎么修）
- 是否对用户现有 CLAUDE.md / 自定义配置零干扰（安全）
- 是否能和 codex-retrospective 良好协同

### 对 `xiaohongshu-netfeel-guardian` 的测试重点
- 中文 CoT 强制是否有效（通过盲测 + 人工复盘）
- 是否明显减少“翻译腔”和西方框架（前后对比）
- 是否保留了用户原本想表达的核心内容（不越界）
- 与 xiaohongshu 技能组合后的端到端效果

---

## 四、科学评估标准建议

**客观类 Skill**（lifecycle-doctor）：
- 检测召回率 ≥ 80%
- 建议可执行率（用户实际采纳比例）

**主观类 Skill**（netfeel-guardian）：
- 人工盲测胜率（有守护 vs 无守护）
- 真实发帖“可直接发布率”提升
- 创作者主观满意度（1-10 分）

---

需要我现在帮你把两个 Skill 的目录结构补全（加上更完整的 references/、测试用的真实语料片段、或者直接生成更详细的 evals 断言），还是你想先自己用上面这个协议跑一轮测试？

我已经把两个核心 SKILL.md 按三份研究报告的最优实践写好了，可以直接拿去测试。
