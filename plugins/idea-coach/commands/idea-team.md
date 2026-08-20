---
description: 想法群聊室 — 多角色 AI 团队（调研员/反方/类比者）帮你查漏补缺，不打分不否决
argument-hint: <想法> | resume [slug] | list
---

按本插件的 `idea-team` skill 主持想法群聊。

- 用户输入：$ARGUMENTS
- 参数为空时，先问用户要一句话想法，不要自己编
- 进入群聊前必须依次 Read 三个角色 skill（idea-research / idea-devils-advocate / idea-analogist）加载 voice 边界
- 每回合在一次 assistant response 内按顺序输出 3 个独立角色 block；每个 block 后持久化发言与 speaker 状态，再邀请用户插话
