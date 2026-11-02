#!/usr/bin/env python3
"""Regenerate references/samples.md from references/catalog.json plus the test hooks below."""
import json, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
cat = json.loads((root / 'references/catalog.json').read_text())
HOOKS = {
 '01': ['`button[data-part=shell]`：唯一的按钮外壳，三种状态都是它', '`[role=status]`：读出“加载中 / 已完成”等状态'],
 '02': ['`[role=tablist]`、3 个 `[role=tab]`、`[role=tabpanel]`', '`[data-part=indicator]`：黑色胶囊，左右边缘就是它的 left/right'],
 '03': ['`[role=slider]`：接收指针的命中区，带 aria-valuenow/min/max', '`[data-part=track]`：轨道（逻辑 0–100 对应它的宽度）', '`[data-part=fill]`：已填充部分，右边缘＝视觉位置，越界时可以超出轨道', '`[data-part=value]`：数字文本'],
 '04': ['`button[role=switch]`', '`[data-part=knob]`：旋钮，左右边缘就是它的 left/right', '`[data-part=state]`：On / Off 文本'],
 '05': ['`[data-part=card]`：卡片外壳，高度变化发生在它身上', '`button[aria-expanded][aria-controls]`：展开按钮，aria-controls 指向详情区的 id'],
 '06': ['`button[data-part=add]`：新增通知', '`[data-part=toast]`：每条通知；内含 `button[data-part=close]`', '`[data-part=live][aria-live=polite]`：独立的宣告区'],
 '07': ['`button[data-part=trigger]`：Open commands', '`[role=dialog]` 内含 `input[role=combobox]`、`[role=listbox]`、`[role=option]`', '`[data-part=result]`：执行结果文本'],
 '08': ['3 个 `[data-part=row]`，每行含 `[data-part=grip]`、`button[data-part=up]`、`button[data-part=down]`', '`[data-part=live]`：宣告新顺序', '松手或点按钮后，行在 DOM 里的顺序就是新顺序'],
 '09': ['`[data-part=stage]`：预览区，提示不能出它的边界', '3 个 `[data-part=swatch]`，带 `data-name`（颜色名）和 `data-value`（色值）', '`[role=tooltip]`：唯一的提示层'],
 '10': ['`[data-part=card]`：图表卡片，提示不能出它的边界', '`[data-part=chart]`：可聚焦的绘图区，也接收指针', '`path[data-part=line]`：折线', '`table`：7 行 `tbody tr`，第一格日期、第二格数值', '`[role=tooltip]`：提示', '`button[data-part=replay]`'],
}
NOTES = {
 '01': ['状态文本示例：Ready / Exporting… / Done，失败时 Failed · Retry。演示可加一个触发失败的方式', '减少动态效果时转圈可停住，只保留状态文字'],
 '02': ['Space/Enter 也可激活标签；tab 用 aria-controls 指向面板'],
 '03': ['逻辑值取整；合法范围内松手吸附到取整值对应的位置；两端越界对称处理'],
 '04': ['参考尺寸：轨道 72×44（也是触控目标），旋钮 34px，左右各留 5px'],
 '05': ['展开时外壳先走，内容约 140ms 后淡入；高度目标取 max(278, 内容实测高度)，长文字不被截断'],
 '06': ['第 4 条到来时移除最旧的一条（不是隐藏）', '关闭也要在 live region 宣告，比如“已关闭，剩余 2 条”', '后层正文与按钮用 visibility:hidden + inert + aria-hidden'],
 '07': ['用原生 dialog + showModal；退出时先加关闭类跑 140ms 过渡，再调用 close()；拦截 cancel 事件让 Escape 也走带动画的关闭'],
 '08': ['参考：行高 64、行距 74；拖动位置夹在列表范围内（上下各留约 15px）', '拖动中只改逻辑顺序和其他行的位置，松手时再重排 DOM（拖动中移动节点会丢 pointer capture），之后恢复焦点', '拖柄 aria-hidden，键盘走上移/下移按钮'],
 '09': ['只有键盘聚焦（:focus-visible）才把提示固定在色块旁；鼠标点击按钮也会触发 focus，此时保持跟随', '提示先尝试右下，放不下时水平或垂直翻转，最后夹紧；键盘聚焦时放在色块下方，放不下放上方'],
 '10': ['数据表可以只给读屏器（视觉隐藏），单元格放原始整数；提示显示千分位', '空态：数据为空时显示 No data yet，不画折线（验收脚本暂未覆盖）', '笔画不缩放：path 加 vector-effect: non-scaling-stroke'],
}
out = ['# FORM 10 个样例\n', '每节可单独复制。**提示词**是原文，**可改项**交给使用者替换，**验收**是完成标准，**测试钩子**是 `scripts/verify.mjs` 定位元素用的，复现或接入后都保留它们。\n',
       '所有样例共享视觉方向：' + cat['shared_direction'] + '\n']
for s in cat['samples']:
    out += [f"\n## {s['id']} · {s['name']}（{s['english']}）\n",
            f"- 用户可能会说：{s['phrase']}", f"- 适用：{s['use_when']}", f"- 试玩：{s['gesture']}", f"- 参考实现：`assets/reference.html` 里的 `{s['implementation']}`，`reference.html?sample={s['id']}` 直接打开\n",
            '**提示词**\n', '> ' + s['prompt'] + '\n',
            '**可改项**：' + '、'.join(s['editable']) + '\n', '**验收**\n'] + [f"- {a}" for a in s['acceptance']] + ([''] + ['**补充说明**（盲测时发现提示词没写清的地方）\n'] + [f"- {n}" for n in NOTES.get(s['id'], [])] if NOTES.get(s['id']) else []) + ['', '**测试钩子**（根元素 `[data-form="%s"]`）\n' % s['id']] + [f"- {h}" for h in HOOKS[s['id']]]
(root / 'references/samples.md').write_text('\n'.join(out) + '\n')
print('wrote', root / 'references/samples.md')
