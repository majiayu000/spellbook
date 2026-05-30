# vscode-doctor 评估计划

## 目标
验证 skill 是否能在真实卡顿场景中：
1. 正确把 macOS 26 Tahoe bug 识别为最高优先级（最常见 2026 年痛点）
2. 优先推荐仓库内已有的 `scripts/collect_vscode_diagnostics.sh` 而不是自己硬写一堆命令
3. 输出结构清晰、可直接复制执行的修复命令
4. 正确区分 Cursor 和 VS Code 路径
5. 安全：绝不擅自修改用户文件
6. 给出用户可选处理方案，并用保守区间说明预期降低多少 watcher / CPU / RSS 压力

## 当前测试用例（7 个）

| ID | 场景 | 核心验证点 |
|----|------|-----------|
| 1 | macOS 26 Tahoe 典型卡顿 | Tahoe bug 必须排第一 + 给出两个关键命令 |
| 2 | 大 monorepo 文件监听 | 必须指出 watcherExclude 缺失并给出完整推荐配置 |
| 3 | 多 AI 扩展冲突 | 识别 Copilot + Continue + Cursor 内置同时存在 |
| 4 | 非 Tahoe 打字延迟 | 推荐硬件加速关闭 + Extension Bisect 流程 |
| 5 | 同时使用 Cursor + VSCode | 两个编辑器都要覆盖 |
| 6 | 用户说“全都做” | 必须输出分阶段批处理方案，禁止无备份覆盖配置 |
| 7 | 用户坚持打开大父目录 | 必须提供“大目录轻量导航窗口”方案 + 前后对比验证模板 |

## 后续迭代方向（等用户反馈后）

- 是否需要增加 Windows / Linux 测试用例？
- 日志分析能力是否足够（当前主要靠脚本里的 rg）？
- 是否要支持一键生成推荐的 `.vscode/settings.json` 片段文件（当前只给内容）？
- 是否要检测特定重扩展的已知坏配置（如 GitLens 在 >10k 文件仓库）？

## 运行方式（推荐）

使用 skill-creator 脚本：

```bash
# 在 claude-arsenal 根目录
python -m skills.skill-creator.scripts.run_eval \
  --skill-path skills/vscode-doctor \
  --eval-set skills/vscode-doctor/evals/evals.json \
  --iterations 2
```

或者手动让 Claude/Grok 带上这个 skill 去回答 evals.json 里的 prompt，然后人工或用 grader 打分。

## 评分维度（建议）

- 根因排序准确性（Tahoe 是否 #1）
- 是否复用了仓库内 collector 脚本
- 修复命令是否安全且可复制
- 中文报告是否清晰易懂
- 是否区分了 VSCode 和 Cursor
- 是否提供「选项 / 预估收益 / 代价 / 验证指标 / 回滚」表格
- 收益百分比是否基于采集证据且使用保守区间，而不是承诺精确提速
- 用户要求全做时，是否按风险分阶段输出，并避免 `cat > settings.json` / `cat > argv.json` 这种无备份覆盖命令
- 用户坚持打开大父目录时，是否提供保留大目录的轻量导航窗口方案，而不是只建议“别打开”
- 是否强制使用真实 opened workspace 路径作为 collector 参数，避免误扫 skill 当前目录
- 修复后是否输出 before/after 对比表，缺少 baseline 时是否明确说明无法量化

最后更新：2026-05-30
